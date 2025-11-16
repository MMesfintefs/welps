# =========================
# FILE: app.py (NOVA+Gmail/Calendar Ready)
# =========================

import os
import re
import requests
import pytz
import datetime
from datetime import datetime as dt

import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

from openai import OpenAI
from gmail_calendar import (
    ensure_google_login,
    read_latest_emails,
    get_upcoming_events
)

# -------------------- Page Setup --------------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

# -------------------- OpenAI Client --------------------
client = OpenAI()  # Automatically uses OPENAI_API_KEY from Streamlit secrets

def nova_brain(prompt):
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            system="You are NOVA, a friendly, intelligent finance and productivity assistant.",
            input=prompt
        )
        return response.output_text
    except Exception as e:
        return f"NOVA malfunctioned: {e}"


# -------------------- Weather --------------------
def get_weather():
    try:
        key = st.secrets["weather"]["api_key"]
        city = "Boston"
        url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={city}&aqi=no"

        res = requests.get(url, timeout=10).json()
        temp_c = res["current"]["temp_c"]
        temp_f = (temp_c * 9/5) + 32
        condition = res["current"]["condition"]["text"]

        return f"{temp_f:.1f}°F • {condition}"
    except:
        return "Unavailable"


# -------------------- Macro Snapshot --------------------
def get_macro_snapshot():
    return "Inflation 3.1% • Unemployment 3.8% • Fed Funds 5.33%"


# -------------------- Stock Lookup --------------------
def get_stock_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        return hist if not hist.empty else None
    except:
        return None


def basic_signal(df):
    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[0]
    if last > prev:
        return "Bullish 📈"
    elif last < prev:
        return "Bearish 📉"
    return "Neutral ➖"


# -------------------- Layout Header --------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦 Weather")
    st.metric("Boston", get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    st.write(get_macro_snapshot())

with col3:
    now = dt.now(pytz.timezone("America/New_York"))
    st.markdown("### 🕓 Time (Boston)")
    st.write(now.strftime("%A, %B %d, %Y %I:%M %p"))

st.divider()


# -------------------- Google Login --------------------
st.markdown("#### 🔐 Google Services")
tokens = ensure_google_login()

st.divider()


# -------------------- Chat History --------------------
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# -------------------- Chat Input --------------------
user_input = st.chat_input("Ask NOVA anything…")

if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    lower = user_input.lower()

    # -------------------- STOCK MODE --------------------
    if any(word in lower for word in ["stock", "price", "chart", "tsla", "aapl", "nvda", "msft"]):

        tickers = re.findall(r"\b[A-Z]{1,5}\b", user_input.upper())

        if not tickers:
            reply = "Tell me the ticker you want: for example AAPL or TSLA."
            with st.chat_message("assistant"):
                st.write(reply)
            st.session_state.history.append({"role": "assistant", "content": reply})

        else:
            for tk in tickers:
                data = get_stock_data(tk)
                if data is None:
                    st.warning(f"No data found for {tk}.")
                    continue

                df = data.reset_index()

                fig = px.line(df, x="Date", y="Close", title=f"{tk} • 1-Month Chart")
                st.plotly_chart(fig, use_container_width=True)

                sig = basic_signal(df)
                st.write(f"**Signal for {tk}: {sig}**")

            st.session_state.history.append({"role": "assistant", "content": "Stock analysis finished."})

    # -------------------- EMAIL MODE --------------------
    elif "email" in lower or "inbox" in lower:
        if not tokens:
            reply = "You must log in with Google first."
        else:
            emails = read_latest_emails()
            reply = "**📨 Latest Emails:**\n" + "\n".join(f"- {e}" for e in emails)

        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # -------------------- CALENDAR MODE --------------------
    elif "calendar" in lower or "event" in lower or "schedule" in lower:
        if not tokens:
            reply = "You must log in with Google first."
        else:
            events = get_upcoming_events()
            reply = "**📆 Upcoming Events:**\n" + "\n".join(f"- {e}" for e in events)

        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # -------------------- DEFAULT NOVA RESPONSE --------------------
    else:
        reply = nova_brain(user_input)

        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state.history.append({"role": "assistant", "content": reply})
