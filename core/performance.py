"""
Adaptive performance system — detects machine capabilities and sets tier.

Tiers:
  HIGH   — M1 Pro/Max/Ultra, 32GB+: full resolution, face every frame
  MEDIUM — M1/M2, 16GB+: 640x480 inference, face every 2nd frame
  LOW    — Intel or <16GB: 320x240 inference, face every 4th frame

Override: MIDI_CAMERA_TIER=high|medium|low
"""

import os
import platform
import subprocess
from dataclasses import dataclass
from enum import Enum


class Tier(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class TierSettings:
    tier: Tier
    # Inference resolution (width, height) — None = full camera resolution
    inference_size: tuple | None
    # Face tracker: run every N frames (1 = every frame)
    face_frame_skip: int
    # MediaPipe model complexity (0=lite, 1=full)
    hand_model_complexity: int
    # Frame budget in seconds — if inference exceeds this, degrade
    frame_budget: float


TIER_CONFIGS = {
    Tier.HIGH: TierSettings(
        tier=Tier.HIGH,
        inference_size=None,
        face_frame_skip=1,
        hand_model_complexity=1,
        frame_budget=0.040,  # 25fps
    ),
    Tier.MEDIUM: TierSettings(
        tier=Tier.MEDIUM,
        inference_size=(640, 480),
        face_frame_skip=2,
        hand_model_complexity=1,
        frame_budget=0.050,  # 20fps
    ),
    Tier.LOW: TierSettings(
        tier=Tier.LOW,
        inference_size=(320, 240),
        face_frame_skip=4,
        hand_model_complexity=0,
        frame_budget=0.066,  # 15fps
    ),
}


def _get_ram_gb() -> float:
    """Get total RAM in GB using sysctl (macOS) or /proc/meminfo (Linux)."""
    try:
        if platform.system() == "Darwin":
            # Try os.sysconf first (no subprocess needed)
            try:
                pages = os.sysconf("SC_PHYS_PAGES")
                page_size = os.sysconf("SC_PAGE_SIZE")
                return (pages * page_size) / (1024 ** 3)
            except (ValueError, OSError):
                pass
            # Fallback to sysctl with full path
            for sysctl in ["/usr/sbin/sysctl", "sysctl"]:
                try:
                    out = subprocess.check_output(
                        [sysctl, "-n", "hw.memsize"], text=True, timeout=2
                    ).strip()
                    return int(out) / (1024 ** 3)
                except FileNotFoundError:
                    continue
        else:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
    except Exception:
        pass
    return 8.0  # safe fallback


def _detect_tier() -> Tier:
    """Auto-detect performance tier from hardware."""
    proc = platform.processor()
    cpu_count = os.cpu_count() or 4
    ram_gb = _get_ram_gb()

    is_apple_silicon = proc == "arm" or "Apple" in proc

    if not is_apple_silicon:
        return Tier.LOW

    if ram_gb < 16:
        return Tier.LOW

    # Pro/Max/Ultra have 8+ perf cores → high CPU count
    if ram_gb >= 32 or cpu_count >= 10:
        return Tier.HIGH

    return Tier.MEDIUM


def get_tier() -> TierSettings:
    """Return the active performance tier settings."""
    override = os.environ.get("MIDI_CAMERA_TIER", "").lower().strip()
    if override in ("high", "medium", "low"):
        tier = Tier(override)
    else:
        tier = _detect_tier()
    return TIER_CONFIGS[tier]


def print_tier_info(settings: TierSettings):
    """Print tier info at startup."""
    ram = _get_ram_gb()
    res = f"{settings.inference_size[0]}x{settings.inference_size[1]}" if settings.inference_size else "full"
    print(f"[perf] tier={settings.tier.value.upper()}  "
          f"inference={res}  face_skip={settings.face_frame_skip}  "
          f"ram={ram:.0f}GB  cpus={os.cpu_count()}")
