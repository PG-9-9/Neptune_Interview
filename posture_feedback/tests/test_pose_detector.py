import cv2
import numpy as np
import pytest
from modules.pose_detector import PoseDetector
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_pose_detector_runs_on_black_image():
    detector = PoseDetector()
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detector.detect_pose(dummy_img)
    assert results is not None

def test_pose_detector_handles_none_input():
    detector = PoseDetector()
    with pytest.raises(ValueError):
        detector.detect_pose(None)

def test_pose_detector_on_sample_image():
    detector = PoseDetector()
    img = cv2.imread("tests/sample_frame.jpg")
    if img is None:
        pytest.skip("Sample image not found")
    results = detector.detect_pose(img)
    assert results is not None
