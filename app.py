# =========================
# FILE: app.py
# =========================

import os
import re
import requests
from datetime import datetime
import pytz
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# -------------------- imports from your modules --------------------
from analysis import compute_market_mood, decision_signal, get_finance_news
from report import generate_daily_report

# -------------------- page setup --------------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

# -------------------- OpenAI brain --------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =====================================================
#                 WEATHER + MACRO SNAPSHOTS
# =====================================================
def get_weather():
    key = os.getenv("WEATHER_API_KEY")
    city = "Boston"
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={city}&aqi=no"
        res = requests.get(url, timeout=10).json()
        if "error" in res:
            return "⚠️ Weather unavailable"
        temp_c = res["current"]["temp_c"]
        temp_f = (temp_c * 9 / 5) + 32
        cond = res["current"]["condition"]["text"]
        return f"{city}: {temp_f:.1f}°F, {cond}"
    except Exception:
        return "⚠️ Weather unavailable"

def get_macro_snapshot():
    fred_key = os.getenv("FRED_API_KEY")
    if not fred_key:
        return "No macro data (missing API key)"
    try:
        base = "https://api.stlouisfed.org/fred/series/observations"

        def fred_series(series_id):
            r = requests.get(
                base,
                params={"series_id": series_id, "api_key": fred_key, "file_type": "json"},
                timeout=10,
            )
            r.raise_for_status()
            return float(r.json()["observations"][-1]["value"])

        inflation = fred_series("CPIAUCSL")
        unemp = fred_series("UNRATE")
        fed = fred_series("FEDFUNDS")
        return f"📊 Inflation: {inflation:.1f} | Unemployment: {unemp:.1f}% | Fed Rate: {fed:.2f}%"
    except Exception:
        return "Macro data unavailable"

# =====================================================
#                 STOCK DATA (Yahoo Finance)
# =====================================================
def get_stock_data(ticker: str, period: str = "1mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return None
        price = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else price
        pct = (price - prev) / prev * 100 if prev else 0
        return {
            "ticker": ticker.upper(),
            "price": round(price, 2),
            "pct": round(pct, 2),
            "history": hist.reset_index()[["Date", "Close"]],
        }
    except Exception:
        return None

# =====================================================
#                 NOVA'S BRAIN / ROUTER
# =====================================================
def nova_brain(prompt):
    system_prompt = """You are NOVA 😊 — a smart, concise assistant who answers questions about weather, stocks, or macroeconomics.
    You call external tools when relevant instead of guessing data."""
    try:
        # detect user intent
        text = prompt.lower()

        # --- Weather ---
        if "weather" in text or "temperature" in text:
            return f"🌦️ {get_weather()}"

        # --- Stock info ---
        tickers = re.findall(r"\b[A-Z]{1,5}\b", prompt.upper())
        if "stock" in text or tickers:
            if not tickers:
                return "Please specify a ticker symbol (e.g., AAPL, TSLA, MSFT)."
            out = []
            for t in tickers:
                data = get_stock_data(t)
                if data:
                    df = pd.DataFrame(data["history"])
                    fig = px.line(df, x="Date", y="Close", title=f"{t} Price History")
                    st.plotly_chart(fig, use_container_width=True)
                    out.append(f"{t}: ${data['price']} ({data['pct']}%)")
                else:
                    out.append(f"No data found for {t}.")
            return " | ".join(out)

        # --- Macro snapshot ---
        if "macro" in text or "economy" in text or "inflation" in text:
            return get_macro_snapshot()

        # --- Default: Chat with model ---
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    except Exception as e:
        err = str(e)
        if "insufficient_quota" in err or "rate_limit" in err:
            return "⚠️ OpenAI quota limit reached or rate-limited. Please try again later."
        return f"⚠️ Unexpected error: {err}"

# =====================================================
#                   PAGE LAYOUT
# =====================================================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦️ ")
    st.metric("Current", get_weather())

with col2:
    st.markdown("### 📊 ")
    st.markdown(get_macro_snapshot())

with col3:
    boston_time = datetime.now(pytz.timezone("America/New_York"))
    now = boston_time.strftime("%A, %B %d, %Y %I:%M %p")
    st.markdown("### 🕓 Time")
    st.markdown(f"**{now}**")

st.divider()

# =====================================================
#                   NOVA CHAT INTERFACE
# =====================================================
st.markdown(
    "<h1 style='text-align:center;'>NOVA 😊</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;'></p>",
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

# display history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# input
user_text = st.chat_input("Ask NOVA anything (e.g. 'What's Tesla's stock and Boston's weather?')")

if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("NOVA is thinking..."):
            reply = nova_brain(user_text)
        st.markdown(reply)

    st.session_state.history.append({"role": "assistant", "content": reply})
