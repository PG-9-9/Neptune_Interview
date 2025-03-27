import cv2
import mediapipe as mp

class PoseDetector:
    """
    Wrapper class around MediaPipe's pose estimation pipeline.
    Provides methods for detecting human pose landmarks from images
    and drawing those landmarks on a frame.
    """

    def __init__(self, static_image_mode=False, model_complexity=1,
                 enable_segmentation=False, min_detection_confidence=0.5,
                 min_tracking_confidence=0.5):
        """
        Initializes the PoseDetector with MediaPipe's Pose module.

        Args:
            static_image_mode (bool): If True, treats input images as static.
            model_complexity (int): Complexity of the pose landmark model (0, 1, or 2).
            enable_segmentation (bool): Whether to enable segmentation masks.
            min_detection_confidence (float): Minimum confidence for detection.
            min_tracking_confidence (float): Minimum confidence for landmark tracking.
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            enable_segmentation=enable_segmentation,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        # Drawing utilities from MediaPipe
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def detect_pose(self, image):
        """
        Detect pose landmarks in the input image.

        Args:
            image (np.ndarray): BGR image from OpenCV.

        Returns:
            results: MediaPipe pose estimation results object.

        Raises:
            ValueError: If image is None.
        """
        if image is None:
            raise ValueError("Input image is None.")

        # Convert image to RGB as required by MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Perform pose detection
        return self.pose.process(image_rgb)

    def draw_landmarks(self, image, results):
        """
        Draw pose landmarks and connections on the image.

        Args:
            image (np.ndarray): Image to draw on.
            results: Results object returned by `detect_pose`.

        Returns:
            np.ndarray: Image with pose landmarks drawn (if any found).
        """
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image=image,
                landmark_list=results.pose_landmarks,
                connections=self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
            )
        return image
