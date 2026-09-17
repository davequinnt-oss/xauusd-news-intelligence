from __future__ import annotations
import json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

from data_sources import market_snapshot, cme_fedwatch_snapshot, economic_calendar, upcoming_fomc, save_pre_release_snapshot, provider_health
from xau_news_engine_v2 import analyze

st.set_page_config(page_title="XAUUSD News Intelligence", page_icon="📊", layout="wide")
st.title("XAUUSD News Intelligence")
st.caption("Analysis-only decision support — no trade execution, no MT5.")

with st.sidebar:
    st.header("Live controls")
    refresh = st.button("↻ Refresh live data", use_container_width=True)
    event_name = st.text_input("Focus event", "FOMC")
    st.caption("Market data are read-only. Provider availability is shown on the dashboard.")

if refresh or "snapshot" not in st.session_state:
    with st.spinner("Refreshing market and event data…"):
        st.session_state.snapshot = market_snapshot()
        st.session_state.fedwatch = cme_fedwatch_snapshot()
        st.session_state.calendar = economic_calendar()
        st.session_state.fomc = upcoming_fomc()

m = st.session_state.snapshot
fw = st.session_state.fedwatch
cal = st.session_state.calendar
fomc = st.session_state.fomc

# ---------- Top status ----------
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("XAUUSD", "—" if m.xauusd is None else f"{m.xauusd:,.2f}")
c2.metric("DXY", "—" if m.dxy is None else f"{m.dxy:,.2f}")
c3.metric("US 2Y", "—" if m.us2y is None else f"{m.us2y:.2f}%")
c4.metric("US 10Y", "—" if m.us10y is None else f"{m.us10y:.2f}%")
c5.metric("US Real 10Y", "—" if m.real10y is None else f"{m.real10y:.2f}%")

st.caption(f"Market snapshot: {m.timestamp_utc}. FRED yield series can be delayed/daily; provider timestamps and status are shown below.")
st.caption("Live quote sources: " + ", ".join(f"{k}={v}" for k,v in m.source_detail.items()))

with st.expander("Provider health", expanded=False):
    st.json(provider_health(), expanded=False)

# ---------- Upcoming events ----------
st.subheader("Upcoming major events")
if not cal.empty:
    display_cal = cal.copy()
    # Keep the dashboard focused on USD events that can materially affect gold.
    if "country" in display_cal.columns:
        display_cal = display_cal[display_cal["country"].astype(str).str.upper().isin(["USD", "US", "UNITED STATES"])].copy()
else:
    display_cal = pd.DataFrame()
if not fomc.empty:
    display_cal = pd.concat([display_cal, fomc], ignore_index=True).drop_duplicates(subset=["date","event"], keep="first")
if display_cal.empty:
    st.warning("No economic-calendar provider is configured. The dashboard is using the official FOMC schedule as its calendar floor when available.")
else:
    st.dataframe(display_cal.head(20), use_container_width=True, hide_index=True)
    try:
        upcoming = pd.to_datetime(display_cal["date"] + " " + display_cal["time"].fillna("00:00"), utc=True, errors="coerce")
        future = display_cal.loc[upcoming >= pd.Timestamp.now(tz="UTC")].copy()
        if not future.empty:
            idx = future.index[0]
            event_dt = upcoming.loc[idx]
            remaining = event_dt - pd.Timestamp.now(tz="UTC")
            st.info(f"Next scheduled event: **{future.loc[idx, 'event']}** — {event_dt.isoformat()} — countdown: **{remaining}**")
    except Exception:
        pass

# ---------- Pre-release snapshot ----------
st.subheader("Pre-release snapshot")
st.write("Capture this before a major release so the model can separate information known beforehand from the subsequent market reaction.")
if st.button("Save current pre-release snapshot", use_container_width=False):
    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "event": event_name,
        "market": m.__dict__,
        "fedwatch": fw,
        "calendar": display_cal.to_dict(orient="records") if not display_cal.empty else [],
    }
    path = save_pre_release_snapshot(event_name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), payload)
    st.success(f"Snapshot saved: {path.name}")

# ---------- FedWatch ----------
st.subheader("Fed expectations")
if fw.get("available"):
    st.success("CME FedWatch connection: available")
    st.json(fw.get("data"), expanded=False)
else:
    st.warning("CME FedWatch is not connected. Configure CME_FEDWATCH_API_URL and CME_FEDWATCH_API_KEY in .env. Do not invent missing probabilities.")

# ---------- Analysis inputs ----------
st.subheader("Event intelligence")
left, right = st.columns(2)
with left:
    event = st.text_input("Event", event_name, key="analysis_event")
    actual_text = st.text_input("Actual (leave blank before release)", "")
    forecast_text = st.text_input("Forecast / consensus", "")
    previous_text = st.text_input("Previous", "")
    unit = st.text_input("Unit", "rate")
with right:
    use_manual_probability = st.checkbox("Override probability manually", value=False)
    manual_p_down = st.slider("Manual XAUUSD DOWN probability", 0.0, 1.0, 0.50, 0.01, disabled=not use_manual_probability)
    magnitude = st.number_input("Expected absolute XAUUSD move (%)", min_value=0.0, value=0.0, step=0.01)
    fed_shift = st.number_input("Fed expected-rate shift (bp)", value=0.0, step=1.0)

def _num(text):
    try:
        return float(text)
    except Exception:
        return None

actual = _num(actual_text)
forecast = _num(forecast_text)
previous = _num(previous_text)
model_input = {"event": event, "actual": actual, "forecast": forecast, "previous": previous, "rate_surprise_bp": fed_shift}
if use_manual_probability:
    p_down = manual_p_down
    model_name = "manual override"
else:
    model_result = analyze(model_input)
    p_down = model_result["pre_release"]["probability_down"]
    model_name = model_result["model"]

surprise = None if actual is None or forecast is None else actual - forecast
direction = "BEARISH" if p_down >= 0.60 else "BULLISH" if p_down <= 0.40 else "MIXED"
confidence = abs(p_down - 0.5) * 2

c1,c2,c3,c4=st.columns(4)
c1.metric("XAUUSD DOWN",f"{p_down:.0%}")
c2.metric("XAUUSD UP",f"{1-p_down:.0%}")
c3.metric("Expected move",f"{magnitude:.2f}%")
c4.metric("Assessment",direction)

actual_display = "—" if actual is None else f"{actual:g}"
forecast_display = "—" if forecast is None else f"{forecast:g}"
previous_display = "—" if previous is None else f"{previous:g}"
surprise_display = "—" if surprise is None else f"{surprise:+g}"
st.markdown(f"**{event}** — Actual `{actual_display}` | Forecast `{forecast_display}` | Previous `{previous_display}` | Unit `{unit}`")
st.write(f"Raw surprise: **{surprise_display}**")
st.caption(f"Probability source: **{model_name}**. Until a walk-forward calibrated historical model is trained, treat the probability as an initial estimate rather than a validated forecast.")

st.subheader("Cross-market confirmation")
rows = [
    ("DXY", m.dxy, "USD strength/weakness should agree with the macro interpretation."),
    ("US 2Y", m.us2y, "Short-rate repricing is a key policy-path check."),
    ("US real 10Y", m.real10y, "Real-yield direction is an important gold confirmation variable."),
    ("XAUUSD", m.xauusd, "Gold should confirm rather than contradict the initial interpretation."),
]
for name,value,desc in rows:
    status = "AVAILABLE" if value is not None else "MISSING"
    st.write(f"**{name}:** {value if value is not None else '—'} — `{status}` — {desc}")

st.subheader("Scenarios")
a,b,c=st.columns(3)
with a:
    st.markdown("### Bearish gold")
    st.write("Hawkish surprise → USD/yields rise → real yields strengthen → gold weakens or fails to reclaim structure.")
with b:
    st.markdown("### Bullish gold")
    st.write("Dovish surprise → USD/yields fall → real yields weaken → gold strengthens or reclaims structure.")
with c:
    st.markdown("### Mixed / whipsaw")
    st.write("Headline is close to expectations or cross-market signals disagree; the first move can reverse.")

st.subheader("What would invalidate the initial interpretation?")
st.markdown("""
- DXY reverses sharply against the initial macro interpretation.
- Treasury yields reverse the initial policy repricing.
- Real yields contradict the rate interpretation.
- XAUUSD immediately contradicts the cross-market signal.
- For FOMC events, the statement, projections, or press conference changes the policy interpretation.
""")

st.subheader("Data quality")
quality = pd.DataFrame([
    ["XAUUSD", m.xauusd is not None, "Yahoo Finance market quote"],
    ["DXY", m.dxy is not None, "Yahoo Finance market quote"],
    ["US 2Y", m.us2y is not None, "FRED DGS2"],
    ["US 10Y", m.us10y is not None, "FRED DGS10"],
    ["US real 10Y", m.real10y is not None, "FRED DFII10"],
    ["FedWatch", fw.get("available", False), "CME FedWatch API"],
    ["Economic calendar", not cal.empty, "Configured calendar provider"],
], columns=["Input","Available","Source"])
st.dataframe(quality, use_container_width=True, hide_index=True)

if not all(quality["Available"]):
    st.warning("One or more inputs are missing. Treat any model assessment as incomplete rather than filling missing values with guesses.")

st.subheader("Final intelligence")
if confidence >= .4 and magnitude >= .10:
    significance="Meaningful model separation, subject to confirmation"
elif confidence >= .2:
    significance="Moderate / mixed conviction"
else:
    significance="Low directional separation"
st.markdown(f"**Current assessment:** {direction}")
st.markdown(f"**Probability estimate:** {p_down:.0%} down / {(1-p_down):.0%} up")
st.markdown(f"**Expected magnitude estimate:** {magnitude:.2f}%")
st.markdown(f"**Assessment quality:** {significance}")
st.markdown("**This dashboard informs your decision; it does not place trades or issue broker orders.**")

st.divider()
st.caption("Provider notes: CME documents FedWatch as a JSON REST API derived from 30-Day Fed Funds futures. FRED provides API access to economic series. Official FOMC dates are sourced from the Federal Reserve calendar. Current provider availability depends on credentials, licensing and network access.")
