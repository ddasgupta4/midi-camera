"""
Mode manager — tracks available modes, handles switching.

Handles lifecycle (on_enter/on_exit), fires all_notes_off on switch,
and processes mode-switching keys (/ to cycle, 1-9 for direct select).
"""

from core.modes.base import Mode


class ModeManager:
    def __init__(self, modes: list[Mode], initial_index: int = 0):
        self.modes = modes
        self._index = max(0, min(initial_index, len(modes) - 1))

    @property
    def current_mode(self) -> Mode:
        return self.modes[self._index]

    @property
    def current_index(self) -> int:
        return self._index

    def switch_to(self, index: int, midi) -> bool:
        """Switch to mode at index. Returns True if switched."""
        if index < 0 or index >= len(self.modes) or index == self._index:
            return False
        self.modes[self._index].on_exit(midi)
        self._index = index
        self.modes[self._index].on_enter(midi)
        midi.all_notes_off()
        return True

    def next_mode(self, midi) -> bool:
        new_idx = (self._index + 1) % len(self.modes)
        return self.switch_to(new_idx, midi)

    def prev_mode(self, midi) -> bool:
        new_idx = (self._index - 1) % len(self.modes)
        return self.switch_to(new_idx, midi)

    def handle_key(self, key: int, raw_key: int, midi) -> bool:
        """
        Handle mode-switching keys.
        / = cycle forward, 1-9 = direct select.
        Returns True if a key was consumed.
        """
        if key == ord('/'):
            self.next_mode(midi)
            return True
        if ord('1') <= key <= ord('9'):
            idx = key - ord('1')
            if idx < len(self.modes):
                self.switch_to(idx, midi)
                return True
        return False
