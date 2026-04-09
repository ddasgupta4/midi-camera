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
| Right | Y position | Pitch (top=high, bottom=low, quantized to scale) |
| Right | X position | Vibrato (CC1 mod wheel, edges=more) |
| Right | Fist | Silence |
| Right | Any fingers | Enable pitch tracking |
| Left | 0-4 fingers | Octave offset +0 to +4 |
| Left | Thumb out | Sustain |

2 octaves of scale notes, quantized.

---

## Mode 5 — Melody Guitar

| Hand | Gesture | Effect |
|---|---|---|
| Left | 1-5 fingers | Scale degree 1-5 |
| Left | Thumb only | Scale degree 6 |
| Left | Thumb + pinky | Scale degree 7 |
| Right | Downward flick | Pluck / trigger note |
| Right | Fist | Mute / note off |
| Right | 1-4 fingers (while held) | Octave 0 to +3 |
| Right | Pluck speed | Velocity |

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

Move hand into zone = trigger. Hand speed = velocity. Both hands tracked independently.

---

## Mode 9 — Drums Strike

| Hand | Left half (X < 0.5) | Right half (X > 0.5) |
|---|---|---|
| Right | Kick (36) | Snare (38) |
| Left | Closed Hat (42) | Crash (49) |

Strike down (fast wrist drop) = hit. Strike speed = velocity.

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
