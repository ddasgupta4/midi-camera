# MIDI Camera — Controls Cheat Sheet

## Global Keyboard

| Key | Action |
|---|---|
| `A S D F G H J` | Set key: C D E F G A B |
| `W E T Y U` | Set key: C# D# F# G# A# |
| `< >` (arrows) | Chromatic key shift |
| `Z / X` | Octave down / up |
| `M` | Toggle major / minor |
| `/` | Cycle mode forward |
| `1-9` | Jump to mode directly |
| `.` | Toggle smart extensions |
| `;` | Manual sauce toggle (Andrew) |
| `V` | Voicing panel |
| `P` | Bass & pedal panel |
| `L` | Latency slider |
| `H` | Help overlay |
| `` ` `` | Debug overlay |
| `Q` | Quit |
| `ESC` | Close panel / back to config |

---

## Right Hand — Degree Mapping (shared across chord + melody modes)

| Gesture | Degree |
|---|---|
| Fist | Silence |
| 1 finger | I |
| 2 fingers | II |
| 3 fingers | III |
| 4 fingers (thumb tucked) | IV |
| Open hand (thumb out) | V |
| Thumb only | VI |
| Thumb + pinky | VII |

---

## Mode 1 — Andrew (Jazz Chords)

| Hand | Gesture | Effect |
|---|---|---|
| Left | Fist | Triad |
| Left | 1 finger | + 7th |
| Left | 2 fingers | + 9th |
| Left | 3 fingers | + 11th |
| Left | 4 fingers | + 13th |
| Left | Thumb out | Flip quality (maj↔min) |
| Left | Wrist height | Velocity |
| Face | Open mouth | Sauce mode (jazz voicings) |

**Supports:** voicings, bass/pedals, sauce, smart extensions

---

## Mode 2 — Dylan (Pop Chords)

| Hand | Gesture | Effect |
|---|---|---|
| Left | Fist | Triad |
| Left | 1 finger | 7th |
| Left | 2 fingers | add9 (no 7th) |
| Left | 3 fingers | sus4 |
| Left | 4 fingers | 9th (7th + 9th) |
| Left | Thumb out | Flip quality |
| Left | Wrist height | Velocity |

**Supports:** voicings, bass/pedals, smart extensions. No sauce.

---

## Mode 3 — Melody Piano

| Hand | Gesture | Effect |
|---|---|---|
| Right | Degree gesture | Scale degree (single note) |
| Right | Wrist height | Velocity |
| Left | Fist | Base octave |
| Left | 1-4 fingers | Octave +1 to +4 |
| Left | Thumb out | Sustain (hold note) |

---

## Mode 4 — Melody Theremin

| Hand | Gesture | Effect |
|---|---|---|
| Right | Y position | Pitch (top=high, bottom=low, smoothed + quantized to scale) |
| Right | X position | Vibrato (CC1 mod wheel). Center 30% = deadzone. |
| Right | Wrist height | Velocity (high = loud) |
| Right | Fist | Silence |
| Right | Any fingers | Enable pitch tracking |
| Left | 0-4 fingers | Octave offset +0 to +4 |
| Left | Thumb out | Sustain |
| Key `C` | — | Toggle continuous (pitch-bend glissando) mode |

3 octaves of scale notes. Positions are EMA-smoothed to kill hand tremor.
In continuous mode, MIDI pitch bend fills in between scale notes for a true
theremin slide. In-scene overlay: right-edge pitch ladder shows your current
position; top-center bar shows vibrato depth.

---

## Mode 5 — Melody Guitar

| Hand | Gesture | Effect |
|---|---|---|
| Left | 1-5 fingers | Scale degree 1-5 |
| Left | Thumb only | Scale degree 6 |
| Left | Thumb + pinky | Scale degree 7 |
| Right | Down flick | Pluck / trigger note (down-strum) |
| Right | Up flick | Pluck / trigger note (up-strum) |
| Right | 1-4 fingers **at pluck time** | Octave 0 to +3 (latched — you don't need to hold) |
| Right | Pinch (thumb + index touch) | Release note |
| Right | Fist | Release note |
| Right | Pluck speed | Velocity (time-normalized, frame-rate independent) |

In-scene overlay: pluck flash + cooldown ring at wrist.

---

## Mode 6 — MIDI Mapper

| Axis | CC | Range |
|---|---|---|
| Right X | CC1 | 0-127 |
| Right Y | CC2 | 0-127 |
| Right finger count | CC5 | 0-127 |
| Left X | CC3 | 0-127 |
| Left Y | CC4 | 0-127 |
| Left finger count | CC6 | 0-127 |

All values EMA-smoothed (α=0.3). Continuous stream, no debounce.

---

## Mode 7 — Drums Finger

| Finger | Right Hand | Left Hand |
|---|---|---|
| Index | Kick (36) | Crash (49) |
| Middle | Snare (38) | Ride (51) |
| Ring | Closed Hat (42) | Low Tom (45) |
| Pinky | Open Hat (46) | High Tom (48) |
| Thumb | Accent (+30 vel) | Accent (+30 vel) |
| Wrist height | Velocity | Velocity |

Rising-edge detection. Extend finger = hit, retract = release.

---

## Mode 8 — Drums Zone

```
Screen grid (2x4):
+----------+----------+----------+----------+
|  CRASH   |  RIDE    |  OP-HAT  |  SPLASH  |
|   (49)   |   (51)   |   (46)   |   (55)   |
+----------+----------+----------+----------+
|  KICK    |  SNARE   |  CH-HAT  |  TOM     |
|   (36)   |   (38)   |   (42)   |   (45)   |
+----------+----------+----------+----------+
```

**Trigger**: moving into a new zone OR striking down within the same zone
(so you can repeatedly hit a kick without leaving the cell).
**Velocity**: downward component of wrist velocity (rewards striking force,
not lateral drift).
**Decay**: notes release after ~80 ms — drums don't sustain.
**Overlay**: grid is drawn directly on the camera view with per-cell hit
flashes and live crosshairs at each wrist.

---

## Mode 9 — Drums Strike

8 pads total (4 per hand), picked by wrist (x, y) at the moment of impact:

```
Right hand                  Left hand
+-----------+-----------+   +-----------+-----------+
| RIDE (51) | CRASH(49) |   |OP-HAT(46) |SPLASH(55) |
+-----------+-----------+   +-----------+-----------+
| KICK (36) | SNARE(38) |   |CH-HAT(42) | TOM  (45) |
+-----------+-----------+   +-----------+-----------+
```

**Trigger**: fast downward wrist velocity (time-normalized, frame-rate
independent).
**Reset gate**: after a strike, the wrist must rise back above the strike
point before another strike is allowed — prevents vertical oscillation from
double-triggering.
**Velocity**: strike speed.
**Overlay**: target rectangles drawn on the camera view, fading motion
trails show your strike arc, and cells flash on hit.

---

## Voicing Panel (`V`)

| Key | Action |
|---|---|
| `< >` | Select degree |
| `I / U` | Invert up / down |
| `N` | Cycle selected note |
| `↑ ↓` | Nudge note ±1 semitone |
| `R` | Reset degree |
| `V / ESC` | Close |

## Bass & Pedal Panel (`P`)

| Key | Action |
|---|---|
| `B` | Toggle bass note |
| `↑ ↓` | Bass octave offset |
| `< >` | Select pedal |
| `N` | Cycle adding note name |
| `O / I` | Adding octave up / down |
| `Enter` | Add pedal |
| `X` | Delete selected pedal |
| `R` | Reset all |

## Latency Slider (`L`)

| Key | Action |
|---|---|
| `< >` | Adjust debounce ±10ms |
| `R` | Reset to default (100ms) |
