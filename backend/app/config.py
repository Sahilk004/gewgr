"""Runtime settings. Everything that is an *assumption* lives here, not in logic."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = BACKEND_DIR / "data"
    # Delivery days the assignment cares about (purchase decisions made in Jan 2026
    # are for delivery days Jan 1..31; decisions are made on D-1).
    delivery_start: date = date(2026, 1, 1)
    delivery_end: date = date(2026, 1, 31)
    # Day-ahead gate closure, Europe/London local time. GB day-ahead auctions close
    # in the ~09:20-09:50 window (verify). We default to the EARLIEST close so no forecast
    # that was published after any auction had closed can be used. User-adjustable.
    default_cutoff: str = "09:20"
    # How the half-hourly actuals are compared with an hourly forecast.
    default_alignment: str = "hour_mean"
    days_before: int = 1
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://localhost:8080")

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", str(d.data_dir))),
            delivery_start=date.fromisoformat(os.getenv("DELIVERY_START", d.delivery_start.isoformat())),
            delivery_end=date.fromisoformat(os.getenv("DELIVERY_END", d.delivery_end.isoformat())),
            default_cutoff=os.getenv("DEFAULT_CUTOFF", d.default_cutoff),
            default_alignment=os.getenv("DEFAULT_ALIGNMENT", d.default_alignment),
            cors_origins=tuple(os.getenv("CORS_ORIGINS", ",".join(d.cors_origins)).split(",")),
        )
