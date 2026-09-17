# XAUUSD NEWS INTELLIGENCE ENGINE — FINAL ANALYSIS BUILD

## Purpose

This project is an analysis-only system for XAUUSD around major economic events.

It does NOT:
- place trades
- connect to MT5
- manage positions
- generate broker orders

It DOES:
- compare actual vs consensus
- model event-specific surprise
- incorporate Fed/FedWatch expectations
- incorporate FOMC SEP/Dot Plot information
- analyze DXY, Treasury yields and real yields
- estimate XAUUSD direction
- estimate expected move magnitude
- create bullish/bearish/mixed scenarios
- identify confirmation and invalidation conditions
- evaluate whipsaw risk
- produce a human-readable intelligence report
- support chronological walk-forward validation

## iPhone use

The included Streamlit app is designed as the user-facing dashboard. It can be deployed to a cloud Streamlit host or another Python hosting service and opened from an iPhone browser.

## Data integrity

The most important requirement is genuine historical data:
- original release timestamp
- original consensus/forecast available BEFORE release
- actual release value
- previous value
- historical FedWatch snapshot
- timestamped XAUUSD/DXY/yield prices

Do not fabricate missing consensus values.

## Research standard

A high probability is not proof of a profitable trade. The model must be evaluated chronologically on unseen events and should include realistic spread, slippage and latency in any performance interpretation.

## Main files

app.py
xau_news_engine_v2.py
macro_features.py
ensemble.py
fedwatch_features.py
merge_fedwatch.py
dotplot_features.py
magnitude_model.py
signal_filter.py
cost_stress.py
event_study.py
calibrate.py
validate_dataset.py
intelligence_report.py
scenario_engine.py

## Final output philosophy

The engine should answer:
1. What is priced in?
2. What is the surprise?
3. What does it mean for the Fed/rates/USD?
4. What does that imply for gold?
5. How large might the reaction be?
6. What confirms it?
7. What invalidates it?
8. Is the environment likely directional or whipsaw-prone?

The human makes the final decision.
