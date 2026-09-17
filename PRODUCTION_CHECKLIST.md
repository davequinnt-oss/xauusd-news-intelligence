# Production checklist

## Phase A — historical research
- [x] Official FOMC event dates
- [x] Treasury/real-yield market fields
- [x] Gold/DXY reaction labels
- [x] Walk-forward validator
- [ ] Historical consensus/actual dataset
- [ ] CME FedWatch historical probabilities
- [ ] CPI/PCE/NFP/PPI/claims event history
- [ ] Event-time intraday data

## Phase B — probability calibration
- [ ] Chronological train/validation/test split
- [ ] Brier score
- [ ] reliability curve
- [ ] calibration intercept/slope
- [ ] event-specific models
- [ ] probability of magnitude
- [ ] probability of persistence/reversal

## Phase C — live engine
- [ ] Economic calendar provider
- [ ] CME FedWatch API credentials
- [ ] live Treasury feed
- [ ] live DXY/XAUUSD feed
- [ ] automatic pre-event snapshot
- [ ] automatic post-event snapshot
- [ ] alert engine

## Phase D — iPhone
- [x] Streamlit dashboard foundation
- [ ] cloud deployment
- [ ] password protection
- [ ] push notifications
- [ ] mobile layout

## Phase E — trading integration
Only after extensive out-of-sample validation:
- [ ] signal gating
- [ ] position sizing
- [ ] max daily loss
- [ ] max event risk
- [ ] kill switch
- [ ] MT5 bridge

No probability output should be treated as guaranteed direction.
