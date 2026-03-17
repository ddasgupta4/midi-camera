# MIDI Camera

Hand gesture MIDI controller using computer vision and the Nashville Number System. Point your webcam at your hands and play chords in any DAW.

**Right hand** = chord degree (I-VII). **Left hand** = quality modifiers + velocity.

## Requirements

- Python 3.12 (3.14 doesn't compile python-rtmidi yet)
- macOS with IAC Driver enabled (for virtual MIDI routing)
- Webcam
- `brew install python@3.12 python-tk@3.12`

## Setup

### 1. Enable IAC Driver (macOS)

Open **Audio MIDI Setup** (Spotlight -> "Audio MIDI Setup"), then go to **Window > Show MIDI Studio**. Double-click **IAC Driver**, check **"Device is online"**, and close.

### 2. Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run

```bash
source .venv/bin/activate
python app.py
```

A config screen appears first — pick your key, mode, MIDI channel, octave, and camera. Hit Start.

## Gesture Reference

### Right Hand — Chord Degree

| Gesture | Degree |
|---------|--------|
| Closed fist | None (silence) |
| 1 finger (index) | I |
| 2 fingers (index + middle) | II |
| 3 fingers (index + middle + ring) | III |
| 4 fingers (all except thumb) | IV |
| 5 fingers (all including thumb) | V |
| Thumb only | VI |
| Thumb + pinky | VII |

### Left Hand — Modifiers

| Gesture | Effect |
|---------|--------|
| No left hand / relaxed | Diatonic default quality |
| Open flat palm | Force major |
| Curled half-fist | Force minor |
| Pinch (thumb + index) | Dominant 7th |
| All fingers spread wide | Major 7th |
| Index finger only | Add 7th to chord |
| Index + middle (peace) | Add 9th to chord |
| Hand height (top/bottom) | Velocity (high/low, 40-127) |

## Connecting to Ableton

1. Open Ableton Live
2. Go to **Preferences > Link/Tempo/MIDI**
3. Under MIDI Ports, find **"MIDI Camera"** (or IAC Driver)
4. Enable **Track** and/or **Remote** for the input
5. Arm a MIDI track — incoming chords should trigger your instrument

Also works with Logic, GarageBand, Reaper, or anything that accepts MIDI input.

## Controls

- **Q** — Quit
- **ESC** — Return to config screen

## Project Structure

```
app.py              — main entry point (config -> camera loop)
core/
  chord_engine.py   — Nashville Number System, chord voicing builder
  hand_tracker.py   — MediaPipe Hands wrapper
  gesture.py        — gesture interpretation (finger counting, modifiers)
  midi_output.py    — python-rtmidi wrapper, note on/off
ui/
  overlay.py        — OpenCV HUD (chord card, velocity bar, status)
  config_screen.py  — tkinter config dialog
```
