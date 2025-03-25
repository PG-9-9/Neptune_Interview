import streamlit as st
import cv2
import numpy as np
import time
import math
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

st.set_page_config(page_title="Violinist Posture Feedback", layout="centered")
st.title("Violin Posture Feedback System")

col1, col2, col3 = st.columns([1, 1, 1])
start_cam = col1.button("Start Camera")
stop_cam = col2.button("Stop Camera")
if "save_snapshot" not in st.session_state:
    st.session_state.save_snapshot = False
if "set_reference" not in st.session_state:
    st.session_state.set_reference = False

if col3.button("Set Reference", key="set_reference_btn"):
    st.session_state.set_reference = True

if st.button("Save Pose Snapshot", key="pose_button"):
    st.session_state.save_snapshot = True

FRAME_WINDOW = st.image([])

# Initialize camera and pose detector
detector = PoseDetector()
cap = cv2.VideoCapture(0)

# Buffers and tracking
status_buffer = deque(maxlen=5)
elbow_position_history = deque(maxlen=10)
wrist_trajectory = deque(maxlen=50)
right_shoulder_heights = deque(maxlen=10)

skip_counter = 0
skip_interval = 1
results = None

reference_elbow_angle = 150  # default angle
elbow_angle_threshold = 15
shoulder_baseline = None

frame_count = 0
prev_time = time.time()

if start_cam and not stop_cam:
    while True:
        ret, frame = cap.read()
        if not ret:
            st.warning("Unable to access webcam")
            break

        frame_count += 1
        shoulder_lift = 0

        if skip_counter % skip_interval == 0:
            results = detector.detect_pose(frame)
        skip_counter += 1

        if results and results.pose_landmarks:
            shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)
            elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)
            wrist = get_landmark_coordinates(frame, results.pose_landmarks, 16)

            elbow_angle = calculate_angle(shoulder, elbow, wrist)

            # Set reference posture dynamically
            if st.session_state.set_reference:
                reference_elbow_angle = elbow_angle
                st.success(f"Reference posture set at {int(reference_elbow_angle)}°")
                st.session_state.set_reference = False

            deviation = abs(elbow_angle - reference_elbow_angle)
            posture_correct = deviation <= elbow_angle_threshold

            if posture_correct:
                posture_status = f"Reference Posture ({int(elbow_angle)} Deg)"
                posture_color = (0, 255, 0)
            else:
                posture_status = f"Deviated Posture ({int(elbow_angle)} Deg)"
                posture_color = (0, 0, 255)

            cv2.putText(frame, posture_status, (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, posture_color, 2)

            elbow_visibly_above = elbow[1] < shoulder[1]
            elbow_bent_upward = elbow_angle < 90
            elbow_raised = elbow_visibly_above or elbow_bent_upward
            status_buffer.append(elbow_raised)
            smoothed_status = sum(status_buffer) > len(status_buffer) // 2

            frame = draw_right_arm(frame, results.pose_landmarks, elbow_above_shoulder=smoothed_status, annotate=True)
            draw_status_bar(frame, active=smoothed_status, color=(0, 0, 255) if smoothed_status else (0, 255, 0))

            wrist_trajectory.append(wrist)
            frame = draw_wrist_trajectory(frame, wrist_trajectory)

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

            if not posture_correct:
                hint = "Try extending your bowing arm more"
            elif shoulder_lift > 15:
                hint = "Lower your shoulder slightly"
            elif not smoothed_status:
                hint = "Keep bowing arm stable"
            else:
                hint = "Great posture!"

            cv2.putText(frame, f"Hint: {hint}", (20, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            if st.session_state.save_snapshot:
                export_pose_to_json(results.pose_landmarks, frame_count)
                st.success("Snapshot saved!")
                st.session_state.save_snapshot = False

        curr_time = time.time()
        fps_display = int(1 / (curr_time - prev_time + 1e-6))
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {fps_display}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

if stop_cam:
    cap.release()
    st.warning("Camera stopped.")
