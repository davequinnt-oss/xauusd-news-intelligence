#!/usr/bin/env python3
"""Walk-forward calibration report with Brier score and reliability bins."""

import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score

def reliability(y, p, bins=10):
    edges=np.linspace(0,1,bins+1)
    rows=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        mask=(p>=lo)&(p<hi if hi<1 else p<=hi)
        if mask.sum()==0: continue
        rows.append({
            "bin_low":lo,"bin_high":hi,"count":int(mask.sum()),
            "mean_probability":float(p[mask].mean()),
            "observed_frequency":float(y[mask].mean())
        })
    return pd.DataFrame(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--target",default="target_down")
    p.add_argument("--date",default="date")
    p.add_argument("--min_train",type=int,default=20)
    p.add_argument("--out",default="calibration_report.csv")
    a=p.parse_args()

    d=pd.read_csv(a.csv)
    d[a.date]=pd.to_datetime(d[a.date],utc=True,errors="coerce")
    d=d.dropna(subset=[a.date,a.target]).sort_values(a.date).reset_index(drop=True)
    drop={a.target,a.date,"timestamp","event","country","unit","importance"}
    features=[c for c in d.columns if c not in drop]
    X=d[features].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
    X=X.fillna(X.median(numeric_only=True)).fillna(0)
    y=pd.to_numeric(d[a.target],errors="coerce").astype(int).values

    probs=[]; ys=[]; dates=[]
    for i in range(a.min_train,len(d)):
        model=LogisticRegression(max_iter=2000,class_weight="balanced")
        model.fit(X.iloc[:i],y[:i])
        probs.append(model.predict_proba(X.iloc[[i]])[0,1])
        ys.append(y[i]); dates.append(d.iloc[i][a.date])

    if not probs:
        raise SystemExit("Not enough observations for walk-forward calibration.")

    probs=np.array(probs); ys=np.array(ys)
    report=reliability(ys,probs,10)
    report.to_csv(a.out,index=False)

    print(f"Predictions: {len(ys):,}")
    print(f"Accuracy: {accuracy_score(ys,probs>=0.5):.4f}")
    print(f"Brier: {brier_score_loss(ys,probs):.4f}")
    if len(np.unique(ys))>1:
        print(f"ROC AUC: {roc_auc_score(ys,probs):.4f}")
    print(f"Reliability table saved: {a.out}")

if __name__=="__main__":
    main()
