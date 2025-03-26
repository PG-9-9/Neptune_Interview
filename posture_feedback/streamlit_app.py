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

# Set up Streamlit page configuration
st.set_page_config(page_title="Violinist Posture Feedback", layout="centered")
st.title("Violin Posture Feedback System")

# Create three columns for buttons
col1, col2, col3 = st.columns([1, 1, 1])
start_cam = col1.button("Start Camera")  # Button to start the camera
stop_cam = col2.button("Stop Camera")    # Button to stop the camera

# Initialize session state variables for snapshot and reference posture
if "save_snapshot" not in st.session_state:
    st.session_state.save_snapshot = False
if "set_reference" not in st.session_state:
    st.session_state.set_reference = False

# Button to set reference posture
if col3.button("Set Reference", key="set_reference_btn"):
    st.session_state.set_reference = True

# Button to save a pose snapshot
if st.button("Save Pose Snapshot", key="pose_button"):
    st.session_state.save_snapshot = True

# Placeholder for displaying video frames
FRAME_WINDOW = st.image([])

# Initialize pose detector and webcam
detector = PoseDetector()          # Object for detecting human pose
cap = cv2.VideoCapture(0)          # Access the default webcam (index 0)

# Initialize buffers for smoothing and tracking
status_buffer = deque(maxlen=5)           # Buffer for elbow status
elbow_position_history = deque(maxlen=10) # History of elbow positions
wrist_trajectory = deque(maxlen=50)       # Track wrist movement path
right_shoulder_heights = deque(maxlen=10) # Track shoulder height

# Frame skipping variables for performance
skip_counter = 0
skip_interval = 1
results = None

# Default posture settings
reference_elbow_angle = 150  # Default reference elbow angle in degrees
elbow_angle_threshold = 15   # Acceptable deviation from reference angle
shoulder_baseline = None     # Baseline shoulder height (set dynamically)

# FPS calculation variables
frame_count = 0
prev_time = time.time()

# Main loop when camera is started
if start_cam and not stop_cam:
    while True:
        ret, frame = cap.read()  # Capture frame from webcam
        if not ret:
            st.warning("Unable to access webcam")
            break

        frame_count += 1
        shoulder_lift = 0  # Initialize shoulder lift value

        # Skip frames for performance, process pose every 'skip_interval' frames
        if skip_counter % skip_interval == 0:
            results = detector.detect_pose(frame)  # Detect pose landmarks
        skip_counter += 1

        # Process pose landmarks if detected
        if results and results.pose_landmarks:
            # Extract coordinates of key landmarks
            shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)  # Right shoulder
            elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)     # Right elbow
            wrist = get_landmark_coordinates(frame, results.pose_landmarks, 16)      # Right wrist

            # Calculate elbow angle
            elbow_angle = calculate_angle(shoulder, elbow, wrist)

            # Set reference posture when button is pressed
            if st.session_state.set_reference:
                reference_elbow_angle = elbow_angle
                st.success(f"Reference posture set at {int(reference_elbow_angle)}°")
                st.session_state.set_reference = False

            # Check if posture deviates from reference
            deviation = abs(elbow_angle - reference_elbow_angle)
            posture_correct = deviation <= elbow_angle_threshold

            # Display posture status on frame
            if posture_correct:
                posture_status = f"Reference Posture ({int(elbow_angle)} Deg)"
                posture_color = (0, 255, 0)  # Green for correct posture
            else:
                posture_status = f"Deviated Posture ({int(elbow_angle)} Deg)"
                posture_color = (0, 0, 255)  # Red for deviated posture
            cv2.putText(frame, posture_status, (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, posture_color, 2)

            # Evaluate elbow position
            elbow_visibly_above = elbow[1] < shoulder[1]  # Check if elbow is above shoulder
            elbow_bent_upward = elbow_angle < 90          # Check if elbow is bent sharply
            elbow_raised = elbow_visibly_above or elbow_bent_upward
            status_buffer.append(elbow_raised)            # Add to buffer for smoothing
            smoothed_status = sum(status_buffer) > len(status_buffer) // 2  # Majority vote

            # Draw arm and status bar on frame
            frame = draw_right_arm(frame, results.pose_landmarks, elbow_above_shoulder=smoothed_status, annotate=True)
            draw_status_bar(frame, active=smoothed_status, color=(0, 0, 255) if smoothed_status else (0, 255, 0))

            # Track and draw wrist trajectory
            wrist_trajectory.append(wrist)
            frame = draw_wrist_trajectory(frame, wrist_trajectory)

            # Monitor shoulder height
            right_shoulder_heights.append(shoulder[1])
            if len(right_shoulder_heights) == right_shoulder_heights.maxlen:
                avg_shoulder_height = sum(right_shoulder_heights) / len(right_shoulder_heights)
                if shoulder_baseline is None:
                    shoulder_baseline = avg_shoulder_height  # Set initial baseline

                shoulder_lift = shoulder_baseline - avg_shoulder_height  # Calculate lift
                if shoulder_lift > 15:
                    shoulder_status = "Shoulder Elevated"
                    shoulder_color = (0, 0, 255)  # Red for elevated
                    skip_interval = 1             # Process every frame
                else:
                    shoulder_status = "Shoulder Normal"
                    shoulder_color = (0, 255, 0)  # Green for normal
                    skip_interval = 2             # Skip every other frame
                cv2.putText(frame, shoulder_status, (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, shoulder_color, 2)

            # Provide posture feedback hints
            if not posture_correct:
                hint = "Try extending your bowing arm more"
            elif shoulder_lift > 15:
                hint = "Lower your shoulder slightly"
            elif not smoothed_status:
                hint = "Keep bowing arm stable"
            else:
                hint = "Great posture!"
            cv2.putText(frame, f"Hint: {hint}", (20, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Save pose snapshot if requested
            if st.session_state.save_snapshot:
                export_pose_to_json(results.pose_landmarks, frame_count)
                st.success("Snapshot saved!")
                st.session_state.save_snapshot = False

        # Calculate and display FPS
        curr_time = time.time()
        fps_display = int(1 / (curr_time - prev_time + 1e-6))  # Avoid division by zero
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {fps_display}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        # Display the processed frame in Streamlit
        FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

# Stop camera and release resources
if stop_cam:
    cap.release()
    st.warning("Camera stopped.")