"""
MIDI Mapper Mode — Map hand axes to MIDI CC values.

Right hand: X→CC1, Y→CC2, finger count→CC5 (0-127)
Left hand:  X→CC3, Y→CC4, finger count→CC6 (0-127)
All values smoothed with exponential moving average (alpha=0.3).
Continuous stream, no debounce needed.
"""

from core.modes.base import Mode


# CC assignments
CC_RIGHT_X = 1
CC_RIGHT_Y = 2
CC_LEFT_X = 3
CC_LEFT_Y = 4
CC_RIGHT_FINGERS = 5
CC_LEFT_FINGERS = 6

CC_NAMES = {
    CC_RIGHT_X: "R.X",
    CC_RIGHT_Y: "R.Y",
    CC_LEFT_X: "L.X",
    CC_LEFT_Y: "L.Y",
    CC_RIGHT_FINGERS: "R.Fing",
    CC_LEFT_FINGERS: "L.Fing",
}

ALPHA = 0.3  # EMA smoothing factor (higher = less smoothing)


class MidiMapperMode(Mode):
    name = "Mapper"
    description = "Hand axes → MIDI CC (6 channels)"
    debounce_time = 0.0  # continuous stream

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        # Smoothed CC values (float for EMA, int for actual sent value)
        self.cc_smooth = {cc: 0.0 for cc in CC_NAMES}
        self.cc_sent = {cc: -1 for cc in CC_NAMES}  # -1 = never sent
        self.left_gesture_name = ""

    def _ema(self, cc: int, raw_value: float) -> int:
        """Exponential moving average, returns clamped int 0-127."""
        self.cc_smooth[cc] = ALPHA * raw_value + (1 - ALPHA) * self.cc_smooth[cc]
        return max(0, min(127, int(self.cc_smooth[cc])))

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        cc_values = {}

        # Right hand axes
        if right_gesture:
            cc_values[CC_RIGHT_X] = self._ema(CC_RIGHT_X, right_gesture.wrist_x * 127)
            cc_values[CC_RIGHT_Y] = self._ema(CC_RIGHT_Y, right_gesture.wrist_y * 127)
            cc_values[CC_RIGHT_FINGERS] = self._ema(CC_RIGHT_FINGERS, right_gesture.finger_count * 25.4)  # 0-5 → 0-127
        else:
            # Keep last smoothed values (no sudden drops)
            for cc in (CC_RIGHT_X, CC_RIGHT_Y, CC_RIGHT_FINGERS):
                cc_values[cc] = int(self.cc_smooth[cc])

        # Left hand axes
        raw = get_left_hand_raw(left_hand)
        if raw:
            cc_values[CC_LEFT_X] = self._ema(CC_LEFT_X, raw['wrist_x'] * 127)
            cc_values[CC_LEFT_Y] = self._ema(CC_LEFT_Y, raw['wrist_y'] * 127)
            cc_values[CC_LEFT_FINGERS] = self._ema(CC_LEFT_FINGERS, raw['finger_count'] * 25.4)
            self.left_gesture_name = "tracking"
        else:
            for cc in (CC_LEFT_X, CC_LEFT_Y, CC_LEFT_FINGERS):
                cc_values[cc] = int(self.cc_smooth[cc])
            self.left_gesture_name = "no hand"

        # Send CC values (only if changed)
        for cc, val in cc_values.items():
            if val != self.cc_sent[cc]:
                midi.send_cc(cc, val)
                self.cc_sent[cc] = val

        # Build display info for overlay
        cc_display = []
        for cc in (CC_RIGHT_X, CC_RIGHT_Y, CC_RIGHT_FINGERS, CC_LEFT_X, CC_LEFT_Y, CC_LEFT_FINGERS):
            cc_display.append({
                'cc': cc,
                'name': CC_NAMES[cc],
                'value': cc_values.get(cc, 0),
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
        }

    def on_exit(self, midi):
        super().on_exit(midi)
        # Zero all CCs on exit
        for cc in CC_NAMES:
            midi.send_cc(cc, 0)
        self.cc_sent = {cc: -1 for cc in CC_NAMES}

    def get_help_sections(self):
        return [
            ("RIGHT HAND → CC", [
                f"X position      =  CC{CC_RIGHT_X} (0-127)",
                f"Y position      =  CC{CC_RIGHT_Y} (0-127)",
                f"Finger count    =  CC{CC_RIGHT_FINGERS} (0-127)",
            ]),
            ("LEFT HAND → CC", [
                f"X position      =  CC{CC_LEFT_X} (0-127)",
                f"Y position      =  CC{CC_LEFT_Y} (0-127)",
                f"Finger count    =  CC{CC_LEFT_FINGERS} (0-127)",
            ]),
        ]
