"""Lightweight, dependency-free metrics registry with Prometheus exposition.

We avoid pulling in `prometheus_client` so the service stays dependency-light and
the same registry works in tests. The registry is process-global and thread-safe
enough for the single-worker dev/demo deployment; for multi-worker production a
push-gateway or the official client can be swapped in behind the same interface.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._hist_buckets: dict[tuple[str, tuple[tuple[str, str], ...]], list[int]] = {}
        self._hist_sum: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._hist_count: dict[tuple[str, tuple[tuple[str, str], ...]], int] = defaultdict(int)
        self._started = time.time()

    @staticmethod
    def _key(name: str, labels: dict[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
        items = tuple(sorted((labels or {}).items()))
        return name, items

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            if key not in self._hist_buckets:
                self._hist_buckets[key] = [0] * len(_LATENCY_BUCKETS)
            for i, bound in enumerate(_LATENCY_BUCKETS):
                if value <= bound:
                    self._hist_buckets[key][i] += 1
            self._hist_sum[key] += value
            self._hist_count[key] += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": time.time() - self._started,
                "counters": {self._fmt(k): v for k, v in self._counters.items()},
                "gauges": {self._fmt(k): v for k, v in self._gauges.items()},
            }

    @staticmethod
    def _fmt(key: tuple[str, tuple[tuple[str, str], ...]]) -> str:
        name, items = key
        if not items:
            return name
        labelstr = ",".join(f'{k}="{v}"' for k, v in items)
        return f"{name}{{{labelstr}}}"

    def render_prometheus(self) -> str:
        """Render the registry in Prometheus text exposition format (v0.0.4)."""
        lines: list[str] = []
        with self._lock:
            lines.append("# HELP mandate_uptime_seconds Process uptime in seconds.")
            lines.append("# TYPE mandate_uptime_seconds gauge")
            lines.append(f"mandate_uptime_seconds {time.time() - self._started:.3f}")

            counter_names = {k[0] for k in self._counters}
            for name in sorted(counter_names):
                lines.append(f"# TYPE {name} counter")
                for (cname, items), value in self._counters.items():
                    if cname == name:
                        lines.append(f"{self._fmt((cname, items))} {value:g}")

            gauge_names = {k[0] for k in self._gauges}
            for name in sorted(gauge_names):
                lines.append(f"# TYPE {name} gauge")
                for (gname, items), value in self._gauges.items():
                    if gname == name:
                        lines.append(f"{self._fmt((gname, items))} {value:g}")

            hist_names = {k[0] for k in self._hist_buckets}
            for name in sorted(hist_names):
                lines.append(f"# TYPE {name} histogram")
                for (hname, items) in list(self._hist_buckets):
                    if hname != name:
                        continue
                    buckets = self._hist_buckets[(hname, items)]
                    cumulative = 0
                    base_labels = dict(items)
                    for i, bound in enumerate(_LATENCY_BUCKETS):
                        cumulative += buckets[i]
                        le_labels = {**base_labels, "le": str(bound)}
                        lines.append(f"{self._fmt((name + '_bucket', tuple(sorted(le_labels.items()))))} {cumulative}")
                    inf_labels = {**base_labels, "le": "+Inf"}
                    total = self._hist_count[(hname, items)]
                    lines.append(f"{self._fmt((name + '_bucket', tuple(sorted(inf_labels.items()))))} {total}")
                    lines.append(f"{self._fmt((name + '_sum', items))} {self._hist_sum[(hname, items)]:g}")
                    lines.append(f"{self._fmt((name + '_count', items))} {total}")
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
