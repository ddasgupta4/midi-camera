"""
MIDI Camera — macOS Menu Bar App

Sits in the menu bar. Configure settings, launch/stop the camera window.
Run with: .venv/bin/python menubar.py
"""

import os
import json
import subprocess
import rumps

# ── Config file ────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

DEFAULTS = {
    'key':     'C',
    'mode':    'major',
    'channel': 0,       # 0-indexed internally (display as 1-16)
    'octave':  3,
    'camera':  -1,      # -1 = auto-detect
}

ALL_KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
KEY_DISPLAY = ['C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B']


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                saved = json.load(f)
            cfg = {**DEFAULTS, **saved}
            return cfg
        except Exception:
            pass
    return dict(DEFAULTS)


def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[config] save failed: {e}")


# ── Camera detection ───────────────────────────────────────────────────────────

def detect_cameras() -> list[tuple[int, str]]:
    """
    Returns list of (cv_index, display_name) for available cameras.
    Uses AVFoundation to get real device names, maps to OpenCV indices.
    """
    cameras = []

    # Try AVFoundation for real names
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeVideo
        devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
        av_names = [d.localizedName() for d in devices]
    except Exception:
        av_names = []

    # Probe OpenCV indices 0-4
    cv_indices = []
    for idx in range(5):
        cap = __import__('cv2').VideoCapture(idx)
        if cap.isOpened():
            cv_indices.append(idx)
            cap.release()

    # Pair them up (AVFoundation order usually matches OpenCV order)
    for i, cv_idx in enumerate(cv_indices):
        if i < len(av_names):
            name = av_names[i]
        else:
            name = f"Camera {cv_idx}"
        cameras.append((cv_idx, name))

    if not cameras:
        cameras = [(0, "Default Camera"), (1, "Camera 1")]

    return cameras


def best_camera(cameras: list[tuple[int, str]]) -> int:
    """Pick best camera — prefer built-in FaceTime, avoid virtual/Continuity/iPhone."""
    SKIP = ('continuity', 'iphone', 'ipad', 'obs', 'virtual', 'ndisplay', 'capture')
    PREFER = ('facetime', 'built-in', 'isight')
    # First pass: prefer known built-in
    for idx, name in cameras:
        low = name.lower()
        if any(s in low for s in SKIP):
            continue
        if any(p in low for p in PREFER):
            return idx
    # Second pass: anything real
    for idx, name in cameras:
        low = name.lower()
        if any(s in low for s in SKIP):
            continue
        return idx
    return cameras[0][0] if cameras else 0


# ── Menu bar app ───────────────────────────────────────────────────────────────

class MidiCameraApp(rumps.App):
    def __init__(self):
        super().__init__("🎹", quit_button=None)

        self.cfg = load_config()
        self.cameras = detect_cameras()

        # Auto-detect camera on first run
        if self.cfg['camera'] == -1:
            self.cfg['camera'] = best_camera(self.cameras)
            save_config(self.cfg)

        self._proc = None
        self._poll_timer = None

        self._build_menu()

    # ── Menu construction ──────────────────────────────────────────────────────

    def _build_menu(self):
        self.menu.clear()

        # Header (non-clickable title)
        self.menu.add(rumps.MenuItem("MIDI Camera", callback=None))
        self.menu.add(rumps.separator)

        # Camera
        cam_menu = rumps.MenuItem("Camera")
        for cv_idx, name in self.cameras:
            item = rumps.MenuItem(
                name,
                callback=self._make_camera_cb(cv_idx)
            )
            if cv_idx == self.cfg['camera']:
                item.state = 1
            cam_menu.add(item)
        self.menu.add(cam_menu)

        # MIDI Channel
        ch_menu = rumps.MenuItem("MIDI Channel")
        for ch in range(1, 17):
            item = rumps.MenuItem(
                f"Channel {ch}",
                callback=self._make_channel_cb(ch - 1)
            )
            if ch - 1 == self.cfg['channel']:
                item.state = 1
            ch_menu.add(item)
        self.menu.add(ch_menu)

        # Key
        key_menu = rumps.MenuItem("Key")
        for k, kd in zip(ALL_KEYS, KEY_DISPLAY):
            item = rumps.MenuItem(kd, callback=self._make_key_cb(k))
            if k == self.cfg['key']:
                item.state = 1
            key_menu.add(item)
        self.menu.add(key_menu)

        # Mode
        mode_menu = rumps.MenuItem("Mode")
        for m in ('major', 'minor'):
            item = rumps.MenuItem(m.capitalize(), callback=self._make_mode_cb(m))
            if m == self.cfg['mode']:
                item.state = 1
            mode_menu.add(item)
        self.menu.add(mode_menu)

        # Octave
        oct_menu = rumps.MenuItem("Octave")
        for o in range(1, 7):
            item = rumps.MenuItem(f"Octave {o}", callback=self._make_octave_cb(o))
            if o == self.cfg['octave']:
                item.state = 1
            oct_menu.add(item)
        self.menu.add(oct_menu)

        self.menu.add(rumps.separator)

        # Performance tier (read-only)
        tier_label = self._get_tier_label()
        self.menu.add(rumps.MenuItem(tier_label, callback=None))

        self.menu.add(rumps.separator)

        # Launch / Stop
        self._launch_item = rumps.MenuItem("▶  Launch", callback=self.toggle_launch)
        self.menu.add(self._launch_item)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=self.quit_app))

    def _get_tier_label(self) -> str:
        try:
            from core.performance import get_tier
            settings = get_tier()
            return f"Performance: {settings.tier.name}"
        except Exception:
            return "Performance: unknown"

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _make_camera_cb(self, cv_idx):
        def cb(sender):
            self._set_checked_in_submenu(sender, "Camera")
            self.cfg['camera'] = cv_idx
            save_config(self.cfg)
        return cb

    def _make_channel_cb(self, ch_idx):
        def cb(sender):
            self._set_checked_in_submenu(sender, "MIDI Channel")
            self.cfg['channel'] = ch_idx
            save_config(self.cfg)
        return cb

    def _make_key_cb(self, key):
        def cb(sender):
            self._set_checked_in_submenu(sender, "Key")
            self.cfg['key'] = key
            save_config(self.cfg)
        return cb

    def _make_mode_cb(self, mode):
        def cb(sender):
            self._set_checked_in_submenu(sender, "Mode")
            self.cfg['mode'] = mode
            save_config(self.cfg)
        return cb

    def _make_octave_cb(self, octave):
        def cb(sender):
            self._set_checked_in_submenu(sender, "Octave")
            self.cfg['octave'] = octave
            save_config(self.cfg)
        return cb

    def _set_checked_in_submenu(self, selected_item, submenu_title):
        """Uncheck all items in a submenu, check the selected one."""
        submenu = self.menu[submenu_title]
        for item in submenu.values():
            item.state = 0
        selected_item.state = 1

    # ── Launch / Stop ──────────────────────────────────────────────────────────

    def toggle_launch(self, _):
        if self._proc and self._proc.poll() is None:
            self._stop()
        else:
            self._launch()

    def _launch(self):
        if self._proc and self._proc.poll() is None:
            return  # already running

        save_config(self.cfg)

        venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'bin', 'python')
        app_path = os.path.join(os.path.dirname(__file__), 'app.py')

        # Pass config via env vars so app.py can read from config.json
        env = os.environ.copy()

        self._proc = subprocess.Popen(
            [venv_python, app_path],
            cwd=os.path.dirname(__file__),
            env=env,
        )

        self._launch_item.title = "■  Stop"
        self.title = "🎹●"  # dot = running

        # Poll process status every second
        self._poll_timer = rumps.Timer(self._poll_proc, 1)
        self._poll_timer.start()

    def _stop(self):
        if hasattr(self, '_poll_timer') and self._poll_timer:
            try: self._poll_timer.stop()
            except Exception: pass
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        self._on_stopped()

    def _poll_proc(self, timer):
        """Check if subprocess exited (called every 1s by rumps.Timer)."""
        if self._proc and self._proc.poll() is not None:
            timer.stop()
            self._on_stopped()

    def _on_stopped(self, *_):
        self._proc = None
        self._launch_item.title = "▶  Launch"
        self.title = "🎹"

    def quit_app(self, _):
        self._stop()
        rumps.quit_application()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    MidiCameraApp().run()


if __name__ == '__main__':
    main()
