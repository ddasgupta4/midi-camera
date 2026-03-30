"""
Melody Theremin Mode — Continuous pitch from hand position.

Right hand Y (wrist_y) = pitch mapped to 2 octaves of scale notes, quantized.
Right hand X (wrist_x) = vibrato via MIDI CC1 (mod wheel).
Left hand finger count = octave offset (0-4).
Left hand thumb = sustain.
"""

from core.modes.base import Mode, _midi_name
from core.chord_engine import midi_to_note_name, ROMAN


class MelodyThereminMode(Mode):
    name = "Theremin"
    description = "Pitch from Y position, vibrato from X"
    debounce_time = 0.03  # 30ms — very snappy for continuous feel

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    VIBRATO_CC = 1  # mod wheel
    NUM_SCALE_NOTES = 14  # 2 octaves of 7 scale degrees

    def __init__(self):
        super().__init__()
        self.octave_offset = 0
        self.sustain = False
        self.last_velocity = 90
        self.left_gesture_name = ""
        self.last_vibrato = 0

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
            # Map wrist_y (0=top, 1=bottom) to scale note index
            # Invert: top of frame = high pitch, bottom = low pitch
            y = 1.0 - right_gesture.wrist_y
            y = max(0.0, min(1.0, y))
            note_idx = int(y * (self.NUM_SCALE_NOTES - 1) + 0.5)  # quantize to nearest

            # Convert to scale degree + octave within the 2-octave range
            scale_degree = (note_idx % 7) + 1  # 1-7
            octave_in_range = note_idx // 7      # 0 or 1

            root = engine.get_scale_degree_root(scale_degree)
            note = root + 12 * (self.octave_offset + octave_in_range)
            note = max(21, min(108, note))

            # Vibrato from X position (center = no vibrato, edges = max)
            x = right_gesture.wrist_x
            vibrato = int(abs(x - 0.5) * 2 * 64)  # 0-64 range, subtle
            vibrato = max(0, min(127, vibrato))
            if vibrato != self.last_vibrato:
                midi.send_cc(self.VIBRATO_CC, vibrato)
                self.last_vibrato = vibrato

            # Fixed velocity (theremin doesn't have velocity naturally)
            self.last_velocity = 90

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
            if self.sustain and self._current:
                new_notes = self._current['notes']
                new_info = self._current
            else:
                new_notes = []
                new_info = {}
                # Reset vibrato when hand disappears
                if self.last_vibrato != 0:
                    midi.send_cc(self.VIBRATO_CC, 0)
                    self.last_vibrato = 0

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
        }

    def on_exit(self, midi):
        super().on_exit(midi)
        # Reset vibrato CC
        midi.send_cc(self.VIBRATO_CC, 0)
        self.last_vibrato = 0

    def get_help_sections(self):
        return [
            ("RIGHT HAND (theremin)", [
                "Y position      =  Pitch (top=high, bottom=low)",
                "X position      =  Vibrato (edges=more)",
                "Fist            =  Silence",
                "Any fingers     =  Enable pitch tracking",
                "2 octaves of scale notes, quantized",
            ]),
            ("LEFT HAND (octave/sustain)", [
                "Fist            =  Base octave",
                "1 finger        =  Octave +1",
                "2 fingers       =  Octave +2",
                "3 fingers       =  Octave +3",
                "4 fingers       =  Octave +4",
                "Thumb out       =  Sustain (hold note)",
            ]),
        ]
