"""
Abstract base class for MIDI Camera modes.

Each mode defines how hand gestures map to MIDI output.
Modes own their own settle/debounce logic and MIDI sending.
"""

from abc import ABC, abstractmethod


def _midi_name(midi_num: int) -> str:
    NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    octave = (midi_num // 12) - 1
    return f"{NOTE_NAMES[midi_num % 12]}{octave}"


class Mode(ABC):
    """Base class for all MIDI Camera modes."""

    name: str = ""
    description: str = ""
    debounce_time: float = 0.10  # settle window in seconds

    # Feature flags — app.py uses these to enable/disable UI panels
    supports_voicings: bool = False
    supports_bass_pedals: bool = False
    supports_sauce: bool = False
    supports_smart_extensions: bool = False

    def __init__(self):
        self._desired_notes: list = []
        self._desired_info: dict = {}
        self._desired_since: float = 0.0
        self._current: dict | None = None

    def reset_state(self):
        """Reset debounce/settle state (e.g. after key change)."""
        self._current = None
        self._desired_notes = []
        self._desired_info = {}
        self._desired_since = 0.0

    @property
    def current_playing_notes(self) -> list:
        return self._current.get('notes', []) if self._current else []

    def _check_settle(self, new_notes: list, new_info: dict, now: float) -> bool:
        """
        Common settle logic. Call each frame with what SHOULD play.
        Returns True when the desired notes have been stable long enough to fire.
        """
        if new_notes != self._desired_notes:
            self._desired_notes = list(new_notes)
            self._desired_info = dict(new_info) if new_info else {}
            self._desired_since = now

        playing = self.current_playing_notes
        return self._desired_notes != playing and (now - self._desired_since) >= self.debounce_time

    @abstractmethod
    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now: float) -> dict:
        """
        Process one frame. Interpret gestures, settle, send MIDI.

        Args:
            right_gesture: RightHandGesture (shared) or None
            left_hand: raw HandData for left hand (mode interprets this)
            sauce_from_face: bool or None (from face tracker, None = no tracker)
            engine: ChordEngine
            midi: MidiOutput
            now: current time.time()

        Returns dict with at least:
            type: 'chord' | 'melody'
            chord_info: dict (compatible with draw_chord_card)
            velocity: int
            left_gesture_name: str
            sauce_mode: bool
            desired_notes: list
            desired_since: float
        """

    def handle_key(self, key: int, raw_key: int, **context) -> bool:
        """Handle mode-specific keyboard shortcut. Return True if consumed."""
        return False

    def on_enter(self, midi):
        """Called when entering this mode."""
        pass

    def on_exit(self, midi):
        """Called when leaving this mode."""
        midi.all_notes_off()
        self._current = None
        self._desired_notes = []
        self._desired_info = {}

    def get_help_sections(self) -> list:
        """Return [(section_title, [item_strings])] for help overlay."""
        return []
