"""
Melody Guitar Mode — Pluck-style note triggering.

Left hand: finger count = scale degree (same mapping as piano mode).
Right hand: "pluck" = fast downward movement triggers the note.
Pluck velocity from speed of downward movement.
Right hand finger count while note held = octave variant (1-4).
"""

from core.modes.base import Mode, _midi_name
from core.chord_engine import midi_to_note_name, ROMAN


class MelodyGuitarMode(Mode):
    name = "Guitar"
    description = "Pluck notes — L=degree, R=strum"
    debounce_time = 0.04  # 40ms

    supports_voicings = False
    supports_bass_pedals = False
    supports_sauce = False
    supports_smart_extensions = False

    PLUCK_THRESHOLD = 0.06  # wrist_y delta per frame to count as pluck (downward)
    MIN_PLUCK_INTERVAL = 0.08  # minimum seconds between plucks

    def __init__(self):
        super().__init__()
        self.prev_wrist_y = None
        self.last_pluck_time = 0.0
        self.last_velocity = 80
        self.left_gesture_name = ""
        self.current_degree = 0
        self.octave_variant = 0  # 0-3 from right hand finger count
        self.note_held = False

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import get_left_hand_raw

        # Left hand: degree selector
        raw = get_left_hand_raw(left_hand)
        if raw:
            # Same degree mapping as piano: finger count 1-5 = degree 1-5
            # thumb extends to 6-7
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

        # Right hand: pluck detection + octave variant
        plucked = False
        if right_gesture:
            wrist_y = right_gesture.wrist_y

            # Octave variant from right finger count (1-4 octave selection)
            self.octave_variant = max(0, min(3, right_gesture.finger_count - 1))

            # Pluck: detect fast downward movement (increasing Y = downward)
            if self.prev_wrist_y is not None:
                delta = wrist_y - self.prev_wrist_y  # positive = moving down
                if delta > self.PLUCK_THRESHOLD and (now - self.last_pluck_time) > self.MIN_PLUCK_INTERVAL:
                    plucked = True
                    self.last_pluck_time = now
                    # Velocity from pluck speed (faster = louder)
                    self.last_velocity = max(50, min(127, int(delta * 1200)))

            # Fist = note off
            if right_gesture.finger_count == 0 and right_gesture.degree == 0:
                self.note_held = False

            self.prev_wrist_y = wrist_y
        else:
            self.prev_wrist_y = None
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
                "Downward flick  =  Pluck/trigger note",
                "Fist            =  Mute / note off",
                "1 finger        =  Octave 0",
                "2 fingers       =  Octave +1",
                "3 fingers       =  Octave +2",
                "4 fingers       =  Octave +3",
                "Pluck speed     =  Velocity",
            ]),
        ]
