"""
MIDI Camera modes.

Each mode defines how hand gestures map to MIDI output.
"""

from core.modes.base import Mode
from core.modes.chord_andrew import AndrewMode
from core.modes.chord_dylan import DylanMode
from core.modes.melody_piano import MelodyPianoMode
from core.modes.melody_theremin import MelodyThereminMode
from core.modes.melody_guitar import MelodyGuitarMode
from core.modes.midi_mapper import MidiMapperMode
from core.modes.drums_finger import DrumsFingerMode
from core.modes.drums_zone import DrumsZoneMode
from core.modes.drums_strike import DrumsStrikeMode


def get_all_modes(voicing_editor=None, bass_pedals=None) -> list[Mode]:
    """Create and return all available modes in order."""
    return [
        AndrewMode(voicing_editor, bass_pedals),       # 1
        DylanMode(voicing_editor, bass_pedals),         # 2
        MelodyPianoMode(),                              # 3
        MelodyThereminMode(),                           # 4
        MelodyGuitarMode(),                             # 5
        MidiMapperMode(),                               # 6
        DrumsFingerMode(),                              # 7
        DrumsZoneMode(),                                # 8
        DrumsStrikeMode(),                              # 9
    ]
