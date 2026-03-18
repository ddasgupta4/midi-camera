"""
OpenCV-based config screen — no tkinter, no framework conflicts.

Arrow keys navigate, Enter starts. Clean dark UI drawn with cv2.
"""

import cv2
import numpy as np
from typing import Optional


KEY_OPTIONS = [
    'C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F',
    'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B'
]

KEY_MAP = {
    'C': 'C', 'C#/Db': 'C#', 'D': 'D', 'D#/Eb': 'D#', 'E': 'E',
    'F': 'F', 'F#/Gb': 'F#', 'G': 'G', 'G#/Ab': 'G#', 'A': 'A',
    'A#/Bb': 'A#', 'B': 'B'
}

MODE_OPTIONS = ['Major', 'Minor']
CHANNEL_OPTIONS = [str(i) for i in range(1, 17)]
OCTAVE_OPTIONS = [str(i) for i in range(1, 7)]
CAMERA_OPTIONS = ['0', '1', '2', '3']

FIELDS = [
    ('Key', KEY_OPTIONS, 0),
    ('Mode', MODE_OPTIONS, 0),
    ('MIDI Channel', CHANNEL_OPTIONS, 0),
    ('Octave', OCTAVE_OPTIONS, 2),    # default octave 3 (index 2)
    ('Camera', CAMERA_OPTIONS, 0),
]

# Colors
BG = (26, 26, 26)
FG = (224, 224, 224)
ACCENT = (138, 255, 138)
DIM = (120, 120, 120)
HIGHLIGHT_BG = (50, 50, 50)
SELECTED_BG = (60, 80, 60)


def draw_config(frame, fields, indices, active_row):
    """Draw the config screen onto frame."""
    h, w = frame.shape[:2]
    frame[:] = BG

    # Title
    cv2.putText(frame, "MIDI Camera", (w // 2 - 120, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, ACCENT, 2)
    cv2.putText(frame, "Hand Gesture MIDI Controller", (w // 2 - 165, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, DIM, 1)

    # Fields
    y_start = 130
    row_h = 50

    for i, (label, options, _default) in enumerate(fields):
        y = y_start + i * row_h
        is_active = (i == active_row)

        # Row background
        if is_active:
            cv2.rectangle(frame, (30, y - 5), (w - 30, y + 35), SELECTED_BG, -1)
        else:
            cv2.rectangle(frame, (30, y - 5), (w - 30, y + 35), HIGHLIGHT_BG, -1)

        # Label
        color = ACCENT if is_active else FG
        cv2.putText(frame, label, (50, y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        # Value with arrows
        val = options[indices[i]]
        val_x = w - 200

        if is_active:
            # Draw left/right arrows
            cv2.putText(frame, "<", (val_x - 25, y + 23),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, ACCENT, 2)
            cv2.putText(frame, val, (val_x, y + 23),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, ACCENT, 2)
            val_w = cv2.getTextSize(val, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)[0][0]
            cv2.putText(frame, ">", (val_x + val_w + 12, y + 23),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, ACCENT, 2)
        else:
            cv2.putText(frame, val, (val_x, y + 23),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, FG, 1)

    # Start button area
    btn_y = y_start + len(fields) * row_h + 25
    btn_w = 160
    btn_x = w // 2 - btn_w // 2
    cv2.rectangle(frame, (btn_x, btn_y), (btn_x + btn_w, btn_y + 45), (50, 120, 50), -1)
    cv2.putText(frame, "ENTER to Start", (btn_x + 10, btn_y + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, FG, 1)

    # Controls hint
    hint_y = h - 20
    cv2.putText(frame, "Up/Down: select field   Left/Right: change value   Enter: start   Q: quit",
                (30, hint_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, DIM, 1)


def show_config_screen() -> Optional[dict]:
    """
    Show OpenCV config screen. Returns config dict or None if cancelled.
    """
    W, H = 480, 420
    frame = np.zeros((H, W, 3), dtype=np.uint8)

    indices = [f[2] for f in FIELDS]  # default indices
    active_row = 0

    cv2.namedWindow("MIDI Camera", cv2.WINDOW_AUTOSIZE)

    while True:
        draw_config(frame, FIELDS, indices, active_row)
        cv2.imshow("MIDI Camera", frame)

        key = cv2.waitKey(30) & 0xFF

        if key == ord('q'):
            cv2.destroyAllWindows()
            return None

        elif key == 13 or key == 10:  # Enter
            cv2.destroyAllWindows()
            cv2.waitKey(1)  # flush

            key_val = KEY_OPTIONS[indices[0]]
            return {
                'key': KEY_MAP.get(key_val, 'C'),
                'mode': MODE_OPTIONS[indices[1]].lower(),
                'channel': int(CHANNEL_OPTIONS[indices[2]]) - 1,
                'octave': int(OCTAVE_OPTIONS[indices[3]]),
                'camera': int(CAMERA_OPTIONS[indices[4]]),
            }

        # Arrow keys (macOS OpenCV uses these codes)
        elif key == 0:  # Up
            active_row = (active_row - 1) % len(FIELDS)
        elif key == 1:  # Down
            active_row = (active_row + 1) % len(FIELDS)
        elif key == 2:  # Left
            n = len(FIELDS[active_row][1])
            indices[active_row] = (indices[active_row] - 1) % n
        elif key == 3:  # Right
            n = len(FIELDS[active_row][1])
            indices[active_row] = (indices[active_row] + 1) % n

        # Also support W/S for up/down and A/D for left/right
        elif key == ord('w'):
            active_row = (active_row - 1) % len(FIELDS)
        elif key == ord('s'):
            active_row = (active_row + 1) % len(FIELDS)
        elif key == ord('a'):
            n = len(FIELDS[active_row][1])
            indices[active_row] = (indices[active_row] - 1) % n
        elif key == ord('d'):
            n = len(FIELDS[active_row][1])
            indices[active_row] = (indices[active_row] + 1) % n
