import streamlit as st
import cv2
import numpy as np
import time
import math
from collections import deque
from datetime import datetime
from PIL import Image
import os
import threading
import subprocess

from modules.pose_detector import PoseDetector
from modules.utils import (
    get_landmark_coordinates,
    calculate_angle,
    draw_right_arm,
    draw_status_bar,
    draw_wrist_trajectory,
    export_pose_to_json
)

# Configure Streamlit page settings
st.set_page_config(page_title="Violinist Posture Feedback", layout="centered")
st.title("🎻 Violin Posture Feedback System")  # Title with violin emoji

# Initialize session state variables to manage app state
if "run_camera" not in st.session_state:
    st.session_state.run_camera = False  # Controls camera loop
if "save_snapshot" not in st.session_state:
    st.session_state.save_snapshot = False  # Triggers pose snapshot save
if "set_reference" not in st.session_state:
    st.session_state.set_reference = False  # Sets reference posture

# Create three columns for camera control buttons
col1, col2, col3 = st.columns([1, 1, 1])
start_cam = col1.button("Start Camera", key="start_btn")  # Button to start webcam
stop_cam = col2.button("Stop Camera", key="stop_btn")     # Button to stop webcam
if col3.button("Set Reference", key="set_reference_btn"): # Button to set reference posture
    st.session_state.set_reference = True
if st.button("Save Pose Snapshot", key="pose_button"):    # Button to save current pose
    st.session_state.save_snapshot = True

# Placeholder for displaying live video feed
FRAME_WINDOW = st.image([])

# Section for accuracy comparison visualization
st.markdown("---")  # Horizontal line separator
st.header("📊 Accuracy Comparison Across Approaches")  # Header with chart emoji
plot_placeholder = st.empty()  # Placeholder for plot image
plot_path = "metrics/plots/accuracy_vs_spec_groundtruth.png"  # Path to accuracy plot

def run_metrics_plotter():
    """Run the external plot_metrics.py script to generate accuracy plot."""
    try:
        subprocess.run(["python", "plot_metrics.py"], check=True)  # Execute plotting script
    except Exception as e:
        st.warning(f"Plotting failed: {e}")  # Display warning if script fails

def show_latest_plot():
    """Display the latest accuracy comparison plot if available."""
    run_metrics_plotter()  # Generate the plot
    if os.path.exists(plot_path):  # Check if plot file exists
        image = Image.open(plot_path)  # Open the plot image
        plot_placeholder.image(image, caption="Accuracy vs Spec-Based Ground Truth by Phase")  # Display plot
        st.info("📌 This plot refreshes when you reload the page. Consider refreshing every ~30 seconds to see new results.")
    else:
        plot_placeholder.warning("No comparison plot found. Please run `plot_metrics.py`.")  # Warn if plot is missing

show_latest_plot()  # Initial call to display plot

# Camera processing loop
if start_cam:
    detector = PoseDetector()  # Initialize pose detection object
    cap = cv2.VideoCapture(0)  # Access default webcam
    if not cap.isOpened():     # Check if webcam is accessible
        st.warning("Could not access webcam.")
    else:
        st.session_state.run_camera = True  # Set camera running state
        # Initialize buffers for smoothing and tracking
        status_buffer = deque(maxlen=5)           # Buffer for elbow status
        wrist_trajectory = deque(maxlen=50)       # Track wrist movement path
        right_shoulder_heights = deque(maxlen=10) # Track shoulder height

        # Default posture settings
        reference_elbow_angle = 150  # Initial reference elbow angle in degrees
        elbow_angle_threshold = 15   # Acceptable deviation from reference angle
        shoulder_baseline = None     # Baseline shoulder height (set dynamically)

        # Frame processing variables
        skip_counter = 0    # Counter for frame skipping
        skip_interval = 1   # Initial frame skip interval
        results = None      # Store pose detection results
        frame_count = 0     # Track total frames processed
        prev_time = time.time()  # For FPS calculation

        # Main camera loop
        while st.session_state.run_camera:
            ret, frame = cap.read()  # Capture frame from webcam
            if not ret:
                st.warning("Unable to access webcam")
                break

            frame_count += 1
            shoulder_lift = 0  # Initialize shoulder lift value

            # Process pose detection on selected frames for performance
            if skip_counter % skip_interval == 0:
                results = detector.detect_pose(frame)  # Detect pose landmarks
            skip_counter += 1

            # Analyze pose if landmarks are detected
            if results and results.pose_landmarks:
                # Extract coordinates of key landmarks
                shoulder = get_landmark_coordinates(frame, results.pose_landmarks, 12)  # Right shoulder
                elbow = get_landmark_coordinates(frame, results.pose_landmarks, 14)     # Right elbow
                wrist = get_landmark_coordinates(frame, results.pose_landmarks, 16)      # Right wrist

                elbow_angle = calculate_angle(shoulder, elbow, wrist)  # Calculate elbow angle

                # Set reference posture dynamically
                if st.session_state.set_reference:
                    reference_elbow_angle = elbow_angle
                    st.session_state.set_reference = False

                # Evaluate posture correctness
                deviation = abs(elbow_angle - reference_elbow_angle)
                posture_correct = deviation <= elbow_angle_threshold
                posture_status = f"{'Reference' if posture_correct else 'Deviated'} Posture ({int(elbow_angle)} Deg)"
                posture_color = (0, 255, 0) if posture_correct else (0, 0, 255)  # Green for correct, red for deviated
                cv2.putText(frame, posture_status, (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, posture_color, 2)

                # Assess elbow position
                elbow_visibly_above = elbow[1] < shoulder[1]  # Elbow above shoulder
                elbow_bent_upward = elbow_angle < 90          # Elbow sharply bent
                elbow_raised = elbow_visibly_above or elbow_bent_upward
                status_buffer.append(elbow_raised)            # Add to buffer
                smoothed_status = sum(status_buffer) > len(status_buffer) // 2  # Smoothed result

                # Draw arm and status bar
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
                    shoulder_status = "Shoulder Elevated" if shoulder_lift > 15 else "Shoulder Normal"
                    shoulder_color = (0, 0, 255) if shoulder_lift > 15 else (0, 255, 0)  # Red if elevated, green if normal
                    skip_interval = 1 if shoulder_lift > 15 else 2  # Adjust frame skipping
                    cv2.putText(frame, shoulder_status, (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, shoulder_color, 2)

                # Provide posture feedback hints
                hint = "Great posture!"
                if not posture_correct:
                    hint = "Try extending your bowing arm more"
                elif shoulder_lift > 15:
                    hint = "Lower your shoulder slightly"
                elif not smoothed_status:
                    hint = "Keep bowing arm stable"
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

            # Display processed frame in Streamlit
            FRAME_WINDOW.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Cleanup when loop ends
        cap.release()
        st.success("Camera stopped.")

# Stop camera when stop button is pressed
if stop_cam:
    st.session_state.run_camera = False  # Halt camera loop