"""
OpenCV overlay drawing for the camera view.
"""

import cv2
import numpy as np


def draw_semi_transparent_rect(frame, x, y, w, h, color=(0, 0, 0), alpha=0.7):
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(fw, x + w), min(fh, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2].copy()
    cv2.rectangle(roi, (0, 0), (x2 - x1, y2 - y1), color, -1)
    cv2.addWeighted(roi, alpha, frame[y1:y2, x1:x2], 1 - alpha, 0, frame[y1:y2, x1:x2])


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


def draw_status(frame, midi_connected: bool, smart_extensions: bool = True,
                mode_name: str = '', mode_index: int = 0, mode_count: int = 1):
    """MIDI status — top right."""
    fh, fw = frame.shape[:2]
    label = "MIDI: Connected" if midi_connected else "MIDI: Off"
    color = (70, 255, 110) if midi_connected else (80, 80, 255)
    sz = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)[0]
    tx = fw - sz[0] - 18
    ty = 36
    draw_semi_transparent_rect(frame, tx - 10, ty - 24, sz[0] + 20, 34, (15, 15, 15), 0.65)
    cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 1)

    # Mode badge — show name and index
    mode_label = f"{mode_index + 1}/{mode_count} {mode_name.upper()}"
    # Cycle colors for modes
    mode_colors = [
        (180, 130, 255),  # purple
        (100, 220, 255),  # cyan
        (255, 200, 80),   # gold
        (130, 255, 130),  # green
        (255, 130, 160),  # pink
    ]
    mode_color = mode_colors[mode_index % len(mode_colors)]
    msz = cv2.getTextSize(mode_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    mx = fw - msz[0] - 18
    my = ty + 22
    cv2.putText(frame, mode_label, (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1)

    # Smart extensions indicator (only shown when relevant)
    if smart_extensions is not None:
        ext_label = "EXT: smart" if smart_extensions else "EXT: retrigger"
        ext_color = (180, 220, 255) if smart_extensions else (140, 140, 140)
        esz = cv2.getTextSize(ext_label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
        ex = fw - esz[0] - 18
        ey = my + 20
        cv2.putText(frame, ext_label, (ex, ey), cv2.FONT_HERSHEY_SIMPLEX, 0.45, ext_color, 1)


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


def draw_debug_gestures(frame, right_gesture, left_gesture, desired_notes, playing_notes, settle_progress: float, thumb_signal: float = 0.0):
    """Debug overlay showing raw gesture state — press ` to toggle."""
    fh, fw = frame.shape[:2]

    lines = []
    if right_gesture:
        lines.append(f"R: degree={right_gesture.degree}  fingers={right_gesture.finger_count}")
    else:
        lines.append("R: no hand")
    
    if left_gesture:
        lines.append(f"L: flip={left_gesture.flip_quality}  7={left_gesture.add_7th}  "
                     f"9={left_gesture.add_9th}  11={left_gesture.add_11th}  13={left_gesture.add_13th}  sus4={left_gesture.add_sus4}")
    else:
        lines.append("L: (via mode)")
    lines.append(f"L thumb signal: {thumb_signal:.3f}")
    lines.append(f"Desired: {desired_notes}")
    lines.append(f"Playing: {playing_notes}")
    
    # Settle progress bar
    bar_pct = min(1.0, settle_progress)
    bar_color = (80, 255, 130) if bar_pct >= 1.0 else (80, 180, 255)
    lines.append(f"Settle: {'#' * int(bar_pct * 20)}{'.' * (20 - int(bar_pct * 20))} {bar_pct*100:.0f}%")

    box_h = 20 + len(lines) * 20
    box_w = 460
    bx, by = 10, fh - box_h - 10

    draw_semi_transparent_rect(frame, bx, by, box_w, box_h, (0, 0, 0), 0.85)
    for i, line in enumerate(lines):
        color = (180, 255, 180) if i < 2 else (200, 200, 200)
        cv2.putText(frame, line, (bx + 10, by + 18 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)


def draw_perf_hud(frame, tier_name: str, display_fps: float,
                  hands_fps: float, face_fps: float):
    """Performance HUD — shown when L panel is open, above the latency slider."""
    fh, fw = frame.shape[:2]

    hud_w = 500
    hud_h = 58
    hx = (fw - hud_w) // 2
    hy = fh - 90 - 20 - hud_h - 8  # above the latency slider

    draw_semi_transparent_rect(frame, hx, hy, hud_w, hud_h, (12, 12, 18), 0.85)
    cv2.rectangle(frame, (hx, hy), (hx + hud_w, hy + hud_h), (80, 80, 80), 1)

    # Tier badge
    tier_colors = {"HIGH": (70, 255, 130), "MEDIUM": (255, 200, 60), "LOW": (80, 80, 255)}
    tier_color = tier_colors.get(tier_name, (180, 180, 180))
    cv2.putText(frame, f"TIER: {tier_name}", (hx + 14, hy + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, tier_color, 1)

    # FPS readouts
    fps_str = (f"Display: {display_fps:.0f}fps  |  "
               f"Hands: {hands_fps:.0f}fps  |  "
               f"Face: {face_fps:.0f}fps")
    cv2.putText(frame, fps_str, (hx + 14, hy + 46),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)


def draw_latency_slider(frame, current: float, lo: float, hi: float):
    """Latency/debounce slider — press L, then < > to adjust, R to reset."""
    fh, fw = frame.shape[:2]

    bar_w = 500
    bar_h = 90
    bx = (fw - bar_w) // 2
    by = fh - bar_h - 20

    draw_semi_transparent_rect(frame, bx, by, bar_w, bar_h, (12, 12, 18), 0.88)
    cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (100, 100, 100), 1)

    cv2.putText(frame, "LATENCY  (< > adjust  |  R reset)",
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


def draw_help_overlay(frame, mode_sections=None):
    """Full help screen — press H to toggle. mode_sections from current mode."""
    fh, fw = frame.shape[:2]

    # Dark overlay over whole frame
    draw_semi_transparent_rect(frame, 0, 0, fw, fh, (10, 10, 10), 0.85)

    title = "MIDI CAMERA — CONTROLS"
    sz = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
    cv2.putText(frame, title, ((fw - sz[0]) // 2, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    # Mode-specific sections first, then keyboard
    sections = list(mode_sections or [])
    sections.append(("KEYBOARD", [
        "A S D F G H J   =  C D E F G A B",
        "W E   T Y U     =  C# D#  F# G# A#",
        "Z / X           =  Octave down / up",
        "M               =  Toggle major / minor",
        "< / >           =  Key chromatic shift",
        "V               =  Voicing panel",
        "P               =  Bass/pedal panel",
        "L               =  Latency slider",
        "/               =  Cycle mode   1-9 = select",
        "H               =  This help screen",
        "Q / ESC         =  Quit / Config",
    ]))

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

    cv2.putText(frame, "Press H to close  |  / = cycle mode", ((fw - 380) // 2, fh - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (130, 130, 130), 1)


def draw_voicing_panel(frame, chord_engine, voicing_editor, sauce_mode: bool):
    """
    Interactive voicing panel.
    < > : select degree   I/U : invert up/down   ^ v : nudge note   N : next note   R : reset
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
        "< > : degree    I : invert+    U : invert-    N : next note",
        "^ v : nudge note ±1 semitone    R : reset degree    V/ESC : close",
    ]
    for i, h in enumerate(hints):
        cv2.putText(frame, h, (px + 20, py + panel_h - 36 + i * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (130, 130, 130), 1)


def draw_cc_card(frame, cc_display: list, key_display: str, mode_display: str, left_gesture: str = ""):
    """Bottom-left card for MIDI Mapper mode — shows CC values with bar graphs."""
    fh, fw = frame.shape[:2]

    card_w = 390
    card_h = 260
    card_x = 15
    card_y = fh - card_h - 15
    pad = 18

    draw_semi_transparent_rect(frame, card_x, card_y, card_w, card_h, (15, 15, 15), 0.82)
    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h), (90, 90, 90), 1)

    tx = card_x + pad
    ty = card_y + pad + 8

    cv2.putText(frame, "MIDI CC MAPPER", (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 220, 255), 1)

    bar_w = card_w - pad * 2 - 80
    bar_h = 12

    for i, cc in enumerate(cc_display):
        y = ty + 30 + i * 30
        label = f"CC{cc['cc']:>2} {cc['name']:<6}"
        cv2.putText(frame, label, (tx, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        # Bar background
        bx = tx + 110
        cv2.rectangle(frame, (bx, y), (bx + bar_w, y + bar_h), (40, 40, 40), -1)

        # Bar fill
        fill = int((cc['value'] / 127) * bar_w)
        g = min(255, cc['value'] * 2)
        r = max(0, 255 - cc['value'] * 2)
        cv2.rectangle(frame, (bx, y), (bx + fill, y + bar_h), (0, g, r), -1)

        # Value text
        cv2.putText(frame, str(cc['value']), (bx + bar_w + 6, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    # Key / mode + left gesture at bottom
    by = ty + 30 + len(cc_display) * 30 + 10
    cv2.putText(frame, f"{key_display} {mode_display}", (tx, by),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)
    if left_gesture:
        cv2.putText(frame, left_gesture, (tx + 160, by),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (130, 130, 130), 1)


def draw_drum_card(frame, result: dict, key_display: str, mode_display: str, left_gesture: str = ""):
    """Bottom-left card for drum modes — shows recent hits and pad/zone state."""
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

    layout = result.get('drum_layout', 'finger')
    hits = result.get('drum_hits', [])

    # Title
    cv2.putText(frame, f"DRUMS ({layout.upper()})", (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 180, 80), 1)

    # Last hits — big text
    hit_str = '  '.join(hits[-4:]) if hits else "---"
    cv2.putText(frame, hit_str, (tx, ty + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 255, 160), 2)

    # Layout-specific display
    if layout == 'finger':
        pads = result.get('drum_pads', [])
        # Show pads as grid
        for i, pad_info in enumerate(pads):
            col = i % 4
            row = i // 4
            px = tx + col * 88
            py = ty + 75 + row * 35
            color = (80, 255, 160) if pad_info['active'] else (70, 70, 70)
            label = f"{pad_info['side']}:{pad_info['name']}"
            cv2.putText(frame, label, (px, py),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1)

    elif layout == 'zone':
        grid = result.get('zone_grid', [])
        active = result.get('active_zones', [])
        for row_idx, row in enumerate(grid):
            for col_idx, name in enumerate(row):
                px = tx + col_idx * 88
                py = ty + 75 + row_idx * 30
                is_active = (row_idx, col_idx) in active
                color = (80, 255, 160) if is_active else (100, 100, 100)
                cv2.putText(frame, name, (px, py),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1 + int(is_active))

    elif layout == 'strike':
        zones = result.get('strike_zones', {})
        y_off = ty + 75
        for hand, zone_list in zones.items():
            label = f"{'R' if hand == 'right' else 'L'} hand:"
            cv2.putText(frame, label, (tx, y_off),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
            for j, z in enumerate(zone_list):
                px = tx + 90 + j * 100
                cv2.putText(frame, f"[{z['side']}] {z['name']}", (px, y_off),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 220, 255), 1)
            y_off += 28

    # Key / mode
    cv2.putText(frame, f"{key_display} {mode_display}", (tx, ty + 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)
    if left_gesture:
        cv2.putText(frame, left_gesture, (tx + 180, ty + 165),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (130, 130, 130), 1)


def draw_theremin_overlay(frame, display: dict):
    """In-scene theremin feedback: right-edge pitch ladder + top vibrato bar.

    display: {'active','y','x','num_notes','vibrato','continuous','deadzone'}
    """
    if not display:
        return
    fh, fw = frame.shape[:2]

    # ── Pitch ladder (right edge) ────────────────────────────────────────
    pad = 14
    lw = 34
    lh = int(fh * 0.70)
    lx = fw - lw - pad
    ly = (fh - lh) // 2

    draw_semi_transparent_rect(frame, lx, ly, lw, lh, (12, 12, 20), 0.72)
    cv2.rectangle(frame, (lx, ly), (lx + lw, ly + lh), (90, 90, 90), 1)

    # Tick marks for each scale note
    num = max(1, int(display.get('num_notes', 14)))
    for i in range(num):
        # 0 = bottom, num-1 = top (matches y=wrist_y inversion in the mode)
        frac = i / (num - 1)
        ty_line = ly + int((1.0 - frac) * lh)
        # Make "root" notes (every 7th starting at 0) brighter
        is_root = (i % 7 == 0)
        color = (130, 220, 255) if is_root else (70, 110, 150)
        tick_w = 18 if is_root else 10
        cv2.line(frame, (lx + 4, ty_line), (lx + 4 + tick_w, ty_line), color, 1 + int(is_root))

    # Cursor = current smoothed wrist Y
    if display.get('active'):
        y = max(0.0, min(1.0, float(display.get('y', 0.5))))
        cy = ly + int((1.0 - y) * lh)
        cv2.circle(frame, (lx + lw // 2, cy), 6, (80, 255, 160), -1)
        cv2.circle(frame, (lx + lw // 2, cy), 7, (15, 15, 15), 1)

    # Mode label (continuous vs stepped)
    mode_label = "SLIDE" if display.get('continuous') else "STEP"
    cv2.putText(frame, mode_label, (lx - 4, ly - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 200, 255), 1)

    # ── Vibrato bar (top center) ─────────────────────────────────────────
    vb_w = 220
    vb_h = 8
    vb_x = (fw - vb_w) // 2
    vb_y = 12

    cv2.rectangle(frame, (vb_x, vb_y), (vb_x + vb_w, vb_y + vb_h), (35, 35, 45), -1)
    cv2.rectangle(frame, (vb_x, vb_y), (vb_x + vb_w, vb_y + vb_h), (90, 90, 90), 1)
    # Center tick
    mid = vb_x + vb_w // 2
    cv2.line(frame, (mid, vb_y - 2), (mid, vb_y + vb_h + 2), (150, 150, 150), 1)

    vibrato = int(display.get('vibrato', 0))
    if vibrato > 0:
        half = vb_w // 2
        # Symmetric fill from center; vibrato is 0..96 in theremin mode
        fill = int(min(1.0, vibrato / 96.0) * half)
        cv2.rectangle(frame, (mid - fill, vb_y), (mid + fill, vb_y + vb_h),
                      (80, 200, 255), -1)
    cv2.putText(frame, "VIBRATO", (vb_x - 80, vb_y + vb_h),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 180, 220), 1)


def draw_guitar_overlay(frame, display: dict, right_landmarks=None):
    """In-scene guitar feedback: pluck flash + cooldown ring around wrist."""
    if not display or right_landmarks is None:
        return
    fh, fw = frame.shape[:2]

    # Wrist is landmark 0. Landmarks are computed from the already-flipped
    # frame, so coordinates are directly in display space.
    try:
        wx_norm, wy_norm = right_landmarks[0][0], right_landmarks[0][1]
    except (IndexError, KeyError, TypeError):
        return
    wx = int(wx_norm * fw)
    wy = int(wy_norm * fh)

    flash_age = float(display.get('pluck_flash_age', 999.0))
    if flash_age < 0.18:
        alpha = max(0.0, 1.0 - flash_age / 0.18)
        r = int(22 + 30 * alpha)
        cv2.circle(frame, (wx, wy), r, (80, 255, 160), 2)
        cv2.circle(frame, (wx, wy), 4, (80, 255, 160), -1)

    # Cooldown ring — 0..1 progress, full = ready
    cooldown = float(display.get('cooldown', 1.0))
    if cooldown < 1.0:
        # Draw an arc; OpenCV uses ellipse() for partial arcs
        angle = int(cooldown * 360)
        cv2.ellipse(frame, (wx, wy), (28, 28), -90, 0, angle,
                    (100, 180, 255), 2)
    else:
        # Ready — faint full ring
        cv2.circle(frame, (wx, wy), 28, (60, 120, 180), 1)

    # Octave badge near wrist
    oct_var = int(display.get('octave_variant', 0))
    cv2.putText(frame, f"O{oct_var}", (wx + 34, wy + 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 220, 255), 1)


def _zone_rect(fw: int, fh: int, row: int, col: int) -> tuple[int, int, int, int]:
    """2×4 zone grid rectangle (x, y, w, h) covering the full frame."""
    w = fw // 4
    h = fh // 2
    return col * w, row * h, w, h


def draw_zone_grid_overlay(frame, zone_names: list, active_zones: list,
                            flash_times: dict, hand_positions: dict, now: float):
    """In-scene 2×4 drum zone grid with flash feedback."""
    fh, fw = frame.shape[:2]
    active_set = set(tuple(z) for z in (active_zones or []))

    for row in range(2):
        for col in range(4):
            x, y, w, h = _zone_rect(fw, fh, row, col)
            name = zone_names[row][col] if row < len(zone_names) and col < len(zone_names[row]) else ""

            # Base cell — very faint translucent panel
            draw_semi_transparent_rect(frame, x + 2, y + 2, w - 4, h - 4,
                                       (20, 25, 35), 0.22)

            border_color = (60, 70, 90)
            thickness = 1

            # Flash on recent hit
            flash_t = flash_times.get((row, col)) if flash_times else None
            if flash_t is not None:
                age = now - flash_t
                if age < 0.18:
                    f_alpha = max(0.0, 1.0 - age / 0.18)
                    # Brighter translucent fill
                    draw_semi_transparent_rect(frame, x + 2, y + 2, w - 4, h - 4,
                                               (60, 220, 140), 0.15 + 0.35 * f_alpha)
                    border_color = (80, 255, 160)
                    thickness = 2

            # Active (hand currently in this cell)
            if (row, col) in active_set:
                border_color = (140, 220, 255)
                thickness = max(thickness, 2)

            cv2.rectangle(frame, (x + 2, y + 2), (x + w - 2, y + h - 2),
                          border_color, thickness)

            # Label
            cv2.putText(frame, name, (x + 12, y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 240), 1)

    # Hand position crosshairs — wrist_x/y come from landmarks computed on
    # the flipped frame, so they're already in display space.
    for side, pos in (hand_positions or {}).items():
        if not pos:
            continue
        hx, hy = pos
        cx = int(hx * fw)
        cy = int(hy * fh)
        color = (80, 255, 160) if side == 'right' else (255, 180, 80)
        cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 18, 2)


def draw_strike_targets_overlay(frame, pads: dict, hand_positions: dict,
                                 flash_times: dict, trails: dict, now: float):
    """In-scene 2×2 strike targets per hand with motion trails + hit flashes."""
    fh, fw = frame.shape[:2]

    # For each hand, draw 4 target cells across the full frame (left/right split).
    # The frame is flipped horizontally at display time, so the user's right
    # hand appears on the LEFT half of the displayed frame.
    for side, pads_map in (pads or {}).items():
        for (row, col), drum_name in pads_map.items():
            # Compute cell in normalized (0..1) space and convert to pixels
            # with horizontal flip (display mirrors x).
            cell_w = fw // 2
            cell_h = fh // 2
            x = col * cell_w
            y = row * cell_h

            border_color = (60, 80, 100)
            thickness = 1

            flash_t = flash_times.get((side[0].upper(), row, col)) if flash_times else None
            if flash_t is not None:
                age = now - flash_t
                if age < 0.18:
                    f_alpha = max(0.0, 1.0 - age / 0.18)
                    color = (80, 200, 255) if side == 'right' else (255, 180, 100)
                    draw_semi_transparent_rect(frame, x + 3, y + 3, cell_w - 6, cell_h - 6,
                                               color, 0.15 + 0.30 * f_alpha)
                    border_color = color
                    thickness = 2

            cv2.rectangle(frame, (x + 3, y + 3), (x + cell_w - 3, y + cell_h - 3),
                          border_color, thickness)
            # Label — color-tagged per hand
            label_color = (200, 220, 255) if side == 'right' else (255, 210, 160)
            cv2.putText(frame, f"{side[0].upper()}:{drum_name}", (x + 14, y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_color, 1)

    # Motion trails (last ~200 ms, fading). Positions are already in
    # display coordinates (landmarks computed on the flipped frame).
    for side, trail in (trails or {}).items():
        if not trail:
            continue
        trail_color = (80, 255, 160) if side == 'right' else (255, 180, 80)
        for (tx, ty, tt) in trail:
            age = now - tt
            if age > 0.2:
                continue
            alpha = max(0.0, 1.0 - age / 0.2)
            px = int(tx * fw)
            py = int(ty * fh)
            radius = int(2 + 4 * alpha)
            cv2.circle(frame, (px, py), radius, trail_color, -1)

    # Current position crosshair
    for side, pos in (hand_positions or {}).items():
        if not pos:
            continue
        hx, hy = pos
        cx = int(hx * fw)
        cy = int(hy * fh)
        color = (80, 255, 160) if side == 'right' else (255, 180, 80)
        cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 22, 2)


def draw_bass_pedal_panel(frame, bp):
    """Bass note & pedal tones panel — press P to toggle."""
    fh, fw = frame.shape[:2]

    panel_w = 420
    panel_h = 260
    px = (fw - panel_w) // 2
    py = (fh - panel_h) // 2

    draw_semi_transparent_rect(frame, px, py, panel_w, panel_h, (15, 15, 20), 0.92)
    cv2.rectangle(frame, (px, py), (px + panel_w, py + panel_h), (100, 100, 100), 1)

    # Title
    cv2.putText(frame, "BASS & PEDALS", (px + 20, py + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (140, 220, 255), 2)

    # ── Bass section ──
    bass_color = (100, 255, 160) if bp.bass_enabled else (120, 120, 120)
    bass_label = f"BASS: {'ON  -{bp.bass_octave_offset}oct' if bp.bass_enabled else 'OFF'}"
    cv2.putText(frame, bass_label, (px + 20, py + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, bass_color, 2 if bp.bass_enabled else 1)

    cv2.putText(frame, "B=toggle  ^v=octave", (px + 250, py + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 100, 100), 1)

    # Divider
    cv2.line(frame, (px + 20, py + 75), (px + panel_w - 20, py + 75), (60, 60, 60), 1)

    # ── Pedal section ──
    cv2.putText(frame, "PEDAL TONES", (px + 20, py + 98),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1)

    # Current pedals
    if bp.pedals:
        for i, midi_note in enumerate(bp.pedals):
            name = bp.pedal_name(midi_note)
            is_selected = (i == bp.selected_pedal)
            color = (140, 255, 200) if is_selected else (180, 180, 180)
            weight = 2 if is_selected else 1
            x_pos = px + 30 + i * 80
            cv2.putText(frame, name, (x_pos, py + 128),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, weight)
            if is_selected:
                # Underline
                tw = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, weight)[0][0]
                cv2.line(frame, (x_pos, py + 132), (x_pos + tw, py + 132), color, 2)
    else:
        cv2.putText(frame, "(none)", (px + 30, py + 128),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (80, 80, 80), 1)

    # ── Add pedal section ──
    cv2.putText(frame, "Add:", (px + 20, py + 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (160, 160, 160), 1)

    # Show the note being built
    adding_str = bp.adding_note_name
    cv2.putText(frame, adding_str, (px + 80, py + 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 220, 100), 2)

    cv2.putText(frame, "N=note  O/I=oct+/-  ENTER=add", (px + 170, py + 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (100, 100, 100), 1)

    # ── Controls hint ──
    hints = [
        "< > : select pedal    X : delete    R : reset all",
        "P / ESC : close panel",
    ]
    for i, h in enumerate(hints):
        cv2.putText(frame, h, (px + 20, py + panel_h - 36 + i * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (110, 110, 110), 1)
