#!/usr/bin/env python3
"""Create leakage-safe pre-release macro features.

Expected macro columns:
actual, forecast, previous, unit, event

Features:
- surprise_raw = actual - forecast
- surprise_direction = sign(actual - forecast)
- surprise_z_event = event-specific standardized surprise using PAST rows only
- previous_revision = actual - previous (descriptive only; use carefully)
- rate/inflation/labor pressure transforms

The event-specific rolling z-score is causal: it only uses earlier observations.
"""

import argparse
import numpy as np
import pandas as pd

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--out",default="macro_features.csv")
    p.add_argument("--min-history",type=int,default=10)
    a=p.parse_args()

    d=pd.read_csv(a.csv)
    d["date"]=pd.to_datetime(d["date"],utc=True,errors="coerce")
    d=d.sort_values("date").reset_index(drop=True)

    d["actual"]=pd.to_numeric(d["actual"],errors="coerce")
    d["forecast"]=pd.to_numeric(d["forecast"],errors="coerce")
    d["previous"]=pd.to_numeric(d["previous"],errors="coerce")

    d["surprise_raw"]=d["actual"]-d["forecast"]
    d["surprise_direction"]=np.sign(d["surprise_raw"]).fillna(0)

    # Event-specific causal standardization
    def causal_z(s):
        past=s.shift(1)
        mu=past.expanding(min_periods=a.min_history).mean()
        sd=past.expanding(min_periods=a.min_history).std()
        return (s-mu)/sd.replace(0,np.nan)

    d["surprise_z_event"]=d.groupby("event",group_keys=False)["surprise_raw"].apply(causal_z)
    d["surprise_z_event"]=d["surprise_z_event"].replace([np.inf,-np.inf],np.nan).fillna(d["surprise_direction"])

    d["actual_vs_previous"]=d["actual"]-d["previous"]

    # Broad pressure proxies. Sign conventions are normalized so positive means
    # greater inflation/rate/labor pressure, but event-specific interpretation
    # should still be validated empirically.
    ev=d["event"].str.lower()
    d["inflation_pressure"]=np.where(ev.str.contains("cpi|pce|ppi|inflation"),d["surprise_z_event"],0)
    d["labor_pressure"]=np.where(ev.str.contains("nonfarm|payroll|nfp|wage|average hourly|employment"),d["surprise_z_event"],0)

    d.to_csv(a.out,index=False)
    print(f"Saved {len(d):,} rows to {a.out}")

if __name__=="__main__":
    main()
