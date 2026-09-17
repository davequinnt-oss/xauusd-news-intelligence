# Phase 3 — Macro Event + Reaction Layer

The engine now has a clean place for real historical macro releases and reaction labels.

IMPORTANT:
- Do not fill consensus/forecast fields with guesses.
- Import them from a trustworthy economic-calendar dataset/provider.
- Keep release timestamps in UTC.
- Labels are computed separately from pre-release features to reduce leakage.

The recommended pipeline is:

calendar data
  -> macro_events.csv
  -> event_study.py
  -> reaction labels
  -> validate_dataset.py
  -> walk-forward/calibration
  -> event-specific models
  -> ensemble/meta-model

FedWatch remains a separate expectation stream. CME states that FedWatch probabilities
are implied by 30-Day Fed Funds futures and its API provides historical data for
backtesting. See the official CME documentation before connecting credentials.
