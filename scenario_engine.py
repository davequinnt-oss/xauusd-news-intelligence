#!/usr/bin/env python3
"""Create structured pre-news scenarios from model inputs.

This layer does not choose a trade. It explains what combinations of outcomes
would support each market interpretation.
"""

import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--event",required=True)
    p.add_argument("--p-down",type=float,required=True)
    p.add_argument("--expected-move",type=float,default=None)
    p.add_argument("--fed-shift-bp",type=float,default=None)
    p.add_argument("--out",default="scenario.json")
    a=p.parse_args()

    pd=a.p_down
    if pd>=.65:
        base="bearish"
    elif pd<=.35:
        base="bullish"
    else:
        base="mixed"

    data={
      "event":a.event,
      "p_down":pd,
      "p_up":1-pd,
      "predicted_abs_move_pct":a.expected_move,
      "base_assessment":base,
      "drivers":[],
      "scenarios":{
        "bearish":"Actual/communication is more hawkish than priced in, while DXY and Treasury yields rise and gold fails to reclaim key pre-event structure.",
        "bullish":"Actual/communication is more dovish than priced in, while DXY and Treasury yields fall and gold holds/reclaims key structure.",
        "mixed":"Headline result is close to expectations or cross-market confirmation disagrees; two-way volatility and reversal risk remain elevated."
      },
      "invalidation":[
        "A strong reversal in DXY or Treasury yields against the initial interpretation.",
        "Gold reclaiming/breaking the pre-event structure that supported the initial scenario.",
        "A later part of the release (statement, projections or press conference) materially changing the policy interpretation."
      ],
      "confirmation":{
        "required_for_high_confidence":"DXY, yields and XAUUSD should point in the same direction.",
        "fed_path":"Use FedWatch/SEP changes as context rather than treating the headline decision alone as the signal."
      },
      "whipsaw_risk":"High around releases until cross-market confirmation develops."
    }
    if a.fed_shift_bp is not None:
        data["drivers"].append(f"Fed expected-rate shift: {a.fed_shift_bp:+.1f} bp")
    data["drivers"].append(f"Model pre-news DOWN probability: {pd:.1%}")
    if a.expected_move is not None:
        data["drivers"].append(f"Predicted absolute move: {a.expected_move:.3f}%")
    Path(a.out).write_text(json.dumps(data,indent=2))
    print(f"Saved: {a.out}")

if __name__=="__main__":
    main()
