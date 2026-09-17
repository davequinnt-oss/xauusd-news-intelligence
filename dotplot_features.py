#!/usr/bin/env python3
"""Normalize FOMC SEP/Dot Plot data for the model.

Expected input:
meeting_date,projection_year,median_rate

Optional:
prior_median_rate

The model feature is the change in the median projected rate, in basis points.
Do not infer participant dots from charts when machine-readable official tables exist.
"""

import argparse
import pandas as pd

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--out",default="dotplot_features.csv")
    a=p.parse_args()

    d=pd.read_csv(a.csv)
    req={"meeting_date","projection_year","median_rate"}
    miss=req-set(d.columns)
    if miss: raise SystemExit("Missing columns: "+", ".join(sorted(miss)))
    d["meeting_date"]=pd.to_datetime(d["meeting_date"],utc=True,errors="coerce")
    d["projection_year"]=pd.to_numeric(d["projection_year"],errors="coerce")
    d["median_rate"]=pd.to_numeric(d["median_rate"],errors="coerce")
    d=d.dropna(subset=["meeting_date","projection_year","median_rate"]).sort_values(["projection_year","meeting_date"])
    d["prior_median_rate"]=d.groupby("projection_year")["median_rate"].shift(1)
    d["dotplot_shift_bp"]=(d["median_rate"]-d["prior_median_rate"])*100
    d.to_csv(a.out,index=False)
    print(f"Saved {len(d):,} dot-plot rows to {a.out}")

if __name__=="__main__":
    main()
