from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Timer:
    started: float
    elapsed_ms: int = 0


@contextmanager
def measure_ms():
    timer = Timer(started=time.perf_counter())
    try:
        yield timer
    finally:
        timer.elapsed_ms = int((time.perf_counter() - timer.started) * 1000)
