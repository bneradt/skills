#!/usr/bin/env python3
"""Progress reporting helpers for long-running commentary tasks."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ProgressReporter:
    enabled: bool = False
    json_mode: bool = False

    def emit(self, phase: str, message: str, **extra: Any) -> None:
        if not self.enabled:
            return
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if self.json_mode:
            payload: Dict[str, Any] = {"ts": ts, "phase": phase, "message": message}
            payload.update(extra)
            print(json.dumps(payload), flush=True)
            return
        tail = ""
        if extra:
            formatted = " ".join(f"{k}={v}" for k, v in extra.items())
            tail = f" ({formatted})"
        print(f"{phase}: {message}{tail}", flush=True)

    def heartbeat_every(self, count: int, every: int, phase: str, message: str) -> None:
        if every > 0 and count % every == 0:
            self.emit(phase, message, count=count)

