"""Bootstrap a research dataset for XAUUSD News Intelligence.

Downloads read-only market history plus a normalized U.S. macro calendar.
It never invents consensus/actual values and never executes trades.

Usage:
  python historical_bootstrap.py --days 730

Environment:
  ECONOMIC_CALENDAR_URL / ECONOMIC_CALENDAR_API_KEY
  TRADING_ECONOMICS_API_KEY (optional; if set, the script can build a TE calendar URL)
  FRED_API_KEY (optional)
"""
from __future__ import annotations
import argparse, os
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_cache" / "historical"
DATA.mkdir(parents=True, exist_ok=True)
load_dotenv(ROOT / ".env")
TIMEOUT = int(os.getenv("DATA_REQUEST_TIMEOUT", "20"))


def get(url, params=None, headers=None):
    r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def yahoo_history(symbol: str, days: int = 730, interval: str = "1h") -> pd.DataFrame:
    end = int(datetime.now(timezone.utc).timestamp())
    start = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    j = get(url, {"period1": start, "period2": end, "interval": interval, "events": "history"}).json()
    result = (j.get("chart", {}).get("result") or [None])[0]
    if not result:
        return pd.DataFrame()
    ts = result.get("timestamp", [])
    q = result.get("indicators", {}).get("quote", [{}])[0]
    n = min(len(ts), len(q.get("open", [])))
    df = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(ts[:n], unit="s", utc=True),
        "open": q.get("open", [])[:n], "high": q.get("high", [])[:n],
        "low": q.get("low", [])[:n], "close": q.get("close", [])[:n],
        "volume": q.get("volume", [])[:n],
    }).dropna(subset=["close"])
    df["symbol"] = symbol
    return df


def fred_history(series: str, days: int = 730) -> pd.DataFrame:
    end = datetime.now(timezone.utc).date()
    start = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    url = "https://api.stlouisfed.org/fred/series/observations"
    key = os.getenv("FRED_API_KEY")
    if key:
        try:
            j = get(url, {"series_id": series, "api_key": key, "file_type": "json",
                          "observation_start": str(start), "observation_end": str(end)}).json()
            rows = [{"date": x["date"], "value": x["value"]} for x in j.get("observations", [])]
            return pd.DataFrame(rows)
        except Exception:
            pass
    r = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}",
            {"cosd": str(start), "coed": str(end)})
    return pd.read_csv(StringIO(r.text))[["observation_date", series]].rename(
        columns={"observation_date": "date", series: "value"})


def calendar_history() -> pd.DataFrame:
    url = os.getenv("ECONOMIC_CALENDAR_URL", "").strip()
    key = os.getenv("ECONOMIC_CALENDAR_API_KEY", "").strip()
    te_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not url and te_key:
        url = "https://api.tradingeconomics.com/calendar/country/United%20States"
        key = te_key
    if not url:
        raise RuntimeError("Configure ECONOMIC_CALENDAR_URL + key, or TRADING_ECONOMICS_API_KEY.")
    headers = {"Authorization": f"Client {key}"} if key else {}
    j = get(url, headers=headers).json()
    if isinstance(j, dict):
        for k in ("events", "data", "results"):
            if isinstance(j.get(k), list):
                j = j[k]; break
    df = pd.DataFrame(j)
    # Common Trading Economics names -> project schema.
    rename = {"Date":"date", "Time":"time", "Event":"event", "Country":"country",
              "Actual":"actual", "Consensus":"forecast", "Forecast":"forecast",
              "Previous":"previous", "Unit":"unit", "Importance":"importance",
              "CalendarId":"release_id", "Ticker":"ticker"}
    df = df.rename(columns=rename)
    for c in ["date","time","event","country","actual","forecast","previous","unit","importance"]:
        if c not in df: df[c] = None
    out = df[["date","time","event","country","actual","forecast","previous","unit","importance"]].copy()
    # Preserve revisions rather than overwriting them.
    out["date"] = pd.to_datetime(out["date"], utc=True, errors="coerce")
    out["time"] = out["time"].fillna("").astype(str)
    parsed_time = pd.to_datetime(out["time"], format="%H:%M:%S", errors="coerce")
    missing = parsed_time.isna()
    parsed_time.loc[missing] = pd.to_datetime(out.loc[missing, "time"], format="%H:%M", errors="coerce")
    out["timestamp_utc"] = out["date"].dt.normalize() + (parsed_time - parsed_time.dt.normalize())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=730)
    ap.add_argument("--interval", default="1h", choices=["1h", "1d"])
    args = ap.parse_args()
    failures = []
    for symbol, name in [("XAUUSD=X", "xauusd"), ("DX-Y.NYB", "dxy")]:
        try:
            df = yahoo_history(symbol, args.days, args.interval)
            p = DATA / f"{name}_{args.interval}.csv"; df.to_csv(p, index=False)
            print(f"{name}: {len(df)} rows -> {p}")
        except Exception as e:
            failures.append(f"{name}: {type(e).__name__}")
            print(f"{name}: UNAVAILABLE ({type(e).__name__})")
    for series, name in [("DGS2", "us2y"), ("DGS10", "us10y"), ("DFII10", "real10y")]:
        try:
            df = fred_history(series, args.days)
            p = DATA / f"{name}.csv"; df.to_csv(p, index=False)
            print(f"{name}: {len(df)} rows -> {p}")
        except Exception as e:
            failures.append(f"{name}: {type(e).__name__}")
            print(f"{name}: UNAVAILABLE ({type(e).__name__})")
    try:
        cal = calendar_history()
        p = DATA / "us_macro_calendar.csv"; cal.to_csv(p, index=False)
        print(f"calendar: {len(cal)} rows -> {p}")
    except Exception as e:
        failures.append(f"calendar: {type(e).__name__}")
        print(f"calendar: UNAVAILABLE ({type(e).__name__})")
    if failures:
        print("\nBootstrap finished with unavailable providers:")
        for f in failures: print(" -", f)
        print("No missing values were fabricated. Configure provider access and rerun to complete the dataset.")
    else:
        print("\nBootstrap complete. Validate timestamps and point-in-time consensus before model training.")

if __name__ == "__main__": main()
