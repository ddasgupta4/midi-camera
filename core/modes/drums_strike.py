"""
Drums Strike Mode — Downward strike triggers drums.

8 pads total (4 per hand), selected by wrist (x, y) at the moment of impact:

  Right hand              |  Left hand
  ----------------------- | ------------------------
  top-left   = RIDE (51)  |  top-left   = OP-HAT (46)
  top-right  = CRASH (49) |  top-right  = SPLASH (55)
  bot-left   = KICK (36)  |  bot-left   = CH-HAT (42)
  bot-right  = SNARE (38) |  bot-right  = TOM  (45)

Strike = fast downward wrist motion (velocity per second > threshold).
Velocity is time-normalized, so detection is frame-rate independent.

A "reset-to-top" gate prevents vertical oscillation from double-triggering:
after a strike, the wrist must rise back above (strike_y - 0.04) before
another strike is eligible.
"""

from core.modes.base import Mode
from core.gesture_filters import EMA, VelocityTracker


# 8-pad drum assignments per hand
# Keyed by (row, col) where row 0 = top, col 0 = left
RIGHT_PADS = {
    (0, 0): 51,  # ride
    (0, 1): 49,  # crash
    (1, 0): 36,  # kick
    (1, 1): 38,  # snare
}
LEFT_PADS = {
    (0, 0): 46,  # open hat
    (0, 1): 55,  # splash
    (1, 0): 42,  # closed hat
    (1, 1): 45,  # tom
}

DRUM_NAMES = {
    36: "KICK", 38: "SNARE", 42: "CH-HAT", 49: "CRASH",
    45: "TOM", 46: "OP-HAT", 51: "RIDE", 55: "SPLASH",
}

STRIKE_VEL_THRESHOLD = 1.2   # screen-heights per second
MIN_STRIKE_INTERVAL = 0.05   # 50 ms absolute lockout
RESET_Y_MARGIN = 0.04        # must rise this far above last strike_y
NOTE_DECAY_SEC = 0.08        # drum decay


def _pad_at(x: float, y: float) -> tuple[int, int]:
    row = 0 if y < 0.5 else 1
    col = 0 if x < 0.5 else 1
    return row, col


class _HandState:
    def __init__(self):
        self.ema_y = EMA(alpha=0.5)
        self.vel = VelocityTracker()
        self.last_strike_time = 0.0
        self.last_strike_y: float | None = None
        self.has_reset = True  # whether the reset-to-top gate is open
        self.held_note: int | None = None
        self.held_until: float = 0.0
        self.last_drum_name = ""
        # Motion trail for overlay: list of (x, y, t), newest last
        self.trail: list = []
        self.last_pos: tuple[float, float] | None = None

    def reset(self):
        self.ema_y.reset()
        self.vel.reset()
        self.last_strike_time = 0.0
        self.last_strike_y = None
        self.has_reset = True
        self.held_note = None
        self.held_until = 0.0
        self.trail = []
        self.last_pos = None


class DrumsStrikeMode(Mode):
    name = "StrikeDrm"
    description = "Strike down to hit — 8 drums (4 per hand)"
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
        self.flash_times = {}  # {('R'|'L', row, col): last_hit_time}

    def _release_expired(self, state: _HandState, midi, now: float):
        if state.held_note is not None and now >= state.held_until:
            midi.send_note(state.held_note, velocity=0, on=False)
            state.held_note = None

    def _update_trail(self, state: _HandState, x: float, y: float, now: float):
        state.trail.append((x, y, now))
        # Keep last ~200ms for overlay
        state.trail = [(tx, ty, tt) for (tx, ty, tt) in state.trail if now - tt < 0.2]

    def _process_hand(self, state: _HandState, pads: dict, side: str,
                      x: float, y: float, midi, now: float, hits: list):
        state.last_pos = (x, y)
        self._update_trail(state, x, y, now)

        y_s = state.ema_y.update(y)
        vel_per_sec, _dt = state.vel.update(y_s, now)  # +ve = moving down

        # Reset-to-top gate: after a strike, wait until we move above
        # (last_strike_y - RESET_Y_MARGIN) before allowing the next strike.
        if not state.has_reset and state.last_strike_y is not None:
            if y_s < state.last_strike_y - RESET_Y_MARGIN:
                state.has_reset = True

        strike_ready = (state.has_reset
                        and vel_per_sec > STRIKE_VEL_THRESHOLD
                        and (now - state.last_strike_time) > MIN_STRIKE_INTERVAL)

        if strike_ready:
            pad_key = _pad_at(x, y)
            drum = pads[pad_key]
            v = int(50 + min(77, vel_per_sec * 20))
            v = max(50, min(127, v))

            # Release any previous held note before firing new one
            if state.held_note is not None:
                midi.send_note(state.held_note, velocity=0, on=False)
            midi.send_note(drum, velocity=v, on=True)
            state.held_note = drum
            state.held_until = now + NOTE_DECAY_SEC
            state.last_strike_time = now
            state.last_strike_y = y_s
            state.has_reset = False
            state.last_drum_name = DRUM_NAMES[drum]
            hits.append(state.last_drum_name)
            self.flash_times[(side, pad_key[0], pad_key[1])] = now

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        hits = []

        # Expire decay timers
        self._release_expired(self._right, midi, now)
        self._release_expired(self._left, midi, now)

        # Right hand
        if right_gesture:
            self._process_hand(self._right, RIGHT_PADS, 'R',
                               right_gesture.wrist_x, right_gesture.wrist_y,
                               midi, now, hits)
        else:
            if self._right.held_note is not None:
                midi.send_note(self._right.held_note, velocity=0, on=False)
            self._right.reset()

        # Left hand
        raw = get_left_hand_raw(left_hand)
        if raw:
            self._process_hand(self._left, LEFT_PADS, 'L',
                               raw['wrist_x'], raw['wrist_y'],
                               midi, now, hits)
            self.left_gesture_name = "tracking"
        else:
            if self._left.held_note is not None:
                midi.send_note(self._left.held_note, velocity=0, on=False)
            self._left.reset()
            self.left_gesture_name = "no hand"

        if hits:
            self.last_hits = hits

        # Expire old flash entries
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
            'drum_layout': 'strike',
            'strike_pads': {
                'right': {pad: DRUM_NAMES[note] for pad, note in RIGHT_PADS.items()},
                'left': {pad: DRUM_NAMES[note] for pad, note in LEFT_PADS.items()},
            },
            'strike_hand_positions': {
                'right': self._right.last_pos,
                'left': self._left.last_pos,
            },
            'strike_trails': {
                'right': list(self._right.trail),
                'left': list(self._left.trail),
            },
            'strike_flash_times': dict(self.flash_times),
            'strike_now': now,
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
            ("RIGHT HAND (4 pads)", [
                "Strike down     =  Trigger drum",
                "Top-left        =  Ride (51)",
                "Top-right       =  Crash (49)",
                "Bot-left        =  Kick (36)",
                "Bot-right       =  Snare (38)",
            ]),
            ("LEFT HAND (4 pads)", [
                "Top-left        =  Open Hat (46)",
                "Top-right       =  Splash (55)",
                "Bot-left        =  Closed Hat (42)",
                "Bot-right       =  Tom (45)",
            ]),
            ("MECHANICS", [
                "Strike speed    =  Velocity",
                "Must raise arm  =  Before next strike",
            ]),
        ]
