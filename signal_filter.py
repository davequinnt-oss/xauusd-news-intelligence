#!/usr/bin/env python3
"""Translate probability + magnitude into a conservative research signal.

No trade execution. The output intentionally includes NO_TRADE whenever the
probability edge or expected magnitude is weak.
"""

import argparse, pandas as pd, numpy as np

def classify(p_down, predicted_abs_move, p_threshold=0.60, min_move=0.10):
    edge=abs(p_down-0.5)
    if edge < p_threshold-0.5 or predicted_abs_move < min_move:
        return "NO_TRADE"
    return "DOWN" if p_down>=p_threshold else "UP" if p_down<=1-p_threshold else "NO_TRADE"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--out",default="research_signal.csv")
    p.add_argument("--prob-threshold",type=float,default=.60)
    p.add_argument("--min-move",type=float,default=.10)
    a=p.parse_args()
    d=pd.read_csv(a.csv)
    d["signal"]=[classify(x,y,a.prob_threshold,a.min_move)
                 for x,y in zip(d.p_down,d.predicted_abs_move_pct)]
    d["confidence_distance"]=abs(d.p_down-.5)*2
    d.to_csv(a.out,index=False)
    print(d["signal"].value_counts().to_string())
    print(f"Saved: {a.out}")

if __name__=="__main__":
    main()
