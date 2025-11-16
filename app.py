# =========================
# FILE: app.py
# A stable, minimal version of NOVA
# =========================

import os
import requests
import datetime
import pytz
import streamlit as st
import yfinance as yf

# =========================
# Load Streamlit Secrets
# =========================
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
WEATHER_KEY = st.secrets.get("WEATHER_API_KEY", "")
FRED_KEY = st.secrets.get("FRED_API_KEY", "")

# =========================
# OpenAI REST Call (NO SDK)
# =========================
def ask_nova(prompt):
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are NOVA, an intelligent assistant."},
                {"role": "user", "content": prompt}
            ]
        }
        r = requests.post(url, json=data, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error contacting NOVA: {e}"

# =========================
# Weather
# =========================
def get_weather():
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q=Boston&aqi=no"
        r = requests.get(url, timeout=10).json()

        if "current" not in r:
            return "Unavailable"

        temp_c = r["current"]["temp_c"]
        cond = r["current"]["condition"]["text"]
        temp_f = temp_c * 9/5 + 32

        return f"{temp_f:.1f}°F, {cond}"
    except:
        return "Unavailable"

# =========================
# FRED Macro Data
# =========================
def fred(series):
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        r = requests.get(url, params={
            "series_id": series,
            "api_key": FRED_KEY,
            "file_type": "json"
        })
        val = float(r.json()["observations"][-1]["value"])
        return val
    except:
        return None

def macro_snapshot():
    try:
        infl = fred("CPIAUCSL")
        unemp = fred("UNRATE")
        fed = fred("FEDFUNDS")
        return f"Inflation: {infl:.1f} | Unemployment: {unemp:.1f}% | Fed Rate: {fed:.2f}%"
    except:
        return "Unavailable"

# =========================
# Stocks
# =========================
def get_stock(tic):
    try:
        s = yf.Ticker(tic)
        price = s.info.get("regularMarketPrice")
        change = s.info.get("regularMarketChangePercent")
        if price is None:
            return None
        return f"{tic.upper()}: ${price} ({change}%)"
    except:
        return None

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="NOVA", page_icon="✨", layout="wide")

st.title("NOVA ✨")
st.write("Your lightweight agentic assistant (stable mode).")

# Top Info
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🌤 Weather")
    st.write(get_weather())

with col2:
    st.subheader("📊 Macro Snapshot")
    st.write(macro_snapshot())

with col3:
    st.subheader("⏰ Time")
    now = datetime.datetime.now(pytz.timezone("America/New_York"))
    st.write(now.strftime("%A, %B %d — %I:%M %p"))

st.divider()

# Chat history
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
q = st.chat_input("Ask Nova anything...")

if q:
    st.session_state.history.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.write(q)

    # detect stock tickers
    words = q.upper().split()
    tickers = [w for w in words if w.isalpha() and len(w) <= 5]

    if tickers:
        reply_lines = []
        for t in tickers:
            data = get_stock(t)
            reply_lines.append(data if data else f"No data for {t}")
        reply = "\n".join(reply_lines)
    else:
        reply = ask_nova(q)

    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
