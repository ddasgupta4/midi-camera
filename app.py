"""
MIDI Camera — Hand Gesture MIDI Controller
"""

import time
import cv2

from core.performance import get_tier, print_tier_info, Tier, TIER_CONFIGS
from core.hand_tracker import HandTracker
from core.face_tracker import FaceTracker
from core.gesture import interpret_right_hand, reset_gesture_state
from core.chord_engine import ChordEngine
from core.midi_output import MidiOutput
from core.modes import get_all_modes
from core.mode_manager import ModeManager
from ui.overlay import (draw_chord_card, draw_status, draw_controls_hint,
                         draw_sauce_banner, draw_help_overlay, draw_voicing_panel,
                         draw_latency_slider, draw_perf_hud, draw_debug_gestures,
                         draw_bass_pedal_panel, draw_cc_card, draw_drum_card)


DEBOUNCE_MIN  = 0.00   # 0ms   — unhinged
DEBOUNCE_MAX  = 0.40   # 400ms — fort knox
DEBOUNCE_DEFAULT = 0.10  # 100ms — unified settle window (hysteresis handles noise, this is the only gate)
TARGET_FPS = 30
ALL_KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Piano keyboard layout (following standard computer-keyboard piano mapping)
# Middle row: A=C  S=D  D=E  F=F  G=G  H=A  J=B  K=C  L=D
# Top row:    W=C# E=D# T=F# Y=G# U=A#
KEY_MAP = {
    ord('a'): 'C',  ord('s'): 'D',  ord('d'): 'E',  ord('f'): 'F',
    ord('g'): 'G',  ord('h'): 'A',  ord('j'): 'B',  ord('k'): 'C',
    ord('w'): 'C#', ord('e'): 'D#', ord('t'): 'F#', ord('y'): 'G#',
    ord('u'): 'A#',
}


class VoicingEditor:
    """Manages per-degree voicing customization (inversion + note offsets)."""

    def __init__(self):
        # Per degree (1-7): inversion index (0=root, 1=1st, 2=2nd, 3=3rd)
        self.inversions = {d: 0 for d in range(1, 8)}
        # Per degree: per-note semitone offsets (list, indexed by note position)
        self.note_offsets = {d: {} for d in range(1, 8)}

        # Panel state
        self.selected_degree = 1
        self.selected_note = 0

    TRIAD_SIZE = 3  # inversions always apply to the first 3 notes (triad) only

    def apply(self, notes: list, degree: int) -> list:
        """
        Apply inversion and offsets.
        Inversions only affect the triad (first 3 notes).
        Extensions (7th, 9th, 11th, 13th) always stack above the triad.
        """
        if not notes:
            return notes

        # Split into triad and extensions
        triad = list(notes[:self.TRIAD_SIZE])
        extensions = list(notes[self.TRIAD_SIZE:])

        # Apply note offsets to triad notes (by index)
        offsets = self.note_offsets.get(degree, {})
        for i, offset in offsets.items():
            if i < len(triad):
                triad[i] += offset

        # Apply inversion: cycle bottom triad note up an octave
        inv = self.inversions.get(degree, 0) % max(1, len(triad))
        for _ in range(inv):
            triad.sort()
            triad[0] += 12
        triad.sort()

        # Ensure all extensions sit above the top triad note
        if triad and extensions:
            ceiling = max(triad)
            adjusted = []
            for e in sorted(extensions):
                while e <= ceiling:
                    e += 12
                adjusted.append(e)
            extensions = sorted(adjusted)

        return triad + extensions

    def invert(self, degree: int, direction: int = 1):
        """Cycle inversion up or down."""
        current = self.inversions[degree]
        self.inversions[degree] = (current + direction) % 4

    def nudge_note(self, degree: int, note_idx: int, semitones: int):
        """Move a specific note by semitones."""
        offsets = self.note_offsets.setdefault(degree, {})
        offsets[note_idx] = offsets.get(note_idx, 0) + semitones

    def reset_degree(self, degree: int):
        self.inversions[degree] = 0
        self.note_offsets[degree] = {}


NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


class BassAndPedals:
    """Bass note (root N octaves below) + fixed pedal tones."""

    def __init__(self):
        self.bass_enabled = False
        self.bass_octave_offset = 1  # 1-3 octaves below root

        self.pedals: list[int] = []  # MIDI note numbers
        self.max_pedals = 4

        # Panel UI state
        self.selected_pedal = 0
        self.adding_note_idx = 0   # index into NOTE_NAMES_SHARP
        self.adding_octave = 4

    def apply(self, notes: list, root_midi: int) -> list:
        """Add bass note and pedal tones to the note array."""
        if not notes:
            return notes
        result = list(notes)

        # Bass note — always 1 octave below the chord's lowest note
        if self.bass_enabled and root_midi > 0:
            # Use the root's pitch class but place it below the chord
            root_pc = root_midi % 12
            lowest = min(notes)
            # Put root pitch class just below the lowest chord note
            bass = lowest - (lowest - root_pc) % 12
            if bass == lowest:
                bass -= 12  # must be below the chord
            # Apply additional octave offset (offset 1 = already 1 oct below)
            bass -= 12 * (self.bass_octave_offset - 1)
            while bass < 21:  # don't go below A0 (MIDI 21)
                bass += 12
            if bass not in result:
                result.insert(0, bass)

        # Pedal tones
        for p in self.pedals:
            if p not in result:
                result.append(p)

        return sorted(result)

    def add_pedal(self):
        if len(self.pedals) >= self.max_pedals:
            return
        midi_note = (self.adding_octave + 1) * 12 + self.adding_note_idx
        if midi_note not in self.pedals:
            self.pedals.append(midi_note)
            self.selected_pedal = len(self.pedals) - 1

    def delete_pedal(self):
        if self.pedals and 0 <= self.selected_pedal < len(self.pedals):
            self.pedals.pop(self.selected_pedal)
            if self.selected_pedal >= len(self.pedals):
                self.selected_pedal = max(0, len(self.pedals) - 1)

    def cycle_note(self, direction=1):
        self.adding_note_idx = (self.adding_note_idx + direction) % 12

    def cycle_octave(self, direction=1):
        self.adding_octave = max(1, min(6, self.adding_octave + direction))

    def transpose(self, semitones: int):
        """Shift all pedal notes by semitones (e.g. key change)."""
        self.pedals = [
            max(21, min(108, p + semitones)) for p in self.pedals
        ]

    def reset(self):
        self.bass_enabled = False
        self.bass_octave_offset = 1
        self.pedals.clear()
        self.selected_pedal = 0

    @property
    def adding_note_name(self):
        return f"{NOTE_NAMES_SHARP[self.adding_note_idx]}{self.adding_octave}"

    def pedal_name(self, midi_note: int) -> str:
        note = NOTE_NAMES_SHARP[midi_note % 12]
        octave = (midi_note // 12) - 1
        return f"{note}{octave}"


def _handle_bass_pedal_key(key: int, bp: BassAndPedals, raw_key: int = -1) -> bool:
    """Handle keypresses inside the bass/pedal panel."""
    if key == ord('b') or key == ord('B'):
        bp.bass_enabled = not bp.bass_enabled
        return True
    elif key == 0 or raw_key == 63232:  # UP — bass octave up
        bp.bass_octave_offset = min(3, bp.bass_octave_offset + 1)
        return True
    elif key == 1 or raw_key == 63233:  # DOWN — bass octave down
        bp.bass_octave_offset = max(1, bp.bass_octave_offset - 1)
        return True
    elif key == 3 or raw_key == 63235:  # RIGHT — select next pedal / cycle note
        if bp.pedals:
            bp.selected_pedal = (bp.selected_pedal + 1) % len(bp.pedals)
        return True
    elif key == 2 or raw_key == 63234:  # LEFT — select prev pedal / cycle note
        if bp.pedals:
            bp.selected_pedal = (bp.selected_pedal - 1) % len(bp.pedals)
        return True
    elif key == ord('n') or key == ord('N'):  # N — cycle adding note name
        bp.cycle_note(1)
        return True
    elif key == ord('o') or key == ord('O'):  # O — cycle adding octave UP
        bp.cycle_octave(1)
        return True
    elif key == ord('i') or key == ord('I'):  # I — cycle adding octave DOWN
        bp.cycle_octave(-1)
        return True
    elif key == 13 or key == 10:  # ENTER — add the pedal
        bp.add_pedal()
        return True
    elif key == ord('x') or key == ord('X'):  # X — delete selected pedal
        bp.delete_pedal()
        return True
    elif key == ord('r') or key == ord('R'):  # R — reset all
        bp.reset()
        return True
    return False


def _handle_shortcut(key: int, engine, midi, voicing_editor=None, voicing_panel_open=False, raw_key: int = -1, bass_pedals=None) -> bool:
    """Handle keyboard shortcuts. Returns True if key/octave changed."""

    old_key_idx = ALL_KEYS.index(engine.key)

    # Z/X = octave down/up
    if key in (ord('z'), ord('Z')):
        if engine.octave > 1:
            engine.octave -= 1
            return True
    elif key in (ord('x'), ord('X')):
        if engine.octave < 6:
            engine.octave += 1
            return True

    # Piano keyboard layout for key selection
    elif key in KEY_MAP:
        new_key = KEY_MAP[key]
        semis = (ALL_KEYS.index(new_key) - old_key_idx) % 12
        if semis > 6: semis -= 12  # shortest path
        engine.set_key(new_key)
        if bass_pedals and bass_pedals.pedals and semis != 0:
            bass_pedals.transpose(semis)
        return True

    # Arrow keys for key shift when voicing panel NOT open
    elif not voicing_panel_open:
        if key == 3 or raw_key == 63235:  # RIGHT arrow
            engine.set_key(ALL_KEYS[(old_key_idx + 1) % 12])
            if bass_pedals and bass_pedals.pedals:
                bass_pedals.transpose(1)
            return True
        elif key == 2 or raw_key == 63234:  # LEFT arrow
            engine.set_key(ALL_KEYS[(old_key_idx - 1) % 12])
            if bass_pedals and bass_pedals.pedals:
                bass_pedals.transpose(-1)
            return True

    # M = toggle major/minor
    if key == ord('m') or key == ord('M'):
        engine.set_mode('minor' if engine.mode == 'major' else 'major')
        return True

    # Debug: print unhandled keys
    if key not in (255, 0) and raw_key != -1:
        print(f"[debug] unhandled key={key} raw={raw_key}")

    return False


def _handle_voicing_key(key: int, ve: VoicingEditor, engine, sauce_mode: bool, raw_key: int = -1) -> bool:
    """Handle keypresses inside the voicing panel. Returns True if state changed."""
    d = ve.selected_degree
    n = ve.selected_note

    if key == 3 or raw_key == 63235:  # RIGHT — next degree
        ve.selected_degree = min(7, d + 1)
        ve.selected_note = 0
        return True
    elif key == 2 or raw_key == 63234:  # LEFT — prev degree
        ve.selected_degree = max(1, d - 1)
        ve.selected_note = 0
        return True
    elif key == 0 or raw_key == 63232:  # UP — nudge selected note up
        ve.nudge_note(d, n, 1)
        return True
    elif key == 1 or raw_key == 63233:  # DOWN — nudge selected note down
        ve.nudge_note(d, n, -1)
        return True
    elif key == ord('i'):  # I = invert up
        ve.invert(d, 1)
        return True
    elif key == ord('u'):  # U = invert down
        ve.invert(d, -1)
        return True
    elif key == ord('r'):  # R = reset selected degree
        ve.reset_degree(d)
        return True
    elif key == ord('n'):  # N = next note in chord
        # Get chord to know how many notes
        try:
            if sauce_mode:
                info = engine.build_sauce_chord(d)
            else:
                info = engine.build_chord(degree=d)
            max_n = len(info['notes']) - 1
            ve.selected_note = (n + 1) % (max_n + 1)
        except Exception:
            pass
        return True
    return False


# ── Graceful degradation ──

class DegradationMonitor:
    """Tracks inference timing, auto-degrades if behind, recovers when stable."""

    WARMUP_FRAMES = 60          # ignore timing until camera/models are warmed up
    BEHIND_THRESHOLD = 20       # consecutive slow frames before degrading
    RECOVER_THRESHOLD = 120     # consecutive fast frames before upgrading
    WARN_COOLDOWN = 10.0        # seconds between log spam

    def __init__(self, tier_settings):
        self.settings = tier_settings
        self._behind_count = 0
        self._fast_count = 0
        self._face_skip_boost = 0
        self._degraded_tier = None
        self._last_warn = 0.0
        self._frame_count = 0   # for warmup

    @property
    def effective_face_skip(self) -> int:
        return self.settings.face_frame_skip + self._face_skip_boost

    @property
    def effective_tier(self):
        return self._degraded_tier or self.settings.tier

    def check(self, frame_elapsed: float):
        """Call each frame with processing time. Auto-degrades or recovers."""
        self._frame_count += 1
        if self._frame_count < self.WARMUP_FRAMES:
            return  # don't act during warmup

        budget = self.settings.frame_budget
        if frame_elapsed > budget:
            self._behind_count += 1
            self._fast_count = 0
            if self._behind_count >= self.BEHIND_THRESHOLD:
                self._degrade()
                self._behind_count = 0
        else:
            self._fast_count += 1
            self._behind_count = max(0, self._behind_count - 1)
            if self._fast_count >= self.RECOVER_THRESHOLD:
                if self._degraded_tier is not None:
                    self._recover()
                elif self._face_skip_boost > 0:
                    self._face_skip_boost = max(0, self._face_skip_boost - 2)
                    print(f"[perf] face skip recovering → {self.effective_face_skip}")
                self._fast_count = 0

    def _degrade(self):
        now = time.time()
        if now - self._last_warn < self.WARN_COOLDOWN:
            return

        # If base tier is HIGH, never downgrade tier label — just boost face skip
        # HIGH machines should always show HIGH regardless of transient slowdowns
        base_is_high = self.settings.tier == Tier.HIGH

        if self._face_skip_boost < 8:
            self._face_skip_boost += 2
            print(f"[perf] inference behind, face skip → {self.effective_face_skip}")
        elif not base_is_high:
            tier_order = [Tier.HIGH, Tier.MEDIUM, Tier.LOW]
            current = self._degraded_tier or self.settings.tier
            idx = tier_order.index(current)
            if idx < len(tier_order) - 1:
                self._degraded_tier = tier_order[idx + 1]
                print(f"[perf] dropping to {self._degraded_tier.value.upper()} tier")
        self._last_warn = now

    def _recover(self):
        """Step back up one tier if things are running smoothly."""
        tier_order = [Tier.HIGH, Tier.MEDIUM, Tier.LOW]
        current = self._degraded_tier or self.settings.tier
        idx = tier_order.index(current)
        if idx > 0:
            self._degraded_tier = tier_order[idx - 1]
            self._face_skip_boost = max(0, self._face_skip_boost - 2)
            if self._degraded_tier == self.settings.tier:
                self._degraded_tier = None
                self._face_skip_boost = 0
            print(f"[perf] recovering → {(self._degraded_tier or self.settings.tier).value.upper()}")


def run_camera(config: dict):
    # ── Performance tier ──
    tier = get_tier()
    print_tier_info(tier)

    engine = ChordEngine(key=config['key'], mode=config['mode'], octave=config['octave'])
    midi = MidiOutput(port_name="MIDI Camera", channel=config['channel'])
    tracker = HandTracker(inference_size=tier.inference_size)
    ve = VoicingEditor()
    bp = BassAndPedals()
    degradation = DegradationMonitor(tier)

    # ── Mode system ──
    modes = get_all_modes(voicing_editor=ve, bass_pedals=bp)

    # Resolve initial mode from config (backwards-compatible with style_mode)
    initial_mode_index = config.get('mode_index', None)
    if initial_mode_index is None:
        # Legacy: map style_mode to index
        style = config.get('style_mode', 'andrew')
        initial_mode_index = 1 if style == 'dylan' else 0
    mode_mgr = ModeManager(modes, initial_index=initial_mode_index)

    # Apply saved smart_extensions to chord modes
    saved_smart_ext = config.get('smart_extensions', True)
    for m in modes:
        if m.supports_smart_extensions:
            m.smart_extensions = saved_smart_ext

    try:
        face = FaceTracker(frame_skip=tier.face_frame_skip)
        print("[*] Face tracker loaded (tongue = sauce mode)")
    except FileNotFoundError as e:
        print(f"[!] Face tracker unavailable: {e}")
        face = None

    midi_ok = midi.open()
    if not midi_ok:
        print("[!] Could not open MIDI port.")

    print(f"[*] Opening camera [{config['camera']}] ({config.get('camera_name', '?')})")
    cap = cv2.VideoCapture(config['camera'])
    if not cap.isOpened():
        print(f"[!] Could not open camera {config['camera']}")
        midi.close(); tracker.release(); return 'quit'

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cv2.namedWindow("MIDI Camera", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("MIDI Camera", 640, 480)  # display smaller; capture stays 960x720

    show_help = False
    show_voicings = False
    show_latency = False
    show_debug = False
    show_bass_pedals = False

    # Display FPS tracking
    display_fps = 0.0
    display_frame_count = 0
    display_fps_timer = time.time()

    frame_time = 1.0 / TARGET_FPS
    print(f"[*] MIDI Camera running — Key: {engine.get_key_display()} {engine.get_mode_display()}")
    print(f"[*] Mode: {mode_mgr.current_mode.name} ({mode_mgr.current_index + 1}/{len(modes)})")
    print(f"[*] MIDI port: {'MIDI Camera' if midi_ok else 'NOT CONNECTED'}")
    print("[*] Press H for help, / to cycle mode, Q to quit")

    while True:
      try:
        t_start = time.time()
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        mode = mode_mgr.current_mode

        # Submit frame to threaded hand tracker
        tracker.submit_frame(frame)

        # Face tracking (only when current mode supports sauce)
        sauce_from_face = None
        if face and mode.supports_sauce:
            face.frame_skip = degradation.effective_face_skip
            face.submit_frame(frame)
            sauce_from_face = face.get_result()

        # Read latest hand results (non-blocking)
        left_hand, right_hand = tracker.get_result()

        if right_hand:
            tracker.draw_landmarks(frame, right_hand, color=(0, 255, 100))
        if left_hand:
            tracker.draw_landmarks(frame, left_hand, color=(255, 180, 0))

        # Right hand gesture — shared across all modes
        right_gesture = interpret_right_hand(right_hand)

        # ── Process frame through current mode ──
        now = time.time()
        result = mode.process_frame(right_gesture, left_hand, sauce_from_face, engine, midi, now)

        # ── Draw overlay ── dispatch by mode type
        result_type = result.get('type', 'chord')
        if result_type == 'mapper':
            draw_cc_card(
                frame, cc_display=result.get('cc_display', []),
                key_display=engine.get_key_display(),
                mode_display=engine.get_mode_display(),
                left_gesture=result.get('left_gesture_name', ''),
            )
        elif result_type == 'drums':
            draw_drum_card(
                frame, result=result,
                key_display=engine.get_key_display(),
                mode_display=engine.get_mode_display(),
                left_gesture=result.get('left_gesture_name', ''),
            )
        else:
            draw_chord_card(
                frame, chord_info=result.get('chord_info', {}),
                key_display=engine.get_key_display(),
                mode_display=engine.get_mode_display(),
                velocity=result.get('velocity', 80),
                left_gesture=result.get('left_gesture_name', ''),
            )
        draw_status(
            frame, midi.connected,
            smart_extensions=getattr(mode, 'smart_extensions', None),
            mode_name=mode.name,
            mode_index=mode_mgr.current_index,
            mode_count=len(modes),
        )
        draw_controls_hint(frame)
        if result.get('sauce_mode'):
            draw_sauce_banner(frame)
        if show_help:
            draw_help_overlay(frame, mode_sections=mode.get_help_sections())
        elif show_voicings and mode.supports_voicings:
            draw_voicing_panel(frame, engine, ve, result.get('sauce_mode', False))
        elif show_bass_pedals and mode.supports_bass_pedals:
            draw_bass_pedal_panel(frame, bp)
        if show_latency:
            draw_perf_hud(
                frame,
                tier_name=degradation.effective_tier.value.upper(),
                display_fps=display_fps,
                hands_fps=tracker.inference_fps,
                face_fps=face.inference_fps if face else 0.0,
            )
            draw_latency_slider(frame, mode.debounce_time, DEBOUNCE_MIN, DEBOUNCE_MAX)
        if show_debug:
            desired_notes = result.get('desired_notes', [])
            desired_since = result.get('desired_since', 0.0)
            playing_notes = mode.current_playing_notes
            settle_progress = (now - desired_since) / max(mode.debounce_time, 0.001) if desired_notes != playing_notes else 1.0
            from core.gesture import _left_thumb
            draw_debug_gestures(frame, right_gesture, None, desired_notes,
                                playing_notes, settle_progress,
                                thumb_signal=_left_thumb.last_signal)

        cv2.imshow("MIDI Camera", frame)

        raw_key = cv2.waitKeyEx(1)
        key = raw_key & 0xFF

        if key == ord('q'):
            break
        elif key == 27:  # ESC
            if show_help or show_voicings or show_bass_pedals:
                show_help = False; show_voicings = False; show_bass_pedals = False
            else:
                reset_gesture_state()
                midi.close(); tracker.release()
                if face: face.release()
                cap.release(); cv2.destroyAllWindows()
                return 'config'
        elif mode_mgr.handle_key(key, raw_key, midi):
            # Mode switched — close panels, save, log
            show_voicings = False; show_bass_pedals = False
            _save_config({'mode_index': mode_mgr.current_index})
            print(f"[*] Mode: {mode_mgr.current_mode.name} ({mode_mgr.current_index + 1}/{len(modes)})")
        elif key == ord('h'):
            show_help = not show_help; show_voicings = False; show_latency = False
        elif key == ord('v') and mode.supports_voicings:
            show_voicings = not show_voicings; show_help = False; show_latency = False; show_bass_pedals = False
        elif key == ord('p') or key == ord('P'):
            if mode.supports_bass_pedals:
                show_bass_pedals = not show_bass_pedals; show_help = False; show_voicings = False
        elif key == ord('l'):
            show_latency = not show_latency; show_help = False
        elif key == ord('`'):
            show_debug = not show_debug
        elif key == ord('.') and mode.supports_smart_extensions:
            mode.smart_extensions = not mode.smart_extensions
            _save_config({'smart_extensions': mode.smart_extensions})
            print(f"[*] Smart extensions: {'ON' if mode.smart_extensions else 'OFF'}")
        elif key == ord(';') and mode.supports_sauce:
            mode.sauce_active = not mode.sauce_active
            print(f"[*] Sauce: {'ON' if mode.sauce_active else 'OFF'} (manual toggle)")
        elif key != 255:
            if show_latency:
                step = 0.01
                if key == 3 or raw_key == 63235:   mode.debounce_time = min(DEBOUNCE_MAX, mode.debounce_time + step)
                elif key == 2 or raw_key == 63234: mode.debounce_time = max(DEBOUNCE_MIN, mode.debounce_time - step)
                elif key == ord('r'): mode.debounce_time = DEBOUNCE_DEFAULT
            elif show_voicings and mode.supports_voicings:
                _handle_voicing_key(key, ve, engine, result.get('sauce_mode', False), raw_key)
            elif show_bass_pedals and mode.supports_bass_pedals:
                _handle_bass_pedal_key(key, bp, raw_key)
            elif not show_help:
                changed = _handle_shortcut(key, engine, midi, ve, show_voicings, raw_key, bass_pedals=bp)
                if changed:
                    midi.all_notes_off(); mode.reset_state()
                    print(f"[*] {engine.get_key_display()} {engine.get_mode_display()} oct{engine.octave}")
                    _save_config({'key': engine.key, 'mode': engine.mode, 'octave': engine.octave})

        # Frame timing + degradation check
        elapsed = time.time() - t_start
        degradation.check(elapsed)

        # Display FPS tracking
        display_frame_count += 1
        fps_elapsed = time.time() - display_fps_timer
        if fps_elapsed >= 1.0:
            display_fps = display_frame_count / fps_elapsed
            display_frame_count = 0
            display_fps_timer = time.time()

        if elapsed < frame_time:
            time.sleep(frame_time - elapsed)

      except Exception as e:
        print(f"[!] Error in main loop: {e}")
        break

    midi.close(); tracker.release()
    if face: face.release()
    cap.release(); cv2.destroyAllWindows()
    return 'quit'


def _load_config() -> dict:
    """Load config.json if it exists, otherwise use defaults."""
    import json, os
    defaults = {'key': 'C', 'mode': 'major', 'channel': 0, 'octave': 3, 'camera': -1, 'smart_extensions': True, 'style_mode': 'andrew', 'mode_index': None}
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                saved = json.load(f)
            cfg = {**defaults, **saved}
        except Exception as e:
            print(f"[!] Could not read config.json: {e}, using defaults")
            cfg = defaults
    else:
        cfg = defaults

    # Resolve camera by NAME (indices shift between reboots)
    try:
        from menubar import detect_cameras, best_camera
        cams = detect_cameras()
    except Exception:
        cams = []

    saved_name = cfg.get('camera_name', '')
    cam_idx = -1

    if cams:
        print(f"[*] Cameras: {', '.join(f'[{i}] {n}' for i, n in cams)}")

    # Try to find saved camera by name (exact match first, then substring)
    if saved_name:
        for idx, name in cams:
            if name == saved_name:
                cam_idx = idx
                break
        if cam_idx < 0:
            saved_lower = saved_name.lower()
            for idx, name in cams:
                if saved_lower in name.lower() or name.lower() in saved_lower:
                    cam_idx = idx
                    cfg['camera_name'] = name  # update to exact name
                    break
        if cam_idx >= 0:
            _save_config({'camera': cam_idx, 'camera_name': cfg.get('camera_name', saved_name)})
        else:
            print(f"[!] Saved camera '{saved_name}' not found, auto-detecting...")

    # Fallback: auto-detect best camera
    if cam_idx < 0:
        if cams:
            cam_idx = best_camera(cams)
            # Save the name for next time
            for idx, name in cams:
                if idx == cam_idx:
                    cfg['camera_name'] = name
                    break
        else:
            cam_idx = 0  # last resort
        _save_config({'camera_name': cfg.get('camera_name', ''), 'camera': cam_idx})
        print(f"[*] Auto-detected camera: {cam_idx} ({cfg.get('camera_name', '?')})")

    cfg['camera'] = cam_idx

    return cfg


def _save_config(updates: dict):
    """Merge updates into config.json."""
    import json, os
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        existing = {}
        if os.path.exists(config_path):
            with open(config_path) as f:
                existing = json.load(f)
        existing.update(updates)
        with open(config_path, 'w') as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def main():
    config = _load_config()
    mode_idx = config.get('mode_index')
    style_info = f"ModeIdx={mode_idx}" if mode_idx is not None else f"Style={config.get('style_mode', 'andrew')}"
    print(f"[*] Starting: Key={config['key']} Mode={config['mode']} "
          f"Ch={config['channel']+1} Oct={config['octave']} Cam={config['camera']} "
          f"{style_info}")
    run_camera(config)
    print("[*] MIDI Camera closed.")


if __name__ == '__main__':
    main()
