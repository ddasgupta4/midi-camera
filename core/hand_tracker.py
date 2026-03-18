"""
MediaPipe Hands wrapper — uses the Tasks API (mediapipe >= 0.10).

Processes camera frames and returns hand landmarks with
handedness classification (left/right).
"""

import os
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from typing import Optional, Tuple
from dataclasses import dataclass


MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'hand_landmarker.task')

# MediaPipe hand connection pairs (landmark indices)
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),          # thumb
    (0,5),(5,6),(6,7),(7,8),          # index
    (0,9),(9,10),(10,11),(11,12),     # middle
    (0,13),(13,14),(14,15),(15,16),   # ring
    (0,17),(17,18),(18,19),(19,20),   # pinky
    (5,9),(9,13),(13,17),             # palm
]


@dataclass
class HandData:
    """Processed hand data from MediaPipe."""
    landmarks: list        # 21 landmark points (x, y, z normalized)
    handedness: str        # 'Left' or 'Right'
    pixel_landmarks: list  # landmarks as pixel coords (x, y)


class HandTracker:
    def __init__(self, max_hands: int = 2,
                 detection_confidence: float = 0.7,
                 tracking_confidence: float = 0.6):

        model_path = os.path.abspath(MODEL_PATH)
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Hand landmarker model not found at {model_path}\n"
                "Run: curl -L -o models/hand_landmarker.task "
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                "hand_landmarker/float16/1/hand_landmarker.task --create-dirs"
            )

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self.landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._start_time = time.time()

    def process(self, frame: np.ndarray) -> Tuple[Optional[HandData], Optional[HandData]]:
        """
        Process a BGR frame. Returns (left_hand, right_hand), either may be None.
        Frame should already be mirrored (selfie mode) before calling.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Timestamp in milliseconds
        timestamp_ms = int((time.time() - self._start_time) * 1000)
        results = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        left_hand = None
        right_hand = None

        if not results.hand_landmarks:
            return left_hand, right_hand

        h, w, _ = frame.shape

        for lm_list, handedness_list in zip(
            results.hand_landmarks,
            results.handedness
        ):
            label = handedness_list[0].category_name  # 'Left' or 'Right'

            landmarks = [(lm.x, lm.y, lm.z) for lm in lm_list]
            pixel_landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in lm_list]

            hand = HandData(
                landmarks=landmarks,
                handedness=label,
                pixel_landmarks=pixel_landmarks,
            )

            # In mirrored (selfie) mode, MediaPipe 'Right' = user's right hand
            if label == 'Right':
                right_hand = hand
            else:
                left_hand = hand

        return left_hand, right_hand

    def draw_landmarks(self, frame: np.ndarray, hand: HandData,
                       color: Tuple[int, int, int] = (0, 255, 100)):
        """Draw hand landmarks and connections on frame."""
        for (px, py) in hand.pixel_landmarks:
            cv2.circle(frame, (px, py), 5, color, -1)

        for start_idx, end_idx in HAND_CONNECTIONS:
            p1 = hand.pixel_landmarks[start_idx]
            p2 = hand.pixel_landmarks[end_idx]
            cv2.line(frame, p1, p2, color, 2)

    def release(self):
        self.landmarker.close()
