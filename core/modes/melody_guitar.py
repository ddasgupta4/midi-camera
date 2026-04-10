"""
Melody Guitar Mode — Pluck-style note triggering.

Left hand: finger count = scale degree (same mapping as piano mode).
Right hand: "pluck" = fast wrist movement triggers the note. Both downward
            and upward plucks trigger (up-strums and down-strums both work).

Pluck velocity comes from time-normalized wrist velocity (screen-heights/sec),
so it is independent of the main-loop frame rate.

Octave is LATCHED at pluck time from right-hand finger count — you don't have
to hold it while the note sustains. Pinch (thumb+index) or fist releases.
"""

from core.modes.base import Mode, _midi_name
from core.chord_engine import midi_to_note_name, ROMAN
from core.gesture_filters import EMA, VelocityTracker


class MelodyGuitarMode(Mode):
    name = "Guitar"
    description = "Pluck notes — L=degree, R=strum"
    debounce_time = 0.01  # 10ms — latency matters here

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    # Time-normalized velocity thresholds (screen-heights per second)
    PLUCK_VEL_THRESHOLD = 1.6
    MIN_PLUCK_INTERVAL = 0.05  # 50 ms lockout — 20 plucks/sec ceiling

    def __init__(self):
        super().__init__()
        self.last_pluck_time = 0.0
        self.last_velocity = 80
        self.left_gesture_name = ""
        self.current_degree = 0
        self.octave_variant = 0       # latched at pluck time
        self.note_held = False
        self._ema_y = EMA(alpha=0.5)  # light smoothing, doesn't hide real plucks
        self._vel_y = VelocityTracker()
        # For overlay display
        self.pluck_flash_time = 0.0
        self.cooldown_progress = 1.0
        self.last_pluck_wrist = None  # (x, y) normalized at pluck time

    def on_enter(self, midi):
        self._ema_y.reset()
        self._vel_y.reset()
        self.note_held = False

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        # Left hand: degree selector (same scheme as piano mode)
        raw = get_left_hand_raw(left_hand)
        if raw:
            fc = raw['finger_count']
            thumb = raw['thumb_out']
            if fc == 0 and thumb:
                self.current_degree = 6
            elif thumb and fc == 1 and raw['extended'][3] and not raw['extended'][0]:
                self.current_degree = 7  # thumb + pinky
            elif fc == 0:
                self.current_degree = 0
            else:
                self.current_degree = min(fc, 5)
                if fc == 4 and thumb:
                    self.current_degree = 5
            self.left_gesture_name = f"deg {self.current_degree}" if self.current_degree else "fist"
        else:
            self.current_degree = 0
            self.left_gesture_name = "no hand"

        # Right hand: pluck detection + octave variant + pinch-release
        plucked = False
        if right_gesture:
            y_smoothed = self._ema_y.update(right_gesture.wrist_y)
            vel_per_sec, _dt = self._vel_y.update(y_smoothed, now)

            # Pinch-to-release: thumb + only index extended
            pinched = right_gesture.thumb_out and not any(right_gesture.extended)

            # Either down OR up strum triggers; direction of motion = sign
            if (abs(vel_per_sec) > self.PLUCK_VEL_THRESHOLD
                    and (now - self.last_pluck_time) > self.MIN_PLUCK_INTERVAL):
                plucked = True
                self.last_pluck_time = now
                # Velocity from absolute speed; wider, flatter curve than before
                v = int(50 + min(77, abs(vel_per_sec) * 25))
                self.last_velocity = max(50, min(127, v))
                # Latch octave at strike time
                self.octave_variant = max(0, min(3, right_gesture.finger_count - 1))
                self.pluck_flash_time = now
                self.last_pluck_wrist = (right_gesture.wrist_x, right_gesture.wrist_y)

            # Release conditions: fist OR pinch
            if pinched:
                self.note_held = False
            elif right_gesture.finger_count == 0 and right_gesture.degree == 0 and not right_gesture.thumb_out:
                self.note_held = False
        else:
            self._ema_y.reset()
            self._vel_y.reset()
            self.note_held = False

        # Build note if plucked and we have a degree
        if plucked and self.current_degree > 0:
            root = engine.get_scale_degree_root(self.current_degree)
            note = root + 12 * self.octave_variant
            note = max(21, min(108, note))
            self.note_held = True

            note_name = midi_to_note_name(note)
            new_notes = [note]
            new_info = {
                'notes': [note],
                'name': note_name,
                'roman': ROMAN[self.current_degree - 1],
                'root_name': note_name.rstrip('0123456789'),
                'note_names': [note_name],
                'quality': 'note',
                'degree': self.current_degree,
            }
        elif self.note_held and self._current:
            # Sustain current note
            new_notes = self._current['notes']
            new_info = self._current
        else:
            new_notes = []
            new_info = {}

        if self._check_settle(new_notes, new_info, now):
            if not self._desired_notes:
                midi.all_notes_off()
                self._current = None
            else:
                midi.send_chord(self._desired_notes, velocity=self.last_velocity)
                self._current = dict(
                    self._desired_info,
                    notes=list(self._desired_notes),
                    note_names=[_midi_name(n) for n in self._desired_notes],
                )

        # Cooldown progress for overlay: 0.0..1.0, 1.0 = ready
        since_pluck = now - self.last_pluck_time
        self.cooldown_progress = max(0.0, min(1.0, since_pluck / self.MIN_PLUCK_INTERVAL))

        return {
            'type': 'melody',
            'chord_info': self._current or {},
            'velocity': self.last_velocity,
            'left_gesture_name': self.left_gesture_name,
            'sauce_mode': False,
            'desired_notes': self._desired_notes,
            'desired_since': self._desired_since,
            'guitar_display': {
                'pluck_flash_age': (now - self.pluck_flash_time) if self.pluck_flash_time else 999.0,
                'cooldown': self.cooldown_progress,
                'last_pluck_wrist': self.last_pluck_wrist,
                'note_held': self.note_held,
                'octave_variant': self.octave_variant,
            },
        }

    def get_help_sections(self):
        return [
            ("LEFT HAND (degree)", [
                "Fist            =  No note selected",
                "1 finger        =  Scale degree 1",
                "2 fingers       =  Scale degree 2",
                "3 fingers       =  Scale degree 3",
                "4 fingers       =  Scale degree 4",
                "Open hand       =  Scale degree 5",
                "Thumb only      =  Scale degree 6",
                "Thumb + pinky   =  Scale degree 7",
            ]),
            ("RIGHT HAND (strum)", [
                "Down / up flick =  Pluck (both strums work)",
                "Pluck speed     =  Velocity",
                "Finger count    =  Octave (latched at pluck)",
                "Pinch (thumb)   =  Release note",
                "Fist            =  Release note",
            ]),
        ]
