"""
Gesture interpretation from hand landmarks.

Right hand (user's left): finger counting -> scale degree (I-VII)
Left hand (user's right): thumb = flip quality, fingers = stack extensions
Tongue/jaw: sauce mode (handled in face_tracker, passed in from app.py)

NOTE: Camera is mirrored. MediaPipe "Right" = user's left hand (degree).
MediaPipe "Left" = user's right hand (modifier).
"""

import math
import time
from collections import deque
from dataclasses import dataclass

from core.hand_tracker import HandData


# MediaPipe landmark indices
WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_PIP, MIDDLE_TIP = 10, 12
RING_PIP, RING_TIP = 14, 16
PINKY_MCP, PINKY_PIP, PINKY_TIP = 17, 18, 20

FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]


@dataclass
class RightHandGesture:
    degree: int
    finger_count: int


@dataclass
class LeftHandGesture:
    flip_quality: bool
    velocity: int
    add_7th: bool
    add_9th: bool
    add_11th: bool
    add_13th: bool
    gesture_name: str


# ── Smoothing buffers ──

_right_history = deque(maxlen=9)
_right_confirmed = 0
_right_time = 0.0

_left_fingers_history = deque(maxlen=8)
_left_fingers_confirmed = 0
_left_fingers_time = 0.0

_left_thumb_history = deque(maxlen=10)
_left_thumb_confirmed = False
_left_thumb_time = 0.0


def _smooth(history, confirmed, conf_time, raw, consensus, min_hold):
    """Generic smoothing with consensus threshold and hold time."""
    history.append(raw)
    if len(history) < 3:
        return confirmed, conf_time

    counts = {}
    for v in history:
        counts[v] = counts.get(v, 0) + 1

    dominant = max(counts, key=counts.get)
    ratio = counts[dominant] / len(history)

    if dominant != confirmed and ratio >= consensus:
        now = time.time()
        if now - conf_time >= min_hold:
            return dominant, now

    if counts.get(confirmed, 0) == 0:
        return dominant, time.time()

    return confirmed, conf_time


# ── Detection helpers ──

def _is_finger_extended(landmarks, tip_idx, pip_idx):
    return landmarks[tip_idx][1] < landmarks[pip_idx][1] - 0.025


def _count_fingers(landmarks):
    extended = [_is_finger_extended(landmarks, t, p) for t, p in zip(FINGER_TIPS, FINGER_PIPS)]
    return sum(extended), extended


def _distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


MIDDLE_MCP = 9


class ThumbDetector:
    """
    Hysteretic, palm-size-normalized thumb detection.

    Normalizes thumb distances by palm height (WRIST→MIDDLE_MCP) so
    detection is consistent regardless of how close/far the hand is
    from the camera, and regardless of hand size.

    Hysteresis: uses a higher threshold to enter "out" state than
    to stay in it — prevents flicker in the mushy middle zone.
    """

    def __init__(self, thresh_out=0.50, thresh_in=0.38,
                 history_len=12, consensus=0.65, min_hold=0.08):
        """
        thresh_out: normalized dist needed to ENTER "out" state (stricter)
        thresh_in:  normalized dist needed to STAY "out" (more lenient)
        Both thresholds are relative to palm height (WRIST→MIDDLE_MCP).
        """
        self.thresh_out = thresh_out
        self.thresh_in  = thresh_in
        self._history   = deque(maxlen=history_len)
        self._consensus = consensus
        self._min_hold  = min_hold
        self._confirmed = False
        self._conf_time = 0.0

    @property
    def is_out(self) -> bool:
        return self._confirmed

    def update(self, landmarks) -> bool:
        raw = self._detect(landmarks)
        self._confirmed, self._conf_time = _smooth(
            self._history, self._confirmed, self._conf_time,
            raw, self._consensus, self._min_hold,
        )
        return self._confirmed

    def reset(self):
        self._history.clear()
        self._confirmed = False
        self._conf_time = 0.0

    def _detect(self, lm) -> bool:
        # Normalize by palm size so results are scale-invariant
        palm = _distance(lm[WRIST], lm[MIDDLE_MCP])
        if palm < 0.01:
            palm = 0.15  # fallback for degenerate frames

        nd_index  = _distance(lm[THUMB_TIP], lm[INDEX_MCP])  / palm
        nd_middle = _distance(lm[THUMB_TIP], lm[MIDDLE_MCP]) / palm

        # Hysteresis: stay in current state unless signal is strong enough
        thresh = self.thresh_in if self._confirmed else self.thresh_out

        # OR vote: either signal alone is sufficient (belt-and-suspenders)
        return nd_index > thresh or nd_middle > (thresh * 1.08)


# Two detector instances — one per hand, different sensitivity
# Degree hand: needs to reliably distinguish IV (thumb in) vs V (thumb out)
# Lower thresh + faster response = more decisive switching
_thumb_degree   = ThumbDetector(thresh_out=0.44, thresh_in=0.30, history_len=10, consensus=0.60, min_hold=0.06)
# Modifier hand: flip quality — a bit more lenient to enter, same to hold
_thumb_modifier = ThumbDetector(thresh_out=0.42, thresh_in=0.28, history_len=10, consensus=0.60, min_hold=0.06)


# ── Right hand (user's left): degree ──

def interpret_right_hand(hand: HandData) -> RightHandGesture:
    """
    Finger count -> scale degree.
      Fist=silence, 1-3=I-III, 4(thumb tucked)=IV,
      4(thumb out)=V, thumb only=VI, thumb+pinky=VII
    """
    global _right_confirmed, _right_time
    lm = hand.landmarks
    finger_count, extended = _count_fingers(lm)

    # Smoothed, hysteretic, palm-normalized thumb detection
    thumb_out = _thumb_degree.update(lm)

    if finger_count == 0 and not thumb_out:
        raw = 0                                                # fist = silence
    elif finger_count == 0 and thumb_out:
        raw = 6                                                # thumb only = VI
    elif thumb_out and finger_count == 1 and extended[3] and not extended[0]:
        raw = 7                                                # thumb + pinky = VII
    elif finger_count == 4:
        raw = 5 if thumb_out else 4                           # V vs IV
    elif not thumb_out:
        raw = min(finger_count, 4)                            # I–III
    else:
        raw = min(finger_count, 4)

    _right_confirmed, _right_time = _smooth(
        _right_history, _right_confirmed, _right_time,
        raw, consensus=0.60, min_hold=0.1,
    )
    return RightHandGesture(degree=_right_confirmed, finger_count=finger_count)


# ── Left hand (user's right): thumb flip + finger extensions ──

def interpret_left_hand(hand: HandData) -> LeftHandGesture:
    """
    Thumb (smoothed separately) = flip chord quality.
    Fingers (smoothed separately) = stack diatonic extensions.

      Thumb out  = flip quality (I/IV/V -> minor, ii/iii/vi -> major)
      Thumb in   = diatonic quality

      0 fingers = triad
      1 finger  = 7th
      2 fingers = 9th (includes 7th)
      3 fingers = 11th (includes 7th, 9th)
      4 fingers = 13th (includes 7th, 9th, 11th)

    Velocity from wrist height.
    """
    global _left_fingers_confirmed, _left_fingers_time
    global _left_thumb_confirmed, _left_thumb_time
    lm = hand.landmarks

    # Velocity
    velocity = max(40, min(127, int(127 - lm[WRIST][1] * 87)))

    # Raw detection — thumb uses ThumbDetector (hysteresis + normalization)
    # Fingers smoothed separately via legacy buffer
    raw_thumb = _thumb_modifier.update(lm)
    raw_fingers, _ = _count_fingers(lm)

    # Thumb is handled by ThumbDetector — copy result into legacy buffer so
    # _left_thumb_confirmed stays in sync for reset_gesture_state()
    _left_thumb_history.append(raw_thumb)
    _left_thumb_confirmed = raw_thumb
    # Fingers: 70% consensus over 8 frames, 100ms hold
    _left_fingers_confirmed, _left_fingers_time = _smooth(
        _left_fingers_history, _left_fingers_confirmed, _left_fingers_time,
        raw_fingers, consensus=0.70, min_hold=0.1,
    )

    flip = _left_thumb_confirmed
    fc = _left_fingers_confirmed

    # Build name
    ext_names = {0: "triad", 1: "7th", 2: "9th", 3: "11th", 4: "13th"}
    name = ("flip " if flip else "") + ext_names.get(fc, "triad")

    return LeftHandGesture(
        flip_quality=flip,
        velocity=velocity,
        add_7th=fc >= 1,
        add_9th=fc >= 2,
        add_11th=fc >= 3,
        add_13th=fc >= 4,
        gesture_name=name,
    )


def reset_gesture_state():
    global _right_confirmed, _right_time
    global _left_fingers_confirmed, _left_fingers_time
    global _left_thumb_confirmed, _left_thumb_time
    _right_history.clear()
    _right_confirmed = 0
    _right_time = 0.0
    _left_fingers_history.clear()
    _left_fingers_confirmed = 0
    _left_fingers_time = 0.0
    _left_thumb_history.clear()
    _left_thumb_confirmed = False
    _left_thumb_time = 0.0
    _thumb_degree.reset()
    _thumb_modifier.reset()
