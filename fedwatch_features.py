#!/usr/bin/env python3
"""Normalize CME FedWatch probability snapshots and calculate expectation shifts.

Input CSV schema:
meeting_date,snapshot_time,target_rate,probability

Each row is one target-rate outcome for a meeting at a given snapshot time.

Outputs:
- probability change versus previous snapshot
- probability change versus 1 day / 1 week / 1 month when available
- expected target rate at each snapshot
- expected-rate change in basis points

The script does NOT invent missing snapshots. Missing comparison windows remain NaN.
"""

import argparse
import pandas as pd
import numpy as np

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--out",default="fedwatch_features.csv")
    a=p.parse_args()

    d=pd.read_csv(a.csv)
    req={"meeting_date","snapshot_time","target_rate","probability"}
    missing=req-set(d.columns)
    if missing:
        raise SystemExit("Missing columns: "+", ".join(sorted(missing)))

    d["meeting_date"]=pd.to_datetime(d["meeting_date"],utc=True,errors="coerce")
    d["snapshot_time"]=pd.to_datetime(d["snapshot_time"],utc=True,errors="coerce")
    d["target_rate"]=pd.to_numeric(d["target_rate"],errors="coerce")
    d["probability"]=pd.to_numeric(d["probability"],errors="coerce")
    d=d.dropna(subset=["meeting_date","snapshot_time","target_rate","probability"])
    d=d.sort_values(["meeting_date","snapshot_time","target_rate"])

    # Probability normalization if source expresses probabilities as percentages.
    if d["probability"].max()>1.5:
        d["probability"]=d["probability"]/100.0

    # Expected target rate = sum(rate * probability) across outcomes.
    agg=(d.groupby(["meeting_date","snapshot_time"])
           .apply(lambda g: pd.Series({
               "expected_target_rate":float((g.target_rate*g.probability).sum()),
               "probability_sum":float(g.probability.sum())
           }),include_groups=False).reset_index())

    agg["expected_target_rate"]=agg["expected_target_rate"].where(
        agg["probability_sum"].between(0.98,1.02)
    )

    def add_shift(hours):
        vals=[]
        for _,r in agg.iterrows():
            cutoff=r["snapshot_time"]-pd.Timedelta(hours=hours)
            prior=agg[(agg.meeting_date==r.meeting_date)&
                      (agg.snapshot_time<=cutoff)].tail(1)
            vals.append(np.nan if prior.empty else
                        (r["expected_target_rate"]-prior.iloc[0]["expected_target_rate"])*100)
        return vals

    agg["expected_rate_shift_bp_vs_1d"]=add_shift(24)
    agg["expected_rate_shift_bp_vs_1w"]=add_shift(24*7)
    agg["expected_rate_shift_bp_vs_1m"]=add_shift(24*30)

    # Immediate preceding snapshot shift.
    agg["expected_rate_shift_bp_prev"]=(
        agg.groupby("meeting_date")["expected_target_rate"].diff()*100
    )

    agg.to_csv(a.out,index=False)
    print(f"Saved {len(agg):,} FedWatch snapshot rows to {a.out}")
    print("Missing historical comparison windows are retained as NaN; no values are fabricated.")

if __name__=="__main__":
    main()
