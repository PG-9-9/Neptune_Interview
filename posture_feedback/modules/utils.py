import cv2
import math
import json
import os
from datetime import datetime

def get_landmark_coordinates(image, landmarks, index):
    """
    Extracts the pixel coordinates of a specified landmark index.

    Args:
        image (np.ndarray): The frame/image containing the pose.
        landmarks: MediaPipe landmark object containing normalized coordinates.
        index (int): The landmark index to extract (e.g., 12 for shoulder).

    Returns:
        tuple: (x, y) pixel coordinates of the landmark on the image.
    """
    h, w, _ = image.shape
    landmark = landmarks.landmark[index]
    return int(landmark.x * w), int(landmark.y * h)


def calculate_angle(a, b, c):
    """
    Calculates the angle at point b given three 2D points a, b, and c.

    Args:
        a (tuple): Coordinates of the first point (e.g., shoulder).
        b (tuple): Coordinates of the middle point (e.g., elbow).
        c (tuple): Coordinates of the third point (e.g., wrist).

    Returns:
        float: Angle in degrees between the three points at b.
    """
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    dot_product = ba[0]*bc[0] + ba[1]*bc[1]
    magnitude = math.hypot(*ba) * math.hypot(*bc) + 1e-6  # Avoid division by zero

    cosine_angle = max(-1.0, min(1.0, dot_product / magnitude))  # Clamp to [-1, 1] 
    angle = math.degrees(math.acos(cosine_angle))
    return angle


def draw_right_arm(image, landmarks, elbow_above_shoulder=False, annotate=False):
    """
    Draws the right arm bones and joints and optionally annotates posture status.

    Args:
        image (np.ndarray): Image frame to draw on.
        landmarks: MediaPipe landmark object.
        elbow_above_shoulder (bool): Whether the elbow is higher than the shoulder.
        annotate (bool): Whether to add text annotation ("Raised Arm", etc.).

    Returns:
        np.ndarray: Image with arm overlay.
    """
    h, w, _ = image.shape

    def get_coords(index):
        lm = landmarks.landmark[index]
        return int(lm.x * w), int(lm.y * h)

    shoulder = get_coords(12)
    elbow = get_coords(14)
    wrist = get_coords(16)

    # Draw arm bones
    cv2.line(image, shoulder, elbow, (255, 255, 255), 2)
    cv2.line(image, elbow, wrist, (255, 255, 255), 2)

    # Draw joints
    cv2.circle(image, shoulder, 6, (255, 255, 0), -1)  # Cyan
    elbow_color = (0, 0, 255) if elbow_above_shoulder else (0, 255, 0)
    cv2.circle(image, elbow, 8, elbow_color, -1)
    cv2.circle(image, wrist, 6, (255, 255, 0), -1)  # Cyan

    if annotate:
        text = "Raised Arm" if elbow_above_shoulder else "Standard Arm"
        color = (0, 0, 255) if elbow_above_shoulder else (0, 255, 0)
        cv2.putText(image, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    return image


def draw_status_bar(image, active=True, color=(0, 255, 0)):
    """
    Draws a simple status bar indicating active/inactive posture condition.

    Args:
        image (np.ndarray): Frame to draw on.
        active (bool): Whether the status is active.
        color (tuple): RGB color of the active bar.
    """
    h, w, _ = image.shape
    thickness = 20
    bar_width = int(w * 0.4)

    if active:
        cv2.rectangle(image, (10, h - 30), (10 + bar_width, h - 10), color, -1)
    else:
        cv2.rectangle(image, (10, h - 30), (10 + bar_width, h - 10), (100, 100, 100), -1)


def draw_wrist_trajectory(image, trajectory):
    """
    Draws the trajectory path of the wrist over time.

    Args:
        image (np.ndarray): Frame to draw on.
        trajectory (deque): History of wrist positions.

    Returns:
        np.ndarray: Frame with wrist path overlay.
    """
    if len(trajectory) >= 2:
        for i in range(1, len(trajectory)):
            pt1 = trajectory[i - 1]
            pt2 = trajectory[i]
            cv2.line(image, pt1, pt2, (200, 200, 255), 2)
    return image


def export_pose_to_json(landmarks, frame_id, output_dir="pose_snapshots"):
    """
    Exports landmark coordinates to a JSON file.

    Args:
        landmarks: MediaPipe landmark list.
        frame_id (int): Frame number (used as metadata).
        output_dir (str): Directory where JSON will be saved.

    Saves:
        A timestamped JSON file in the `pose_snapshots` directory containing
        normalized x, y, z, and visibility for each landmark.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    keypoints = [{
        "x": lm.x,
        "y": lm.y,
        "z": lm.z,
        "visibility": lm.visibility
    } for lm in landmarks.landmark]

    json_data = {
        "frame_id": frame_id,
        "keypoints": keypoints
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"pose_{timestamp}.json")

    with open(filepath, "w") as f:
        json.dump(json_data, f, indent=4)

    print(f"Pose snapshot saved to: {filepath}")
