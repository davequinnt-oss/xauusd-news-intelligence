# Phase 6 — XAUUSD Reaction Magnitude + Trade Filter

Added:
1. Causal magnitude model
   - predicts absolute XAUUSD move after a release
   - uses log-transformed absolute returns
   - walk-forward fitting

2. Conservative signal layer
   - combines directional probability and predicted move
   - emits NO_TRADE when either confidence or expected movement is weak

3. Cost stress testing
   - applies configurable transaction-cost assumptions
   - reports gross/net proxy and percentage positive after cost

The next model should use:
direction probability + magnitude probability + confirmation after release.

Do not convert these outputs into live orders until the historical model has
passed chronological out-of-sample validation including realistic spread,
slippage, latency and missed fills.
