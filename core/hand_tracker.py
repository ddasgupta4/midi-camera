"""
MediaPipe Hands wrapper — uses the Tasks API (mediapipe >= 0.10).

Runs inference in a background thread to decouple camera FPS from
inference FPS. Main thread writes frames, reads latest results.
"""

import os
import time
import threading
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
                 tracking_confidence: float = 0.6,
                 inference_size: tuple | None = None):
        """
        Args:
            inference_size: (w, h) to downscale before inference, or None for full res.
        """
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
        self._inference_size = inference_size

        # Threading state
        self._lock = threading.Lock()
        self._frame_slot: Optional[np.ndarray] = None  # latest frame to process
        self._frame_shape: Optional[tuple] = None       # (h, w) of display frame
        self._result: Tuple[Optional[HandData], Optional[HandData]] = (None, None)
        self._running = True
        self._has_frame = threading.Event()

        # FPS tracking
        self._inference_count = 0
        self._inference_fps = 0.0
        self._fps_timer = time.time()

        # Start inference thread
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()

    def submit_frame(self, frame: np.ndarray):
        """Submit a new frame for inference (non-blocking, drops old frames)."""
        with self._lock:
            self._frame_slot = frame
            self._frame_shape = frame.shape[:2]
        self._has_frame.set()

    def get_result(self) -> Tuple[Optional[HandData], Optional[HandData]]:
        """Get latest inference result (non-blocking)."""
        with self._lock:
            return self._result

    @property
    def inference_fps(self) -> float:
        return self._inference_fps

    def _inference_loop(self):
        """Background thread: process frames as they arrive."""
        while self._running:
            self._has_frame.wait(timeout=0.1)
            self._has_frame.clear()

            with self._lock:
                frame = self._frame_slot
                display_shape = self._frame_shape
                self._frame_slot = None

            if frame is None:
                continue

            left, right = self._run_inference(frame, display_shape)

            with self._lock:
                self._result = (left, right)

            # FPS tracking
            self._inference_count += 1
            now = time.time()
            elapsed = now - self._fps_timer
            if elapsed >= 1.0:
                self._inference_fps = self._inference_count / elapsed
                self._inference_count = 0
                self._fps_timer = now

    def _run_inference(self, frame: np.ndarray,
                       display_shape: tuple) -> Tuple[Optional[HandData], Optional[HandData]]:
        """Run MediaPipe on a single frame. Handles downscaling."""
        display_h, display_w = display_shape

        # Downscale for inference if configured
        if self._inference_size:
            inf_w, inf_h = self._inference_size
            small = cv2.resize(frame, (inf_w, inf_h), interpolation=cv2.INTER_LINEAR)
        else:
            small = frame

        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - self._start_time) * 1000)

        results = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        left_hand = None
        right_hand = None

        if not results.hand_landmarks:
            return left_hand, right_hand

        for lm_list, handedness_list in zip(
            results.hand_landmarks,
            results.handedness
        ):
            label = handedness_list[0].category_name

            landmarks = [(lm.x, lm.y, lm.z) for lm in lm_list]
            # Scale pixel landmarks to display resolution (not inference resolution)
            pixel_landmarks = [
                (int(lm.x * display_w), int(lm.y * display_h)) for lm in lm_list
            ]

            hand = HandData(
                landmarks=landmarks,
                handedness=label,
                pixel_landmarks=pixel_landmarks,
            )

            if label == 'Right':
                right_hand = hand
            else:
                left_hand = hand

        return left_hand, right_hand

    # ── Legacy synchronous API (used by draw_landmarks) ──

    def process(self, frame: np.ndarray) -> Tuple[Optional[HandData], Optional[HandData]]:
        """
        Synchronous process — submits frame and returns latest result.
        For backwards compat; prefer submit_frame + get_result in threaded mode.
        """
        self.submit_frame(frame)
        return self.get_result()

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
        self._running = False
        self._has_frame.set()  # unblock thread
        self._thread.join(timeout=1.0)
        self.landmarker.close()
