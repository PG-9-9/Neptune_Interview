
# 🎻 Violin Posture Feedback System

Real-time feedback for violinists using computer vision. Whether you're bowing like Paganini or flailing like you're conducting a wind symphony, this app’s here to lend a (digital) hand.

---

## 📸 What It Does

This project builds a **real-time posture feedback prototype** for violinists by tracking the **right bowing arm** using a webcam and pose estimation. Initially built to answer the classic interview prompt:

> _"Build a real-time posture feedback prototype. Highlight the elbow in red if it's lifted above shoulder level."_

...but, of course, I couldn’t stop there. Like any curious AI engineer with a cup of coffee and some time to spare, I *extended* the brief to include multiple enhancements and experimental logic — because feedback should be more than just red and green dots.

---

## 🧠 Methods & Add-Ons

Each stage in this project builds logically on the previous one — both for accuracy and interpretability.

### ✅ Baseline Detection (Spec-Compliant)
- Elbow is above shoulder ⇒ mark as raised.
- Simple, intuitive, and directly follows the original spec.

### ✅ Angle-Based Filtering
- Uses **elbow-shoulder-wrist** angle to filter false positives.
- Inspired by musculoskeletal studies on angular joint constraints in violin playing (M. Klimek et al., *2019*).
- Helps separate "elbow merely floating" vs. "arm deliberately bent".

### ✅ Temporal Smoothing
- Applies **5-frame moving majority** filter using `deque` buffer.
- Reduces jittery results caused by single-frame detection spikes.
- Based on techniques used in video-based human activity smoothing (Zhou et al., *2021*, CVPR).

### ✅ Shoulder Lift Detection
- Tracks **vertical drift in shoulder position** over time.
- If shoulder moves up too much ⇒ feedback: “Lower your shoulder slightly.”
- Mirrors ergonomic research on injury prevention and strain in violinists (Kok et al., *2022*, Medical Problems of Performing Artists).

### ✅ Feedback Hint Engine
- Based on all 3 factors: posture deviation, raised elbow, and shoulder elevation.
- Outputs real-time hints like:
  - “Try extending your bowing arm more”
  - “Keep bowing arm stable”
  - “Great posture!”

### ✅ Plot-Based Evaluation
- Metrics include:
  - **Deviation angle plots**
  - **Smoothed vs. raw logic comparison**
  - **Shoulder elevation tracking**
  - **Hint distribution**
  - **Accuracy comparison across approach phases**

---

## 🧪 Comparison of Approaches

| Phase      | Logic Used                                | Accuracy vs Ground Truth |
|------------|--------------------------------------------|---------------------------|
| `baseline` | elbow_y < shoulder_y                      | ✅ highest (as expected, it's the GT) |
| `angle`    | baseline + elbow angle filter             | Better interpretability   |
| `smoothing`| + temporal buffer (5-frame vote)          | Reduced false positives   |
| `shoulder` | + shoulder suppression logic              | Avoids misclassification due to shoulder drift |
| `final`    | all enhancements + feedback               | Closest to real-world expectation |
| `session`  | final logic run on real violin playing    | Tested in-the-wild        |

> **Ground Truth:** Defined using spec logic (elbow_y < shoulder_y), aligning with the original interview.

---

## 🖼️ Sample Visualizations

### Standard Arm Posture

![Standard Arm](images/image1.png)

- Elbow is roughly level with shoulder.
- Angle = 172° ⇒ outside acceptable elbow range.
- Posture marked as “Deviated” but arm is stable.
- Hint: “Try extending your bowing arm more”

---

### Raised Arm Posture

![Raised Arm](images//image2.png)

- Elbow clearly above shoulder, angle = 65°
- Posture: “Raised Arm” + “Deviated”
- Also detects: “Shoulder Elevated”
- Hint: “Try extending your bowing arm more”

---

### Accuracy Comparison Chart

![Accuracy Graph](images/image3.png)

This graph shows how each enhancement step affected accuracy relative to the baseline spec. Notice how final/session reach near real-world correctness when all logic is combined.

---

## 🎯 Other Interview Questions (Integrated)

| Prompt                                                                 | Status          | Where |
|------------------------------------------------------------------------|------------------|-------|
| Extract 3D joint angles and flag deviation                            | ✅ Done via elbow-shoulder-wrist |
| Classify posture as “good” or “bad”                                   | ✅ Angle + threshold logic |
| Track shoulder elevation and smooth temporally                        | ✅ `deque` + average tracking |
| Plot wrist trajectory to detect inconsistent bowing                   | ✅ `wrist_trajectory` buffer |
| Build MediaPipe mobile-friendly demo                                  | ✅ Optimized, Streamlit UI |
| Export to ONNX and Unity-ready wrapper                                | ✅ ONNX export available |
| Animate a stick figure from pose                                      | ❌ Not yet integrated (future idea) |

---

## 🚀 Try it Yourself (Docker)

```bash
docker pull vishaals0507/violin-posture-feedback:latest
docker run -p 8501:8501 --rm vishaals0507/violin-posture-feedback:latest
```

Then, open your browser: `http://localhost:8501`

---

## 🧊 Final Thoughts

Yes, this started as an interview challenge. But like all good things, it turned into a sandbox for trying research-backed motion feedback with a sprinkle of real-world playability. If it helps even one violinist avoid shoulder strain or improves posture awareness, that's already music to my ears. 🎻

---

## 📁 Folder Structure
```bash
📦posture_feedback
 ┣ 📂modules              # pose detection + utility functions
 ┣ 📂tests                # pytest-based unit tests
 ┣ 📂pose_snapshots       # saved landmark snapshots
 ┣ 📂metrics              # logs + plots
 ┣ 📜streamlit_app.py     # main Streamlit app
 ┣ 📜main.py              # camera-based runner
 ┣ 📜plot_metrics.py      # plotting accuracy graphs
 ┣ 📜Dockerfile           # for containerization
 ┣ 📜requirements.txt     # dependencies
 ┗ 📜README.md            # you're here
```

---

## ✨ Made by Vishaal  
🧠 AI + CV + Streamlit + Docker.  
🎻 Attempting to make bowing less bow-rring.  
