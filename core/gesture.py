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

def _is_thumb_out(landmarks, threshold=0.09):
    """Thumb detection using distance from thumb tip to index MCP."""
    return _distance(landmarks[THUMB_TIP], landmarks[INDEX_MCP]) > threshold


def _is_thumb_out_modifier(landmarks):
    """
    More lenient thumb detection for the modifier hand.
    Uses MIDDLE_MCP (center of palm) as reference — more stable
    when the hand is held in different orientations.
    Also lower threshold since the modifier hand is often more relaxed.
    """
    # Check both middle and index MCP — if either fires, thumb is out
    dist_middle = _distance(landmarks[THUMB_TIP], landmarks[MIDDLE_MCP])
    dist_index = _distance(landmarks[THUMB_TIP], landmarks[INDEX_MCP])
    return dist_middle > 0.10 or dist_index > 0.08


# ── Right hand (user's left): degree ──

def interpret_right_hand(hand: HandData) -> RightHandGesture:
    """
    Finger count -> scale degree.
      Fist=silence, 1-3=I-III, 4(thumb tucked)=IV,
      open hand=V, thumb only=VI, thumb+pinky=VII
    """
    global _right_confirmed, _right_time
    lm = hand.landmarks
    finger_count, extended = _count_fingers(lm)
    thumb_dist = _distance(lm[THUMB_TIP], lm[INDEX_MCP])
    thumb_out = thumb_dist > 0.09

    if finger_count == 0 and not thumb_out:
        raw = 0
    elif finger_count == 0 and thumb_out:
        raw = 6
    elif thumb_out and finger_count == 1 and extended[3] and not extended[0]:
        raw = 7
    elif finger_count == 4:
        raw = 5 if thumb_dist > 0.09 else 4
    elif not thumb_out:
        raw = min(finger_count, 4)
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

    # Raw detection
    raw_thumb = _is_thumb_out_modifier(lm)
    raw_fingers, _ = _count_fingers(lm)

    # Smooth thumb and fingers INDEPENDENTLY
    # Thumb: 65% consensus over 10 frames, 100ms hold — more responsive
    _left_thumb_confirmed, _left_thumb_time = _smooth(
        _left_thumb_history, _left_thumb_confirmed, _left_thumb_time,
        raw_thumb, consensus=0.65, min_hold=0.1,
    )
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
