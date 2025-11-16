# =========================
# FILE: app.py (NOVA CLEAN BASE)
# =========================

import os
import re
import requests
import datetime
from datetime import datetime as dt
import pytz
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# ---------------- Streamlit Setup ----------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

# ---------------- OpenAI Client ----------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def nova_brain(prompt):
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            system="You are NOVA, a smart, friendly market and productivity assistant."
        )
        return response.output[0].content[0].text
    except Exception as e:
        return f"NOVA had a brain freeze: {e}"


# ---------------- Weather ----------------
def get_weather():
    try:
        key = st.secrets["weather"]["api_key"]
        city = "Boston"
        url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={city}&aqi=no"
        res = requests.get(url).json()

        temp_c = res["current"]["temp_c"]
        temp_f = (temp_c * 9/5) + 32
        condition = res["current"]["condition"]["text"]

        return f"{temp_f:.1f}°F • {condition}"
    except:
        return "Unavailable"


# ---------------- Macro Snapshot ----------------
def get_macro_snapshot():
    # Placeholder (avoid API calls for now)
    return "Inflation 3.1% | Unemployment 3.8% | Fed Funds 5.33%"


# ---------------- Stock Lookup ----------------
def get_stock_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            return None
        return hist
    except:
        return None


def basic_signal(df):
    # Extremely simple “signal”
    last = df["Close"].iloc[-1]
    prev = df["Close"].iloc[-5] if len(df) >= 5 else df["Close"].iloc[0]

    if last > prev:
        return "Bullish 📈"
    elif last < prev:
        return "Bearish 📉"
    return "Sideways ➖"


# ---------------- Header UI ----------------
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


# ---------------- Chat History ----------------
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------- User Input ----------------
user_input = st.chat_input("Ask NOVA anything…")

if user_input:
    # Store + display user message
    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    text = user_input.lower()

    # --------------------------------------
    # STOCK LOOKUP
    # --------------------------------------
    if any(k in text for k in ["stock", "price", "chart", "buy", "sell", "tsla", "aapl", "msft"]):

        # Find ticker symbols (simple regex)
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
                    with st.chat_message("assistant"):
                        st.warning(f"No stock data found for {tk}.")
                    continue

                df = data.reset_index()
                fig = px.line(df, x="Date", y="Close", title=f"{tk} (1-month)")
                st.plotly_chart(fig, use_container_width=True)

                sig = basic_signal(df)
                with st.chat_message("assistant"):
                    st.write(f"**Signal for {tk}: {sig}**")

            st.session_state.history.append({"role": "assistant", "content": "Stock analysis completed."})

    # --------------------------------------
    # DEFAULT NOVA RESPONSE
    # --------------------------------------
    else:
        reply = nova_brain(user_input)
        with st.chat_message("assistant"):
            st.write(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
