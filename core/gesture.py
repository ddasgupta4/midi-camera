"""
Gesture interpretation from hand landmarks.

Right hand: finger counting -> scale degree (I-VII)
Left hand:  chord quality modifiers + velocity
"""

import math
from typing import Optional, Tuple
from dataclasses import dataclass

from core.hand_tracker import HandData


# MediaPipe landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

# Fingertip and PIP indices for extension check (not thumb)
FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]


@dataclass
class RightHandGesture:
    """Right hand state: which chord degree to play."""
    degree: int           # 0 = no chord (fist), 1-7 = scale degree
    finger_count: int     # how many non-thumb fingers extended
    thumb_up: bool        # is thumb extended


@dataclass
class LeftHandGesture:
    """Left hand state: modifiers for chord quality."""
    quality_override: Optional[str]  # None = diatonic default
    velocity: int                     # MIDI velocity 40-127
    add_7th: bool                     # extend chord with 7th
    add_9th: bool                     # extend chord with 9th
    gesture_name: str                 # for display


def _is_finger_extended(landmarks: list, tip_idx: int, pip_idx: int) -> bool:
    """Check if a finger is extended by comparing tip vs PIP y-coords."""
    # In normalized coords, lower y = higher in frame
    return landmarks[tip_idx][1] < landmarks[pip_idx][1]


def _is_thumb_extended(landmarks: list) -> bool:
    """
    Check if thumb is extended. Uses x-axis distance from thumb tip
    to thumb MCP — if tip is far from palm center, thumb is out.
    """
    thumb_tip = landmarks[THUMB_TIP]
    thumb_mcp = landmarks[THUMB_MCP]
    index_mcp = landmarks[INDEX_MCP]

    # Thumb is extended if tip is farther from index MCP than thumb MCP is
    # (works for both left/right hands in mirrored view)
    dist_tip = math.sqrt((thumb_tip[0] - index_mcp[0])**2 + (thumb_tip[1] - index_mcp[1])**2)
    dist_mcp = math.sqrt((thumb_mcp[0] - index_mcp[0])**2 + (thumb_mcp[1] - index_mcp[1])**2)

    return dist_tip > dist_mcp * 1.3


def _distance(p1: tuple, p2: tuple) -> float:
    """Euclidean distance between two landmark points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def _fingers_spread(landmarks: list) -> bool:
    """Check if all fingers are spread wide apart."""
    # Measure distances between adjacent fingertips
    tips = [landmarks[INDEX_TIP], landmarks[MIDDLE_TIP],
            landmarks[RING_TIP], landmarks[PINKY_TIP]]
    min_spread = float('inf')
    for i in range(len(tips) - 1):
        d = _distance(tips[i], tips[i + 1])
        min_spread = min(min_spread, d)
    # "Spread" = all adjacent tips reasonably far apart
    return min_spread > 0.06


def _fingers_curled(landmarks: list) -> bool:
    """
    Check if fingers are in a curled/half-fist position.
    Tips should be below DIPs but above MCPs (not fully closed).
    """
    curled_count = 0
    dip_indices = [INDEX_DIP, MIDDLE_DIP, RING_DIP, PINKY_DIP]
    for tip, dip in zip(FINGER_TIPS, dip_indices):
        # Tip is below DIP (higher y value = lower in frame)
        if landmarks[tip][1] > landmarks[dip][1]:
            curled_count += 1
    return curled_count >= 3


def interpret_right_hand(hand: HandData) -> RightHandGesture:
    """
    Interpret right hand gesture into a scale degree.

    Finger count:
      0 fingers = fist = no chord (degree 0)
      1-5 fingers = degrees I-V
      Thumb + no other fingers = VI
      Thumb + pinky only = VII
    """
    lm = hand.landmarks
    thumb_up = _is_thumb_extended(lm)

    extended = []
    for tip, pip in zip(FINGER_TIPS, FINGER_PIPS):
        extended.append(_is_finger_extended(lm, tip, pip))

    finger_count = sum(extended)  # count of non-thumb extended fingers

    # Determine degree
    if finger_count == 0 and not thumb_up:
        # Closed fist — no chord
        degree = 0
    elif finger_count == 0 and thumb_up:
        # Thumb only = VI
        degree = 6
    elif thumb_up and finger_count == 1 and extended[3]:
        # Thumb + pinky = VII
        degree = 7
    elif thumb_up and finger_count >= 1:
        # Thumb + fingers: use finger count for degree
        # (but if it's just thumb+pinky, that's VII above)
        degree = min(finger_count, 5)
    else:
        # Just fingers, no thumb
        degree = min(finger_count, 5)

    return RightHandGesture(
        degree=degree,
        finger_count=finger_count,
        thumb_up=thumb_up,
    )


def interpret_left_hand(hand: HandData) -> LeftHandGesture:
    """
    Interpret left hand gesture into chord modifiers.

    Gestures:
      - Open flat palm (all extended, not spread) = force major
      - Curled/half fist = force minor
      - Pinch (thumb + index close) = dominant 7th
      - All 5 spread wide = major 7th
      - Index only = add 7th extension
      - Index + middle = add 9th extension
      - Relaxed/neutral = diatonic default

    Hand height (y) controls velocity.
    """
    lm = hand.landmarks

    # Velocity from hand height (wrist y position)
    # y=0 is top of frame (high velocity), y=1 is bottom (low velocity)
    wrist_y = lm[WRIST][1]
    velocity = int(127 - (wrist_y * 87))  # maps 0->127, 1->40
    velocity = max(40, min(127, velocity))

    thumb_up = _is_thumb_extended(lm)
    extended = [_is_finger_extended(lm, t, p) for t, p in zip(FINGER_TIPS, FINGER_PIPS)]
    finger_count = sum(extended)
    all_extended = all(extended)

    # Check for pinch (thumb tip close to index tip)
    pinch = _distance(lm[THUMB_TIP], lm[INDEX_TIP]) < 0.05

    quality_override = None
    add_7th = False
    add_9th = False
    gesture_name = "default"

    if pinch and not all_extended:
        # Pinch = dominant 7th
        quality_override = 'dominant7'
        gesture_name = "pinch (dom7)"
    elif all_extended and _fingers_spread(lm):
        # All 5 spread wide = major 7th
        quality_override = 'major7'
        gesture_name = "spread (maj7)"
    elif all_extended and not _fingers_spread(lm):
        # Flat open palm = force major
        quality_override = 'major'
        gesture_name = "open palm (major)"
    elif _fingers_curled(lm):
        # Curled = force minor
        quality_override = 'minor'
        gesture_name = "curled (minor)"
    elif finger_count == 1 and extended[0]:
        # Index only = add 7th
        add_7th = True
        gesture_name = "index (+7th)"
    elif finger_count == 2 and extended[0] and extended[1]:
        # Index + middle = add 9th
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
