import cv2


def get_landmark_coordinates(image, landmarks, index):
    h, w, _ = image.shape
    landmark = landmarks.landmark[index]
    return int(landmark.x * w), int(landmark.y * h)

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
