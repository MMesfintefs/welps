# =========================
# FILE: app.py
# =========================

import os
import requests
import datetime
import pytz
import streamlit as st
import yfinance as yf
from openai import OpenAI

# =========================
# Load API keys from Streamlit Secrets
# =========================
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
WEATHER_KEY = st.secrets.get("WEATHER_API_KEY", "")
FRED_KEY = st.secrets.get("FRED_API_KEY", "")

# =========================
# OpenAI Client (v1.0+)
# =========================
client = OpenAI(api_key=OPENAI_KEY)

# =========================
# Weather
# =========================
def get_weather():
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q=Boston&aqi=no"
        data = requests.get(url, timeout=8).json()
        if "error" in data:
            return "Weather unavailable"

        temp_c = data["current"]["temp_c"]
        temp_f = temp_c * 9/5 + 32
        cond = data["current"]["condition"]["text"]

        return f"Boston: {temp_f:.1f}°F, {cond}"
    except:
        return "Weather unavailable"

# =========================
# Macro Snapshot from FRED
# =========================
def fred_series(series_id):
    try:
        base = "https://api.stlouisfed.org/fred/series/observations"
        r = requests.get(base, params={
            "series_id": series_id,
            "api_key": FRED_KEY,
            "file_type": "json"
        })
        r.raise_for_status()
        return float(r.json()["observations"][-1]["value"])
    except:
        return None

def get_macro_snapshot():
    try:
        infl = fred_series("CPIAUCSL")
        unemp = fred_series("UNRATE")
        fed = fred_series("FEDFUNDS")

        return f"📊 Inflation: {infl:.1f} | Unemployment: {unemp:.1f}% | Fed Rate: {fed:.2f}%"
    except:
        return "Macro data unavailable"

# =========================
# Stock Lookup
# =========================
def get_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        price = info.get("regularMarketPrice")
        change = info.get("regularMarketChangePercent")

        if price is None:
            return None

        return {
            "price": price,
            "change": change,
            "name": info.get("shortName", ticker.upper()),
        }
    except:
        return None

# =========================
# Chat with OpenAI
# =========================
def ask_nova(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are NOVA, a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

st.markdown(
    "<h1 style='text-align: center;'>NOVA 😊</h1>"
    "<p style='text-align: center;'>Your self-directing agentic assistant — ready to act and analyze.</p>",
    unsafe_allow_html=True
)

# ===== Top Section (Weather | Macro | Time) =====
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦️ Weather")
    st.metric("Current", get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    st.metric("Status", "Live Data")
    st.markdown(get_macro_snapshot())

with col3:
    st.markdown("### 🕓 Time")
    now = datetime.datetime.now(pytz.timezone("America/New_York"))
    st.markdown(f"**{now.strftime('%A, %B %d, %Y %I:%M %p')}**")

st.divider()

# ===== Chat History =====
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===== User Input =====
user_text = st.chat_input("Ask NOVA anything (e.g. 'Show AAPL stock and Boston weather')")

if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # If user asks for stock
    words = user_text.upper().split()
    tickers = [w for w in words if len(w) <= 5 and w.isalpha()]

    if tickers:
        results = []
        for t in tickers:
            data = get_stock(t)
            if data:
                results.append(f"**{t}** → ${data['price']} ({data['change']}%)")
            else:
                results.append(f"No data found for {t}.")
        nova_reply = "\n".join(results)
    else:
        nova_reply = ask_nova(user_text)

    st.session_state.history.append({"role": "assistant", "content": nova_reply})

    with st.chat_message("assistant"):
        st.markdown(nova_reply)
