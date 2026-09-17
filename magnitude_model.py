#!/usr/bin/env python3
"""Causal XAUUSD reaction magnitude model.

Predicts absolute post-release XAUUSD move using historical event features.
Uses log1p(abs(return)) so extreme moves do not dominate the regression.

This is deliberately a research model. It does not claim profitability.
"""

import argparse, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

DROP={"xau_return_pct","target_down","date","timestamp","event","country","unit",
      "importance","source","release_id","snapshot_time","family"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--target",default="xau_return_pct")
    p.add_argument("--horizon",type=int,default=15)
    p.add_argument("--min-train",type=int,default=30)
    p.add_argument("--out",default="magnitude_predictions.csv")
    a=p.parse_args()
    d=pd.read_csv(a.csv)
    if "target_horizon_minutes" in d:
        d=d[d.target_horizon_minutes==a.horizon].copy()
    d["date"]=pd.to_datetime(d["date"],utc=True,errors="coerce")
    d=d.dropna(subset=["date","xau_return_pct"]).sort_values("date").reset_index(drop=True)
    feats=[c for c in d.columns if c not in DROP]
    X=d[feats].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
    X=X.fillna(X.median(numeric_only=True)).fillna(0)
    y=np.log1p(np.abs(pd.to_numeric(d.xau_return_pct,errors="coerce").values))
    actual=np.abs(pd.to_numeric(d.xau_return_pct,errors="coerce").values)

    preds=[]
    for i in range(a.min_train,len(d)):
        model=HistGradientBoostingRegressor(max_iter=200,max_depth=3,learning_rate=.05,l2_regularization=1.0)
        model.fit(X.iloc[:i],y[:i])
        pred=np.expm1(model.predict(X.iloc[[i]])[0])
        preds.append({"date":d.iloc[i].date,"event":d.iloc[i].get("event",""),
                      "predicted_abs_move_pct":pred,
                      "actual_abs_move_pct":actual[i]})
    out=pd.DataFrame(preds)
    out.to_csv(a.out,index=False)
    if len(out):
        print(f"Predictions: {len(out):,}")
        print(f"MAE: {mean_absolute_error(out.actual_abs_move_pct,out.predicted_abs_move_pct):.5f}")
        print(f"RMSE: {mean_squared_error(out.actual_abs_move_pct,out.predicted_abs_move_pct)**0.5:.5f}")
    print(f"Saved: {a.out}")

if __name__=="__main__":
    main()
