"""
Drums Strike Mode — Downward strike triggers drums.

Right hand: left side = kick(36), right side = snare(38)
Left hand:  left side = closed-hat(42), right side = crash(49)

Strike = fast downward hand movement (wrist_y delta > threshold).
Velocity from strike speed (faster = louder).
Hand X position determines which of the two drums is hit.
"""

from core.modes.base import Mode

# Drum assignments per hand and side
RIGHT_LEFT_DRUM = 36   # kick
RIGHT_RIGHT_DRUM = 38  # snare
LEFT_LEFT_DRUM = 42    # closed hat
LEFT_RIGHT_DRUM = 49   # crash

DRUM_NAMES = {
    36: "KICK", 38: "SNARE", 42: "CH-HAT", 49: "CRASH",
}

STRIKE_THRESHOLD = 0.05  # wrist_y delta to register as strike
MIN_STRIKE_INTERVAL = 0.06  # seconds between strikes per hand


class DrumsStrikeMode(Mode):
    name = "StrikeDrm"
    description = "Strike down to hit — 4 drums"
    debounce_time = 0.0  # instant

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        self.prev_wrist_y_right = None
        self.prev_wrist_y_left = None
        self.last_strike_time_right = 0.0
        self.last_strike_time_left = 0.0
        self.last_hits = []
        self.left_gesture_name = ""
        # For display: which drum was last hit per hand
        self.right_drum_name = ""
        self.left_drum_name = ""
        # Held notes — released on next frame to avoid zero-length
        self.held_note_right = None
        self.held_note_left = None

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        hits = []

        # Right hand strike detection
        # Release previous frame's held note
        if self.held_note_right is not None:
            midi.send_note(self.held_note_right, velocity=0, on=False)
            self.held_note_right = None

        if right_gesture:
            wy = right_gesture.wrist_y
            wx = right_gesture.wrist_x

            if self.prev_wrist_y_right is not None:
                delta = wy - self.prev_wrist_y_right  # positive = downward
                if delta > STRIKE_THRESHOLD and (now - self.last_strike_time_right) > MIN_STRIKE_INTERVAL:
                    vel = max(50, min(127, int(delta * 1400)))
                    # X position determines drum: left half = kick, right half = snare
                    drum = RIGHT_LEFT_DRUM if wx < 0.5 else RIGHT_RIGHT_DRUM
                    midi.send_note(drum, velocity=vel, on=True)
                    self.held_note_right = drum
                    self.right_drum_name = DRUM_NAMES[drum]
                    hits.append(self.right_drum_name)
                    self.last_strike_time_right = now

            self.prev_wrist_y_right = wy
        else:
            self.prev_wrist_y_right = None

        # Left hand strike detection
        # Release previous frame's held note
        if self.held_note_left is not None:
            midi.send_note(self.held_note_left, velocity=0, on=False)
            self.held_note_left = None

        raw = get_left_hand_raw(left_hand)
        if raw:
            wy = raw['wrist_y']
            wx = raw['wrist_x']

            if self.prev_wrist_y_left is not None:
                delta = wy - self.prev_wrist_y_left
                if delta > STRIKE_THRESHOLD and (now - self.last_strike_time_left) > MIN_STRIKE_INTERVAL:
                    vel = max(50, min(127, int(delta * 1400)))
                    drum = LEFT_LEFT_DRUM if wx < 0.5 else LEFT_RIGHT_DRUM
                    midi.send_note(drum, velocity=vel, on=True)
                    self.held_note_left = drum
                    self.left_drum_name = DRUM_NAMES[drum]
                    hits.append(self.left_drum_name)
                    self.last_strike_time_left = now

            self.prev_wrist_y_left = wy
            self.left_gesture_name = "tracking"
        else:
            self.prev_wrist_y_left = None
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
            'drum_layout': 'strike',
            'strike_zones': {
                'right': [
                    {'name': DRUM_NAMES[RIGHT_LEFT_DRUM], 'side': 'L'},
                    {'name': DRUM_NAMES[RIGHT_RIGHT_DRUM], 'side': 'R'},
                ],
                'left': [
                    {'name': DRUM_NAMES[LEFT_LEFT_DRUM], 'side': 'L'},
                    {'name': DRUM_NAMES[LEFT_RIGHT_DRUM], 'side': 'R'},
                ],
            },
        }

    def on_exit(self, midi):
        if self.held_note_right is not None:
            midi.send_note(self.held_note_right, velocity=0, on=False)
            self.held_note_right = None
        if self.held_note_left is not None:
            midi.send_note(self.held_note_left, velocity=0, on=False)
            self.held_note_left = None
        self.prev_wrist_y_right = None
        self.prev_wrist_y_left = None
        super().on_exit(midi)

    def get_help_sections(self):
        return [
            ("RIGHT HAND (strike)", [
                "Strike down     =  Trigger drum",
                "Left half       =  Kick (36)",
                "Right half      =  Snare (38)",
                "Strike speed    =  Velocity",
            ]),
            ("LEFT HAND (strike)", [
                "Strike down     =  Trigger drum",
                "Left half       =  Closed Hat (42)",
                "Right half      =  Crash (49)",
                "Strike speed    =  Velocity",
            ]),
        ]
