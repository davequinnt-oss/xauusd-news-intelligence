#!/usr/bin/env python3
"""Merge FedWatch expectation features into macro event rows without leakage.

For each event, the selected FedWatch snapshot is the latest snapshot at or before
the release timestamp. This prevents using a later market expectation snapshot
when constructing pre-release features.
"""

import argparse
import pandas as pd

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--events",required=True)
    p.add_argument("--fedwatch",required=True)
    p.add_argument("--out",default="macro_with_fedwatch.csv")
    a=p.parse_args()

    ev=pd.read_csv(a.events)
    fw=pd.read_csv(a.fedwatch)

    if "timestamp" not in ev.columns:
        ev["timestamp"]=pd.to_datetime(ev["date"].astype(str)+" "+ev["time"].astype(str),utc=True)
    else:
        ev["timestamp"]=pd.to_datetime(ev["timestamp"],utc=True,errors="coerce")
    fw["snapshot_time"]=pd.to_datetime(fw["snapshot_time"],utc=True,errors="coerce")
    fw["meeting_date"]=pd.to_datetime(fw["meeting_date"],utc=True,errors="coerce")

    ev["meeting_date"]=pd.to_datetime(ev.get("meeting_date",ev["date"]),utc=True,errors="coerce")
    # Merge on the FOMC meeting date only. Non-FOMC events remain unmatched.
    left=ev.sort_values("timestamp")
    right=fw.sort_values("snapshot_time")

    out=pd.merge_asof(
        left,right,
        left_on="timestamp",
        right_on="snapshot_time",
        by="meeting_date",
        direction="backward",
        suffixes=("","_fw")
    )
    out.to_csv(a.out,index=False)
    print(f"Saved {len(out):,} rows to {a.out}")

if __name__=="__main__":
    main()
