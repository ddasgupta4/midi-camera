"""
MIDI Camera — Hand Gesture MIDI Controller

Main entry point. Shows config screen, then runs the camera loop
with hand tracking, gesture interpretation, chord output, and overlay.
"""

import sys
import time
import cv2

from core.hand_tracker import HandTracker
from core.gesture import interpret_right_hand, interpret_left_hand, LeftHandGesture
from core.chord_engine import ChordEngine
from core.midi_output import MidiOutput
from ui.overlay import draw_chord_card, draw_status, draw_controls_hint
from ui.config_screen import show_config_screen


# Debounce: chord must be held this long before triggering (seconds)
DEBOUNCE_TIME = 0.35

# Target FPS for camera loop
TARGET_FPS = 30


def run_camera(config: dict):
    """Main camera loop."""
    # Init components
    engine = ChordEngine(
        key=config['key'],
        mode=config['mode'],
        octave=config['octave'],
    )
    midi = MidiOutput(port_name="MIDI Camera", channel=config['channel'])
    tracker = HandTracker()

    # Open MIDI port
    midi_ok = midi.open()
    if not midi_ok:
        print("[!] Could not open MIDI port. Continuing without MIDI output.")

    # Open camera
    cap = cv2.VideoCapture(config['camera'])
    if not cap.isOpened():
        print(f"[!] Could not open camera {config['camera']}")
        midi.close()
        tracker.release()
        return 'quit'

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Create window explicitly so it renders properly
    cv2.namedWindow("MIDI Camera", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("MIDI Camera", 960, 720)

    # State tracking
    current_chord = None       # Currently sounding chord info dict
    pending_degree = 0         # Degree being held (waiting for debounce)
    pending_since = 0.0        # When the pending degree was first seen
    pending_quality = None
    pending_add_7th = False
    pending_add_9th = False
    last_velocity = 80
    left_gesture_name = ""
    last_quality_change = 0.0     # timestamp of last quality change
    QUALITY_DEBOUNCE = 0.4        # seconds before quality change retriggers chord

    # Default left hand state when no left hand detected
    default_left = LeftHandGesture(
        quality_override=None, velocity=80,
        add_7th=False, add_9th=False, gesture_name="no hand"
    )

    frame_time = 1.0 / TARGET_FPS

    print(f"[*] MIDI Camera running — Key: {engine.get_key_display()} {engine.get_mode_display()}")
    print(f"[*] MIDI port: {'MIDI Camera' if midi_ok else 'NOT CONNECTED'}")
    print("[*] Press Q to quit, ESC to return to config")

    while True:
        t_start = time.time()

        ret, frame = cap.read()
        if not ret:
            break

        # Mirror the frame (selfie mode)
        frame = cv2.flip(frame, 1)

        # Track hands
        left_hand, right_hand = tracker.process(frame)

        # Draw hand landmarks
        if right_hand:
            tracker.draw_landmarks(frame, right_hand, color=(0, 255, 100))
        if left_hand:
            tracker.draw_landmarks(frame, left_hand, color=(255, 180, 0))

        # Interpret gestures
        right_gesture = interpret_right_hand(right_hand) if right_hand else None
        left_gesture = interpret_left_hand(left_hand) if left_hand else default_left

        last_velocity = left_gesture.velocity
        left_gesture_name = left_gesture.gesture_name

        # Determine target degree from right hand
        target_degree = right_gesture.degree if right_gesture else 0

        # Debounce logic: new degree must be held for DEBOUNCE_TIME
        now = time.time()
        if target_degree != pending_degree:
            # Degree changed — start new debounce timer
            pending_degree = target_degree
            pending_since = now
            pending_quality = left_gesture.quality_override
            pending_add_7th = left_gesture.add_7th
            pending_add_9th = left_gesture.add_9th
        else:
            # Same degree still held — update modifiers in real time
            pending_quality = left_gesture.quality_override
            pending_add_7th = left_gesture.add_7th
            pending_add_9th = left_gesture.add_9th

        # Check if debounce has elapsed
        debounce_met = (now - pending_since) >= DEBOUNCE_TIME

        if debounce_met:
            current_degree = current_chord['degree'] if current_chord else 0

            # Resolve what the pending quality would actually be
            if pending_degree >= 1:
                pending_resolved_quality = (
                    pending_quality or engine.diatonic_qualities[pending_degree - 1]
                )
            else:
                pending_resolved_quality = None

            # Check if chord degree changed
            degree_changed = (pending_degree != current_degree)

            # Check if quality/extensions changed (with separate debounce)
            quality_changed = (
                (current_chord and pending_resolved_quality != current_chord.get('quality'))
                or (current_chord and pending_add_7th != current_chord.get('_add_7th', False))
                or (current_chord and pending_add_9th != current_chord.get('_add_9th', False))
            )

            # Quality changes need their own debounce to prevent flutter
            quality_debounce_met = (now - last_quality_change) >= QUALITY_DEBOUNCE
            chord_changed = degree_changed or (quality_changed and quality_debounce_met)

            if chord_changed:
                if pending_degree == 0:
                    # Silence — note off
                    midi.all_notes_off()
                    current_chord = None
                else:
                    # Build and send new chord
                    chord_info = engine.build_chord(
                        degree=pending_degree,
                        quality_override=pending_quality,
                        add_7th=pending_add_7th,
                        add_9th=pending_add_9th,
                    )
                    chord_info['_add_7th'] = pending_add_7th
                    chord_info['_add_9th'] = pending_add_9th

                    midi.send_chord(chord_info['notes'], velocity=last_velocity)
                    current_chord = chord_info
                    if quality_changed:
                        last_quality_change = now

            elif current_chord and pending_degree != 0:
                # Same chord but velocity may have changed — update velocity
                # (re-send if velocity changed significantly)
                pass

        # Draw overlay
        draw_chord_card(
            frame,
            chord_info=current_chord or {},
            key_display=engine.get_key_display(),
            mode_display=engine.get_mode_display(),
            velocity=last_velocity,
            left_gesture=left_gesture_name,
        )
        draw_status(frame, midi.connected)
        draw_controls_hint(frame)

        cv2.imshow("MIDI Camera", frame)

        # Key handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            midi.close()
            tracker.release()
            cap.release()
            cv2.destroyAllWindows()
            return 'quit'
        elif key == 27:  # ESC
            midi.close()
            tracker.release()
            cap.release()
            cv2.destroyAllWindows()
            return 'config'

        # Frame rate limiting
        elapsed = time.time() - t_start
        if elapsed < frame_time:
            time.sleep(frame_time - elapsed)

    # Cleanup on camera failure
    midi.close()
    tracker.release()
    cap.release()
    cv2.destroyAllWindows()
    return 'quit'


def main():
    # Defaults — just launch. Change these or add CLI args later.
    config = {
        'key': 'C',
        'mode': 'major',
        'channel': 0,    # MIDI channel 1 (0-indexed)
        'octave': 3,
        'camera': 1,     # built-in webcam (0 = iPhone Continuity Camera on this mac)
    }

    print(f"[*] Starting with: Key={config['key']} Mode={config['mode']} "
          f"Ch={config['channel']+1} Oct={config['octave']} Cam={config['camera']}")

    result = run_camera(config)
    print("[*] MIDI Camera closed.")


if __name__ == '__main__':
    main()
