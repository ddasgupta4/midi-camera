"""
Drums Zone Mode — Screen divided into 8 zones (2 rows × 4 columns).

Top row:    crash(49), ride(51), open-hat(46), splash(55)
Bottom row: kick(36), snare(38), closed-hat(42), tom(45)

Each hand triggers whatever zone its wrist is in. A hit fires when:
  (a) the hand ENTERS a new zone, or
  (b) the hand is already in a zone and the wrist moves DOWNWARD faster than
      a retrigger threshold (so you can repeatedly hit a drum without leaving
      the zone).

Velocity = downward component of wrist motion (normalized by time), so slow
drift doesn't produce loud hits.

Held notes are released on a short decay timer (~80 ms) rather than held
indefinitely — drums should not sustain.
"""

from core.modes.base import Mode
from core.gesture_filters import EMA, VelocityTracker

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

# Retrigger threshold in screen-heights per second (downward)
RETRIGGER_VEL = 0.8
# How long held notes live after a hit (so the sample fully plays)
NOTE_DECAY_SEC = 0.08
# Minimum time between retriggers on same zone (ms): prevents one motion
# from firing on consecutive frames as it continues downward.
MIN_RETRIGGER_INTERVAL = 0.06


def _pos_to_zone(x: float, y: float) -> tuple[int, int]:
    """Convert normalized (0-1) position to (row, col) zone index."""
    col = min(3, max(0, int(x * 4)))
    row = 0 if y < 0.5 else 1
    return row, col


def _zone_note(row: int, col: int) -> int:
    return ZONE_GRID[row][col]


class _HandState:
    """Per-hand tracking state for zone drums."""
    def __init__(self):
        self.ema_y = EMA(alpha=0.45)
        self.vel_y = VelocityTracker()
        self.prev_zone: tuple[int, int] | None = None
        self.held_note: int | None = None
        self.held_until: float = 0.0
        self.last_hit_time: float = 0.0
        self.last_pos: tuple[float, float] | None = None  # (x, y) for display

    def reset(self):
        self.ema_y.reset()
        self.vel_y.reset()
        self.prev_zone = None
        self.held_note = None
        self.held_until = 0.0
        self.last_hit_time = 0.0
        self.last_pos = None


class DrumsZoneMode(Mode):
    name = "ZoneDrm"
    description = "8-zone drum grid — move or strike to trigger"
    debounce_time = 0.0  # instant

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        self._right = _HandState()
        self._left = _HandState()
        self.last_hits = []
        self.active_zones = set()   # zones where a hand currently is
        self.flash_times = {}       # {(row, col): last_hit_time} for overlay
        self.left_gesture_name = ""

    def _release_expired(self, state: _HandState, midi, now: float):
        if state.held_note is not None and now >= state.held_until:
            midi.send_note(state.held_note, velocity=0, on=False)
            state.held_note = None

    def _fire(self, state: _HandState, midi, note: int, vel: int, now: float, hits: list):
        # Release any previous held note first (drum decay)
        if state.held_note is not None:
            midi.send_note(state.held_note, velocity=0, on=False)
        midi.send_note(note, velocity=vel, on=True)
        state.held_note = note
        state.held_until = now + NOTE_DECAY_SEC
        state.last_hit_time = now
        hits.append(DRUM_NAMES[note])

    def _process_hand(self, state: _HandState, x: float, y: float,
                      midi, now: float, hits: list):
        # Smooth wrist_y for velocity computation
        y_s = state.ema_y.update(y)
        vel_per_sec, _dt = state.vel_y.update(y_s, now)  # +ve = moving down

        zone = _pos_to_zone(x, y)
        self.active_zones.add(zone)
        state.last_pos = (x, y)

        zone_changed = zone != state.prev_zone
        downward_strike = (vel_per_sec > RETRIGGER_VEL
                           and (now - state.last_hit_time) > MIN_RETRIGGER_INTERVAL)

        should_fire = zone_changed or downward_strike
        if should_fire:
            note = _zone_note(*zone)
            # Velocity: reward striking motion, not lateral drift
            downward_component = max(0.0, vel_per_sec)
            v = int(60 + min(67, downward_component * 25))
            self._fire(state, midi, note, max(50, min(127, v)), now, hits)
            self.flash_times[zone] = now

        state.prev_zone = zone

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        hits = []
        self.active_zones = set()

        # Expire decay timers first
        self._release_expired(self._right, midi, now)
        self._release_expired(self._left, midi, now)

        # Right hand
        if right_gesture:
            self._process_hand(self._right, right_gesture.wrist_x, right_gesture.wrist_y,
                               midi, now, hits)
        else:
            if self._right.held_note is not None:
                midi.send_note(self._right.held_note, velocity=0, on=False)
            self._right.reset()

        # Left hand
        raw = get_left_hand_raw(left_hand)
        if raw:
            self._process_hand(self._left, raw['wrist_x'], raw['wrist_y'],
                               midi, now, hits)
            self.left_gesture_name = "tracking"
        else:
            if self._left.held_note is not None:
                midi.send_note(self._left.held_note, velocity=0, on=False)
            self._left.reset()
            self.left_gesture_name = "no hand"

        if hits:
            self.last_hits = hits

        # Expire old flash entries (keep last 0.2s)
        self.flash_times = {k: t for k, t in self.flash_times.items() if now - t < 0.2}

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
            'zone_flash_times': dict(self.flash_times),
            'zone_hand_positions': {
                'right': self._right.last_pos,
                'left': self._left.last_pos,
            },
            'zone_now': now,
        }

    def on_exit(self, midi):
        if self._right.held_note is not None:
            midi.send_note(self._right.held_note, velocity=0, on=False)
        if self._left.held_note is not None:
            midi.send_note(self._left.held_note, velocity=0, on=False)
        self._right.reset()
        self._left.reset()
        self.flash_times = {}
        super().on_exit(midi)

    def get_help_sections(self):
        return [
            ("ZONE GRID (2×4)", [
                "Top:    CRASH  RIDE   OP-HAT  SPLASH",
                "Bottom: KICK   SNARE  CH-HAT  TOM",
                "",
                "Move hand to new zone = trigger drum",
                "Strike down in zone   = retrigger",
                "Wrist down-speed      = velocity",
            ]),
            ("CONTROLS", [
                "Both hands tracked independently",
                "Notes decay ~80ms (drum-like)",
            ]),
        ]
