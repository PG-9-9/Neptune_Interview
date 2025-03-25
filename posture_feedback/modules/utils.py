import cv2
import math
import json
import os
from datetime import datetime


def get_landmark_coordinates(image, landmarks, index):
    h, w, _ = image.shape
    landmark = landmarks.landmark[index]
    return int(landmark.x * w), int(landmark.y * h)

def calculate_angle(a, b, c):

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    # Dot product and magnitude
    dot_product = ba[0]*bc[0] + ba[1]*bc[1]
    magnitude = math.hypot(*ba) * math.hypot(*bc) + 1e-6  # prevent division by 0

    # Clamp cosine to avoid math domain error
    cosine_angle = max(-1.0, min(1.0, dot_product / magnitude))
    angle = math.degrees(math.acos(cosine_angle))
    return angle

def draw_right_arm(image, landmarks, elbow_above_shoulder=False, annotate=False):
    h, w, _ = image.shape

    def get_coords(index):
        lm = landmarks.landmark[index]
        return int(lm.x * w), int(lm.y * h)

    shoulder = get_coords(12)
    elbow = get_coords(14)
    wrist = get_coords(16)

    # Draw bones
    cv2.line(image, shoulder, elbow, (255, 255, 255), 2)
    cv2.line(image, elbow, wrist, (255, 255, 255), 2)

    # Draw joints
    cv2.circle(image, shoulder, 6, (255, 255, 0), -1)  # Cyan
    elbow_color = (0, 0, 255) if elbow_above_shoulder else (0, 255, 0)
    cv2.circle(image, elbow, 8, elbow_color, -1)
    cv2.circle(image, wrist, 6, (255, 255, 0), -1)  # Cyan

    # Optional annotation
    if annotate:
        text = "Arm Raised" if elbow_above_shoulder else "Arm OK"
        color = (0, 0, 255) if elbow_above_shoulder else (0, 255, 0)
        cv2.putText(image, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    return image

def draw_status_bar(image, active=True, color=(0, 255, 0)):
    h, w, _ = image.shape
    thickness = 20
    bar_width = int(w * 0.4)

    if active:
        cv2.rectangle(image, (10, h - 30), (10 + bar_width, h - 10), color, -1)
    else:
        cv2.rectangle(image, (10, h - 30), (10 + bar_width, h - 10), (100, 100, 100), -1)


def draw_wrist_trajectory(image, trajectory):

    if len(trajectory) >= 2:
        for i in range(1, len(trajectory)):
            pt1 = trajectory[i - 1]
            pt2 = trajectory[i]
            cv2.line(image, pt1, pt2, (200, 200, 255), 2)
    return image

import json
import os

def export_pose_to_json(landmarks, frame_id, output_dir="pose_snapshots"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    keypoints = []
    for lm in landmarks.landmark:
        keypoints.append({
            "x": lm.x,
            "y": lm.y,
            "z": lm.z,
            "visibility": lm.visibility
        })

    json_data = {
        "frame_id": frame_id,
        "keypoints": keypoints
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"pose_{timestamp}.json")

    with open(filepath, "w") as f:
        json.dump(json_data, f, indent=4)

    print(f"Pose snapshot saved to: {filepath}")
