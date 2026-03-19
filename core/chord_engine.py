"""
Nashville Number System chord engine.

Maps scale degrees (I-VII) to actual MIDI note numbers
based on key, mode, and chord quality.
"""

from typing import List, Optional

# All 12 keys in chromatic order
KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Enharmonic display names (flats shown where conventional)
KEY_DISPLAY = {
    'C': 'C', 'C#': 'Db', 'D': 'D', 'D#': 'Eb', 'E': 'E',
    'F': 'F', 'F#': 'F#', 'G': 'G', 'G#': 'Ab', 'A': 'A',
    'A#': 'Bb', 'B': 'B'
}

# Semitone intervals from root
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]  # W W H W W W H
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]  # W H W W H W W

# Diatonic chord qualities per scale degree
# major: I ii iii IV V vi vii°
MAJOR_DIATONIC = ['major', 'minor', 'minor', 'major', 'major', 'minor', 'diminished']
# minor: i ii° III iv v VI VII
MINOR_DIATONIC = ['minor', 'diminished', 'major', 'minor', 'minor', 'major', 'major']

# Chord intervals from root (in semitones)
CHORD_INTERVALS = {
    'major':       [0, 4, 7],
    'minor':       [0, 3, 7],
    'diminished':  [0, 3, 6],
    'augmented':   [0, 4, 8],
    'dominant7':   [0, 4, 7, 10],
    'major7':      [0, 4, 7, 11],
    'minor7':      [0, 3, 7, 10],
    'dim7':        [0, 3, 6, 9],
    'min7b5':      [0, 3, 6, 10],
    'sus4':        [0, 5, 7],        # suspended 4th — no 3rd
    'sus4_7':      [0, 5, 7, 10],   # sus4 + b7 (dom7sus4)
}

# Roman numeral labels
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']

# Note names for display
NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def midi_to_note_name(midi_num: int) -> str:
    """Convert MIDI note number to readable name like 'C3'."""
    octave = (midi_num // 12) - 1
    note = NOTE_NAMES[midi_num % 12]
    return f"{note}{octave}"


class ChordEngine:
    def __init__(self, key: str = 'C', mode: str = 'major', octave: int = 3):
        self.set_key(key)
        self.set_mode(mode)
        self.octave = octave

    def set_key(self, key: str):
        """Set the key. Accepts sharps or flats."""
        # Normalize flat names to sharp equivalents
        flat_to_sharp = {
            'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
            'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'
        }
        self.key = flat_to_sharp.get(key, key)
        if self.key not in KEYS:
            raise ValueError(f"Unknown key: {key}")

    def set_mode(self, mode: str):
        """Set major or minor mode."""
        if mode not in ('major', 'minor'):
            raise ValueError(f"Unknown mode: {mode}")
        self.mode = mode

    @property
    def root_midi(self) -> int:
        """MIDI note number of the root in current octave."""
        return KEYS.index(self.key) + (self.octave + 1) * 12

    @property
    def scale_intervals(self) -> List[int]:
        return MAJOR_SCALE if self.mode == 'major' else MINOR_SCALE

    @property
    def diatonic_qualities(self) -> List[str]:
        return MAJOR_DIATONIC if self.mode == 'major' else MINOR_DIATONIC

    def get_scale_degree_root(self, degree: int) -> int:
        """
        Get the MIDI note of a scale degree root (1-indexed).
        degree: 1-7
        """
        if degree < 1 or degree > 7:
            raise ValueError(f"Degree must be 1-7, got {degree}")
        return self.root_midi + self.scale_intervals[degree - 1]

    def build_chord(
        self,
        degree: int,
        flip_quality: bool = False,
        add_7th: bool = False,
        add_9th: bool = False,
        add_11th: bool = False,
        add_13th: bool = False,
        add_sus4: bool = False,
        quality_override: Optional[str] = None,
    ) -> dict:
        """
        Build a chord for the given scale degree.

        Args:
            degree: 1-7 scale degree
            flip_quality: swap major<->minor from diatonic
            add_7th/9th/11th/13th: stack diatonic extensions
            quality_override: force specific quality (overrides flip)

        Returns dict with notes, name, roman, root_name, note_names, quality, degree.
        """
        if degree < 1 or degree > 7:
            return {'notes': [], 'name': '', 'roman': '', 'root_name': '', 'degree': 0}

        root = self.get_scale_degree_root(degree)
        diatonic = self.diatonic_qualities[degree - 1]

        # Determine triad quality
        if quality_override:
            quality = quality_override
        elif flip_quality:
            quality = {'major': 'minor', 'minor': 'major',
                       'diminished': 'augmented'}.get(diatonic, diatonic)
        else:
            quality = diatonic

        # Sus4 overrides the triad — no 3rd, quality flip ignored
        if add_sus4:
            quality = 'sus4_7' if add_7th else 'sus4'
        # Extend to 7th if requested (diatonic to the quality)
        elif add_7th and quality in ('major', 'minor', 'diminished', 'augmented'):
            quality = self._diatonic_7th_for_quality(quality, degree)

        intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS['major'])
        notes = [root + i for i in intervals]

        # Stack upper extensions
        if add_9th and not add_sus4:
            n = root + 14
            if n not in notes: notes.append(n)
        if add_11th:
            n = root + 17
            if n not in notes: notes.append(n)
        if add_13th:
            n = root + 21
            if n not in notes: notes.append(n)

        # Display name
        root_name = midi_to_note_name(root).rstrip('0123456789')
        quality_label = {
            'major': '', 'minor': 'm', 'diminished': 'dim',
            'augmented': 'aug', 'dominant7': '7', 'major7': 'maj7',
            'minor7': 'm7', 'dim7': 'dim7', 'min7b5': 'm7b5',
            'sus4': 'sus4', 'sus4_7': '7sus4',
        }.get(quality, quality)

        name = f"{root_name}{quality_label}"
        if not add_sus4:
            if add_13th:
                # Cmaj7+13 → Cmaj13, Cm7+13 → Cm13, C7+13 → C13
                name = name.replace('maj7', 'maj').replace('m7', 'm').replace('7', '') + '13'
                if 'maj13' not in name and 'm13' not in name and not name.endswith('13'):
                    name += '13'
            elif add_11th:
                name = name.replace('maj7', 'maj').replace('m7', 'm').replace('7', '') + '11'
                if not name.endswith('11'):
                    name += '11'
            elif add_9th:
                if add_7th:
                    # Cmaj7+9 → Cmaj9, Cm7+9 → Cm9, C7+9 → C9
                    name = name.replace('maj7', 'maj').replace('m7', 'm').replace('7', '') + '9'
                    if not name.endswith('9'):
                        name += '9'
                else:
                    name += 'add9'

        roman = ROMAN[degree - 1]
        if quality in ('minor', 'minor7', 'diminished', 'dim7', 'min7b5'):
            roman = roman.lower()

        return {
            'notes': notes,
            'name': name,
            'roman': roman,
            'root_name': root_name,
            'note_names': [midi_to_note_name(n) for n in notes],
            'quality': quality,
            'degree': degree,
        }

    def _diatonic_7th_for_quality(self, quality: str, degree: int) -> str:
        """Get the 7th chord type based on the triad quality.
        
        major triad -> major7 (or dominant7 for V)
        minor triad -> minor7
        diminished triad -> min7b5
        """
        if quality == 'major':
            # V chord naturally gets dom7; otherwise maj7
            if degree == 5:
                return 'dominant7'
            return 'major7'
        elif quality == 'minor':
            return 'minor7'
        elif quality == 'diminished':
            return 'min7b5'
        return 'dominant7'

    def build_sauce_chord(self, degree: int) -> dict:
        """
        Sauce mode: jazz voicings with good voice leading.
        
        Uses drop-2 and spread voicings that sit well in the mid register.
        All voicings are designed so adjacent degrees share common tones
        and move by small intervals (good voice leading).
        
        Intervals are ABSOLUTE semitones from C0 (MIDI note numbers),
        built relative to the scale degree root in the current octave.
        """
        if degree < 1 or degree > 7:
            return {'notes': [], 'name': '', 'roman': '', 'root_name': '', 'degree': 0}

        root = self.get_scale_degree_root(degree)

        # Sauce voicings: each is a list of semitone offsets from root
        # Designed as drop-2 / spread voicings for smooth voice leading
        # Voicings stay compact (within ~2 octaves) for playability
        if self.mode == 'major':
            sauce_voicings = {
                # I: Cmaj9 drop-2 — root, 9th, 3rd, 7th (rootless-ish, open)
                1: ([0, 4, 11, 14], 'maj9'),
                # ii: Dm9 — root, b3, b7, 9th
                2: ([0, 3, 10, 14], 'm9'),
                # iii: Em7(9) — root, b3, b7, 9 (same shape, different root)
                3: ([0, 3, 10, 14], 'm9'),
                # IV: Fmaj7#11 — root, 3rd, 7th, #11th
                4: ([0, 4, 11, 18], 'maj7#11'),
                # V: G9 — root, 3rd, b7, 9th (drop-2 dom9, no 13)
                5: ([0, 4, 10, 14], '9'),
                # vi: Am9 — root, b3, b7, 9th
                6: ([0, 3, 10, 14], 'm9'),
                # vii: Bm7b5(9) — root, b3, b5, b7, 9
                7: ([0, 3, 6, 10, 14], 'm7b5(9)'),
            }
        else:
            sauce_voicings = {
                # i: Cm9 
                1: ([0, 3, 10, 14], 'm9'),
                # ii: Dm7b5(9)
                2: ([0, 3, 6, 10, 14], 'm7b5(9)'),
                # III: Ebmaj9
                3: ([0, 4, 11, 14], 'maj9'),
                # iv: Fm11 — root, b3, b7, 11th
                4: ([0, 3, 10, 17], 'm11'),
                # v: Gm9
                5: ([0, 3, 10, 14], 'm9'),
                # VI: Abmaj9
                6: ([0, 4, 11, 14], 'maj9'),
                # VII: Bb13
                7: ([0, 4, 10, 21], '13'),
            }

        intervals, suffix = sauce_voicings[degree]
        notes = [root + i for i in intervals]

        root_name = midi_to_note_name(root).rstrip('0123456789')
        name = f"{root_name}{suffix}"

        roman = ROMAN[degree - 1]
        if 'm' in suffix and suffix != 'maj9' and suffix != 'maj7#11':
            roman = roman.lower()

        return {
            'notes': notes,
            'name': f"~{name}~",
            'roman': roman,
            'root_name': root_name,
            'note_names': [midi_to_note_name(n) for n in notes],
            'quality': suffix,
            'degree': degree,
        }

    def get_key_display(self) -> str:
        """Get display-friendly key name."""
        return KEY_DISPLAY.get(self.key, self.key)

    def get_mode_display(self) -> str:
        return self.mode.capitalize()
