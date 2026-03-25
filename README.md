# 🎹 MIDI Camera

Turn your webcam into a MIDI chord controller. Use hand gestures to play chords in any DAW — inspired by [Imogen Heap's Mi.Mu Gloves](https://mimugloves.com/).

**Right hand** = chord degree (Nashville Number System I–VII)  
**Left hand** = extensions & modifiers (7th, 9th, sus4, quality flip)  
**Face** = sauce mode (jazz voicings via jaw/tongue — Andrew Mode only)

## Quick Install

```bash
curl -sL https://raw.githubusercontent.com/ddasgupta4/midi-camera/master/install.sh | bash
```

This will:
- Install Python 3.12 + dependencies automatically
- Download the AI hand/face tracking models
- Create a desktop shortcut

**Requirements:** macOS (Apple Silicon or Intel), a webcam, a DAW with MIDI input.

## Manual Install

```bash
git clone https://github.com/ddasgupta4/midi-camera.git
cd midi-camera
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p models
curl -sL -o models/hand_landmarker.task "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
curl -sL -o models/face_landmarker.task "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
```

## MIDI Setup

You need a virtual MIDI port for the app to send MIDI to your DAW:

1. Open **Audio MIDI Setup** (search in Spotlight)
2. Go to **Window → Show MIDI Studio**
3. Double-click **IAC Driver**
4. Check **"Device is online"**
5. In your DAW, set the MIDI input to "MIDI Camera"

## Usage

```bash
# Menu bar app (recommended)
python menubar.py

# Or standalone camera window
python app.py
```

The menu bar app (🎹) lets you configure camera, MIDI channel, key, mode, and octave before launching.

## Controls

### Right Hand (Degree)
| Gesture | Chord |
|---|---|
| Fist | Silence |
| 1 finger | I |
| 2 fingers | II |
| 3 fingers | III |
| 4 fingers (thumb tucked) | IV |
| Open hand (thumb out) | V |
| Thumb only | VI |
| Thumb + pinky | VII |

### Left Hand — Dylan Mode (Pop/Indie/Emo)
| Gesture | Effect |
|---|---|
| Fist | Triad |
| Thumb out | Flip quality (maj↔min) |
| 1 finger | 7th (adaptive — maj7 or m7) |
| 2 fingers | add9 (no 7th) |
| 3 fingers | sus4 |
| 4 fingers | 9th (7+9) |
| Wrist height | Velocity |

### Left Hand — Andrew Mode (Jazz)
| Gesture | Effect |
|---|---|
| Fist | Triad |
| Thumb out | Flip quality (maj↔min) |
| 1 finger | 7th |
| 2 fingers | 9th |
| 3 fingers | 11th |
| 4 fingers | 13th |
| Face (jaw/tongue) | Sauce mode (jazz voicings) |

### Keyboard Shortcuts
| Key | Action |
|---|---|
| `A S D F G H J` | Set key to C D E F G A B |
| `W E T Y U` | Set key to C# D# F# G# A# |
| `Z / X` | Octave down / up |
| `M` | Toggle major / minor |
| `← →` | Chromatic key shift |
| `/` | Toggle Andrew / Dylan mode |
| `V` | Voicing panel |
| `P` | Bass & pedal panel |
| `L` | Latency slider |
| `.` | Toggle smart extensions |
| `;` | Manual sauce toggle (Andrew Mode) |
| `H` | Help overlay |
| `` ` `` | Debug overlay |
| `Q` | Quit |

## Updating

Click **"Check for Updates"** in the menu bar app, or:

```bash
cd ~/midi-camera && bash update.sh
```

## How It Works

- **MediaPipe** hand & face tracking (runs locally, no cloud)
- **python-rtmidi** for virtual MIDI output
- **OpenCV** for camera feed & overlay
- Adaptive performance: auto-detects your Mac's capability and adjusts inference resolution

## License

MIT
