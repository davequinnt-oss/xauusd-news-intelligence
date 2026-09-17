#!/usr/bin/env python3
"""
Build a first real FOMC event-study dataset.

Sources:
- Official Federal Reserve FOMC calendar for event dates.
- FRED daily Treasury series:
  DGS2, DGS10, DFII10.
- Yahoo Finance via yfinance:
  XAUUSD=X and DX-Y.NYB.

This creates market-reaction labels and pre-event features.
It does NOT fabricate consensus expectations. Consensus/surprise must be added
later from a licensed/appropriate economic-calendar source.
"""

from pathlib import Path
import io, requests, pandas as pd
import numpy as np

FOMC_DATES = [
"2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15",
"2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14",
"2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13",
"2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18",
"2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-10",
"2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16","2026-10-28","2026-12-09"
]

def fred(series):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    r=requests.get(url,timeout=30)
    r.raise_for_status()
    x=pd.read_csv(io.StringIO(r.text))
    x["DATE"]=pd.to_datetime(x["DATE"])
    x=x.rename(columns={series:series.lower()})
    x[series.lower()]=pd.to_numeric(x[series.lower()],errors="coerce")
    return x.dropna()

def yahoo(ticker):
    import yfinance as yf
    x=yf.download(ticker,start="2020-12-01",end="2027-01-10",
                  auto_adjust=False,progress=False)
    if isinstance(x.columns,pd.MultiIndex):
        x=x.xs(ticker,axis=1,level=1)
    x=x.reset_index()
    x["Date"]=pd.to_datetime(x["Date"]).dt.tz_localize(None)
    return x[["Date","Close"]].rename(columns={"Close":ticker})

def main():
    dates=pd.DataFrame({"date":pd.to_datetime(FOMC_DATES)})
    dates["event"]="FOMC"

    dgs2=fred("DGS2").rename(columns={"DATE":"date"})
    dgs10=fred("DGS10").rename(columns={"DATE":"date"})
    real=fred("DFII10").rename(columns={"DATE":"date"})
    gold=yahoo("XAUUSD=X")
    dxy=yahoo("DX-Y.NYB")

    m=dates.merge(dgs2[["date","dgs2"]],on="date",how="left")
    m=m.merge(dgs10[["date","dgs10"]],on="date",how="left")
    m=m.merge(real[["date","dfii10"]],on="date",how="left")
    m=m.merge(gold,on="date",how="left").merge(dxy,on="date",how="left")

    # Pre-event = previous trading day's close.
    for col in ["dgs2","dgs10","dfii10","XAUUSD=X","DX-Y.NYB"]:
        m[f"{col}_pre_change"]=m[col].diff()

    # Forward event reaction: next available row in each market series.
    m["gold_next_close"]=m["XAUUSD=X"].shift(-1)
    m["dxy_next_close"]=m["DX-Y.NYB"].shift(-1)
    m["gold_forward_return_pct"]=(m["gold_next_close"]/m["XAUUSD=X"]-1)*100
    m["dxy_forward_return_pct"]=(m["dxy_next_close"]/m["DX-Y.NYB"]-1)*100

    # Primary label: next-day XAUUSD direction.
    m["target_down"]=(m["gold_forward_return_pct"]<0).astype(int)

    # Initial mappings into the engine feature vocabulary.
    m["surprise_z"]=np.nan
    m["rate_surprise_bp"]=np.nan
    m["inflation_pressure"]=np.nan
    m["employment_pressure"]=np.nan
    m["fed_path_score"]=np.nan
    m["dxy_pre_pct"]=m["DX-Y.NYB_pre_change"]/m["DX-Y.NYB"]*100
    m["us2y_pre_bp"]=m["dgs2_pre_change"]*100
    m["us10y_pre_bp"]=m["dgs10_pre_change"]*100
    m["real10y_pre_bp"]=m["dfii10_pre_change"]*100
    m["gold_pre_pct"]=m["XAUUSD=X_pre_change"]/m["XAUUSD=X"]*100
    m["gold_bearish_structure"]=np.nan
    m["gold_bullish_structure"]=np.nan
    m["event_volatility_score"]=1.0

    out=m[["date","event","target_down"]+
          ["surprise_z","rate_surprise_bp","inflation_pressure","employment_pressure",
           "fed_path_score","dxy_pre_pct","us2y_pre_bp","us10y_pre_bp","real10y_pre_bp",
           "gold_pre_pct","gold_bearish_structure","gold_bullish_structure",
           "event_volatility_score","gold_forward_return_pct","dxy_forward_return_pct"]]
    out.to_csv("fomc_event_study_raw.csv",index=False)

    print("Created fomc_event_study_raw.csv")
    print(f"Rows: {len(out)}")
    print("Note: consensus/surprise fields are intentionally blank rather than fabricated.")

if __name__=="__main__":
    main()
