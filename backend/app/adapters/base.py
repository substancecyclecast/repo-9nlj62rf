"""Adapter base types.

Adapters wrap external systems (chains, swap aggregators, fiat off-ramps, yield
venues, compliance providers). Each has a `mode`:

* ``sandbox`` — deterministic, key-free behaviour that mirrors the real API
  shape, so the whole product runs end-to-end without custody of any keys.
* ``live`` — calls the real provider; enabled by setting MANDATE_INTEGRATION_MODE
  to ``live`` and supplying the relevant API keys/RPC URLs.

Keeping a single interface means promoting an integration to production never
touches business logic — only the adapter implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class QuoteResult:
    ok: bool
    detail: str
    data: dict


class Adapter:
    name: str = "adapter"

    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode or settings.integration_mode

    @property
    def is_live(self) -> bool:
        return self.mode == "live"
