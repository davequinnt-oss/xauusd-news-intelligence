#!/usr/bin/env python3
"""Generate a human-readable XAUUSD macro intelligence report.

This is an analysis/reporting layer only. It does not place trades or connect to
an execution platform.
"""

import argparse, json, math
from pathlib import Path

def pct(x):
    return f"{x*100:.1f}%"

def bias_label(p):
    if p >= .70: return "Strong bearish"
    if p >= .60: return "Moderately bearish"
    if p <= .30: return "Strong bullish"
    if p <= .40: return "Moderately bullish"
    return "Neutral / mixed"

def direction_from_sign(x, positive="bullish", negative="bearish"):
    if x is None: return "Unknown"
    return positive if x>0 else negative if x<0 else "Neutral"

def build(d):
    p=float(d.get("p_down", d.get("probability_down", .5)))
    p=max(0,min(1,p))
    mag=d.get("predicted_abs_move_pct")
    mag_txt="Not available" if mag is None else f"{float(mag):.3f}%"
    lines=[]
    lines.append("XAUUSD NEWS INTELLIGENCE REPORT")
    lines.append("="*36)
    lines.append(f"Directional assessment: {bias_label(p)}")
    lines.append(f"Probability XAUUSD DOWN: {pct(p)}")
    lines.append(f"Probability XAUUSD UP:   {pct(1-p)}")
    lines.append(f"Expected absolute move: {mag_txt}")
    lines.append("")
    lines.append("WHAT IS DRIVING THE OUTLOOK")
    lines.append("-"*28)
    drivers=d.get("drivers",[])
    for x in drivers: lines.append(f"- {x}")
    if not drivers: lines.append("- Driver breakdown not supplied.")
    lines.append("")
    lines.append("MARKET CONFIRMATION")
    lines.append("-"*22)
    confirms=d.get("confirmation",{})
    for k,v in confirms.items():
        lines.append(f"- {k}: {v}")
    if not confirms: lines.append("- No post-release confirmation supplied.")
    lines.append("")
    lines.append("SCENARIOS")
    lines.append("-"*9)
    for name,desc in d.get("scenarios",{}).items():
        lines.append(f"{name.upper()}: {desc}")
    lines.append("")
    lines.append("INVALIDATION / WHAT TO WATCH")
    lines.append("-"*28)
    for x in d.get("invalidation",[]): lines.append(f"- {x}")
    lines.append("")
    lines.append("EVENT RISK")
    lines.append("-"*10)
    lines.append(f"Whipsaw risk: {d.get('whipsaw_risk','Not assessed')}")
    lines.append(f"Volatility regime: {d.get('volatility_regime','Not assessed')}")
    lines.append("")
    lines.append("IMPORTANT")
    lines.append("This report is an analytical decision-support output, not a trade instruction.")
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("json")
    p.add_argument("--out",default="xau_intelligence_report.txt")
    a=p.parse_args()
    d=json.loads(Path(a.json).read_text())
    text=build(d)
    Path(a.out).write_text(text)
    print(text)
    print(f"\nSaved: {a.out}")

if __name__=="__main__":
    main()
