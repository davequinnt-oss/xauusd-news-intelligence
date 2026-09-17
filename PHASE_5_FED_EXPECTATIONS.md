# Phase 5 — Fed Expectations Engine

The engine now has a dedicated layer for market-implied Fed expectations.

Core concept:
- The headline FOMC decision is only one input.
- The model measures the expected target rate before the meeting and how that
  expectation changes over time.
- It can incorporate the 1-day, 1-week, 1-month and immediately preceding snapshot.
- SEP/Dot Plot changes are kept separate because they represent FOMC participants'
  projections rather than market-implied probabilities.

CME describes FedWatch as using 30-Day Fed Funds futures and provides current and
historical probabilities. Its API also offers extended history for backtesting.

For an FOMC release:
pre-event expectations
        +
actual decision
        +
SEP / Dot Plot shift
        +
statement / press-conference information
        =
policy surprise representation

That representation will feed the XAUUSD ensemble.

IMPORTANT:
- Historical consensus data must come from an actual historical source.
- Missing FedWatch snapshots are not filled by interpolation.
- No post-release FedWatch snapshot may be used as a pre-release feature.
