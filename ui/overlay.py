"""
OpenCV overlay drawing for the camera view.
"""

import cv2
import numpy as np


def draw_semi_transparent_rect(frame, x, y, w, h, color=(0, 0, 0), alpha=0.7):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def draw_chord_card(frame, chord_info: dict, key_display: str, mode_display: str,
                    velocity: int, left_gesture: str = ""):
    """Bottom-left chord info card."""
    fh, fw = frame.shape[:2]

    card_w = 390
    card_h = 215
    card_x = 15
    card_y = fh - card_h - 15
    pad = 18

    draw_semi_transparent_rect(frame, card_x, card_y, card_w, card_h, (15, 15, 15), 0.82)
    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h), (90, 90, 90), 1)

    tx = card_x + pad
    ty = card_y + pad + 8

    if chord_info and chord_info.get('degree'):
        roman = chord_info.get('roman', '')
        name  = chord_info.get('name', '')

        # Roman numeral — large green
        cv2.putText(frame, roman, (tx, ty + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (70, 255, 130), 2)
        roman_w = cv2.getTextSize(roman, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)[0][0]

        # Chord name — white, medium
        cv2.putText(frame, name, (tx + roman_w + 14, ty + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)

        # Note names
        notes_str = '  '.join(chord_info.get('note_names', []))
        cv2.putText(frame, notes_str, (tx, ty + 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 200, 255), 1)
    else:
        cv2.putText(frame, "---", (tx, ty + 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (90, 90, 90), 2)

    # Key / mode
    cv2.putText(frame, f"{key_display} {mode_display}", (tx, ty + 112),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (210, 210, 210), 1)

    # Modifier gesture label
    if left_gesture:
        cv2.putText(frame, left_gesture, (tx + 210, ty + 112),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (160, 160, 160), 1)

    # Velocity bar
    bar_y = ty + 138
    bar_w = card_w - pad * 2
    bar_h = 14

    cv2.putText(frame, f"vel {velocity}", (tx, bar_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (150, 150, 150), 1)
    bar_y += 10
    cv2.rectangle(frame, (tx, bar_y), (tx + bar_w, bar_y + bar_h), (50, 50, 50), -1)
    fill = int((velocity / 127) * bar_w)
    g = min(255, velocity * 2)
    r = max(0, 255 - velocity * 2)
    cv2.rectangle(frame, (tx, bar_y), (tx + fill, bar_y + bar_h), (0, g, r), -1)


def draw_status(frame, midi_connected: bool):
    """MIDI status — top right."""
    fh, fw = frame.shape[:2]
    label = "MIDI: Connected" if midi_connected else "MIDI: Off"
    color = (70, 255, 110) if midi_connected else (80, 80, 255)
    sz = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)[0]
    tx = fw - sz[0] - 18
    ty = 36
    draw_semi_transparent_rect(frame, tx - 10, ty - 24, sz[0] + 20, 34, (15, 15, 15), 0.65)
    cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 1)


def draw_controls_hint(frame):
    """Compact shortcut bar — top left, always visible."""
    fh, fw = frame.shape[:2]

    lines = [
        "A-J : key (piano)    Z/X : oct-/oct+    M : maj/min",
        "V : voicings    L : latency    H : help    Q : quit",
    ]

    bar_h = 52
    bar_w = 520
    draw_semi_transparent_rect(frame, 10, 10, bar_w, bar_h, (15, 15, 15), 0.72)
    cv2.rectangle(frame, (10, 10), (10 + bar_w, 10 + bar_h), (70, 70, 70), 1)

    for i, line in enumerate(lines):
        cv2.putText(frame, line, (20, 32 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (190, 190, 190), 1)


def draw_latency_slider(frame, current: float, lo: float, hi: float):
    """Latency/debounce slider — press L, then ← → to adjust, R to reset."""
    fh, fw = frame.shape[:2]

    bar_w = 500
    bar_h = 90
    bx = (fw - bar_w) // 2
    by = fh - bar_h - 20

    draw_semi_transparent_rect(frame, bx, by, bar_w, bar_h, (12, 12, 18), 0.88)
    cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (100, 100, 100), 1)

    cv2.putText(frame, "LATENCY  (← → adjust  |  R reset)",
                (bx + 14, by + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    # Zones
    zones = [
        (lo,  0.08, (255, 60,  60),  "YOLO"),
        (0.08, 0.15, (255, 170, 30), "SPICY"),
        (0.15, 0.22, (60,  255, 120),"DEFAULT"),
        (0.22, 0.32, (60,  200, 255),"SAFE"),
        (0.32, hi,   (160, 80,  255),"FORT KNOX"),
    ]

    track_x = bx + 14
    track_w = bar_w - 28
    track_y = by + 48
    track_h = 16

    cv2.rectangle(frame, (track_x, track_y), (track_x + track_w, track_y + track_h),
                  (40, 40, 40), -1)

    for z_lo, z_hi, color, name in zones:
        z0 = track_x + int((z_lo - lo) / (hi - lo) * track_w)
        z1 = track_x + int((z_hi - lo) / (hi - lo) * track_w)
        cv2.rectangle(frame, (z0, track_y), (z1, track_y + track_h),
                      tuple(int(c * 0.35) for c in color), -1)

    # Fill up to current
    fill_x = track_x + int((current - lo) / (hi - lo) * track_w)
    # Find zone color for current
    cur_color = (60, 255, 120)
    for z_lo, z_hi, color, _ in zones:
        if z_lo <= current <= z_hi:
            cur_color = color; break
    cv2.rectangle(frame, (track_x, track_y), (fill_x, track_y + track_h), cur_color, -1)

    # Thumb
    cv2.circle(frame, (fill_x, track_y + track_h // 2), 10, cur_color, -1)
    cv2.circle(frame, (fill_x, track_y + track_h // 2), 10, (255, 255, 255), 1)

    # Labels
    ms = int(current * 1000)
    label = f"{ms}ms"
    for z_lo, z_hi, color, name in zones:
        if z_lo <= current <= z_hi:
            label = f"{ms}ms  —  {name}"; break

    cv2.putText(frame, label, (bx + 14, by + 82),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, cur_color, 1)


def draw_sauce_banner(frame):
    """Sauce mode banner — top center."""
    fh, fw = frame.shape[:2]
    text = "~ SAUCE MODE ~"
    sz = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
    tx = (fw - sz[0]) // 2
    ty = 58
    draw_semi_transparent_rect(frame, tx - 14, ty - 42, sz[0] + 28, 54, (0, 70, 90), 0.80)
    cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 220, 255), 2)


def draw_help_overlay(frame):
    """Full help screen — press H to toggle."""
    fh, fw = frame.shape[:2]

    # Dark overlay over whole frame
    draw_semi_transparent_rect(frame, 0, 0, fw, fh, (10, 10, 10), 0.85)

    title = "MIDI CAMERA — CONTROLS"
    sz = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
    cv2.putText(frame, title, ((fw - sz[0]) // 2, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    sections = [
        ("RIGHT HAND (degree)", [
            "Fist            =  Silence",
            "1 finger        =  Chord I",
            "2 fingers       =  Chord II",
            "3 fingers       =  Chord III",
            "4 fingers       =  Chord IV  (thumb tucked)",
            "Open hand       =  Chord V",
            "Thumb only      =  Chord VI",
            "Thumb + pinky   =  Chord VII",
        ]),
        ("LEFT HAND (modifier)", [
            "Fist            =  Triad (no extension)",
            "Thumb out       =  Flip quality  (maj↔min)",
            "1 finger        =  Add 7th",
            "2 fingers       =  Add 9th",
            "3 fingers       =  Add 11th",
            "4 fingers       =  Add 13th",
            "Wrist height    =  Velocity",
        ]),
        ("KEYBOARD", [
            "A S D F G H J   =  C D E F G A B",
            "W E   T Y U     =  C# D#  F# G# A#",
            "Z / X           =  Octave down / up",
            "M               =  Toggle major / minor",
            "← / →           =  Key chromatic shift",
            "V               =  Voicing panel",
            "H               =  This help screen",
            "Q / ESC         =  Quit / Config",
        ]),
        ("SAUCE MODE", [
            "Open mouth      =  Toggle sauce mode (saucy jazz voicings)",
        ]),
    ]

    col_x = [60, fw // 2 + 20]
    row_y = 110
    col = 0

    for section_title, items in sections:
        x = col_x[col]
        y = row_y

        cv2.putText(frame, section_title, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 220, 255), 1)
        y += 8
        cv2.line(frame, (x, y), (x + 380, y), (80, 80, 80), 1)
        y += 20

        for item in items:
            cv2.putText(frame, item, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1)
            y += 24

        row_y = y + 20 if col == 1 else row_y
        col = 1 - col  # alternate columns

    cv2.putText(frame, "Press H to close", ((fw - 200) // 2, fh - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (130, 130, 130), 1)


def draw_voicing_panel(frame, chord_engine, voicing_editor, sauce_mode: bool):
    """
    Interactive voicing panel.
    ← → : select degree   I/U : invert up/down   ↑ ↓ : nudge note   N : next note   R : reset
    """
    fh, fw = frame.shape[:2]

    panel_w = 760
    panel_h = 420
    px = (fw - panel_w) // 2
    py = (fh - panel_h) // 2

    draw_semi_transparent_rect(frame, px, py, panel_w, panel_h, (12, 12, 18), 0.92)
    cv2.rectangle(frame, (px, py), (px + panel_w, py + panel_h), (100, 100, 100), 1)

    # Title
    mode_label = "(Sauce)" if sauce_mode else "(Normal)"
    cv2.putText(frame, f"VOICINGS  {mode_label}", (px + 20, py + 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.80,
                (0, 220, 255) if sauce_mode else (220, 220, 220), 1)
    cv2.line(frame, (px + 20, py + 44), (px + panel_w - 20, py + 44), (70, 70, 70), 1)

    roman_labels = ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°']
    col_w = (panel_w - 40) // 7
    sel_deg = voicing_editor.selected_degree
    sel_note = voicing_editor.selected_note

    for deg in range(1, 8):
        cx = px + 20 + (deg - 1) * col_w
        is_sel = (deg == sel_deg)

        # Highlight selected column
        if is_sel:
            draw_semi_transparent_rect(frame, cx - 4, py + 50, col_w - 4, panel_h - 80,
                                       (40, 60, 100), 0.50)

        # Roman numeral header
        hdr_color = (100, 220, 255) if is_sel else (160, 160, 220)
        cv2.putText(frame, roman_labels[deg - 1], (cx + 4, py + 76),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, hdr_color, 1 + int(is_sel))

        # Inversion badge
        inv = voicing_editor.inversions.get(deg, 0)
        inv_labels = ['root', '1st', '2nd', '3rd']
        cv2.putText(frame, inv_labels[inv % 4], (cx + 2, py + 98),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (180, 180, 100), 1)

        # Build chord and apply voicing
        try:
            if sauce_mode:
                raw = chord_engine.build_sauce_chord(deg)
            else:
                raw = chord_engine.build_chord(degree=deg)
            voiced = voicing_editor.apply(raw['notes'], deg)

            # Chord name
            cv2.putText(frame, raw['name'].replace('~', ''), (cx + 2, py + 122),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)

            # Notes stacked
            from core.chord_engine import midi_to_note_name
            for ni, note in enumerate(voiced):
                nn = midi_to_note_name(note)
                is_sel_note = is_sel and ni == sel_note
                note_color = (80, 255, 160) if is_sel_note else (150, 195, 255)
                weight = 2 if is_sel_note else 1
                # Show offset if modified
                offsets = voicing_editor.note_offsets.get(deg, {})
                if ni in offsets and offsets[ni] != 0:
                    nn += f"{'+' if offsets[ni]>0 else ''}{offsets[ni]}"
                cv2.putText(frame, nn, (cx + 2, py + 148 + ni * 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.44, note_color, weight)
        except Exception:
            pass

    # Controls hint at bottom
    hints = [
        "← → : degree    I : invert ↑    U : invert ↓    N : next note",
        "↑ ↓ : nudge note ±1 semitone    R : reset degree    V/ESC : close",
    ]
    for i, h in enumerate(hints):
        cv2.putText(frame, h, (px + 20, py + panel_h - 36 + i * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (130, 130, 130), 1)
