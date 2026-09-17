#!/usr/bin/env python3
"""Build post-release XAU/DXY/yield reaction labels from aligned time-series CSVs.

This intentionally separates labels from pre-release features. The market files should
contain UTC timestamps and columns:
timestamp, close

XAU and DXY use percentage returns. Yield series use basis-point changes.
"""

import argparse
import pandas as pd
import numpy as np

def load_series(path, value_col="close"):
    d = pd.read_csv(path)
    if "timestamp" not in d.columns or value_col not in d.columns:
        raise ValueError(f"{path}: needs timestamp and {value_col}")
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True, errors="coerce")
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    return d.dropna(subset=["timestamp", value_col]).sort_values("timestamp")

def value_at_or_after(s, t):
    x = s[s["timestamp"] >= t]
    return x.iloc[0] if len(x) else None

def label(events, xau, dxy, us2y, real10y, minutes):
    out = []
    delta = pd.Timedelta(minutes=minutes)
    for _, e in events.iterrows():
        t = pd.Timestamp(e["timestamp"])
        end = t + delta
        def pct(series):
            a = series[series["timestamp"] <= t].tail(1)
            b = series[series["timestamp"] <= end].tail(1)
            if len(a)==0 or len(b)==0: return np.nan
            return (b.iloc[0]["close"]/a.iloc[0]["close"]-1)*100
        def bp(series):
            a = series[series["timestamp"] <= t].tail(1)
            b = series[series["timestamp"] <= end].tail(1)
            if len(a)==0 or len(b)==0: return np.nan
            return (b.iloc[0]["close"]-a.iloc[0]["close"])*100
        xr = pct(xau); dr = pct(dxy); yr = bp(us2y); rr = bp(real10y)
        out.append({
            **e.to_dict(),
            "target_horizon_minutes": minutes,
            "xau_return_pct": xr,
            "dxy_return_pct": dr,
            "us2y_change_bp": yr,
            "real10y_change_bp": rr,
            "target_down": int(xr < 0) if pd.notna(xr) else np.nan
        })
    return pd.DataFrame(out)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--events", required=True)
    p.add_argument("--xau", required=True)
    p.add_argument("--dxy", required=True)
    p.add_argument("--us2y", required=True)
    p.add_argument("--real10y", required=True)
    p.add_argument("--minutes", type=int, nargs="+", default=[5,15,30,60,240,1440])
    p.add_argument("--out", default="macro_event_reactions.csv")
    a=p.parse_args()

    ev=pd.read_csv(a.events)
    if "timestamp" not in ev.columns:
        ev["timestamp"]=pd.to_datetime(ev["date"].astype(str)+" "+ev["time"].astype(str),utc=True)
    else:
        ev["timestamp"]=pd.to_datetime(ev["timestamp"],utc=True,errors="coerce")

    xau=load_series(a.xau); dxy=load_series(a.dxy)
    us2y=load_series(a.us2y); real10y=load_series(a.real10y)

    frames=[label(ev,xau,dxy,us2y,real10y,m) for m in a.minutes]
    result=pd.concat(frames,ignore_index=True)
    result.to_csv(a.out,index=False)
    print(f"Saved {len(result):,} reaction rows to {a.out}")

if __name__=="__main__":
    main()
