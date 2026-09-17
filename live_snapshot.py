from __future__ import annotations
import json
from datetime import datetime, timezone
from data_sources import market_snapshot, cme_fedwatch_snapshot, economic_calendar, upcoming_fomc, save_pre_release_snapshot


def build_snapshot(event_name: str = "") -> dict:
    m = market_snapshot()
    fw = cme_fedwatch_snapshot()
    cal = economic_calendar()
    fomc = upcoming_fomc()
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        "market": m.__dict__,
        "fedwatch": fw,
        "calendar_rows": cal.to_dict(orient="records"),
        "official_fomc_rows": fomc.to_dict(orient="records"),
        "data_quality": {
            "market_complete": all(v is not None for v in [m.xauusd, m.dxy, m.us2y, m.us10y, m.real10y]),
            "fedwatch_available": fw.get("available", False),
            "calendar_available": not cal.empty,
        },
    }
    return payload


def save_named_snapshot(event_name: str = "manual") -> str:
    payload = build_snapshot(event_name)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = save_pre_release_snapshot(f"{event_name}_{stamp}", payload)
    return str(p)

if __name__ == "__main__":
    print(json.dumps(build_snapshot(), indent=2, default=str))
