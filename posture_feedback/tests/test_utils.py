import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import numpy as np
from types import SimpleNamespace
from modules.utils import (
    calculate_angle,
    get_landmark_coordinates,
    export_pose_to_json,
    draw_right_arm,
    draw_wrist_trajectory
)



def test_calculate_angle_straight_line():
    a = (0, 0)
    b = (1, 0)
    c = (2, 0)
    angle = calculate_angle(a, b, c)
    assert round(angle) == 180

def test_calculate_angle_right_angle():
    a = (0, 1)
    b = (0, 0)
    c = (1, 0)
    angle = calculate_angle(a, b, c)
    assert round(angle) == 90

def test_get_landmark_coordinates():
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    landmark = SimpleNamespace(x=0.5, y=0.25)
    class FakeLandmarks:
        landmark = [landmark for _ in range(33)]
    coord = get_landmark_coordinates(img, FakeLandmarks(), 1)
    assert coord == (int(0.5 * w), int(0.25 * h))

def test_export_pose_to_json(tmp_path):
    fake_landmark = SimpleNamespace(x=0.1, y=0.2, z=0.3, visibility=0.9)
    class FakeLandmarks:
        landmark = [fake_landmark for _ in range(33)]

    frame_id = 123
    export_pose_to_json(FakeLandmarks(), frame_id, output_dir=str(tmp_path))

    files = list(tmp_path.iterdir())
    assert len(files) == 1
    with open(files[0], 'r') as f:
        data = json.load(f)
        assert "frame_id" in data
        assert len(data["keypoints"]) == 33

def test_draw_right_arm_runs():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    fake_point = SimpleNamespace(x=0.5, y=0.5)
    class FakeLandmarks:
        landmark = [fake_point for _ in range(33)]
    result = draw_right_arm(img, FakeLandmarks(), elbow_above_shoulder=True)
    assert isinstance(result, np.ndarray)

def test_draw_wrist_trajectory_runs():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    trajectory = [(100 + i*5, 200 + i*3) for i in range(10)]
    result = draw_wrist_trajectory(img, trajectory)
    assert isinstance(result, np.ndarray)
