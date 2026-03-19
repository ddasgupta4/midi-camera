"""
Gesture interpretation from hand landmarks.

Architecture:
  - Raw detection with HYSTERESIS (no smoothing buffers, no consensus voting).
    Hysteresis alone prevents flicker without adding latency.
  - The settle window in app.py is the ONLY stability gate.
  - Hand persistence: holds last reading for a few frames when hand disappears.

Right hand (user's left / MediaPipe "Right"): finger count → degree I-VII
Left hand (user's right / MediaPipe "Left"): thumb = flip, fingers = extensions
"""

import math
import time
from dataclasses import dataclass
from typing import Optional

from core.hand_tracker import HandData


# ── MediaPipe landmark indices ──

WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]


# ── Data classes ──

@dataclass
class RightHandGesture:
    degree: int           # 0=silence, 1-7=scale degree
    finger_count: int     # raw finger count for display


@dataclass
class LeftHandGesture:
    flip_quality: bool
    velocity: int
    add_7th: bool
    add_9th: bool
    add_11th: bool
    add_13th: bool
    gesture_name: str


# ── Helpers ──

def _dist(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def _palm_size(lm):
    """Palm height (WRIST → MIDDLE_MCP) for normalization."""
    d = _dist(lm[WRIST], lm[MIDDLE_MCP])
    return max(d, 0.05)  # floor to avoid division issues


# ── Finger detection with per-finger hysteresis ──

class FingerDetector:
    """
    Per-finger hysteresis prevents individual finger flicker.
    
    Uses the gap between PIP joint and fingertip (in y-coords, normalized
    by palm size). Different thresholds for extending vs retracting.
    """
    
    # Thresholds are normalized by palm size
    EXTEND_THRESH = 0.18    # gap needed to register as extended (stricter)
    RETRACT_THRESH = 0.05   # gap needed to stay extended (more lenient)
    
    def __init__(self):
        self._states = [False, False, False, False]  # index, middle, ring, pinky
    
    def update(self, landmarks) -> tuple[int, list[bool]]:
        palm = _palm_size(landmarks)
        
        for i, (tip_idx, pip_idx) in enumerate(zip(FINGER_TIPS, FINGER_PIPS)):
            # Positive gap = tip is above PIP = finger extended
            gap = (landmarks[pip_idx][1] - landmarks[tip_idx][1]) / palm
            
            if self._states[i]:
                # Currently extended — use lower threshold to stay
                self._states[i] = gap > self.RETRACT_THRESH
            else:
                # Currently retracted — use higher threshold to extend
                self._states[i] = gap > self.EXTEND_THRESH
        
        return sum(self._states), list(self._states)
    
    def reset(self):
        self._states = [False, False, False, False]


# ── Thumb detection with hysteresis ──

class ThumbDetector:
    """
    Hysteretic thumb detection normalized by palm size.
    
    No smoothing buffer — hysteresis alone prevents flicker.
    The settle window in app.py handles stability.
    """
    
    def __init__(self, thresh_out=0.48, thresh_in=0.32):
        self.thresh_out = thresh_out  # normalized dist to ENTER "out"
        self.thresh_in  = thresh_in   # normalized dist to STAY "out"
        self._is_out = False
    
    def update(self, landmarks) -> bool:
        palm = _palm_size(landmarks)
        
        # Distance from thumb tip to index MCP and middle MCP
        nd_index  = _dist(landmarks[THUMB_TIP], landmarks[INDEX_MCP]) / palm
        nd_middle = _dist(landmarks[THUMB_TIP], landmarks[MIDDLE_MCP]) / palm
        
        # Use the more generous of the two signals
        signal = max(nd_index, nd_middle * 0.95)
        
        # Hysteresis
        thresh = self.thresh_in if self._is_out else self.thresh_out
        self._is_out = signal > thresh
        
        return self._is_out
    
    def reset(self):
        self._is_out = False


# ── Hand persistence ──

class HandPersistence:
    """
    Holds the last hand reading for a few frames when the hand disappears.
    Prevents chord drops from single-frame detection misses.
    """
    
    def __init__(self, hold_frames: int = 3):
        self._hold_frames = hold_frames
        self._last_hand: Optional[HandData] = None
        self._missing_count = 0
    
    def update(self, hand: Optional[HandData]) -> Optional[HandData]:
        if hand is not None:
            self._last_hand = hand
            self._missing_count = 0
            return hand
        else:
            self._missing_count += 1
            if self._missing_count <= self._hold_frames and self._last_hand is not None:
                return self._last_hand  # hold last reading
            return None
    
    def reset(self):
        self._last_hand = None
        self._missing_count = 0


# ── Module-level detectors ──

_right_fingers = FingerDetector()
_right_thumb = ThumbDetector(thresh_out=0.48, thresh_in=0.32)

_left_fingers = FingerDetector()
_left_thumb = ThumbDetector(thresh_out=0.44, thresh_in=0.28)  # more sensitive for modifier

_right_persistence = HandPersistence(hold_frames=3)
_left_persistence = HandPersistence(hold_frames=3)


# ── Right hand: degree detection ──

def interpret_right_hand(hand: Optional[HandData]) -> Optional[RightHandGesture]:
    """
    Finger count → scale degree. No smoothing — just hysteresis.
    
    Returns None if no hand detected (after persistence expires).
    """
    hand = _right_persistence.update(hand)
    if hand is None:
        return None
    
    lm = hand.landmarks
    finger_count, extended = _right_fingers.update(lm)
    thumb_out = _right_thumb.update(lm)
    
    # Map to degree
    if finger_count == 0 and not thumb_out:
        degree = 0                                          # fist = silence
    elif finger_count == 0 and thumb_out:
        degree = 6                                          # thumb only = VI
    elif thumb_out and finger_count == 1 and extended[3] and not extended[0]:
        degree = 7                                          # thumb + pinky = VII
    elif finger_count == 4:
        degree = 5 if thumb_out else 4                     # open hand = V, 4 fingers = IV
    elif finger_count <= 3:
        degree = finger_count                              # I, II, III
    else:
        degree = min(finger_count, 4)
    
    return RightHandGesture(degree=degree, finger_count=finger_count)


# ── Left hand: modifier detection ──

def interpret_left_hand(hand: Optional[HandData]) -> LeftHandGesture:
    """
    Thumb = flip quality, fingers = extensions. No smoothing.
    
    Returns default gesture if no hand detected.
    """
    _DEFAULT = LeftHandGesture(
        flip_quality=False, velocity=80, add_7th=False,
        add_9th=False, add_11th=False, add_13th=False, gesture_name="no hand"
    )
    
    hand = _left_persistence.update(hand)
    if hand is None:
        return _DEFAULT
    
    lm = hand.landmarks
    finger_count, _ = _left_fingers.update(lm)
    flip = _left_thumb.update(lm)
    
    # Velocity from wrist height (higher hand = louder)
    velocity = max(40, min(127, int(127 - lm[WRIST][1] * 87)))
    
    # Extensions stack
    ext_names = {0: "triad", 1: "7th", 2: "9th", 3: "11th", 4: "13th"}
    name = ("flip " if flip else "") + ext_names.get(finger_count, "triad")
    
    return LeftHandGesture(
        flip_quality=flip,
        velocity=velocity,
        add_7th=finger_count >= 1,
        add_9th=finger_count >= 2,
        add_11th=finger_count >= 3,
        add_13th=finger_count >= 4,
        gesture_name=name,
    )


# ── Reset ──

def reset_gesture_state():
    _right_fingers.reset()
    _right_thumb.reset()
    _left_fingers.reset()
    _left_thumb.reset()
    _right_persistence.reset()
    _left_persistence.reset()
