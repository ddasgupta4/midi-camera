"""
Drums Finger Mode — Individual finger triggers.

Right hand: index=kick(36), middle=snare(38), ring=closed-hat(42), pinky=open-hat(46)
Left hand:  index=crash(49), middle=ride(51), ring=low-tom(45), pinky=high-tom(48)
Thumb on either hand = accent (velocity +30).
Rising edge detection: finger extending triggers the hit.
Velocity from wrist height (higher hand = harder hit).
No debounce — drums need to be instant.
"""

from core.modes.base import Mode
from core.chord_engine import midi_to_note_name

# MIDI note assignments (General MIDI drum map)
RIGHT_DRUMS = [36, 38, 42, 46]  # kick, snare, closed-hat, open-hat
LEFT_DRUMS = [49, 51, 45, 48]   # crash, ride, low-tom, high-tom

DRUM_NAMES = {
    36: "KICK", 38: "SNARE", 42: "CH-HAT", 46: "OP-HAT",
    49: "CRASH", 51: "RIDE", 45: "LO-TOM", 48: "HI-TOM",
}


class DrumsFingerMode(Mode):
    name = "FingerDrm"
    description = "Finger triggers — 8 drum pads"
    debounce_time = 0.0  # no debounce — instant

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        # Previous frame extended state per finger: {hand: [index, middle, ring, pinky]}
        self.prev_right = [False, False, False, False]
        self.prev_left = [False, False, False, False]
        self.last_hits = []  # for display
        self.left_gesture_name = ""

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        hits = []

        # Right hand
        if right_gesture:
            # We need per-finger extended state from RightHandGesture
            # But RightHandGesture only has degree and finger_count
            # We need to re-detect fingers — use the raw landmark approach
            # Actually, interpret_right_hand already ran the finger detector
            # We can access the detector state directly
            from core.gesture import _right_fingers, _right_thumb
            current_right = list(_right_fingers._states)
            thumb_accent = _right_thumb._is_out

            # Velocity from wrist height (top of frame = loud)
            vel = max(50, min(127, int(127 - right_gesture.wrist_y * 77)))
            if thumb_accent:
                vel = min(127, vel + 30)

            # Rising edge detection
            for i in range(4):
                if current_right[i] and not self.prev_right[i]:
                    midi.send_note(RIGHT_DRUMS[i], velocity=vel, on=True)
                    hits.append(DRUM_NAMES[RIGHT_DRUMS[i]])
                elif not current_right[i] and self.prev_right[i]:
                    midi.send_note(RIGHT_DRUMS[i], velocity=0, on=False)

            self.prev_right = current_right
        else:
            # Release all right-hand drums
            for i in range(4):
                if self.prev_right[i]:
                    midi.send_note(RIGHT_DRUMS[i], velocity=0, on=False)
            self.prev_right = [False, False, False, False]

        # Left hand
        raw = get_left_hand_raw(left_hand)
        if raw:
            current_left = list(raw['extended'])
            thumb_accent = raw['thumb_out']

            vel = max(50, min(127, int(127 - raw['wrist_y'] * 77)))
            if thumb_accent:
                vel = min(127, vel + 30)

            for i in range(4):
                if current_left[i] and not self.prev_left[i]:
                    midi.send_note(LEFT_DRUMS[i], velocity=vel, on=True)
                    hits.append(DRUM_NAMES[LEFT_DRUMS[i]])
                elif not current_left[i] and self.prev_left[i]:
                    midi.send_note(LEFT_DRUMS[i], velocity=0, on=False)

            self.prev_left = current_left
            self.left_gesture_name = "tracking"
        else:
            for i in range(4):
                if self.prev_left[i]:
                    midi.send_note(LEFT_DRUMS[i], velocity=0, on=False)
            self.prev_left = [False, False, False, False]
            self.left_gesture_name = "no hand"

        if hits:
            self.last_hits = hits

        return {
            'type': 'drums',
            'chord_info': {},
            'velocity': 0,
            'left_gesture_name': self.left_gesture_name,
            'sauce_mode': False,
            'desired_notes': [],
            'desired_since': 0.0,
            'drum_hits': self.last_hits,
            'drum_layout': 'finger',
            'drum_pads': self._pad_state(),
        }

    def _pad_state(self):
        """Return list of {name, active} for all 8 pads for display."""
        pads = []
        for i, note in enumerate(RIGHT_DRUMS):
            pads.append({'name': DRUM_NAMES[note], 'active': self.prev_right[i], 'side': 'R'})
        for i, note in enumerate(LEFT_DRUMS):
            pads.append({'name': DRUM_NAMES[note], 'active': self.prev_left[i], 'side': 'L'})
        return pads

    def on_exit(self, midi):
        # Note off for any held drums
        for i in range(4):
            if self.prev_right[i]:
                midi.send_note(RIGHT_DRUMS[i], velocity=0, on=False)
            if self.prev_left[i]:
                midi.send_note(LEFT_DRUMS[i], velocity=0, on=False)
        self.prev_right = [False, False, False, False]
        self.prev_left = [False, False, False, False]
        self._current = None
        self._desired_notes = []
        self._desired_info = {}

    def get_help_sections(self):
        return [
            ("RIGHT HAND (drums)", [
                "Index           =  Kick (36)",
                "Middle          =  Snare (38)",
                "Ring            =  Closed Hat (42)",
                "Pinky           =  Open Hat (46)",
                "Thumb           =  Accent (+30 vel)",
                "Wrist height    =  Velocity",
            ]),
            ("LEFT HAND (drums)", [
                "Index           =  Crash (49)",
                "Middle          =  Ride (51)",
                "Ring            =  Low Tom (45)",
                "Pinky           =  High Tom (48)",
                "Thumb           =  Accent (+30 vel)",
                "Wrist height    =  Velocity",
            ]),
        ]
