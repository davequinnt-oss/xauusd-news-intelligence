#!/usr/bin/env python3
"""Validate macro event datasets before they enter model training."""

import argparse
import pandas as pd
import numpy as np

CORE = ["date","time","event","country","actual","forecast","previous","unit","importance"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    missing_cols = [c for c in CORE if c not in df.columns]
    if missing_cols:
        print("ERROR: missing required columns:", ", ".join(missing_cols))
        raise SystemExit(2)

    dt = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str),
                        utc=True, errors="coerce")
    print(f"Bad timestamps: {dt.isna().sum()}")

    dup = df.duplicated(subset=["date","time","event","country"]).sum()
    print(f"Duplicate release keys: {dup}")

    for c in ["actual","forecast","previous"]:
        n = pd.to_numeric(df[c], errors="coerce").isna().sum()
        print(f"{c} non-numeric/missing: {n}")

    if "target_down" in df:
        vals = set(pd.to_numeric(df["target_down"], errors="coerce").dropna().unique())
        print("target_down values:", sorted(vals))
        if not vals.issubset({0,1}):
            print("WARNING: target_down contains values other than 0/1.")

    if "importance" in df:
        allowed = {"low","medium","high"}
        bad = sorted(set(df["importance"].dropna().astype(str).str.lower()) - allowed)
        if bad:
            print("WARNING: unexpected importance values:", bad)

    # Leakage-oriented checks
    leakage_names = [c for c in df.columns if any(x in c.lower()
                     for x in ["future","post_release","forward_return","next_return"])]
    if leakage_names:
        print("WARNING: inspect possible leakage columns:", leakage_names)

    print("\nValidation complete. Warnings require review; this script does not modify data.")

if __name__ == "__main__":
    main()
