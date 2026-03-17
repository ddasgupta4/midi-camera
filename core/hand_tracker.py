"""
MediaPipe Hands wrapper.

Processes camera frames and returns hand landmarks with
handedness classification (left/right).
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class HandData:
    """Processed hand data from MediaPipe."""
    landmarks: list          # 21 landmark points (x, y, z normalized)
    handedness: str          # 'Left' or 'Right'
    pixel_landmarks: list    # landmarks converted to pixel coords (x, y)


class HandTracker:
    def __init__(self, max_hands: int = 2, detection_confidence: float = 0.7,
                 tracking_confidence: float = 0.6):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

    def process(self, frame: np.ndarray) -> Tuple[Optional[HandData], Optional[HandData]]:
        """
        Process a BGR frame. Returns (left_hand, right_hand) or None for each.

        Note: MediaPipe assumes selfie-mode (mirrored), so 'Right' from
        MediaPipe = user's right hand when frame is flipped.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        left_hand = None
        right_hand = None

        if not results.multi_hand_landmarks:
            return left_hand, right_hand

        h, w, _ = frame.shape

        for hand_lms, handedness_info in zip(
            results.multi_hand_landmarks,
            results.multi_handedness
        ):
            label = handedness_info.classification[0].label  # 'Left' or 'Right'

            # Convert normalized landmarks to pixel coordinates
            landmarks = []
            pixel_landmarks = []
            for lm in hand_lms.landmark:
                landmarks.append((lm.x, lm.y, lm.z))
                pixel_landmarks.append((int(lm.x * w), int(lm.y * h)))

            hand = HandData(
                landmarks=landmarks,
                handedness=label,
                pixel_landmarks=pixel_landmarks,
            )

            # MediaPipe in mirrored mode: 'Right' label = user's right hand
            if label == 'Right':
                right_hand = hand
            else:
                left_hand = hand

        return left_hand, right_hand

    def draw_landmarks(self, frame: np.ndarray, hand: HandData,
                       color: Tuple[int, int, int] = (0, 255, 100)):
        """Draw hand landmarks on frame."""
        for i, (px, py) in enumerate(hand.pixel_landmarks):
            cv2.circle(frame, (px, py), 4, color, -1)

        # Draw connections between landmarks
        connections = self.mp_hands.HAND_CONNECTIONS
        for start_idx, end_idx in connections:
            p1 = hand.pixel_landmarks[start_idx]
            p2 = hand.pixel_landmarks[end_idx]
            cv2.line(frame, p1, p2, color, 2)

    def release(self):
        self.hands.close()
