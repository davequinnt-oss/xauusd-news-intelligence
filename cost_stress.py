#!/usr/bin/env python3
"""Simple event-study stress test for spread/slippage/transaction costs.

Input must contain:
date,p_down,predicted_abs_move_pct,actual_down,actual_abs_move_pct

This does NOT simulate order execution. It estimates how much directional
edge would remain after a fixed cost assumption.
"""

import argparse, pandas as pd, numpy as np

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--cost-bps",type=float,default=10)
    p.add_argument("--out",default="cost_stress.csv")
    a=p.parse_args()
    d=pd.read_csv(a.csv)
    cost_pct=a.cost_bps/100
    d["direction"]=np.where(d.p_down>=.5,-1,1)
    d["actual_signed_pct"]=np.where(d.actual_down==1,-d.actual_abs_move_pct,d.actual_abs_move_pct)
    d["gross_proxy_pct"]=d.direction*d.actual_signed_pct
    d["net_proxy_pct"]=d.gross_proxy_pct-cost_pct
    d["profitable_after_cost"]=d.net_proxy_pct>0
    d.to_csv(a.out,index=False)
    print(f"Cost assumption: {a.cost_bps:.2f} bps")
    print(f"Mean gross proxy: {d.gross_proxy_pct.mean():.4f}%")
    print(f"Mean net proxy: {d.net_proxy_pct.mean():.4f}%")
    print(f"Positive after cost: {d.profitable_after_cost.mean():.2%}")
    print(f"Saved: {a.out}")

if __name__=="__main__":
    main()
