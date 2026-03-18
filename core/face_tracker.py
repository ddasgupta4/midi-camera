"""
MediaPipe Face Landmarker — detects tongue-out for "sauce mode."

Uses blendshape scores from the FaceLandmarker Tasks API.
"""

import os
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from collections import deque

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'face_landmarker.task')


class FaceTracker:
    def __init__(self, detection_confidence: float = 0.5):
        model_path = os.path.abspath(MODEL_PATH)
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Face landmarker model not found at {model_path}\n"
                "Download: curl -sL -o models/face_landmarker.task "
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
                "face_landmarker/float16/1/face_landmarker.task"
            )

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=detection_confidence,
            min_face_presence_confidence=detection_confidence,
            min_tracking_confidence=0.5,
            output_face_blendshapes=True,
        )
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        self._start_time = time.time()

        # Smoothing for mouth-open detection
        self._mouth_history = deque(maxlen=8)
        self._mouth_open_confirmed = False
        self._mouth_time = 0.0

        # Toggle state
        self._sauce_on = False
        self._last_toggle_time = 0.0
        self._TOGGLE_COOLDOWN = 1.0  # seconds between toggles

    def process(self, frame: np.ndarray) -> bool:
        """
        Process a BGR frame. Returns True if tongue is out (sauce mode).
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - self._start_time) * 1000)

        results = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        tongue_raw = False

        if results.face_blendshapes and len(results.face_blendshapes) > 0:
            blendshapes = results.face_blendshapes[0]
            tongue_score = 0.0
            jaw_score = 0.0
            for bs in blendshapes:
                if bs.category_name == 'tongueOut':
                    tongue_score = bs.score
                elif bs.category_name == 'jawOpen':
                    jaw_score = bs.score
            # Tongue out OR mouth open = trigger
            tongue_raw = tongue_score > 0.2 or jaw_score > 0.35

        # Smooth the raw detection
        mouth_open = self._smooth_mouth(tongue_raw)

        # Toggle logic: mouth open triggers toggle, then cooldown
        now = time.time()
        if mouth_open and not self._mouth_open_confirmed:
            # Rising edge — mouth just opened
            if now - self._last_toggle_time >= self._TOGGLE_COOLDOWN:
                self._sauce_on = not self._sauce_on
                self._last_toggle_time = now
        self._mouth_open_confirmed = mouth_open

        return self._sauce_on

    def _smooth_mouth(self, raw: bool) -> bool:
        """Smooth mouth detection — 70% consensus over 8 frames."""
        self._mouth_history.append(raw)

        if len(self._mouth_history) < 3:
            return False

        true_count = sum(self._mouth_history)
        return true_count / len(self._mouth_history) >= 0.70

    def release(self):
        self.landmarker.close()
