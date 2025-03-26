import cv2
import time
import math
import json
import os
import csv
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

def create_logger(tag="baseline"):
    log_dir = "metrics"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{tag}_log_{timestamp}.csv")
    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "frame", "elbow_y", "shoulder_y", "angle", "reference_angle", "deviation",
            "smoothed_status", "fps", "hint", "phase"
        ])
    return log_file

def append_log(log_file, data):
    with open(log_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)

def run_model(tag, use_angle=False, use_smoothing=False, use_shoulder=False, use_feedback=True):
    detector = PoseDetector()
    cap = cv2.VideoCapture(0)
    prev_time = 0
    log_file = create_logger(tag)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    status_buffer = deque(maxlen=5)
    wrist_trajectory = deque(maxlen=50)
    right_shoulder_heights = deque(maxlen=10)

    reference_elbow_angle = 150
    elbow_angle_threshold = 15
    shoulder_baseline = None
    frame_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            break
        shoulder_lift = 0
        frame_count += 1

        results = detector.detect_pose(frame)

        if results and results.pose_landmarks:
            shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)
            elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)
            wrist = get_landmark_coordinates(frame, results.pose_landmarks, 16)

            elbow_angle = calculate_angle(shoulder, elbow, wrist) if use_angle else 0
            deviation = abs(elbow_angle - reference_elbow_angle) if use_angle else 0
            posture_correct = deviation <= elbow_angle_threshold if use_angle else True

            elbow_visibly_above = elbow[1] < shoulder[1]
            elbow_bent_upward = elbow_angle < 90 if use_angle else False
            elbow_raised = elbow_visibly_above or elbow_bent_upward

            if use_smoothing:
                status_buffer.append(elbow_raised)
                smoothed_status = sum(status_buffer) > len(status_buffer) // 2
            else:
                smoothed_status = elbow_raised

            frame = draw_right_arm(
                frame,
                results.pose_landmarks,
                elbow_above_shoulder=smoothed_status,
                annotate=True
            )

            draw_status_bar(frame, active=smoothed_status, color=(0, 0, 255) if smoothed_status else (0, 255, 0))
            wrist_trajectory.append(wrist)
            frame = draw_wrist_trajectory(frame, wrist_trajectory)

            if use_shoulder:
                right_shoulder_heights.append(shoulder[1])
                if len(right_shoulder_heights) == right_shoulder_heights.maxlen:
                    avg_shoulder_height = sum(right_shoulder_heights) / len(right_shoulder_heights)
                    if shoulder_baseline is None:
                        shoulder_baseline = avg_shoulder_height

                    shoulder_lift = shoulder_baseline - avg_shoulder_height
                    shoulder_status = "Shoulder Elevated" if shoulder_lift > 15 else "Shoulder Normal"
                    shoulder_color = (0, 0, 255) if shoulder_lift > 15 else (0, 255, 0)
                    cv2.putText(frame, shoulder_status, (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, shoulder_color, 2)

            hint = ""
            if use_feedback:
                if not posture_correct:
                    hint = "Try extending your bowing arm more"
                elif use_shoulder and shoulder_lift > 15:
                    hint = "Lower your shoulder slightly"
                elif not smoothed_status:
                    hint = "Keep bowing arm stable"
                else:
                    hint = "Great posture!"
                cv2.putText(frame, f"Hint: {hint}", (20, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            curr_time = time.time()
            elapsed = curr_time - prev_time
            prev_time = curr_time
            fps_display = int(1 / (elapsed + 1e-6))
            cv2.putText(frame, f"FPS: {fps_display}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

            append_log(log_file, [
                frame_count, elbow[1], shoulder[1], round(elbow_angle, 2), reference_elbow_angle,
                round(deviation, 2), smoothed_status, fps_display, hint, tag
            ])

        cv2.imshow(f'Posture Feedback - {tag}', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Webcam released. Model run ended.")

def main():
    # Run one at a time to record different log files
    # run_model("baseline", use_angle=False, use_smoothing=False, use_shoulder=False, use_feedback=False)
    # run_model("angle_logic", use_angle=True, use_smoothing=False, use_shoulder=False, use_feedback=False)
    # run_model("smoothing", use_angle=True, use_smoothing=True, use_shoulder=False, use_feedback=False)
    # run_model("shoulder_logic", use_angle=True, use_smoothing=True, use_shoulder=True, use_feedback=False)
    run_model("final", use_angle=True, use_smoothing=True, use_shoulder=True, use_feedback=True)

if __name__ == "__main__":
    main()
