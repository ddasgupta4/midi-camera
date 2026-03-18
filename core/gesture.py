"""
Gesture interpretation from hand landmarks.

Right hand: finger counting -> scale degree (I-VII)
Left hand:  chord quality modifiers + velocity

Includes smoothing to prevent flutter on left hand gestures.
"""

import math
import time
from collections import deque
from typing import Optional
from dataclasses import dataclass

from core.hand_tracker import HandData


# MediaPipe landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
FINGER_MCPS = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]


@dataclass
class RightHandGesture:
    degree: int
    finger_count: int
    thumb_up: bool


@dataclass
class LeftHandGesture:
    quality_override: Optional[str]
    velocity: int
    add_7th: bool
    add_9th: bool
    gesture_name: str


# --- Smoothing state for left hand ---
_left_gesture_history = deque(maxlen=8)  # last 8 frames
_left_confirmed_gesture = "neutral"


def _is_finger_extended(landmarks, tip_idx, pip_idx, mcp_idx=None):
    """Check if finger is extended. Uses tip vs PIP y-comparison with margin."""
    margin = 0.02  # small margin to avoid flutter at the boundary
    return landmarks[tip_idx][1] < landmarks[pip_idx][1] - margin


def _is_thumb_extended(landmarks):
    """
    Thumb detection using x-distance from palm center.
    More lenient threshold for easier triggering.
    """
    thumb_tip = landmarks[THUMB_TIP]
    thumb_ip = landmarks[THUMB_IP]
    index_mcp = landmarks[INDEX_MCP]
    middle_mcp = landmarks[MIDDLE_MCP]

    # Palm center approximation
    palm_x = (index_mcp[0] + middle_mcp[0]) / 2

    # Thumb is extended if tip is far from palm center on x-axis
    dist_tip_x = abs(thumb_tip[0] - palm_x)
    dist_ip_x = abs(thumb_ip[0] - palm_x)

    return dist_tip_x > dist_ip_x * 1.15  # lenient


def _distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def _count_fingers(landmarks):
    """Count extended fingers (not thumb). Returns (count, list of bools)."""
    extended = []
    for tip, pip in zip(FINGER_TIPS, FINGER_PIPS):
        extended.append(_is_finger_extended(landmarks, tip, pip))
    return sum(extended), extended


def _fingers_curled(landmarks):
    """Check if most fingers are curled (tips below DIPs)."""
    curled = 0
    dips = [INDEX_DIP, MIDDLE_DIP, RING_DIP, PINKY_DIP]
    for tip, dip in zip(FINGER_TIPS, dips):
        if landmarks[tip][1] > landmarks[dip][1] + 0.01:
            curled += 1
    return curled >= 3


def _get_left_gesture_name(landmarks, thumb_up, finger_count, extended):
    """
    Determine left hand gesture name from landmarks.
    Returns a string key used for smoothing.
    """
    all_extended = all(extended) and finger_count == 4

    # Pinch: thumb + index tips close
    pinch_dist = _distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP])
    if pinch_dist < 0.06 and finger_count <= 2:
        return "pinch"

    # All fingers spread wide
    if all_extended and thumb_up:
        tips = [landmarks[t] for t in FINGER_TIPS]
        min_spread = min(_distance(tips[i], tips[i+1]) for i in range(3))
        if min_spread > 0.055:
            return "spread"
        else:
            return "open_palm"

    # Curled
    if _fingers_curled(landmarks):
        return "curled"

    # Index only
    if finger_count == 1 and extended[0]:
        return "index_only"

    # Peace (index + middle)
    if finger_count == 2 and extended[0] and extended[1]:
        return "peace"

    return "neutral"


def _smooth_left_gesture(raw_gesture):
    """
    Smooth left hand gesture to prevent flutter.
    Only switch to a new gesture if it's been consistent for 5+ of last 8 frames.
    """
    global _left_confirmed_gesture
    _left_gesture_history.append(raw_gesture)

    if len(_left_gesture_history) < 3:
        return raw_gesture

    # Count occurrences of each gesture in history
    counts = {}
    for g in _left_gesture_history:
        counts[g] = counts.get(g, 0) + 1

    # Find the dominant gesture
    dominant = max(counts, key=counts.get)
    dominant_count = counts[dominant]

    # Switch to new gesture only if it's dominant (5+ out of 8)
    threshold = max(5, len(_left_gesture_history) * 0.6)
    if dominant_count >= threshold:
        _left_confirmed_gesture = dominant
    # Also switch if current confirmed gesture has 0 recent occurrences
    elif counts.get(_left_confirmed_gesture, 0) == 0:
        _left_confirmed_gesture = dominant

    return _left_confirmed_gesture


def interpret_right_hand(hand: HandData) -> RightHandGesture:
    """
    Simple right hand mapping:
      Open hand = count total fingers (including thumb)
        1 finger  = I     (index only)
        2 fingers = II    (index + middle)
        3 fingers = III   (index + middle + ring)
        4 fingers = IV    (all except thumb)
        5 fingers = V     (all including thumb — open hand)
      Closed fist = no chord
      Thumb only  = VI
      Thumb + pinky = VII
    """
    lm = hand.landmarks
    thumb_up = _is_thumb_extended(lm)
    finger_count, extended = _count_fingers(lm)

    if finger_count == 0 and not thumb_up:
        degree = 0  # fist
    elif finger_count == 0 and thumb_up:
        degree = 6  # VI
    elif thumb_up and finger_count == 1 and extended[3] and not extended[0]:
        degree = 7  # VII (thumb + pinky)
    elif thumb_up and finger_count == 4:
        degree = 5  # V (all fingers + thumb = open hand)
    elif not thumb_up:
        degree = min(finger_count, 4)  # I-IV without thumb
    else:
        # Thumb + some fingers: use finger count
        degree = min(finger_count, 4)

    return RightHandGesture(
        degree=degree,
        finger_count=finger_count,
        thumb_up=thumb_up,
    )


def interpret_left_hand(hand: HandData) -> LeftHandGesture:
    """
    Left hand with smoothing to prevent flutter.

    Gestures (after smoothing):
      - open_palm (all extended, close together) = force major
      - curled (fingers curled) = force minor
      - pinch (thumb + index close) = dominant 7th
      - spread (all fingers spread wide) = major 7th
      - index_only = add 7th
      - peace (index + middle) = add 9th
      - neutral = diatonic default

    Velocity from wrist height.
    """
    lm = hand.landmarks

    # Velocity from wrist height
    wrist_y = lm[WRIST][1]
    velocity = int(127 - (wrist_y * 87))
    velocity = max(40, min(127, velocity))

    thumb_up = _is_thumb_extended(lm)
    finger_count, extended = _count_fingers(lm)

    # Get raw gesture then smooth it
    raw_gesture = _get_left_gesture_name(lm, thumb_up, finger_count, extended)
    gesture = _smooth_left_gesture(raw_gesture)

    quality_override = None
    add_7th = False
    add_9th = False

    if gesture == "pinch":
        quality_override = 'dominant7'
        gesture_name = "pinch (dom7)"
    elif gesture == "spread":
        quality_override = 'major7'
        gesture_name = "spread (maj7)"
    elif gesture == "open_palm":
        quality_override = 'major'
        gesture_name = "open palm (major)"
    elif gesture == "curled":
        quality_override = 'minor'
        gesture_name = "curled (minor)"
    elif gesture == "index_only":
        add_7th = True
        gesture_name = "index (+7th)"
    elif gesture == "peace":
        add_7th = True
        add_9th = True
        gesture_name = "peace (+9th)"
    else:
        gesture_name = "neutral"

    return LeftHandGesture(
        quality_override=quality_override,
        velocity=velocity,
        add_7th=add_7th,
        add_9th=add_9th,
        gesture_name=gesture_name,
    )


def reset_gesture_state():
    """Reset smoothing state (call when restarting camera)."""
    global _left_confirmed_gesture
    _left_gesture_history.clear()
    _left_confirmed_gesture = "neutral"
