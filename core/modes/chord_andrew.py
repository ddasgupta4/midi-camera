"""
Andrew Mode — Jazz chord stacking.

Left hand: 0=triad, 1=7th, 2=9th, 3=11th, 4=13th (stacking).
Thumb = flip quality (maj<->min). Sauce mode via face tracking.
"""

from core.modes.base import Mode, _midi_name


class AndrewMode(Mode):
    name = "Andrew"
    description = "Jazz stacking (7/9/11/13)"
    debounce_time = 0.10

    supports_voicings = True
    supports_bass_pedals = True
    supports_sauce = True
    supports_smart_extensions = True

    def __init__(self, voicing_editor, bass_pedals):
        super().__init__()
        self.ve = voicing_editor
        self.bp = bass_pedals
        self.smart_extensions = True
        self.sauce_active = False
        self.last_velocity = 80
        self.left_gesture_name = ""

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now):
        from core.gesture import interpret_left_hand

        # Sauce: face tracker overrides, manual toggle persists when no tracker
        if sauce_from_face is not None:
            self.sauce_active = sauce_from_face

        left_gesture = interpret_left_hand(left_hand, style_mode='andrew')
        self.last_velocity = left_gesture.velocity
        self.left_gesture_name = "~SAUCE~" if self.sauce_active else left_gesture.gesture_name

        degree = right_gesture.degree if right_gesture else 0

        if degree == 0:
            new_notes = []
            new_info = {}
        else:
            if self.sauce_active:
                new_info = engine.build_sauce_chord(degree)
            else:
                new_info = engine.build_chord(
                    degree=degree,
                    flip_quality=left_gesture.flip_quality,
                    add_7th=left_gesture.add_7th,
                    add_9th=left_gesture.add_9th,
                    add_11th=left_gesture.add_11th,
                    add_13th=left_gesture.add_13th,
                    add_sus4=left_gesture.add_sus4,
                )
            new_notes = self.ve.apply(new_info['notes'], degree)
            root_midi = engine.get_scale_degree_root(degree)
            new_notes = self.bp.apply(new_notes, root_midi)

        if self._check_settle(new_notes, new_info, now):
            if not self._desired_notes:
                midi.all_notes_off()
                self._current = None
            else:
                extension_only = (
                    self.smart_extensions
                    and self._current is not None
                    and self._desired_info.get('degree') == self._current.get('degree')
                    and self._desired_info.get('quality') == self._current.get('quality')
                )
                if extension_only:
                    midi.send_chord_diff(self._desired_notes, velocity=self.last_velocity)
                else:
                    midi.send_chord(self._desired_notes, velocity=self.last_velocity)
                self._current = dict(
                    self._desired_info,
                    notes=list(self._desired_notes),
                    note_names=[_midi_name(n) for n in self._desired_notes],
                )

        return {
            'type': 'chord',
            'chord_info': self._current or {},
            'velocity': self.last_velocity,
            'left_gesture_name': self.left_gesture_name,
            'sauce_mode': self.sauce_active,
            'desired_notes': self._desired_notes,
            'desired_since': self._desired_since,
        }

    def get_help_sections(self):
        return [
            ("RIGHT HAND (degree)", [
                "Fist            =  Silence",
                "1 finger        =  Chord I",
                "2 fingers       =  Chord II",
                "3 fingers       =  Chord III",
                "4 fingers       =  Chord IV  (thumb tucked)",
                "Open hand       =  Chord V",
                "Thumb only      =  Chord VI",
                "Thumb + pinky   =  Chord VII",
            ]),
            ("LEFT HAND — ANDREW (stacking)", [
                "Fist            =  Triad (no extension)",
                "Thumb out       =  Flip quality  (maj<->min)",
                "1 finger        =  Add 7th",
                "2 fingers       =  Add 9th",
                "3 fingers       =  Add 11th",
                "4 fingers       =  Add 13th",
                "Wrist height    =  Velocity",
            ]),
            ("SAUCE MODE", [
                "Open mouth      =  Sauce (jazz voicings)",
                ";               =  Manual sauce toggle",
            ]),
        ]
