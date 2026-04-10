"""
Reusable gesture signal filters.

These small helpers are shared across modes to kill common problems:
  - EMA            : smooth noisy landmark positions without adding a buffer
  - VelocityTracker: time-normalized velocity so pluck/strike detection
                     doesn't depend on frame rate

All O(1) per frame, zero allocations in the hot path.
"""


class EMA:
    """Exponential moving average for a single scalar.

    smooth[n] = alpha * raw[n] + (1 - alpha) * smooth[n-1]

    Higher alpha = more responsive (less smoothing).
    First sample primes the filter instead of ramping from 0.
    """

    def __init__(self, alpha: float, initial: float = 0.0):
        self.alpha = alpha
        self.value = initial
        self._primed = False

    def update(self, x: float) -> float:
        if not self._primed:
            self.value = x
            self._primed = True
        else:
            self.value = self.alpha * x + (1.0 - self.alpha) * self.value
        return self.value

    def reset(self, initial: float = 0.0):
        self.value = initial
        self._primed = False


class VelocityTracker:
    """Time-normalized velocity of a scalar signal (e.g. wrist_y).

    Returns (velocity_per_second, dt). The first call after a reset returns
    (0.0, 0.0) since no dt is available yet. This makes pluck/strike
    detection independent of the main-loop frame rate.
    """

    def __init__(self):
        self._prev_value: float | None = None
        self._prev_time: float | None = None

    def update(self, value: float, now: float) -> tuple[float, float]:
        if self._prev_value is None or self._prev_time is None:
            self._prev_value = value
            self._prev_time = now
            return 0.0, 0.0
        dt = now - self._prev_time
        if dt <= 0.0:
            return 0.0, 0.0
        vel = (value - self._prev_value) / dt
        self._prev_value = value
        self._prev_time = now
        return vel, dt

    def reset(self):
        self._prev_value = None
        self._prev_time = None
