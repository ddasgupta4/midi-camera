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
DEBOUNCE_TIME = 0.3

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

    # State tracking
    current_chord = None       # Currently sounding chord info dict
    pending_degree = 0         # Degree being held (waiting for debounce)
    pending_since = 0.0        # When the pending degree was first seen
    pending_quality = None
    pending_add_7th = False
    pending_add_9th = False
    last_velocity = 80
    left_gesture_name = ""

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

            # Check if chord actually changed
            chord_changed = (
                pending_degree != current_degree
                or (current_chord and pending_quality != current_chord.get('quality'))
                or (current_chord and pending_add_7th != current_chord.get('_add_7th', False))
                or (current_chord and pending_add_9th != current_chord.get('_add_9th', False))
            )

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
    while True:
        config = show_config_screen()
        if config is None:
            print("[*] Config cancelled. Exiting.")
            sys.exit(0)

        result = run_camera(config)
        if result == 'quit':
            print("[*] MIDI Camera closed.")
            sys.exit(0)
        elif result == 'config':
            # Loop back to config screen
            continue


if __name__ == '__main__':
    main()
