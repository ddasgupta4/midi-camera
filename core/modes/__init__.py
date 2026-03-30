"""
MIDI Camera modes.

Each mode defines how hand gestures map to MIDI output.
"""

from core.modes.base import Mode
from core.modes.chord_andrew import AndrewMode
from core.modes.chord_dylan import DylanMode
from core.modes.melody_piano import MelodyPianoMode


def get_all_modes(voicing_editor=None, bass_pedals=None) -> list[Mode]:
    """Create and return all available modes in order."""
    return [
        AndrewMode(voicing_editor, bass_pedals),
        DylanMode(voicing_editor, bass_pedals),
        MelodyPianoMode(),
    ]
