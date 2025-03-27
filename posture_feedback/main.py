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
    """
    Initializes a new CSV log file to store metrics for a given model configuration.

    Args:
        tag (str): Identifier for the current run (e.g., 'baseline', 'final').

    Returns:
        str: Full path to the created log file.
    """
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
    """
    Appends a row of metric data to the log file.

    Args:
        log_file (str): Path to the CSV file.
        data (list): Row of metric data to append.
    """
    with open(log_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)


def run_model(tag, use_angle=False, use_smoothing=False, use_shoulder=False, use_feedback=True):
    """
    Main pipeline to process webcam feed and evaluate bowing arm posture in real-time.

    The pipeline can be flexibly configured using boolean switches:
    - use_angle: Enables elbow-shoulder-wrist angle check.
    - use_smoothing: Enables majority vote smoothing over a 5-frame buffer.
    - use_shoulder: Tracks shoulder elevation and suppresses false elbow raises.
    - use_feedback: Provides real-time posture improvement hints.

    Args:
        tag (str): Name of the approach phase for logging and display.
        use_angle (bool): Enable angle-based logic.
        use_smoothing (bool): Enable 5-frame smoothing.
        use_shoulder (bool): Enable shoulder elevation logic.
        use_feedback (bool): Enable real-time hint engine.
    """
    detector = PoseDetector()
    cap = cv2.VideoCapture(0)
    prev_time = 0
    log_file = create_logger(tag)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Buffers for temporal smoothing and tracking
    status_buffer = deque(maxlen=5)
    wrist_trajectory = deque(maxlen=50)
    right_shoulder_heights = deque(maxlen=10)

    # Posture and reference settings
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
            # Extract key landmarks
            shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)
            elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)
            wrist = get_landmark_coordinates(frame, results.pose_landmarks, 16)

            # Compute elbow angle if enabled
            elbow_angle = calculate_angle(shoulder, elbow, wrist) if use_angle else 0
            deviation = abs(elbow_angle - reference_elbow_angle) if use_angle else 0
            posture_correct = deviation <= elbow_angle_threshold if use_angle else True

            # Base elbow-shoulder logic
            elbow_visibly_above = elbow[1] < shoulder[1]
            elbow_bent_upward = elbow_angle < 90 if use_angle else False
            elbow_raised = elbow_visibly_above or elbow_bent_upward

            # Optional smoothing using temporal majority voting
            if use_smoothing:
                status_buffer.append(elbow_raised)
                smoothed_status = sum(status_buffer) > len(status_buffer) // 2
            else:
                smoothed_status = elbow_raised

            # Draw visual feedback overlays
            frame = draw_right_arm(
                frame,
                results.pose_landmarks,
                elbow_above_shoulder=smoothed_status,
                annotate=True
            )
            draw_status_bar(frame, active=smoothed_status, color=(0, 0, 255) if smoothed_status else (0, 255, 0))
            wrist_trajectory.append(wrist)
            frame = draw_wrist_trajectory(frame, wrist_trajectory)

            # Shoulder elevation logic (optional)
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

            # Real-time hint generation based on posture
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

            # FPS and performance monitoring
            curr_time = time.time()
            elapsed = curr_time - prev_time
            prev_time = curr_time
            fps_display = int(1 / (elapsed + 1e-6))
            cv2.putText(frame, f"FPS: {fps_display}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

            # Save all metrics
            append_log(log_file, [
                frame_count, elbow[1], shoulder[1], round(elbow_angle, 2), reference_elbow_angle,
                round(deviation, 2), smoothed_status, fps_display, hint, tag
            ])

        # Show window
        cv2.imshow(f'Posture Feedback - {tag}', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Webcam released. Model run ended.")


def main():
    """
    Entry point for posture experiment runs. 
    Uncomment the mode you want to log and test.
    """
    # run_model("baseline", use_angle=False, use_smoothing=False, use_shoulder=False, use_feedback=False)
    # run_model("angle_logic", use_angle=True, use_smoothing=False, use_shoulder=False, use_feedback=False)
    # run_model("smoothing", use_angle=True, use_smoothing=True, use_shoulder=False, use_feedback=False)
    # run_model("shoulder_logic", use_angle=True, use_smoothing=True, use_shoulder=True, use_feedback=False)
    run_model("final", use_angle=True, use_smoothing=True, use_shoulder=True, use_feedback=True)


if __name__ == "__main__":
    main()
