# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Webcam-based MIDI controller for macOS. Hand gestures → chord degrees (Nashville Number System), left hand → extensions/modifiers, face → jazz voicings. Uses MediaPipe for hand/face tracking, python-rtmidi for MIDI output, OpenCV for camera + UI overlay. No GUI framework — all drawing is raw OpenCV.

## Running

```bash
source .venv/bin/activate

# Menu bar app (recommended)
python menubar.py

# Standalone camera window
python app.py

# Override performance tier
MIDI_CAMERA_TIER=high python app.py
```

Requires macOS, Python 3.12, IAC Driver enabled (Audio MIDI Setup → IAC Driver → "Device is online").

## Install / Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Models must exist in models/ — download via install.sh or manually
```

No tests exist. No CI. No linter configured.

## Architecture

### Data Flow (per frame)

```
Camera → HandTracker (bg thread) → gesture.py → Mode.process_frame() → midi_output → DAW
                                                      ↓
                                              ui/overlay.py → cv2.imshow()
```

### Threading Model

- **Main thread**: camera read, face inference, gesture interpretation, mode processing, MIDI send, overlay drawing, keyboard input
- **Background thread** (`HandTracker._inference_loop`): MediaPipe hand inference. Single-slot frame submission (`_frame_slot`) — drops old frames if inference lags. Results read via `tracker.get_result()` under `threading.Lock`

### Key Files

| File | Role |
|---|---|
| `app.py` | Main loop, VoicingEditor, BassAndPedals, DegradationMonitor, keyboard dispatch |
| `menubar.py` | macOS menu bar app (rumps), camera detection, launches app.py as subprocess |
| `core/chord_engine.py` | Stateless Nashville Number chord builder (diatonic chords, extensions, sauce voicings) |
| `core/gesture.py` | Landmark → gesture interpretation. FingerDetector (hysteresis thresholds), HandPersistence (3-frame hold), RightHandGesture/LeftHandGesture dataclasses |
| `core/hand_tracker.py` | MediaPipe HandLandmarker wrapper, background inference thread |
| `core/face_tracker.py` | MediaPipe FaceLandmarker, sauce-mode toggle via jaw/tongue blendshapes |
| `core/midi_output.py` | python-rtmidi virtual port wrapper, send_chord/send_chord_diff/send_note/send_cc. All notes/velocity clamped 0-127; `active_notes` stores clamped values |
| `core/mode_manager.py` | Mode switching, lifecycle (on_enter/on_exit), key routing |
| `core/performance.py` | Hardware tier detection (HIGH/MEDIUM/LOW), adaptive settings |
| `core/modes/base.py` | Abstract Mode base class with settle/debounce gate |
| `core/modes/__init__.py` | `get_all_modes()` factory — ordered list of all 9 modes |
| `ui/overlay.py` | All OpenCV drawing (chord cards, panels, sliders, help, debug). `draw_semi_transparent_rect` uses ROI-only copy+blend (not full frame) |
| `ui/config_screen.py` | OpenCV-based pre-launch config screen |

### Mode System

All modes extend `core/modes/base.py:Mode`. Key interface:

```python
class Mode(ABC):
    name: str
    description: str
    debounce_time: float = 0.10
    supports_voicings: bool = False
    supports_bass_pedals: bool = False
    supports_sauce: bool = False
    supports_smart_extensions: bool = False

    def process_frame(self, right_gesture, left_hand, sauce_from_face, engine, midi, now) -> dict
    def reset_state(self)  # clears debounce/settle state (e.g. after key change)
    def handle_key(self, key, raw_key, **context) -> bool
    def on_enter(self, midi) / on_exit(self, midi)
    def get_help_sections(self) -> list
```

`process_frame` returns a result dict with `type` (`'chord'|'melody'|'drums'|'mapper'`), `chord_info`, `velocity`, etc. The `type` field determines which `draw_*` function `app.py` calls.

**Settle/debounce pattern**: Chord/melody modes call `self._check_settle(new_notes, new_info, now)` — notes must be stable for `debounce_time` seconds before MIDI fires. Drum modes set `debounce_time = 0.0` and use rising-edge detection. Call `mode.reset_state()` (not `mode._current = None`) when key/octave changes to fully clear debounce state.

**Smart extensions**: When enabled, `midi.send_chord_diff()` sustains unchanged triad notes while toggling extension notes (avoids retriggering the whole chord).

**Mode switch lifecycle**: `on_exit()` → `all_notes_off()` → `reset_gesture_state()` → `on_enter()`. Note-off fires *before* new mode enters. All drum modes must call `super().on_exit(midi)` after their own cleanup.

**Exception safety**: The main loop in `app.py` is wrapped in `try/except` — any unhandled exception breaks the loop and cleanup (MIDI close, camera release) always runs.

### Gesture Detection

- **Hysteresis**: `FingerDetector`/`ThumbDetector` use separate extend/retract thresholds (no smoothing buffer)
- **Persistence**: `HandPersistence` holds last valid reading for 3 frames when detection drops
- **Scale-invariant**: All distances normalized by palm size (WRIST to MIDDLE_MCP)
- `RightHandGesture` fields: `degree`, `finger_count`, `wrist_y`, `wrist_x`, `extended` (list of 4 bools), `thumb_out` (bool). Modes should read `extended`/`thumb_out` from the gesture dataclass — never access `_right_fingers._states` or `_right_thumb._is_out` directly.
- `reset_gesture_state()` clears all hysteresis/persistence state. Called on mode switch and ESC.

### Config Persistence

`config.json` (gitignored) stores key, mode, channel, octave, camera, camera_name, mode_index, smart_extensions. Saved incrementally via `_save_config(updates)`. Camera persisted by **name** not index (macOS reorders indices across reboots).

## Modes (9 total)

| # | Mode | Type | Notes |
|---|------|------|-------|
| 1 | Andrew | chord | Jazz stacking (7/9/11/13), sauce voicings, smart extensions |
| 2 | Dylan | chord | Pop extensions (7/add9/sus4/9th), smart extensions |
| 3 | Melody Piano | melody | Finger count = scale degree |
| 4 | Melody Theremin | melody | Y = pitch, X = vibrato CC |
| 5 | Melody Guitar | melody | Pluck gesture triggers notes |
| 6 | MIDI Mapper | mapper | Hand axes → CC1-CC6 (EMA smoothed) |
| 7 | Drums Finger | drums | Per-finger = drum pad (8 pads) |
| 8 | Drums Zone | drums | 2×4 screen grid = pads |
| 9 | Drums Strike | drums | Downward strike = hit |

See [CONTROLS.md](CONTROLS.md) for a full cheat sheet of all gestures and keyboard shortcuts per mode.

## Adding a New Mode

1. Create `core/modes/your_mode.py` extending `Mode`
2. Implement `process_frame()` returning a result dict with `type` key
3. Add to the list in `core/modes/__init__.py` (`get_all_modes()`)
4. If new `type` value, add corresponding `draw_*` function in `ui/overlay.py` and dispatch in `app.py`
5. Override `on_exit(self, midi)` for cleanup, always call `super().on_exit(midi)` at the end
6. For drum modes: never send note-on + note-off in the same frame (zero-length notes). Track held notes and release on the next frame or zone change.
