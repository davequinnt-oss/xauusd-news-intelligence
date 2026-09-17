#!/usr/bin/env python3
"""Event-specific XAUUSD macro ensemble.

Purpose:
- Train separate models by event family when enough historical observations exist.
- Produce an ensemble probability without allowing later observations into training.
- Fall back to the global model when an event family has insufficient history.

This is research infrastructure, not a trading guarantee.
"""

import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, accuracy_score

DROP={"target_down","date","timestamp","event","country","unit","importance",
      "source","release_id","snapshot_time"}

def family(event):
    e=str(event).lower()
    if "fomc" in e or "fed" in e: return "FOMC"
    if "cpi" in e: return "CPI"
    if "pce" in e: return "PCE"
    if "nonfarm" in e or "payroll" in e or "nfp" in e: return "NFP"
    if "unemployment" in e or "jobless claims" in e or "claims" in e: return "LABOR"
    if "ppi" in e: return "PPI"
    if "retail sales" in e: return "RETAIL"
    if "ism" in e: return "ISM"
    if "gdp" in e: return "GDP"
    return "OTHER"

def prepare(df):
    feats=[c for c in df.columns if c not in DROP]
    X=df[feats].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
    X=X.fillna(X.median(numeric_only=True)).fillna(0)
    return X,feats

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--min-family",type=int,default=15)
    p.add_argument("--min-global",type=int,default=25)
    p.add_argument("--out",default="ensemble_predictions.csv")
    a=p.parse_args()

    d=pd.read_csv(a.csv)
    d["date"]=pd.to_datetime(d["date"],utc=True,errors="coerce")
    d=d.dropna(subset=["date","target_down"]).sort_values("date").reset_index(drop=True)
    d["family"]=d["event"].map(family)
    y=pd.to_numeric(d["target_down"],errors="coerce").astype(int)

    preds=[]
    for i in range(a.min_global,len(d)):
        train=d.iloc[:i]
        row=d.iloc[[i]]
        Xall,features=prepare(d.iloc[:i+1])
        Xtr=Xall.iloc[:i]
        Xte=Xall.iloc[[i]]
        model_global=LogisticRegression(max_iter=2000,class_weight="balanced")
        model_global.fit(Xtr,y.iloc[:i])
        pg=model_global.predict_proba(Xte)[0,1]

        fam=row.iloc[0]["family"]
        tf=train[train["family"]==fam]
        if len(tf)>=a.min_family and tf["target_down"].nunique()==2:
            Xtf,_=prepare(pd.concat([tf,row],ignore_index=True))
            mf=LogisticRegression(max_iter=2000,class_weight="balanced")
            mf.fit(Xtf.iloc[:-1],tf["target_down"].astype(int))
            pf=mf.predict_proba(Xtf.iloc[[-1]])[0,1]
            # 60% family model / 40% global model
            pe=0.6*pf+0.4*pg
            used="family+global"
        else:
            pe=pg
            used="global"

        preds.append({
            "date":row.iloc[0]["date"],
            "event":row.iloc[0]["event"],
            "family":fam,
            "p_down":pe,
            "model_used":used,
            "actual_down":int(y.iloc[i])
        })

    out=pd.DataFrame(preds)
    out.to_csv(a.out,index=False)
    print(f"Predictions: {len(out):,}")
    if len(out):
        print(f"Accuracy: {accuracy_score(out.actual_down,out.p_down>=0.5):.4f}")
        print(f"Brier: {brier_score_loss(out.actual_down,out.p_down):.4f}")
        print("\nBy family:")
        print(out.groupby("family").agg(
            n=("actual_down","size"),
            accuracy=("actual_down",lambda x: np.nan),
            mean_p_down=("p_down","mean"),
            observed_down=("actual_down","mean")
        ).to_string())
    print(f"Saved: {a.out}")

if __name__=="__main__":
    main()
