"""
MIDI output via python-rtmidi.

Opens a virtual MIDI port and sends note on/off messages
for chord voicings. Handles chord transitions cleanly.
"""

import rtmidi
from typing import List, Optional


class MidiOutput:
    def __init__(self, port_name: str = "MIDI Camera", channel: int = 0):
        """
        Initialize MIDI output with a virtual port.

        Args:
            port_name: Name of the virtual MIDI port
            channel: MIDI channel 0-15 (displayed as 1-16)
        """
        self.port_name = port_name
        self.channel = channel
        self.midi_out: Optional[rtmidi.MidiOut] = None
        self.active_notes: List[int] = []
        self.connected = False

    def open(self) -> bool:
        """Open the virtual MIDI port. Returns True on success."""
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_out.open_virtual_port(self.port_name)
            self.connected = True
            return True
        except Exception as e:
            print(f"[MIDI] Failed to open port: {e}")
            self.connected = False
            return False

    def send_chord(self, notes: List[int], velocity: int = 100):
        """
        Send a new chord. Turns off any previous notes first,
        then sends note-on for the new chord.
        """
        if not self.connected or not self.midi_out:
            return

        # Note-off for all currently active notes
        self.all_notes_off()

        # Note-on for new chord
        for note in notes:
            note = max(0, min(127, note))
            msg = [0x90 | self.channel, note, velocity]
            self.midi_out.send_message(msg)

        self.active_notes = list(notes)

    def send_chord_diff(self, notes: List[int], velocity: int = 100):
        """
        Smart chord update — sustain unchanged notes, only NoteOff
        dropped notes and NoteOn added notes. Use for extension changes.
        """
        if not self.connected or not self.midi_out:
            return

        current = set(self.active_notes)
        desired = set(notes)

        # NoteOff only for notes that left the chord
        for note in sorted(current - desired):
            note = max(0, min(127, note))
            self.midi_out.send_message([0x80 | self.channel, note, 0])

        # NoteOn only for new notes
        for note in sorted(desired - current):
            note = max(0, min(127, note))
            self.midi_out.send_message([0x90 | self.channel, note, velocity])

        self.active_notes = list(notes)

    def send_note(self, note: int, velocity: int = 100, on: bool = True):
        """Send a single note on or off."""
        if not self.connected or not self.midi_out:
            return
        note = max(0, min(127, note))
        velocity = max(0, min(127, velocity))
        if on:
            msg = [0x90 | self.channel, note, velocity]
            self.midi_out.send_message(msg)
            if note not in self.active_notes:
                self.active_notes.append(note)
        else:
            msg = [0x80 | self.channel, note, 0]
            self.midi_out.send_message(msg)
            if note in self.active_notes:
                self.active_notes.remove(note)

    def send_cc(self, cc_number: int, value: int, channel: int | None = None):
        """Send a MIDI Control Change message."""
        if not self.connected or not self.midi_out:
            return
        ch = channel if channel is not None else self.channel
        cc_number = max(0, min(127, cc_number))
        value = max(0, min(127, value))
        msg = [0xB0 | ch, cc_number, value]
        self.midi_out.send_message(msg)

    def all_notes_off(self):
        """Send note-off for all active notes."""
        if not self.connected or not self.midi_out:
            return

        for note in self.active_notes:
            msg = [0x80 | self.channel, note, 0]
            self.midi_out.send_message(msg)

        self.active_notes = []

    def set_channel(self, channel: int):
        """Set MIDI channel (0-15)."""
        self.channel = max(0, min(15, channel))

    def close(self):
        """Clean shutdown: all notes off, close port."""
        self.all_notes_off()
        if self.midi_out:
            self.midi_out.close_port()
            del self.midi_out
            self.midi_out = None
        self.connected = False
