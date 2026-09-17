# Phase 4 — Event-Specific Ensemble

The next model architecture is now defined:

1. Causal feature engine
   - actual vs forecast
   - event-specific surprise z-score
   - previous comparison
   - inflation/labor pressure proxies

2. Event-family models
   - FOMC
   - CPI
   - PCE
   - NFP
   - LABOR
   - PPI
   - RETAIL
   - ISM
   - GDP
   - OTHER

3. Global model
   - provides a fallback when an event family has too few observations.

4. Ensemble
   - 60% event-family model + 40% global model when sufficient history exists.
   - global-only otherwise.

5. Future upgrade
   - add FedWatch expectation-shift features
   - add pre-release DXY / 2Y / real-yield / XAU structure
   - add magnitude model
   - add post-release confirmation model
   - calibrate probabilities before any execution use.

Do not interpret the ensemble as profitable until it has been tested on a genuinely
out-of-sample period with realistic timestamps and transaction costs.
