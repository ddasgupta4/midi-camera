"""
Melody Piano Mode — Single notes from hand gestures.

Right hand: finger count = scale degree 1-7 (same mapping as chord mode).
Left hand: finger count = octave offset (0-4), thumb = sustain.
Velocity from right hand wrist height.
"""

from core.modes.base import Mode, _midi_name
from core.chord_engine import midi_to_note_name, ROMAN


class MelodyPianoMode(Mode):
    name = "Melody"
    description = "Single notes — R=degree, L=octave"
    debounce_time = 0.05  # 50ms — snappy for melody

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    def __init__(self):
        super().__init__()
        self.octave_offset = 0
        self.sustain = False
        self.last_velocity = 80
        self.left_gesture_name = ""

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        # Left hand: octave selector + sustain
        raw = get_left_hand_raw(left_hand)
        if raw:
            self.octave_offset = min(4, raw['finger_count'])
            self.sustain = raw['thumb_out']
            self.left_gesture_name = f"oct+{self.octave_offset}" + (" HOLD" if self.sustain else "")
        else:
            # No left hand — keep previous octave_offset, drop sustain
            self.sustain = False
            self.left_gesture_name = "no hand"

        # Right hand: degree -> single note
        degree = right_gesture.degree if right_gesture else 0

        # Velocity from right hand wrist height (higher = louder)
        if right_gesture:
            self.last_velocity = max(40, min(127, int(127 - right_gesture.wrist_y * 87)))

        if degree == 0:
            if self.sustain and self._current:
                # Sustain active: keep current note sounding
                new_notes = self._current['notes']
                new_info = self._current
            else:
                new_notes = []
                new_info = {}
        else:
            root = engine.get_scale_degree_root(degree)
            note = root + 12 * self.octave_offset
            note = max(21, min(108, note))  # clamp to piano range

            note_name = midi_to_note_name(note)
            new_notes = [note]
            new_info = {
                'notes': [note],
                'name': note_name,
                'roman': ROMAN[degree - 1],
                'root_name': note_name.rstrip('0123456789'),
                'note_names': [note_name],
                'quality': 'note',
                'degree': degree,
            }

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

    def get_help_sections(self):
        return [
            ("RIGHT HAND (melody)", [
                "Fist            =  Silence",
                "1 finger        =  Scale degree 1",
                "2 fingers       =  Scale degree 2",
                "3 fingers       =  Scale degree 3",
                "4 fingers       =  Scale degree 4",
                "Open hand       =  Scale degree 5",
                "Thumb only      =  Scale degree 6",
                "Thumb + pinky   =  Scale degree 7",
                "Wrist height    =  Velocity",
            ]),
            ("LEFT HAND (octave/sustain)", [
                "Fist            =  Base octave (no offset)",
                "1 finger        =  Octave +1",
                "2 fingers       =  Octave +2",
                "3 fingers       =  Octave +3",
                "4 fingers       =  Octave +4",
                "Thumb out       =  Sustain (hold note)",
            ]),
        ]
