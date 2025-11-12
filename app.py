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

# -------------------- Weather Snapshot --------------------
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
        condition = res["current"]["condition"]["text"]
        return f"{city}: {temp_f:.1f}°F, {condition}"
    except Exception:
        return "⚠️ Weather unavailable"

# -------------------- Macro Snapshot --------------------
def get_macro_snapshot():
    fred_key = os.getenv("FRED_API_KEY")
    if not fred_key:
        return "No macro data (missing API key)"
    try:
        base = "https://api.stlouisfed.org/fred/series/observations"

        def fred_series(series_id):
            r = requests.get(
                base,
                params={
                    "series_id": series_id,
                    "api_key": fred_key,
                    "file_type": "json",
                },
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

# -------------------- Layout: Top 3 Columns --------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦️ Weather Snapshot")
    st.metric("Current", get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    st.metric("Status", "Fetching live data...")
    st.markdown(get_macro_snapshot())

with col3:
    boston_time = datetime.now(pytz.timezone("America/New_York"))
    now = boston_time.strftime("%A, %B %d, %Y %I:%M %p")
    st.markdown("### 🕓 Time")
    st.markdown(f"**{now}**")

st.divider()

# =========================
# CHAT INTERFACE SECTION
# =========================

# Header
st.markdown(
    "<h1 style='text-align:center;'>NOVA 😊</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;'>Your self-directing agentic assistant — ready to act and analyze.</p>",
    unsafe_allow_html=True,
)

# Initialize chat memory
if "history" not in st.session_state:
    st.session_state.history = []

# Display previous messages
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input field
user_text = st.chat_input(
    "Ask NOVA anything (e.g. 'What's Tesla's stock and Boston's weather?')"
)

# AI response function
def nova_brain(prompt):
    system_prompt = """You are NOVA 😊 — a smart, friendly assistant built for live insights.
    You answer about markets, weather, data, or macro info clearly and briefly."""
    try:
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
        else:
            return f"⚠️ Unexpected error: {err}"

# Handle input
if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("NOVA is thinking..."):
            reply = nova_brain(user_text)
        st.markdown(reply)

    st.session_state.history.append({"role": "assistant", "content": reply})
