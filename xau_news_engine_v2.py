#!/usr/bin/env python3
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import requests

FEATURES = [
    "surprise_z","rate_surprise_bp","inflation_pressure","employment_pressure",
    "fed_path_score","dxy_pre_pct","us2y_pre_bp","us10y_pre_bp","real10y_pre_bp",
    "gold_pre_pct","gold_bearish_structure","gold_bullish_structure",
    "event_volatility_score"
]

# Starting heuristic only. Historical calibration should replace these.
W = np.array([-0.55,-0.08,-0.45,0.35,-0.95,-0.30,-0.035,-0.018,-0.028,
              -0.25,0.35,-0.35,0.20])

def sigmoid(x):
    return 1/(1+np.exp(-np.clip(x,-40,40)))

def logit(p):
    p=np.clip(p,1e-6,1-1e-6)
    return np.log(p/(1-p))

def n(d,k,default=0):
    v=d.get(k,default)
    return default if v in (None,"") else float(v)

def features(d):
    event=str(d.get("event","UNKNOWN")).upper().replace("-","_").replace(" ","_")
    actual,forecast=d.get("actual"),d.get("forecast")
    scale=max(abs(n(d,"surprise_scale",1)),1e-9)
    s=0 if actual is None or forecast is None else (float(actual)-float(forecast))/scale
    # For claims/unemployment, a positive surprise is normally gold-positive.
    if event in ("JOBLESS_CLAIMS","UNEMPLOYMENT"): s=-s
    fed=n(d,"dotplot_change_bp")/25+n(d,"guidance_hawkish_score")+n(d,"terminal_rate_change_bp")/25
    return {
        "surprise_z":s,
        "rate_surprise_bp":n(d,"rate_surprise_bp"),
        "inflation_pressure":n(d,"inflation_pressure"),
        "employment_pressure":n(d,"employment_pressure"),
        "fed_path_score":fed,
        "dxy_pre_pct":n(d,"dxy_pre_pct"),
        "us2y_pre_bp":n(d,"us2y_pre_bp"),
        "us10y_pre_bp":n(d,"us10y_pre_bp"),
        "real10y_pre_bp":n(d,"real10y_pre_bp"),
        "gold_pre_pct":n(d,"gold_pre_pct"),
        "gold_bearish_structure":n(d,"gold_bearish_structure"),
        "gold_bullish_structure":n(d,"gold_bullish_structure"),
        "event_volatility_score":n(d,"event_volatility_score",.5)
    }

def heuristic(f,event):
    x=np.array([f[k] for k in FEATURES])
    score=float(W@x)
    if event in ("FOMC","FED"):
        score += -.45*f["fed_path_score"]-.02*f["us2y_pre_bp"]-.03*f["real10y_pre_bp"]
    elif event in ("CPI","PCE","PPI"):
        score += -.65*f["inflation_pressure"]
    elif event in ("NFP","UNEMPLOYMENT","JOBLESS_CLAIMS"):
        score += -.40*f["employment_pressure"]
    return score

def confirmation(d):
    s=0
    for k,positive_is_bearish in [
        ("dxy_post_pct",True),("us2y_post_bp",True),
        ("real10y_post_bp",True),("gold_post_pct",False)]:
        v=n(d,k)
        if v:
            bear=(v>0) if positive_is_bearish else (v<0)
            s += 1 if bear else -1
    return s

def label(p):
    if p>=.70:return "HIGH BEARISH PROBABILITY"
    if p>=.58:return "BEARISH LEAN"
    if p<=.30:return "HIGH BULLISH PROBABILITY"
    if p<=.42:return "BULLISH LEAN"
    return "MIXED / WAIT"

def analyze(d,model=None):
    event=str(d.get("event","UNKNOWN")).upper().replace("-","_").replace(" ","_")
    f=features(d)
    if model:
        score=model["intercept"]+sum(model["coef"][k]*f[k] for k in FEATURES)
        model_name="historically_calibrated_logistic"
    else:
        score=heuristic(f,event); model_name="initial_heuristic"
    p=float(sigmoid(score))
    has_post=any(k in d for k in ("dxy_post_pct","us2y_post_bp","real10y_post_bp","gold_post_pct"))
    c=confirmation(d)
    pp=None if not has_post else float(sigmoid(logit(p)-.55*c))
    return {
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "event":event,"model":model_name,"features":f,
        "pre_release":{"probability_down":round(p,4),"probability_up":round(1-p,4),"assessment":label(p)},
        "post_release":{"confirmation_score":c,
          "probability_down":None if pp is None else round(pp,4),
          "probability_up":None if pp is None else round(1-pp,4),
          "assessment":None if pp is None else label(pp)},
        "rule":"Pre-release is a probability estimate, not a blind trade signal. Require post-release cross-market confirmation."
    }

def train(csv):
    df=pd.read_csv(csv).dropna(subset=FEATURES+["target_down"])
    if len(df)<30: raise ValueError("At least 30 clean historical events are required.")
    X=df[FEATURES].astype(float).values; y=df.target_down.astype(float).values
    mu=X.mean(0); sd=X.std(0); sd[sd<1e-9]=1
    Z=(X-mu)/sd; w=np.zeros(len(FEATURES)); b=0
    for _ in range(6000):
        p=sigmoid(Z@w+b)
        w-=.015*((Z.T@(p-y))/len(y)+.05*w); b-=.015*float(np.mean(p-y))
    coef=w/sd; intercept=float(b-np.sum(w*mu/sd))
    p=sigmoid(X@coef+intercept)
    return {"created_utc":datetime.now(timezone.utc).isoformat(),"n_events":len(df),
            "intercept":intercept,"coef":dict(zip(FEATURES,map(float,coef))),
            "training_accuracy":float(np.mean((p>=.5)==y)),
            "training_brier":float(np.mean((p-y)**2))}

def live():
    out={"retrieved_utc":datetime.now(timezone.utc).isoformat()}
    try:
        import yfinance as yf
        for name,ticker in [("gold","XAUUSD=X"),("dxy","DX-Y.NYB")]:
            x=yf.download(ticker,period="5d",interval="5m",progress=False,auto_adjust=False)
            if len(x):
                c=x["Close"]
                if getattr(c,"ndim",1)>1:c=c.iloc[:,0]
                c=pd.Series(c).dropna()
                out[name]={"last":float(c.iloc[-1])}
    except Exception as e: out["market_error"]=str(e)
    for name,sid in [("us2y","DGS2"),("us10y","DGS10"),("real10y","DFII10")]:
        try:
            u=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
            x=pd.read_csv(requests.get(u,timeout=15).text.splitlines() and __import__("io").StringIO(requests.get(u,timeout=15).text))
            x=x.dropna(); v=x.iloc[:,-1].astype(float)
            out[name]={"last":float(v.iloc[-1])}
            if len(v)>1:out[name]["change_bp_last_day"]=float((v.iloc[-1]-v.iloc[-2])*100)
        except Exception as e:out[name]={"error":str(e)}
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--analyze"); ap.add_argument("--history"); ap.add_argument("--model-out",default="xau_model.json")
    ap.add_argument("--json-out",default="xau_result.json"); ap.add_argument("--report-out",default="xau_report.txt")
    ap.add_argument("--live",action="store_true"); ap.add_argument("--train-only",action="store_true")
    a=ap.parse_args(); model=None
    if a.history:
        model=train(a.history); Path(a.model_out).write_text(json.dumps(model,indent=2))
        print(f"Model trained on {model['n_events']} events; accuracy={model['training_accuracy']:.3f}, Brier={model['training_brier']:.3f}")
    if a.live:
        s=live(); Path("live_snapshot.json").write_text(json.dumps(s,indent=2)); print(json.dumps(s,indent=2))
    if a.train_only:return
    if not a.analyze: print("Use --analyze sample_event.json"); return
    d=json.loads(Path(a.analyze).read_text()); r=analyze(d,model)
    Path(a.json_out).write_text(json.dumps(r,indent=2))
    pre=r["pre_release"]; post=r["post_release"]
    text=(f"XAUUSD NEWS PROBABILITY ENGINE V2\nEvent: {r['event']}\n\n"
          f"PRE-RELEASE DOWN: {pre['probability_down']:.1%}\n"
          f"PRE-RELEASE UP:   {pre['probability_up']:.1%}\nAssessment: {pre['assessment']}\n\n"
          f"POST CONFIRMATION SCORE: {post['confirmation_score']:+.0f}\n")
    if post["probability_down"] is not None:
        text+=f"POST DOWN: {post['probability_down']:.1%}\nPOST UP: {post['probability_up']:.1%}\nAssessment: {post['assessment']}\n"
    text+="\nPre-release: WAIT / do not blindly trade. Post-release: require DXY + Treasury yield + gold confirmation.\n"
    Path(a.report_out).write_text(text)
    print(text)

if __name__=="__main__": main()
