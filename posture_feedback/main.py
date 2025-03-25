# main.py

import cv2
from modules.pose_detector import PoseDetector
from modules.utils import get_landmark_coordinates, draw_right_arm
from collections import deque


def main():
    detector = PoseDetector()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    # Smooth output using a 5-frame buffer
    status_buffer = deque(maxlen=5)
    while True:
        success, frame = cap.read()
        if not success:
            break

        results = detector.detect_pose(frame)

        if results.pose_landmarks:
            # Get points
            right_shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)
            right_elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)

            # Determine if elbow is above shoulder
            elbow_above = right_elbow[1] < right_shoulder[1]

            # Update buffer and smooth result
            status_buffer.append(elbow_above)
            smoothed_status = sum(status_buffer) > len(status_buffer) // 2

            # Draw right arm with smoothed status and annotation
            frame = draw_right_arm(
                frame,
                results.pose_landmarks,
                elbow_above_shoulder=smoothed_status,
                annotate=True
            )
        cv2.imshow('Posture Feedback', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
