# =========================
# FILE: app.py (FINAL NOVA)
# =========================

import os
import re
import json
import requests
import datetime
from datetime import datetime as dt
import pytz
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# ------------- Internal Modules -------------
from analysis import compute_market_mood, decision_signal, get_finance_news
from report import generate_daily_report
from gmail_calendar import (
    list_recent_emails,
    search_emails,
    send_email,
    draft_email,
    list_events,
    create_meeting,
    find_next_free_slot
)

# Page config
st.set_page_config(
    page_title="NOVA 😊",
    page_icon="😊",
    layout="wide"
)

# ---------------- OPENAI SETUP ----------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def nova_brain(prompt, system="You are NOVA, a friendly market assistant. Be concise, smart, and helpful."):
    """
    NOVA's actual thinking brain using the Responses API.
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            system=system
        )
        return response.output[0].content[0].text
    except Exception as e:
        return f"NOVA had a brain freeze: {e}"


# ---------------- WEATHER ----------------
def get_weather():
    key = st.secrets["weather"]["api_key"]
    city = "Boston"
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={city}&aqi=no"
        res = requests.get(url).json()
        temp_c = res["current"]["temp_c"]
        temp_f = (temp_c * 9/5) + 32
        condition = res["current"]["condition"]["text"]
        return f"{temp_f:.1f}°F • {condition}"
    except:
        return "Unavailable"


# ---------------- MACRO DATA ----------------
def get_macro_snapshot():
    try:
        return "Inflation: 3.1% | Unemployment: 3.8% | Fed Funds: 5.33%"
    except:
        return "Unavailable"


# ---------------- STOCK LOOKUP ----------------
def get_stock_data(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            return None
        return hist
    except:
        return None


# ---------------- HEADER UI ----------------
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


# ---------------- CHAT HISTORY ----------------
if "history" not in st.session_state:
    st.session_state.history = []


# Display previous messages
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------- USER INPUT ----------------
user_input = st.chat_input("Ask NOVA anything…")

if user_input:
    # Display user message
    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    text = user_input.lower()

    # ---------------- STOCKS ----------------
    if any(k in text for k in ["stock", "price", "chart", "analyze"]):
        tickers = re.findall(r"\b[A-Z]{1,5}\b", user_input.upper())

        if not tickers:
            reply = "Tell me which ticker. Example: AAPL or MSFT."
        else:
            reply = f"Analyzing: {', '.join(tickers)}"
            with st.chat_message("assistant"):
                st.write(reply)

                for tk in tickers:
                    data = get_stock_data(tk)
                    if data is None:
                        st.warning(f"No data for {tk}.")
                        continue
                    
                    df = data.reset_index()
                    fig = px.line(df, x="Date", y="Close", title=f"{tk} (1 month)")
                    st.plotly_chart(fig, use_container_width=True)

                    sig = decision_signal(df.rename(columns={"Close": "close"}))
                    st.markdown(f"**Signal for {tk}: {sig}**")

        st.session_state.history.append({"role": "assistant", "content": reply})

    # ---------------- EMAILS ----------------
    elif "email" in text or "inbox" in text:
        emails = list_recent_emails(5)
        reply = f"Fetched {len(emails)} recent emails."
        with st.chat_message("assistant"):
            st.write(reply)
            st.json(emails)
        st.session_state.history.append({"role": "assistant", "content": reply})

    elif "search email" in text:
        query = user_input.split("search email", 1)[1].strip()
        emails = search_emails(query)
        reply = f"Found {len(emails)} emails matching: '{query}'."
        with st.chat_message("assistant"):
            st.write(reply)
            st.json(emails)
        st.session_state.history.append({"role": "assistant", "content": reply})

    elif "draft email" in text:
        parts = user_input.split("|")
        to = parts[1].strip()
        subject = parts[2].strip()
        body = parts[3].strip()
        draft_email(to, subject, body)
        reply = f"Draft created for {to}."
        with st.chat_message("assistant"):
            st.write(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    elif "send email" in text:
        parts = user_input.split("|")
        to = parts[1].strip()
        subject = parts[2].strip()
        body = parts[3].strip()
        send_email(to, subject, body)
        reply = f"Email sent to {to}."
        with st.chat_message("assistant"):
            st.write(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # ---------------- CALENDAR ----------------
    elif "calendar" in text or "schedule" in text:
        events = list_events(5)
        reply = f"You have {len(events)} upcoming events."
        with st.chat_message("assistant"):
            st.write(reply)
            st.json(events)
        st.session_state.history.append({"role": "assistant", "content": reply})

    elif "free time" in text or "availability" in text:
        slot = find_next_free_slot()
        reply = f"Your next free 30-minute slot starts at: **{slot}**"
        with st.chat_message("assistant"):
            st.write(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # ---------------- GENERAL CHAT ----------------
    else:
        reply = nova_brain(user_input)
        with st.chat_message("assistant"):
            st.write(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
