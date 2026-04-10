"""
MIDI Mapper Mode — Map hand axes to MIDI CC values.

Six continuous CC streams, smoothed with per-axis EMA and gated by a tiny
deadzone so hand tremor at rest doesn't flood the DAW with noise. Axes can
be inverted and each axis's CC number can be reassigned live (session-only)
so you don't have to edit code to match your synth.

Default assignments:
  Right hand: X→CC1, Y→CC2, finger count→CC5
  Left hand:  X→CC3, Y→CC4, finger count→CC6

Continuous stream, no debounce (the filter + deadzone are the noise gate).
"""

from core.modes.base import Mode
from core.gesture_filters import EMA


# Axis identity (stable across rebinds)
AXIS_R_X = 'R.X'
AXIS_R_Y = 'R.Y'
AXIS_R_FING = 'R.Fing'
AXIS_L_X = 'L.X'
AXIS_L_Y = 'L.Y'
AXIS_L_FING = 'L.Fing'

AXIS_ORDER = [AXIS_R_X, AXIS_R_Y, AXIS_R_FING, AXIS_L_X, AXIS_L_Y, AXIS_L_FING]

DEFAULT_CC = {
    AXIS_R_X: 1,
    AXIS_R_Y: 2,
    AXIS_R_FING: 5,
    AXIS_L_X: 3,
    AXIS_L_Y: 4,
    AXIS_L_FING: 6,
}

# Per-axis EMA alpha: position axes are smooth+responsive, finger count is
# inherently discrete (0-5) and needs heavier smoothing.
ALPHA_POS = 0.4
ALPHA_FING = 0.15

# Deadzone: suppress output when the smoothed float value has drifted less
# than this much since the last send. Int equality alone isn't enough to
# stop tremor spam because small float drift can bounce across a boundary.
DEADZONE = 0.6  # in 0-127 units


class MidiMapperMode(Mode):
    name = "Mapper"
    description = "Hand axes → MIDI CC (6 channels, rebindable)"
    debounce_time = 0.0  # continuous stream

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        # Session-level remapping state
        self.cc_assign: dict[str, int] = dict(DEFAULT_CC)
        self.inverted: dict[str, bool] = {a: False for a in AXIS_ORDER}
        self.selected_idx: int = 0  # for rebind UI — which axis is selected

        # Per-axis filters and sent-value tracking
        self._ema: dict[str, EMA] = {
            AXIS_R_X: EMA(ALPHA_POS),
            AXIS_R_Y: EMA(ALPHA_POS),
            AXIS_R_FING: EMA(ALPHA_FING),
            AXIS_L_X: EMA(ALPHA_POS),
            AXIS_L_Y: EMA(ALPHA_POS),
            AXIS_L_FING: EMA(ALPHA_FING),
        }
        # Last float value that was actually sent (for deadzone compare)
        self._last_sent: dict[str, float] = {a: -1.0 for a in AXIS_ORDER}
        # Last *integer* sent per CC number (for dedup after rebind)
        self._cc_last: dict[int, int] = {}

        self.left_gesture_name = ""
        # Last raw positions for overlay crosshairs
        self.right_pos: tuple[float, float] | None = None
        self.left_pos: tuple[float, float] | None = None

    # ── Filtering pipeline ────────────────────────────────────────────
    def _update_axis(self, axis: str, raw_01: float) -> float:
        """Feed a 0..1 raw value through EMA, apply invert, return 0..127 float."""
        if self.inverted[axis]:
            raw_01 = 1.0 - raw_01
        smoothed = self._ema[axis].update(raw_01 * 127.0)
        return max(0.0, min(127.0, smoothed))

    def _maybe_send(self, axis: str, value_f: float, midi):
        last = self._last_sent[axis]
        if last < 0 or abs(value_f - last) >= DEADZONE:
            cc = self.cc_assign[axis]
            int_val = int(round(value_f))
            # Dedup per actual CC number (rebind can point two axes at the
            # same CC — we still only send when the int changes).
            if self._cc_last.get(cc) != int_val:
                midi.send_cc(cc, int_val)
                self._cc_last[cc] = int_val
            self._last_sent[axis] = value_f

    def on_enter(self, midi):
        # Reset filter state so stale values don't leak across mode switches
        for ema in self._ema.values():
            ema.reset()
        self._last_sent = {a: -1.0 for a in AXIS_ORDER}
        self._cc_last = {}

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        # Right hand
        if right_gesture:
            rx = self._update_axis(AXIS_R_X, right_gesture.wrist_x)
            ry = self._update_axis(AXIS_R_Y, right_gesture.wrist_y)
            rf = self._update_axis(AXIS_R_FING, right_gesture.finger_count / 5.0)
            self._maybe_send(AXIS_R_X, rx, midi)
            self._maybe_send(AXIS_R_Y, ry, midi)
            self._maybe_send(AXIS_R_FING, rf, midi)
            self.right_pos = (right_gesture.wrist_x, right_gesture.wrist_y)
        else:
            self.right_pos = None

        # Left hand
        raw = get_left_hand_raw(left_hand)
        if raw:
            lx = self._update_axis(AXIS_L_X, raw['wrist_x'])
            ly = self._update_axis(AXIS_L_Y, raw['wrist_y'])
            lf = self._update_axis(AXIS_L_FING, raw['finger_count'] / 5.0)
            self._maybe_send(AXIS_L_X, lx, midi)
            self._maybe_send(AXIS_L_Y, ly, midi)
            self._maybe_send(AXIS_L_FING, lf, midi)
            self.left_pos = (raw['wrist_x'], raw['wrist_y'])
            self.left_gesture_name = "tracking"
        else:
            self.left_pos = None
            self.left_gesture_name = "no hand"

        # Build display info for overlay (current smoothed value per axis)
        cc_display = []
        for i, axis in enumerate(AXIS_ORDER):
            val = int(round(max(0.0, self._ema[axis].value)))
            cc_display.append({
                'cc': self.cc_assign[axis],
                'name': axis + (' ⇅' if self.inverted[axis] else ''),
                'value': val,
                'selected': (i == self.selected_idx),
            })

        return {
            'type': 'mapper',
            'chord_info': {},
            'velocity': 0,
            'left_gesture_name': self.left_gesture_name,
            'sauce_mode': False,
            'desired_notes': [],
            'desired_since': 0.0,
            'cc_display': cc_display,
            'mapper_positions': {
                'right': self.right_pos,
                'left': self.left_pos,
            },
        }

    def handle_key(self, key: int, raw_key: int, **context) -> bool:
        """Rebind keys (session-only; reset with 'R' in this mode):

        [ / ]   cycle selected axis
        - / =   decrease / increase CC number for selected axis
        i       invert selected axis
        0       reset all to defaults
        """
        if key == ord('['):
            self.selected_idx = (self.selected_idx - 1) % len(AXIS_ORDER)
            return True
        if key == ord(']'):
            self.selected_idx = (self.selected_idx + 1) % len(AXIS_ORDER)
            return True
        if key == ord('-'):
            axis = AXIS_ORDER[self.selected_idx]
            self.cc_assign[axis] = max(0, self.cc_assign[axis] - 1)
            self._cc_last = {}  # force resend on new CC
            return True
        if key == ord('='):
            axis = AXIS_ORDER[self.selected_idx]
            self.cc_assign[axis] = min(127, self.cc_assign[axis] + 1)
            self._cc_last = {}
            return True
        if key == ord('i'):
            axis = AXIS_ORDER[self.selected_idx]
            self.inverted[axis] = not self.inverted[axis]
            return True
        if key == ord('0'):
            self.cc_assign = dict(DEFAULT_CC)
            self.inverted = {a: False for a in AXIS_ORDER}
            self._cc_last = {}
            return True
        return False

    def on_exit(self, midi):
        super().on_exit(midi)
        # Zero all assigned CCs on exit (use current assignments)
        for cc in set(self.cc_assign.values()):
            midi.send_cc(cc, 0)
        self._last_sent = {a: -1.0 for a in AXIS_ORDER}
        self._cc_last = {}

    def get_help_sections(self):
        return [
            ("RIGHT HAND → CC", [
                f"X position      =  CC{self.cc_assign[AXIS_R_X]} (0-127)",
                f"Y position      =  CC{self.cc_assign[AXIS_R_Y]} (0-127)",
                f"Finger count    =  CC{self.cc_assign[AXIS_R_FING]} (0-127)",
            ]),
            ("LEFT HAND → CC", [
                f"X position      =  CC{self.cc_assign[AXIS_L_X]} (0-127)",
                f"Y position      =  CC{self.cc_assign[AXIS_L_Y]} (0-127)",
                f"Finger count    =  CC{self.cc_assign[AXIS_L_FING]} (0-127)",
            ]),
            ("REBIND KEYS", [
                "[ ]             =  Select axis",
                "- =             =  CC number -/+",
                "i               =  Invert selected axis",
                "0               =  Reset all to defaults",
            ]),
        ]
