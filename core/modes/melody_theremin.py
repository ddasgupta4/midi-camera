"""
Melody Theremin Mode — Continuous pitch from hand position.

Right hand Y (wrist_y) = pitch mapped to 3 octaves of scale notes.
Right hand X (wrist_x) = vibrato via MIDI CC1 (mod wheel), with a center deadzone.
Right hand wrist height also drives velocity (high = loud).
Left hand finger count = octave offset (0-4).
Left hand thumb = sustain.

Wrist positions are EMA-smoothed to kill hand tremor.

Continuous pitch mode (toggled with 'C'): uses MIDI pitch bend around the
nearest scale note for a true theremin glissando feel.
"""

from core.modes.base import Mode, _midi_name
from core.chord_engine import midi_to_note_name, ROMAN
from core.gesture_filters import EMA


class MelodyThereminMode(Mode):
    name = "Theremin"
    description = "Pitch from Y position, vibrato from X"
    debounce_time = 0.01  # 10ms — smoothing handles noise, not this gate

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    VIBRATO_CC = 1          # mod wheel
    NUM_SCALE_NOTES = 21    # 3 octaves of 7 scale degrees (denser than before)
    VIBRATO_DEADZONE = 0.15  # ±15% around x=0.5 → 0 vibrato
    PITCH_BEND_RANGE_SEMITONES = 2  # default for most synths

    def __init__(self):
        super().__init__()
        self.octave_offset = 0
        self.sustain = False
        self.last_velocity = 90
        self.left_gesture_name = ""
        self.last_vibrato = 0
        self.last_pitch_bend = 0
        # Continuous pitch bend mode — off by default, toggle with 'C'
        self.continuous = False
        # Smoothing
        self._ema_y = EMA(alpha=0.35)
        self._ema_x = EMA(alpha=0.35)
        # For pitch ladder display
        self.display_y = 0.5
        self.display_x = 0.5
        self.display_active = False

    def on_enter(self, midi):
        self._ema_y.reset()
        self._ema_x.reset()
        self.last_vibrato = 0
        self.last_pitch_bend = 0
        midi.send_pitch_bend(0)

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        # Left hand: octave selector + sustain
        raw = get_left_hand_raw(left_hand)
        if raw:
            self.octave_offset = min(4, raw['finger_count'])
            self.sustain = raw['thumb_out']
            self.left_gesture_name = f"oct+{self.octave_offset}" + (" HOLD" if self.sustain else "")
        else:
            self.sustain = False
            self.left_gesture_name = "no hand"

        if right_gesture and right_gesture.finger_count > 0:
            # Smooth wrist positions
            y_raw = 1.0 - right_gesture.wrist_y  # top=high, bottom=low
            y_raw = max(0.0, min(1.0, y_raw))
            y = self._ema_y.update(y_raw)
            x = self._ema_x.update(right_gesture.wrist_x)

            self.display_y = y
            self.display_x = x
            self.display_active = True

            # Continuous float position along the scale (0..NUM_SCALE_NOTES-1)
            float_idx = y * (self.NUM_SCALE_NOTES - 1)
            note_idx = int(float_idx + 0.5)  # nearest

            scale_degree = (note_idx % 7) + 1  # 1-7
            octave_in_range = note_idx // 7    # 0..2

            root = engine.get_scale_degree_root(scale_degree)
            note = root + 12 * (self.octave_offset + octave_in_range)
            note = max(21, min(108, note))

            # Vibrato from X with center deadzone
            off_center = abs(x - 0.5)
            if off_center <= self.VIBRATO_DEADZONE:
                vibrato = 0
            else:
                # Ramp from deadzone edge to frame edge → 0..96 modwheel
                ramp = (off_center - self.VIBRATO_DEADZONE) / (0.5 - self.VIBRATO_DEADZONE)
                vibrato = int(max(0.0, min(1.0, ramp)) * 96)
            if vibrato != self.last_vibrato:
                midi.send_cc(self.VIBRATO_CC, vibrato)
                self.last_vibrato = vibrato

            # Continuous pitch bend toward the "true" sub-step position
            if self.continuous:
                # Fraction of a semitone between nearest scale notes.
                # Scale notes aren't semitone-spaced, but bending by
                # (float_idx - note_idx) semitones gives a convincing slide.
                bend_semitones = float_idx - note_idx
                bend_value = int((bend_semitones / self.PITCH_BEND_RANGE_SEMITONES) * 8192)
                if bend_value != self.last_pitch_bend:
                    midi.send_pitch_bend(bend_value)
                    self.last_pitch_bend = bend_value
            elif self.last_pitch_bend != 0:
                midi.send_pitch_bend(0)
                self.last_pitch_bend = 0

            # Dynamic velocity: higher = louder (matches drums_finger convention)
            self.last_velocity = max(60, min(127, int(127 - right_gesture.wrist_y * 77)))

            note_name = midi_to_note_name(note)
            new_notes = [note]
            new_info = {
                'notes': [note],
                'name': note_name,
                'roman': ROMAN[scale_degree - 1],
                'root_name': note_name.rstrip('0123456789'),
                'note_names': [note_name],
                'quality': 'note',
                'degree': scale_degree,
            }
        else:
            self.display_active = False
            if self.sustain and self._current:
                new_notes = self._current['notes']
                new_info = self._current
            else:
                new_notes = []
                new_info = {}
                # Reset vibrato + bend when hand disappears
                if self.last_vibrato != 0:
                    midi.send_cc(self.VIBRATO_CC, 0)
                    self.last_vibrato = 0
                if self.last_pitch_bend != 0:
                    midi.send_pitch_bend(0)
                    self.last_pitch_bend = 0
                self._ema_y.reset()
                self._ema_x.reset()

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

        return {
            'type': 'melody',
            'chord_info': self._current or {},
            'velocity': self.last_velocity,
            'left_gesture_name': self.left_gesture_name,
            'sauce_mode': False,
            'desired_notes': self._desired_notes,
            'desired_since': self._desired_since,
            # For overlay
            'theremin_display': {
                'active': self.display_active,
                'y': self.display_y,
                'x': self.display_x,
                'num_notes': self.NUM_SCALE_NOTES,
                'vibrato': self.last_vibrato,
                'continuous': self.continuous,
                'deadzone': self.VIBRATO_DEADZONE,
            },
        }

    def handle_key(self, key: int, raw_key: int, **context) -> bool:
        # 'c' / 'C' toggles continuous (pitch-bend) mode
        if key in (ord('c'), ord('C')):
            self.continuous = not self.continuous
            return True
        return False

    def on_exit(self, midi):
        super().on_exit(midi)
        # Reset vibrato + pitch bend CC
        midi.send_cc(self.VIBRATO_CC, 0)
        midi.send_pitch_bend(0)
        self.last_vibrato = 0
        self.last_pitch_bend = 0
        self._ema_y.reset()
        self._ema_x.reset()

    def get_help_sections(self):
        return [
            ("RIGHT HAND (theremin)", [
                "Y position      =  Pitch (top=high, bottom=low)",
                "X position      =  Vibrato (edges=more)",
                "Wrist height    =  Velocity (high=loud)",
                "Fist            =  Silence",
                "3 octaves of scale notes, smoothed",
            ]),
            ("LEFT HAND (octave/sustain)", [
                "Fist            =  Base octave",
                "1-4 fingers     =  Octave +1..+4",
                "Thumb out       =  Sustain (hold note)",
            ]),
            ("MODE KEYS", [
                "C               =  Continuous (pitch-bend slides)",
            ]),
        ]
