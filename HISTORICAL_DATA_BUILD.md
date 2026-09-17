# Historical data build

The intelligence model should be trained only on information that was actually available at the time of each release.

## Recommended provider
Trading Economics exposes U.S. economic-calendar data with actual, previous and consensus fields and documents point-in-time data for preserving what the calendar looked like on a historical date. CME FedWatch separately provides market-implied FOMC probabilities and historical data. Federal Reserve pages remain the authority for FOMC dates and official projections.

## Build
1. Copy `.env.example` to `.env`.
2. Add `TRADING_ECONOMICS_API_KEY` or a compatible `ECONOMIC_CALENDAR_URL`/key.
3. Run:

```bash
python historical_bootstrap.py --days 730 --interval 1h
```

This creates read-only files under `data_cache/historical/` for XAUUSD, DXY, U.S. 2Y, 10Y, real 10Y and the U.S. macro calendar.

## Important integrity rule
Do **not** train on today's revised consensus as if it were the consensus known before an old release. For serious calibration, use point-in-time calendar snapshots and timestamped FedWatch snapshots. Missing consensus stays missing; it is never filled with an estimate.

The resulting dataset can then be passed through `validate_dataset.py`, `event_study.py`, `macro_features.py`, `ensemble.py`, `magnitude_model.py`, and `calibrate.py` in chronological order.
