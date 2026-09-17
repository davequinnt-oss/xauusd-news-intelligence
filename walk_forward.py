#!/usr/bin/env python3
"""
Chronological walk-forward validation for XAU News Engine.

Input CSV must contain the model FEATURES plus:
- date
- target_down

Optional:
- event

The script never shuffles events. Each prediction is generated using only
earlier observations, reducing look-ahead bias.
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

FEATURES = [
    "surprise_z","rate_surprise_bp","inflation_pressure","employment_pressure",
    "fed_path_score","dxy_pre_pct","us2y_pre_bp","us10y_pre_bp","real10y_pre_bp",
    "gold_pre_pct","gold_bearish_structure","gold_bullish_structure",
    "event_volatility_score"
]

def sigmoid(x):
    return 1/(1+np.exp(-np.clip(x,-40,40)))

def fit(X,y,epochs=2500,lr=.015,l2=.05):
    mu=X.mean(0); sd=X.std(0); sd[sd<1e-9]=1
    Z=(X-mu)/sd
    w=np.zeros(Z.shape[1]); b=0.
    for _ in range(epochs):
        p=sigmoid(Z@w+b)
        w-=lr*((Z.T@(p-y))/len(y)+l2*w)
        b-=lr*float(np.mean(p-y))
    return float(b-np.sum(w*mu/sd)), w/sd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--min-train",type=int,default=24)
    ap.add_argument("--test-every",type=int,default=1)
    ap.add_argument("--out",default="walk_forward_results.csv")
    a=ap.parse_args()

    df=pd.read_csv(a.csv)
    required=["date","target_down"]+FEATURES
    missing=[x for x in required if x not in df.columns]
    if missing: raise SystemExit("Missing: "+", ".join(missing))

    df["date"]=pd.to_datetime(df["date"])
    df=df.sort_values("date").dropna(subset=FEATURES+["target_down"]).reset_index(drop=True)

    rows=[]
    for i in range(a.min_train,len(df),a.test_every):
        train=df.iloc[:i]
        test=df.iloc[i]
        b,w=fit(train[FEATURES].values,train.target_down.values)
        p=float(sigmoid(b+np.dot(w,test[FEATURES].values)))
        y=int(test.target_down)
        rows.append({
            "date":test.date,
            "event":test.get("event",""),
            "prob_down":p,
            "target_down":y,
            "correct":int((p>=.5)==bool(y)),
            "brier":(p-y)**2
        })

    r=pd.DataFrame(rows)
    if r.empty: raise SystemExit("Not enough clean observations.")

    print("WALK-FORWARD RESULTS")
    print("Predictions:",len(r))
    print("Accuracy:",round(r.correct.mean(),4))
    print("Brier:",round(r.brier.mean(),4))
    print("Down prevalence:",round(r.target_down.mean(),4))
    r.to_csv(a.out,index=False)
    print("Saved:",a.out)

if __name__=="__main__":
    main()
