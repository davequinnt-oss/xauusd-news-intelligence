# Live data setup — iPhone/cloud deployment

The dashboard is analysis-only. It does not execute trades or connect to MT5.

## What was fixed

The live layer now prefers Trading Economics for:
- US economic calendar (actual, consensus/forecast, previous, importance)
- Gold/XAUUSD quote (`XAUUSD:CUR`)
- DXY quote (`DXY:IND`)

It falls back to Yahoo Finance for Gold/DXY when Trading Economics is not configured. Treasury yields remain on FRED.

Trading Economics documents calendar endpoints with actual, previous and consensus fields, and market endpoints for commodities/currencies. See the official API docs before obtaining credentials.

## Streamlit Community Cloud secrets

In your deployed app, open **Manage app → Settings → Secrets** and add:

```toml
TRADING_ECONOMICS_CLIENT = "YOUR_KEY:YOUR_SECRET"
TRADING_ECONOMICS_GOLD_SYMBOL = "XAUUSD:CUR"
TRADING_ECONOMICS_DXY_SYMBOL = "DXY:IND"
CALENDAR_DAYS_AHEAD = "45"
```

Do not put credentials into GitHub code or `.env` files committed to the repository.

## Optional CME FedWatch

If you have CME FedWatch API credentials, keep configuring those separately:

```toml
CME_FEDWATCH_API_URL = "YOUR_CME_ENDPOINT"
CME_FEDWATCH_API_KEY = "YOUR_CME_KEY"
```

## After saving secrets

1. Save the secrets in Streamlit.
2. Reboot/re-run the app.
3. Tap **Refresh live data**.
4. Provider health should show Trading Economics as configured.
5. XAUUSD and DXY should populate when the provider returns them.
6. The calendar should contain major USD events rather than only FOMC.

If a provider is unavailable, the dashboard will show MISSING instead of inventing a value.
