"""
Drums Zone Mode — Screen divided into 8 zones (2 rows × 4 columns).

Top row:    crash(49), ride(51), open-hat(46), splash(55)
Bottom row: kick(36), snare(38), closed-hat(42), tom(45)

Each hand triggers whatever zone its wrist is in.
Hit = hand ENTERS a new zone (zone change detection).
Velocity from hand speed (distance moved since last frame).

Uses reference counting per zone so overlapping hands don't cause
premature note-off when one hand leaves.
"""

import math
from core.modes.base import Mode

# Zone layout: 2 rows × 4 columns
# [row][col] → MIDI note
ZONE_GRID = [
    [49, 51, 46, 55],  # top: crash, ride, open-hat, splash
    [36, 38, 42, 45],  # bottom: kick, snare, closed-hat, tom
]

ZONE_NAMES = [
    ["CRASH", "RIDE", "OP-HAT", "SPLASH"],
    ["KICK", "SNARE", "CH-HAT", "TOM"],
]

DRUM_NAMES = {
    49: "CRASH", 51: "RIDE", 46: "OP-HAT", 55: "SPLASH",
    36: "KICK", 38: "SNARE", 42: "CH-HAT", 45: "TOM",
}


def _pos_to_zone(x: float, y: float) -> tuple[int, int]:
    """Convert normalized (0-1) position to (row, col) zone index."""
    col = min(3, max(0, int(x * 4)))
    row = 0 if y < 0.5 else 1
    return row, col


def _zone_note(row: int, col: int) -> int:
    return ZONE_GRID[row][col]


class DrumsZoneMode(Mode):
    name = "ZoneDrm"
    description = "8-zone drum grid — move hands to trigger"
    debounce_time = 0.0  # instant

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        # Previous zone per hand: (row, col) or None
        self.prev_zone_right = None
        self.prev_zone_left = None
        # Previous positions for velocity calculation
        self.prev_pos_right = None
        self.prev_pos_left = None
        # Reference count per zone: (row, col) → number of hands in zone
        self.zone_ref_count = {}
        self.last_hits = []
        self.active_zones = set()  # (row, col) currently active for display
        self.left_gesture_name = ""

    def _zone_enter(self, zone, midi, velocity):
        """Increment ref count for zone. Send note-on if 0→1."""
        count = self.zone_ref_count.get(zone, 0)
        self.zone_ref_count[zone] = count + 1
        if count == 0:
            note = _zone_note(*zone)
            midi.send_note(note, velocity=velocity, on=True)

    def _zone_leave(self, zone, midi):
        """Decrement ref count for zone. Send note-off if 1→0."""
        count = self.zone_ref_count.get(zone, 0)
        if count <= 0:
            return
        count -= 1
        self.zone_ref_count[zone] = count
        if count == 0:
            note = _zone_note(*zone)
            midi.send_note(note, velocity=0, on=False)

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        hits = []
        self.active_zones = set()

        # Right hand
        if right_gesture:
            x, y = right_gesture.wrist_x, right_gesture.wrist_y
            zone = _pos_to_zone(x, y)
            self.active_zones.add(zone)

            # Velocity from hand speed
            vel = 80
            if self.prev_pos_right is not None:
                dx = x - self.prev_pos_right[0]
                dy = y - self.prev_pos_right[1]
                speed = math.sqrt(dx * dx + dy * dy)
                vel = max(50, min(127, int(speed * 1500)))

            if zone != self.prev_zone_right:
                # Leave previous zone
                if self.prev_zone_right is not None:
                    self._zone_leave(self.prev_zone_right, midi)
                # Enter new zone
                self._zone_enter(zone, midi, vel)
                hits.append(DRUM_NAMES[_zone_note(*zone)])

            self.prev_zone_right = zone
            self.prev_pos_right = (x, y)
        else:
            if self.prev_zone_right is not None:
                self._zone_leave(self.prev_zone_right, midi)
            self.prev_zone_right = None
            self.prev_pos_right = None

        # Left hand
        raw = get_left_hand_raw(left_hand)
        if raw:
            x, y = raw['wrist_x'], raw['wrist_y']
            zone = _pos_to_zone(x, y)
            self.active_zones.add(zone)

            vel = 80
            if self.prev_pos_left is not None:
                dx = x - self.prev_pos_left[0]
                dy = y - self.prev_pos_left[1]
                speed = math.sqrt(dx * dx + dy * dy)
                vel = max(50, min(127, int(speed * 1500)))

            if zone != self.prev_zone_left:
                if self.prev_zone_left is not None:
                    self._zone_leave(self.prev_zone_left, midi)
                self._zone_enter(zone, midi, vel)
                hits.append(DRUM_NAMES[_zone_note(*zone)])

            self.prev_zone_left = zone
            self.prev_pos_left = (x, y)
            self.left_gesture_name = "tracking"
        else:
            if self.prev_zone_left is not None:
                self._zone_leave(self.prev_zone_left, midi)
            self.prev_zone_left = None
            self.prev_pos_left = None
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
            'drum_layout': 'zone',
            'zone_grid': ZONE_NAMES,
            'active_zones': list(self.active_zones),
        }

    def on_exit(self, midi):
        # Release all zones with active ref counts
        for zone, count in self.zone_ref_count.items():
            if count > 0:
                note = _zone_note(*zone)
                midi.send_note(note, velocity=0, on=False)
        self.zone_ref_count.clear()
        self.prev_zone_right = None
        self.prev_zone_left = None
        self.prev_pos_right = None
        self.prev_pos_left = None
        super().on_exit(midi)

    def get_help_sections(self):
        return [
            ("ZONE GRID (2×4)", [
                "Top:    CRASH  RIDE   OP-HAT  SPLASH",
                "Bottom: KICK   SNARE  CH-HAT  TOM",
                "",
                "Move hand to zone = trigger drum",
                "Hand speed        = velocity",
            ]),
            ("CONTROLS", [
                "Both hands tracked independently",
                "Zone change = hit (not continuous)",
            ]),
        ]
