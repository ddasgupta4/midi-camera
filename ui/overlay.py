"""
OpenCV overlay drawing for the camera view.

Renders chord info card, velocity bar, MIDI status,
and hand landmarks on the camera frame.
"""

import cv2
import numpy as np
from typing import Optional


def draw_semi_transparent_rect(frame, x, y, w, h, color=(0, 0, 0), alpha=0.7):
    """Draw a semi-transparent rectangle on the frame."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_chord_card(frame, chord_info: dict, key_display: str, mode_display: str,
                    velocity: int, left_gesture: str = ""):
    """
    Draw the bottom-left chord info card.

    Shows: chord roman numeral, chord name, MIDI notes, key/mode, velocity bar.
    """
    h, w = frame.shape[:2]

    card_w = 320
    card_h = 180
    card_x = 15
    card_y = h - card_h - 15
    padding = 15

    # Semi-transparent dark background
    draw_semi_transparent_rect(frame, card_x, card_y, card_w, card_h, (20, 20, 20), 0.75)

    # Border
    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h),
                  (80, 80, 80), 1)

    text_x = card_x + padding
    y_cursor = card_y + 30

    if chord_info and chord_info.get('degree'):
        # Roman numeral — big
        roman = chord_info.get('roman', '')
        cv2.putText(frame, roman, (text_x, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 255, 150), 2)

        # Chord name next to it
        name = chord_info.get('name', '')
        roman_width = cv2.getTextSize(roman, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0][0]
        cv2.putText(frame, name, (text_x + roman_width + 12, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        # MIDI note names
        y_cursor += 30
        note_names = chord_info.get('note_names', [])
        notes_str = '  '.join(note_names)
        cv2.putText(frame, notes_str, (text_x, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 200, 255), 1)
    else:
        # No chord
        cv2.putText(frame, "---", (text_x, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 100, 100), 2)
        y_cursor += 30

    # Key + Mode
    y_cursor += 30
    key_mode = f"{key_display} {mode_display}"
    cv2.putText(frame, key_mode, (text_x, y_cursor),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

    # Left hand gesture label
    if left_gesture:
        cv2.putText(frame, f"L: {left_gesture}", (text_x + 160, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (140, 140, 140), 1)

    # Velocity bar
    y_cursor += 25
    bar_x = text_x
    bar_w = card_w - padding * 2
    bar_h = 12
    vel_label = f"vel {velocity}"
    cv2.putText(frame, vel_label, (bar_x, y_cursor),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (140, 140, 140), 1)

    y_cursor += 8
    # Bar background
    cv2.rectangle(frame, (bar_x, y_cursor), (bar_x + bar_w, y_cursor + bar_h),
                  (50, 50, 50), -1)
    # Bar fill
    fill_w = int((velocity / 127) * bar_w)
    # Color gradient: low=blue, high=green
    r = max(0, 255 - velocity * 2)
    g = min(255, velocity * 2)
    cv2.rectangle(frame, (bar_x, y_cursor), (bar_x + fill_w, y_cursor + bar_h),
                  (0, g, r), -1)


def draw_status(frame, midi_connected: bool):
    """Draw MIDI connection status in the top-right corner."""
    h, w = frame.shape[:2]

    if midi_connected:
        label = "MIDI: Connected"
        color = (100, 255, 100)
    else:
        label = "MIDI: Disconnected"
        color = (80, 80, 255)

    text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    text_x = w - text_size[0] - 15
    text_y = 30

    # Small dark background
    draw_semi_transparent_rect(frame, text_x - 8, text_y - 18,
                               text_size[0] + 16, 26, (20, 20, 20), 0.6)
    cv2.putText(frame, label, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def draw_controls_hint(frame):
    """Draw keyboard controls hint at bottom-right."""
    h, w = frame.shape[:2]
    hints = "Q: quit  |  ESC: config"
    cv2.putText(frame, hints, (w - 260, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
