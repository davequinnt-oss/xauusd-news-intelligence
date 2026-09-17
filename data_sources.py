"""Read-only live data providers for XAUUSD News Intelligence.

The app is analysis-only. No broker/execution functionality exists here.
Provider order:
- Trading Economics (if TRADING_ECONOMICS_CLIENT is configured): calendar + Gold + DXY.
- Yahoo Finance: fallback for Gold + DXY.
- FRED: US 2Y/10Y/real 10Y.
- Official Federal Reserve calendar: always available as the FOMC schedule floor.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data_cache"
CACHE.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")

TIMEOUT = int(os.getenv("DATA_REQUEST_TIMEOUT", "12"))


@dataclass
class MarketSnapshot:
    timestamp_utc: str
    xauusd: float | None
    dxy: float | None
    us2y: float | None
    us10y: float | None
    real10y: float | None
    source_status: dict[str, str]
    source_detail: dict[str, str]


def _get(url: str, params=None, headers=None, timeout=TIMEOUT):
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r


def _safe_float(v):
    try:
        if v is None or v == "" or v == ".":
            return None
        return float(v)
    except Exception:
        return None


def _te_client() -> str | None:
    """Trading Economics client credential, normally KEY:SECRET."""
    return os.getenv("TRADING_ECONOMICS_CLIENT") or os.getenv("TRADING_ECONOMICS_API_KEY")


def trading_economics_search(term: str) -> list[dict[str, Any]]:
    client = _te_client()
    if not client:
        return []
    try:
        j = _get(
            f"https://api.tradingeconomics.com/search/{requests.utils.quote(term)}",
            params={"c": client, "f": "json"},
        ).json()
        return j if isinstance(j, list) else []
    except Exception:
        return []


def trading_economics_market(symbol: str) -> float | None:
    client = _te_client()
    if not client:
        return None
    try:
        j = _get(
            f"https://api.tradingeconomics.com/markets/symbol/{requests.utils.quote(symbol, safe=':')}",
            params={"c": client, "f": "json"},
        ).json()
        rows = j if isinstance(j, list) else [j]
        for row in rows:
            for key in ("Last", "last", "Close", "close"):
                v = _safe_float(row.get(key)) if isinstance(row, dict) else None
                if v is not None:
                    return v
    except Exception:
        pass
    return None


def trading_economics_market_auto() -> tuple[float | None, float | None, dict[str, str]]:
    """Use documented TE symbols when possible; search is a fallback for DXY."""
    if not _te_client():
        return None, None, {}

    gold_symbol = os.getenv("TRADING_ECONOMICS_GOLD_SYMBOL", "XAUUSD:CUR")
    dxy_symbol = os.getenv("TRADING_ECONOMICS_DXY_SYMBOL", "DXY:IND")

    gold = trading_economics_market(gold_symbol)
    dxy = trading_economics_market(dxy_symbol)
    detail = {}

    if gold is not None:
        detail["xauusd"] = f"Trading Economics {gold_symbol}"
    else:
        # Resolve the symbol if the configured default changes.
        for row in trading_economics_search("gold"):
            if row.get("Symbol") == "XAUUSD:CUR":
                gold = _safe_float(row.get("LatestValue") or row.get("Last"))
                if gold is not None:
                    detail["xauusd"] = "Trading Economics XAUUSD:CUR (search)"
                    break

    if dxy is not None:
        detail["dxy"] = f"Trading Economics {dxy_symbol}"
    else:
        for row in trading_economics_search("DXY"):
            sym = row.get("Symbol", "")
            if str(sym).upper().startswith("DXY"):
                dxy = _safe_float(row.get("LatestValue") or row.get("Last"))
                if dxy is not None:
                    detail["dxy"] = f"Trading Economics {sym} (search)"
                    break

    return gold, dxy, detail


def yahoo_quotes(symbols: list[str]) -> dict[str, float | None]:
    out = {s: None for s in symbols}
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        data = _get(url, params={"symbols": ",".join(symbols)}).json()
        for q in data.get("quoteResponse", {}).get("result", []):
            out[q.get("symbol")] = _safe_float(q.get("regularMarketPrice"))
    except Exception:
        pass

    for symbol in symbols:
        if out[symbol] is not None:
            continue
        try:
            u = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            j = _get(u, params={"range": "1d", "interval": "5m"}).json()
            result = (j.get("chart", {}).get("result") or [None])[0]
            if result:
                out[symbol] = _safe_float(result.get("meta", {}).get("regularMarketPrice"))
        except Exception:
            pass
    return out


def fred_latest(series: str, api_key: str | None = None) -> float | None:
    key = api_key or os.getenv("FRED_API_KEY")
    try:
        params = {"series_id": series, "file_type": "json", "limit": 5, "sort_order": "desc"}
        if key:
            params["api_key"] = key
        j = _get("https://api.stlouisfed.org/fred/series/observations", params=params).json()
        for row in j.get("observations", []):
            v = _safe_float(row.get("value"))
            if v is not None:
                return v
    except Exception:
        pass
    try:
        import io
        r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
        df = pd.read_csv(io.StringIO(r.text))
        if not df.empty and series in df.columns:
            for v in reversed(df[series].tolist()):
                fv = _safe_float(v)
                if fv is not None:
                    return fv
    except Exception:
        pass
    return None


def market_snapshot() -> MarketSnapshot:
    te_gold, te_dxy, te_detail = trading_economics_market_auto()
    source_detail = dict(te_detail)

    # Yahoo is a fallback only; it is intentionally not required for deployment.
    y = yahoo_quotes(["XAUUSD=X", "DX-Y.NYB"])
    xau = te_gold if te_gold is not None else y.get("XAUUSD=X")
    dxy = te_dxy if te_dxy is not None else y.get("DX-Y.NYB")
    if xau is not None and "xauusd" not in source_detail:
        source_detail["xauusd"] = "Yahoo Finance"
    if dxy is not None and "dxy" not in source_detail:
        source_detail["dxy"] = "Yahoo Finance"

    vals = {
        "xauusd": xau,
        "dxy": dxy,
        "us2y": fred_latest("DGS2"),
        "us10y": fred_latest("DGS10"),
        "real10y": fred_latest("DFII10"),
    }
    source_detail.setdefault("us2y", "FRED DGS2")
    source_detail.setdefault("us10y", "FRED DGS10")
    source_detail.setdefault("real10y", "FRED DFII10")
    status = {k: ("OK" if v is not None else "MISSING") for k, v in vals.items()}
    return MarketSnapshot(
        datetime.now(timezone.utc).isoformat(),
        **vals,
        source_status=status,
        source_detail=source_detail,
    )


def cme_fedwatch_snapshot() -> dict[str, Any]:
    """Fetch CME FedWatch JSON when the user's CME endpoint/key are configured."""
    url = os.getenv("CME_FEDWATCH_API_URL")
    key = os.getenv("CME_FEDWATCH_API_KEY")
    if not url or not key:
        return {"available": False, "reason": "CME FedWatch API credentials not configured"}
    try:
        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
        j = _get(url, headers=headers).json()
        return {"available": True, "data": j, "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {"available": False, "reason": f"CME request failed: {type(e).__name__}"}


def _normalize_calendar(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["date", "time", "event", "country", "actual", "forecast", "previous", "unit", "importance"]
    rename = {
        "Date": "date", "date": "date", "Time": "time", "time": "time",
        "Event": "event", "event": "event", "Country": "country", "country": "country",
        "Actual": "actual", "actual": "actual", "Consensus": "forecast", "consensus": "forecast",
        "Forecast": "forecast", "forecast": "forecast", "Previous": "previous", "previous": "previous",
        "Unit": "unit", "unit": "unit", "Importance": "importance", "importance": "importance",
    }
    df = df.rename(columns={c: rename.get(c, c) for c in df.columns})
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].copy()
    parsed = pd.to_datetime(df["date"], errors="coerce", utc=True)
    missing_time = df["time"].isna() | (df["time"].astype(str).str.strip() == "")
    df.loc[missing_time & parsed.notna(), "time"] = parsed[missing_time & parsed.notna()].dt.strftime("%H:%M")
    df["date"] = parsed.dt.strftime("%Y-%m-%d")
    return df


def _trading_economics_calendar() -> pd.DataFrame:
    client = _te_client()
    cols = ["date", "time", "event", "country", "actual", "forecast", "previous", "unit", "importance"]
    if not client:
        return pd.DataFrame(columns=cols)
    try:
        # Use a narrow window so the app does not pull an unnecessarily large calendar.
        today = datetime.now(timezone.utc).date()
        end = today + timedelta(days=int(os.getenv("CALENDAR_DAYS_AHEAD", "45")))
        url = f"https://api.tradingeconomics.com/calendar/country/United%20States/{today.isoformat()}/{end.isoformat()}"
        j = _get(url, params={"c": client, "f": "json"}).json()
        df = pd.DataFrame(j if isinstance(j, list) else j.get("data", []))
        if df.empty:
            return pd.DataFrame(columns=cols)
        return _normalize_calendar(df)
    except Exception:
        return pd.DataFrame(columns=cols)


def economic_calendar() -> pd.DataFrame:
    """Load the configured calendar, preferring Trading Economics when configured."""
    te_df = _trading_economics_calendar()
    if not te_df.empty:
        return te_df

    cols = ["date", "time", "event", "country", "actual", "forecast", "previous", "unit", "importance"]
    url = os.getenv("ECONOMIC_CALENDAR_URL")
    key = os.getenv("ECONOMIC_CALENDAR_API_KEY")
    if not url and os.getenv("TRADING_ECONOMICS_API_KEY"):
        url = "https://api.tradingeconomics.com/calendar/country/United%20States"
        key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not url:
        return pd.DataFrame(columns=cols)
    try:
        headers = {"Authorization": f"Client {key}"} if key else {}
        r = _get(url, headers=headers)
        if "csv" in r.headers.get("content-type", "").lower() or url.lower().endswith(".csv"):
            from io import StringIO
            df = pd.read_csv(StringIO(r.text))
        else:
            j = r.json()
            if isinstance(j, dict):
                for key_name in ("events", "data", "results"):
                    if key_name in j and isinstance(j[key_name], list):
                        j = j[key_name]
                        break
            df = pd.DataFrame(j)
        return _normalize_calendar(df)
    except Exception:
        return pd.DataFrame(columns=cols)


def upcoming_fomc() -> pd.DataFrame:
    """Official FOMC meeting dates; release time is converted from 2pm US/Eastern."""
    rows = [
        ("2026-10-28", "FOMC Rate Decision", False),
        ("2026-12-09", "FOMC Rate Decision + SEP", True),
        ("2027-01-27", "FOMC Rate Decision", False),
        ("2027-03-17", "FOMC Rate Decision + SEP", True),
        ("2027-04-28", "FOMC Rate Decision", False),
        ("2027-06-09", "FOMC Rate Decision + SEP", True),
        ("2027-07-28", "FOMC Rate Decision", False),
        ("2027-09-15", "FOMC Rate Decision + SEP", True),
        ("2027-10-27", "FOMC Rate Decision", False),
        ("2027-12-08", "FOMC Rate Decision + SEP", True),
    ]
    now = datetime.now(timezone.utc)
    data = []
    eastern = ZoneInfo("America/New_York")
    for d, e, sep in rows:
        local = datetime.fromisoformat(d).replace(hour=14, minute=0, tzinfo=eastern)
        dt = local.astimezone(timezone.utc)
        if dt >= now - timedelta(days=1):
            data.append({
                "date": dt.strftime("%Y-%m-%d"), "time": dt.strftime("%H:%M"),
                "event": e, "country": "USD", "actual": None, "forecast": None,
                "previous": None, "unit": "rate", "importance": "high", "sep": sep,
            })
    return pd.DataFrame(data)


def save_pre_release_snapshot(event_id: str, payload: dict[str, Any]):
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in event_id)
    p = CACHE / f"pre_{safe}.json"
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return p


def provider_health() -> dict[str, Any]:
    m = market_snapshot()
    fw = cme_fedwatch_snapshot()
    cal = economic_calendar()
    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "market": m.source_status,
        "market_sources": m.source_detail,
        "fedwatch": "OK" if fw.get("available") else "MISSING",
        "calendar": "OK" if not cal.empty else "MISSING",
        "credentials": {
            "fred_api_key": bool(os.getenv("FRED_API_KEY")),
            "trading_economics": bool(_te_client()),
            "cme_fedwatch": bool(os.getenv("CME_FEDWATCH_API_URL") and os.getenv("CME_FEDWATCH_API_KEY")),
            "economic_calendar": bool(os.getenv("ECONOMIC_CALENDAR_URL")),
        },
    }
