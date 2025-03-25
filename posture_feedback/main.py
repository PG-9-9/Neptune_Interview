import cv2
import time
import math
import json
import os
from collections import deque
from datetime import datetime
from modules.pose_detector import PoseDetector
from modules.utils import (
    get_landmark_coordinates,
    calculate_angle,
    draw_right_arm,
    draw_status_bar,
    draw_wrist_trajectory,
    export_pose_to_json
)

def main():
    detector = PoseDetector()
    cap = cv2.VideoCapture(0)
    prev_time = 0

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Buffers and history
    status_buffer = deque(maxlen=5)
    elbow_position_history = deque(maxlen=10)
    wrist_trajectory = deque(maxlen=50)
    right_shoulder_heights = deque(maxlen=10)

    # Combo score
    combo_score = 0
    last_correct_time = None
    combo_threshold_seconds = 2

    # Frame skip setup
    skip_counter = 0
    skip_interval = 1
    results = None

    # Reference posture
    reference_elbow_angle = 150
    elbow_angle_threshold = 15
    shoulder_baseline = None

    frame_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            break
        shoulder_lift = 0  # Default in case we don't calculate it this frame

        frame_count += 1

        # Adaptive frame skipping
        if skip_counter % skip_interval == 0:
            results = detector.detect_pose(frame)

        skip_counter += 1

        if results and results.pose_landmarks:
            shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)
            elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)
            wrist = get_landmark_coordinates(frame, results.pose_landmarks, 16)

            # Posture logic
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            deviation = abs(elbow_angle - reference_elbow_angle)
            posture_correct = deviation <= elbow_angle_threshold

            if posture_correct:
                posture_status = f"Reference Posture ({int(elbow_angle)}°)"
                posture_color = (0, 255, 0)
            else:
                posture_status = f"Deviated Posture ({int(elbow_angle)}°)"
                posture_color = (0, 0, 255)

            cv2.putText(frame, posture_status, (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, posture_color, 2)

            # Elbow raise logic
            elbow_visibly_above = elbow[1] < shoulder[1]
            elbow_bent_upward = elbow_angle < 90
            elbow_raised = elbow_visibly_above or elbow_bent_upward
            status_buffer.append(elbow_raised)
            smoothed_status = sum(status_buffer) > len(status_buffer) // 2

            frame = draw_right_arm(
                frame,
                results.pose_landmarks,
                elbow_above_shoulder=smoothed_status,
                annotate=True
            )
            draw_status_bar(frame, active=smoothed_status, color=(0, 0, 255) if smoothed_status else (0, 255, 0))

            # Wrist trajectory visualization
            wrist_trajectory.append(wrist)
            frame = draw_wrist_trajectory(frame, wrist_trajectory)

            # Shoulder elevation smoothing
            right_shoulder_heights.append(shoulder[1])
            if len(right_shoulder_heights) == right_shoulder_heights.maxlen:
                avg_shoulder_height = sum(right_shoulder_heights) / len(right_shoulder_heights)
                if shoulder_baseline is None:
                    shoulder_baseline = avg_shoulder_height

                shoulder_lift = shoulder_baseline - avg_shoulder_height
                if shoulder_lift > 15:
                    shoulder_status = "Shoulder Elevated"
                    shoulder_color = (0, 0, 255)
                    skip_interval = 1
                else:
                    shoulder_status = "Shoulder Normal"
                    shoulder_color = (0, 255, 0)
                    skip_interval = 2

                cv2.putText(frame, shoulder_status, (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, shoulder_color, 2)

            # Combo tracker
            if posture_correct and smoothed_status and shoulder_lift <= 15:
                if last_correct_time is None:
                    last_correct_time = time.time()
                    combo_score = 0
                else:
                    time_diff = time.time() - last_correct_time
                    if time_diff > combo_threshold_seconds:
                        combo_score += 1
                        last_correct_time = time.time()
            else:
                last_correct_time = None
                combo_score = 0

            cv2.putText(frame, f"Combo: {combo_score}", (20, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 215, 0), 2)

            # Real-time feedback hint
            if not posture_correct:
                hint = "Try extending your bowing arm more"
            elif shoulder_lift > 15:
                hint = "Lower your shoulder slightly"
            elif not smoothed_status:
                hint = "Keep bowing arm stable"
            else:
                hint = "Great posture!"

            cv2.putText(frame, f"Hint: {hint}", (20, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # FPS counter
        curr_time = time.time()
        elapsed = curr_time - prev_time
        prev_time = curr_time
        fps_display = int(1 / (elapsed + 1e-6))
        cv2.putText(frame, f"FPS: {fps_display}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        # Display
        cv2.imshow('Posture Feedback', frame)

        # Press 's' to save current pose as JSON snapshot
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and results:
            export_pose_to_json(results.pose_landmarks, frame_count)

        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Webcam released. Program terminated cleanly.")

if __name__ == "__main__":
    main()
