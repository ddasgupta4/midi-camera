"""
Drums Finger Mode — Individual finger triggers.

Right hand: index=kick(36), middle=snare(38), ring=closed-hat(42), pinky=open-hat(46)
Left hand:  index=crash(49), middle=ride(51), ring=low-tom(45), pinky=high-tom(48)
Thumb on either hand = accent (velocity +30).
Rising edge detection: finger extending triggers the hit.

Velocity combines two signals:
  - base: wrist height (high = loud)
  - strike bonus: when the wrist is also moving downward at hit-time,
                  add a speed-proportional boost (natural drumming feel)

Per-finger debounce (20 ms) prevents flicker retriggers when MediaPipe
hysteresis state bounces right on the boundary.

Hit decay tracking: stores each finger's last-hit time so the overlay can
flash briefly on strike instead of staying lit for the full finger hold.
"""

from core.modes.base import Mode
from core.gesture_filters import EMA, VelocityTracker

# MIDI note assignments (General MIDI drum map)
RIGHT_DRUMS = [36, 38, 42, 46]  # kick, snare, closed-hat, open-hat
LEFT_DRUMS = [49, 51, 45, 48]   # crash, ride, low-tom, high-tom

DRUM_NAMES = {
    36: "KICK", 38: "SNARE", 42: "CH-HAT", 46: "OP-HAT",
    49: "CRASH", 51: "RIDE", 45: "LO-TOM", 48: "HI-TOM",
}

# Per-finger trigger cooldown — short enough to allow fast rolls but
# long enough to absorb a 1-frame hysteresis bounce.
FINGER_COOLDOWN = 0.02  # 20 ms


class _HandState:
    def __init__(self):
        self.prev_extended = [False, False, False, False]
        self.last_hit_time = [0.0, 0.0, 0.0, 0.0]
        self.ema_y = EMA(alpha=0.5)
        self.vel_y = VelocityTracker()
        self.last_pos: tuple[float, float] | None = None
        # For overlay: last hit timestamp per drum slot (even after release)
        self.flash_time = [0.0, 0.0, 0.0, 0.0]

    def reset(self):
        self.prev_extended = [False, False, False, False]
        self.last_hit_time = [0.0, 0.0, 0.0, 0.0]
        self.ema_y.reset()
        self.vel_y.reset()
        self.last_pos = None
        self.flash_time = [0.0, 0.0, 0.0, 0.0]


def _strike_velocity(wrist_y: float, vel_per_sec: float, accent: bool) -> int:
    """Combine wrist-height base and downward-velocity bonus."""
    base = 70 - wrist_y * 30  # 40..70 range
    bonus = max(0.0, vel_per_sec) * 18.0  # 0..~57 for fast strikes
    vel = int(base + bonus)
    if accent:
        vel += 30
    return max(50, min(127, vel))


class DrumsFingerMode(Mode):
    name = "FingerDrm"
    description = "Finger triggers — 8 drum pads"
    debounce_time = 0.0

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        self._right = _HandState()
        self._left = _HandState()
        self.last_hits = []
        self.left_gesture_name = ""

    def on_enter(self, midi):
        self._right.reset()
        self._left.reset()

    def _process_hand(self, state: _HandState, current_extended: list[bool],
                      wrist_x: float, wrist_y: float, thumb_accent: bool,
                      drums: list[int], midi, now: float, hits: list):
        state.last_pos = (wrist_x, wrist_y)

        # Smoothed wrist_y for velocity; smoothing is mild so real strikes
        # still register.
        y_s = state.ema_y.update(wrist_y)
        vel_per_sec, _dt = state.vel_y.update(y_s, now)  # +ve = downward

        for i in range(4):
            extending = current_extended[i] and not state.prev_extended[i]
            releasing = not current_extended[i] and state.prev_extended[i]

            if extending:
                if now - state.last_hit_time[i] >= FINGER_COOLDOWN:
                    vel = _strike_velocity(wrist_y, vel_per_sec, thumb_accent)
                    midi.send_note(drums[i], velocity=vel, on=True)
                    hits.append(DRUM_NAMES[drums[i]])
                    state.last_hit_time[i] = now
                    state.flash_time[i] = now
            elif releasing:
                midi.send_note(drums[i], velocity=0, on=False)

        state.prev_extended = list(current_extended)

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        hits = []

        # Right hand
        if right_gesture:
            self._process_hand(
                self._right,
                list(right_gesture.extended),
                right_gesture.wrist_x, right_gesture.wrist_y,
                right_gesture.thumb_out,
                RIGHT_DRUMS,
                midi, now, hits,
            )
        else:
            # Release any still-held notes
            for i in range(4):
                if self._right.prev_extended[i]:
                    midi.send_note(RIGHT_DRUMS[i], velocity=0, on=False)
            self._right.reset()

        # Left hand
        raw = get_left_hand_raw(left_hand)
        if raw:
            self._process_hand(
                self._left,
                list(raw['extended']),
                raw['wrist_x'], raw['wrist_y'],
                raw['thumb_out'],
                LEFT_DRUMS,
                midi, now, hits,
            )
            self.left_gesture_name = "tracking"
        else:
            for i in range(4):
                if self._left.prev_extended[i]:
                    midi.send_note(LEFT_DRUMS[i], velocity=0, on=False)
            self._left.reset()
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
            'finger_drum_meta': {
                'right_hand': {
                    'pos': self._right.last_pos,
                    'drums': RIGHT_DRUMS,
                    'flash_times': list(self._right.flash_time),
                    'held': list(self._right.prev_extended),
                },
                'left_hand': {
                    'pos': self._left.last_pos,
                    'drums': LEFT_DRUMS,
                    'flash_times': list(self._left.flash_time),
                    'held': list(self._left.prev_extended),
                },
                'now': now,
            },
        }

    def _pad_state(self):
        """Return list of {name, active} for all 8 pads for display."""
        pads = []
        for i, note in enumerate(RIGHT_DRUMS):
            pads.append({'name': DRUM_NAMES[note], 'active': self._right.prev_extended[i], 'side': 'R'})
        for i, note in enumerate(LEFT_DRUMS):
            pads.append({'name': DRUM_NAMES[note], 'active': self._left.prev_extended[i], 'side': 'L'})
        return pads

    def on_exit(self, midi):
        for i in range(4):
            if self._right.prev_extended[i]:
                midi.send_note(RIGHT_DRUMS[i], velocity=0, on=False)
            if self._left.prev_extended[i]:
                midi.send_note(LEFT_DRUMS[i], velocity=0, on=False)
        self._right.reset()
        self._left.reset()
        super().on_exit(midi)

    def get_help_sections(self):
        return [
            ("RIGHT HAND (drums)", [
                "Index           =  Kick (36)",
                "Middle          =  Snare (38)",
                "Ring            =  Closed Hat (42)",
                "Pinky           =  Open Hat (46)",
                "Thumb           =  Accent (+30 vel)",
                "Wrist height    =  Base velocity",
                "Wrist down-move =  Strike bonus",
            ]),
            ("LEFT HAND (drums)", [
                "Index           =  Crash (49)",
                "Middle          =  Ride (51)",
                "Ring            =  Low Tom (45)",
                "Pinky           =  High Tom (48)",
                "Thumb           =  Accent (+30 vel)",
                "Wrist height    =  Base velocity",
            ]),
        ]
