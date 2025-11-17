# ===============================
# NOVA — Simple, Stable Version
# ===============================

import os
import re
import requests
import datetime as dt
import streamlit as st
import yfinance as yf

from gmail_calendar import read_last_5_emails, get_calendar_events


# ---------------------------------------------------
# OPENAI SETUP (Safe)
# ---------------------------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()
client = None

def get_openai_client():
    global client
    if client:
        return client
    if not OPENAI_KEY:
        return None
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    from openai import OpenAI
    try:
        client = OpenAI()  # NO proxies, NO custom http client
        return client
    except Exception as e:
        st.error(f"OpenAI init error: {e}")
        return None


# ---------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------
st.set_page_config(
    page_title="NOVA",
    page_icon="✨",
    layout="wide"
)

st.title("✨ NOVA")


# ---------------------------------------------------
# SNAPSHOT (Weather + Time)
# ---------------------------------------------------
col1, col2 = st.columns([1,1])

with col1:
    now = dt.datetime.now()
    st.markdown(f"### 🕒 {now.strftime('%A, %B %d — %I:%M %p')}")

with col2:
    WEATHER_KEY = st.secrets.get("WEATHER_API_KEY", "").strip()
    CITY = "Boston"

    if WEATHER_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_KEY}&units=metric"
            data = requests.get(url).json()
            temp = data["main"]["temp"]
            cond = data["weather"][0]["description"].title()
            st.markdown(f"### 🌤 {CITY}")
            st.markdown(f"**{temp}°C — {cond}**")
        except Exception:
            st.markdown("### 🌤 Weather unavailable")
    else:
        st.markdown("### 🌤 Weather unavailable (missing API key)")


# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
with st.sidebar:
    st.subheader("Status")
    st.markdown(f"- OpenAI: {'✅' if OPENAI_KEY else '❌ Missing key'}")

    google_ok = all(st.secrets.get(k, "").strip()
                    for k in ["client_id", "client_secret", "refresh_token"])
    st.markdown(f"- Google APIs: {'✅' if google_ok else '❌ Missing Google credentials'}")

    st.markdown("---")
    st.subheader("Commands")
    st.markdown("""
**Stocks**
- price of AAPL
- check TSLA and MSFT

**Emails**
- read my inbox

**Calendar**
- upcoming events

**Chat**
- anything else
""")


# ---------------------------------------------------
# STOCK HANDLER
# ---------------------------------------------------
def extract_tickers(text):
    tokens = re.split(r"[,\s]+", text.upper())
    return [t for t in tokens if t.isalpha() and 1 <= len(t) <= 5]


def handle_stocks(msg):_
