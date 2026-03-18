"""
MIDI Camera — Controls Infographic Generator
Run: .venv/bin/python3.12 make_infographic.py
Outputs: infographic.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# ── Colors ──
BG       = '#0d0f14'
CARD     = '#161b24'
BORDER   = '#2a3040'
GREEN    = '#3dff8f'
CYAN     = '#00d4ff'
PURPLE   = '#b060ff'
AMBER    = '#ffb020'
WHITE    = '#f0f0f0'
GRAY     = '#7a8090'
DGRAY    = '#3a3f50'
SAUCE    = '#00ccee'
RED      = '#ff5050'

fig = plt.figure(figsize=(20, 26), facecolor=BG)
fig.patch.set_facecolor(BG)

def card(ax, x, y, w, h, color=CARD, border=BORDER, radius=0.015):
    box = FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=color, edgecolor=border, linewidth=1.2,
        transform=ax.transAxes, clip_on=False)
    ax.add_patch(box)

def label(ax, x, y, text, size=11, color=WHITE, weight='normal', ha='left', va='center'):
    ax.text(x, y, text, transform=ax.transAxes,
            fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, fontfamily='monospace')

ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

# ── Title ──
ax.text(0.5, 0.965, 'MIDI CAMERA', fontsize=46, color=WHITE,
        fontweight='bold', ha='center', va='top', transform=ax.transAxes,
        fontfamily='monospace')
ax.text(0.5, 0.945, 'wave your hands. play chords. stick your tongue out.',
        fontsize=14, color=GRAY, ha='center', va='top', transform=ax.transAxes,
        fontfamily='monospace')
ax.axhline(y=0.935, xmin=0.05, xmax=0.95, color=BORDER, linewidth=1)

# ═══════════════════════════════════════════════
# RIGHT HAND — SCALE DEGREE
# ═══════════════════════════════════════════════
card(ax, 0.04, 0.68, 0.44, 0.25)
ax.text(0.06, 0.92, '✋  RIGHT HAND', fontsize=16, color=GREEN,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.text(0.06, 0.906, 'your left hand in real life (mirrored camera)',
        fontsize=9.5, color=GRAY, transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.900, xmin=0.055, xmax=0.465, color=DGRAY, linewidth=0.8)

gestures_r = [
    ('✊  Fist',            '→  Silence / note off'),
    ('☝️  1 finger',        '→  Chord  I'),
    ('✌️  2 fingers',       '→  Chord  II'),
    ('🤟  3 fingers',       '→  Chord  III'),
    ('🖖  4 fingers (thumb tucked)', '→  Chord  IV'),
    ('🖐  Open hand',       '→  Chord  V'),
    ('👍  Thumb only',      '→  Chord  VI'),
    ('🤙  Thumb + pinky',   '→  Chord  VII'),
]

for i, (gesture, result) in enumerate(gestures_r):
    y = 0.888 - i * 0.026
    ax.text(0.065, y, gesture, fontsize=10.5, color=WHITE,
            transform=ax.transAxes, fontfamily='monospace')
    ax.text(0.30, y, result, fontsize=10.5, color=GREEN,
            transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# LEFT HAND — MODIFIER
# ═══════════════════════════════════════════════
card(ax, 0.52, 0.68, 0.44, 0.25)
ax.text(0.54, 0.92, '🤚  LEFT HAND', fontsize=16, color=AMBER,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.text(0.54, 0.906, 'your right hand in real life (mirrored camera)',
        fontsize=9.5, color=GRAY, transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.900, xmin=0.525, xmax=0.945, color=DGRAY, linewidth=0.8)

gestures_l = [
    ('✊  Fist (0)',         '→  Diatonic triad (no extension)'),
    ('👍  Thumb out',        '→  Flip quality  (I↔i, IV↔iv…)'),
    ('☝️  1 finger',         '→  Add 7th'),
    ('✌️  2 fingers',        '→  Add 9th  (7th+9th)'),
    ('🤟  3 fingers',        '→  Add 11th (7th+9th+11th)'),
    ('🖖  4 fingers',        '→  Add 13th (7th+9th+11th+13th)'),
    ('📐  Wrist height',     '→  Velocity  (high = loud)'),
]

for i, (gesture, result) in enumerate(gestures_l):
    y = 0.888 - i * 0.026
    ax.text(0.545, y, gesture, fontsize=10.5, color=WHITE,
            transform=ax.transAxes, fontfamily='monospace')
    ax.text(0.745, y, result, fontsize=10.5, color=AMBER,
            transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# EXTENSIONS CHEAT SHEET
# ═══════════════════════════════════════════════
card(ax, 0.04, 0.52, 0.44, 0.145)
ax.text(0.06, 0.655, '🎵  EXTENSIONS  (in C major)', fontsize=14, color=CYAN,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.648, xmin=0.055, xmax=0.465, color=DGRAY, linewidth=0.8)

ext_rows = [
    ('Degree', 'Triad', '7th', '9th', '11th'),
    ('I  (C)',  'C',    'Cmaj7', 'Cmaj9', 'Cmaj11'),
    ('ii (D)',  'Dm',   'Dm7',   'Dm9',   'Dm11'),
    ('IV (F)',  'F',    'Fmaj7', 'Fmaj9', 'Fmaj11'),
    ('V  (G)',  'G',    'G7',    'G9',    'G11'),
    ('vi (A)',  'Am',   'Am7',   'Am9',   'Am11'),
]

col_xs = [0.065, 0.16, 0.245, 0.335, 0.415]
for ri, row in enumerate(ext_rows):
    y = 0.638 - ri * 0.022
    for ci, cell in enumerate(row):
        color = CYAN if ri == 0 else (WHITE if ci == 0 else CYAN)
        sz = 9.5 if ri > 0 else 9
        w = 'bold' if ri == 0 else 'normal'
        ax.text(col_xs[ci], y, cell, fontsize=sz, color=color if ri > 0 else GRAY,
                fontweight=w, transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# KEYBOARD SHORTCUTS
# ═══════════════════════════════════════════════
card(ax, 0.52, 0.52, 0.44, 0.145)
ax.text(0.54, 0.655, '⌨️  KEYBOARD', fontsize=14, color=PURPLE,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.648, xmin=0.525, xmax=0.945, color=DGRAY, linewidth=0.8)

# Piano key diagram (top row: sharps, bottom row: naturals)
piano_naturals = list('ASDFGHJ')
piano_notes    = ['C','D','E','F','G','A','B']
piano_sharps   = {'W':'C#','E':'D#','T':'F#','Y':'G#','U':'A#'}

kw = 0.042
ky_nat = 0.618
ky_sharp = 0.634

for i, (k, n) in enumerate(zip(piano_naturals, piano_notes)):
    kx = 0.545 + i * kw
    box = FancyBboxPatch((kx, ky_nat - 0.020), kw - 0.003, 0.026,
        boxstyle="round,pad=0,rounding_size=0.003",
        facecolor='#e8e8e8', edgecolor=BORDER, linewidth=0.8,
        transform=ax.transAxes)
    ax.add_patch(box)
    ax.text(kx + kw/2 - 0.002, ky_nat - 0.008, k,
            fontsize=8, color='#222', ha='center', fontweight='bold',
            transform=ax.transAxes, fontfamily='monospace')
    ax.text(kx + kw/2 - 0.002, ky_nat - 0.017, n,
            fontsize=7, color='#555', ha='center',
            transform=ax.transAxes, fontfamily='monospace')

sharp_positions = {'W': 0.5, 'E': 1, 'T': 3, 'Y': 4, 'U': 5}
for k, pos in sharp_positions.items():
    kx = 0.545 + pos * kw + kw * 0.6
    box = FancyBboxPatch((kx, ky_nat - 0.012), kw * 0.7, 0.030,
        boxstyle="round,pad=0,rounding_size=0.002",
        facecolor='#1a1a2e', edgecolor='#555', linewidth=0.8,
        transform=ax.transAxes)
    ax.add_patch(box)
    note = piano_sharps[k]
    ax.text(kx + kw * 0.35, ky_nat + 0.012, k,
            fontsize=7, color=WHITE, ha='center',
            transform=ax.transAxes, fontfamily='monospace')

kb_shortcuts = [
    ('Z / X',  'Octave  −  /  +'),
    ('M',      'Toggle major / minor'),
    ('L',      'Latency slider'),
    ('V',      'Voicing panel'),
    ('H',      'Help overlay'),
]
for i, (k, desc) in enumerate(kb_shortcuts):
    y = 0.604 - i * 0.022
    ax.text(0.545, y, k, fontsize=10, color=PURPLE, fontweight='bold',
            transform=ax.transAxes, fontfamily='monospace')
    ax.text(0.595, y, desc, fontsize=10, color=WHITE,
            transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# SAUCE MODE
# ═══════════════════════════════════════════════
card(ax, 0.04, 0.38, 0.44, 0.13)
ax.text(0.06, 0.500, '😛  SAUCE MODE', fontsize=14, color=SAUCE,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.text(0.06, 0.486, 'Open your mouth to toggle saucy jazz voicings',
        fontsize=9.5, color=GRAY, transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.480, xmin=0.055, xmax=0.465, color=DGRAY, linewidth=0.8)

sauce_voicings = [
    ('I',   'maj9'),  ('ii',  'm9'),   ('iii', 'm9'),
    ('IV',  'maj7#11'),('V',  'dom9'), ('vi',  'm9'),
    ('vii°','m7b5(9)'),
]
sx0 = 0.060
for i, (deg, voicing) in enumerate(sauce_voicings):
    x = sx0 + i * 0.058
    box = FancyBboxPatch((x - 0.002, 0.445), 0.053, 0.030,
        boxstyle="round,pad=0,rounding_size=0.005",
        facecolor='#003344', edgecolor='#005566', linewidth=0.8,
        transform=ax.transAxes)
    ax.add_patch(box)
    ax.text(x + 0.0245, 0.466, deg, fontsize=9.5, color=SAUCE,
            ha='center', fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
    ax.text(x + 0.0245, 0.454, voicing, fontsize=8.5, color=WHITE,
            ha='center', transform=ax.transAxes, fontfamily='monospace')

ax.text(0.06, 0.432, '♻️  Toggle: open mouth once = ON, again = OFF  |  1 sec cooldown',
        fontsize=9, color=GRAY, transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# VOICING PANEL
# ═══════════════════════════════════════════════
card(ax, 0.52, 0.38, 0.44, 0.13)
ax.text(0.54, 0.500, '🎛️  VOICING PANEL  (press V)', fontsize=14, color=PURPLE,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.480, xmin=0.525, xmax=0.945, color=DGRAY, linewidth=0.8)

voicing_keys = [
    ('← →',   'Select degree (I – VII)'),
    ('I / U',  'Invert chord up / down'),
    ('N',      'Cycle to next note in chord'),
    ('↑ ↓',   'Nudge selected note ±1 semitone'),
    ('R',      'Reset degree to default'),
]
for i, (k, desc) in enumerate(voicing_keys):
    y = 0.470 - i * 0.020
    ax.text(0.545, y, k, fontsize=9.5, color=PURPLE, fontweight='bold',
            transform=ax.transAxes, fontfamily='monospace')
    ax.text(0.600, y, desc, fontsize=9.5, color=WHITE,
            transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# LATENCY / SENSITIVITY
# ═══════════════════════════════════════════════
card(ax, 0.04, 0.255, 0.92, 0.115)
ax.text(0.06, 0.362, '⚡  LATENCY SLIDER  (press L)', fontsize=14, color=AMBER,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.355, xmin=0.055, xmax=0.945, color=DGRAY, linewidth=0.8)

# Slider visualization
slider_x0, slider_x1 = 0.08, 0.92
slider_y = 0.318
ax.plot([slider_x0, slider_x1], [slider_y, slider_y], color=DGRAY, linewidth=3,
        transform=ax.transAxes)

# Zones
zones = [
    (0.08, 0.20, RED,    'YOLO\n50ms'),
    (0.20, 0.40, AMBER,  'SPICY\n120ms'),
    (0.40, 0.65, GREEN,  'DEFAULT\n180ms'),
    (0.65, 0.85, CYAN,   'SAFE\n280ms'),
    (0.85, 0.92, PURPLE, 'FORT KNOX\n400ms'),
]

for x0, x1, color, label_text in zones:
    mid = (x0 + x1) / 2
    w = x1 - x0
    box = FancyBboxPatch((x0, slider_y - 0.012), w, 0.024,
        boxstyle="round,pad=0,rounding_size=0.004",
        facecolor=color + '33', edgecolor=color + '88', linewidth=1.0,
        transform=ax.transAxes)
    ax.add_patch(box)
    for j, line in enumerate(label_text.split('\n')):
        ax.text(mid, slider_y + 0.022 - j * 0.016, line,
                fontsize=8.5, color=color, ha='center',
                transform=ax.transAxes, fontfamily='monospace')

# Default marker
def_x = 0.40 + (0.65 - 0.40) * 0.33
ax.plot(def_x, slider_y, 'o', color=GREEN, markersize=10,
        transform=ax.transAxes, zorder=5)
ax.text(def_x, slider_y - 0.028, '← current default',
        fontsize=8, color=GREEN, ha='center',
        transform=ax.transAxes, fontfamily='monospace')

ax.text(0.50, 0.268,
        'Higher latency = more stable but slower response.  '
        'Lower latency = instant but may retrigger.  '
        'Press L in-app, then ← → to adjust.',
        fontsize=9.5, color=GRAY, ha='center',
        transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# SETUP NOTES
# ═══════════════════════════════════════════════
card(ax, 0.04, 0.12, 0.92, 0.125)
ax.text(0.06, 0.236, '🔧  SETUP', fontsize=14, color=WHITE,
        fontweight='bold', transform=ax.transAxes, fontfamily='monospace')
ax.axhline(y=0.229, xmin=0.055, xmax=0.945, color=DGRAY, linewidth=0.8)

setup_items = [
    ('1.', 'Enable IAC Driver:  Audio MIDI Setup → Window → Show MIDI Studio → IAC Driver → "Device is online"'),
    ('2.', 'In Ableton:  Preferences → Link/Tempo/MIDI → find "MIDI Camera" → enable Track input'),
    ('3.', 'Arm a MIDI track in Ableton and set its MIDI input to "MIDI Camera"'),
    ('4.', 'Camera index 0 = iPhone Continuity Camera on Mac.  Use index 1 or 2 for built-in webcam.'),
    ('5.', 'Hold right hand clearly in frame, fingers pointing up. Good lighting = better tracking.'),
]

for i, (num, text) in enumerate(setup_items):
    y = 0.218 - i * 0.022
    ax.text(0.065, y, num, fontsize=9.5, color=CYAN, fontweight='bold',
            transform=ax.transAxes, fontfamily='monospace')
    ax.text(0.090, y, text, fontsize=9.5, color=WHITE,
            transform=ax.transAxes, fontfamily='monospace')

# ═══════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════
ax.text(0.5, 0.065, 'github.com/das/midi-camera  •  inspired by Imogen Heap\'s Mi.Mu gloves',
        fontsize=10, color=GRAY, ha='center', transform=ax.transAxes,
        fontfamily='monospace')
ax.text(0.5, 0.048, 'built with MediaPipe  •  python-rtmidi  •  OpenCV',
        fontsize=9, color=DGRAY, ha='center', transform=ax.transAxes,
        fontfamily='monospace')

plt.tight_layout(pad=0)
plt.savefig('infographic.png', dpi=150, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
print("[*] Saved: infographic.png")
