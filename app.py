# =========================
# FILE: app.py
# =========================

import os
import datetime
import pytz
import requests
import streamlit as st
import yfinance as yf
from openai import OpenAI

# =============== LOAD SECRETS ===============
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
WEATHER_KEY = st.secrets["WEATHER_API_KEY"]
FRED_KEY = st.secrets["FRED_API_KEY"]

GOOGLE_CLIENT_ID = st.secrets["client_id"]
GOOGLE_CLIENT_SECRET = st.secrets["client_secret"]
GOOGLE_REDIRECT_URI = st.secrets["redirect_uri"]

# OpenAI client
client = OpenAI(api_key=OPENAI_KEY)


# =============== WEATHER ===============
def get_weather():
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q=Boston&aqi=no"
        res = requests.get(url, timeout=10).json()
        if "error" in res:
            return "Weather unavailable"

        temp_c = res["current"]["temp_c"]
        temp_f = (temp_c * 9 / 5) + 32
        cond = res["current"]["condition"]["text"]

        return f"Boston: {temp_f:.1f}°F, {cond}"
    except:
        return "Weather unavailable"


# =============== MACRO (FRED) ===============
def get_macro():
    try:
        base = "https://api.stlouisfed.org/fred/series/observations"

        def fred_val(series):
            r = requests.get(
                base,
                params={
                    "series_id": series,
                    "api_key": FRED_KEY,
                    "file_type": "json"
                },
                timeout=10
            )
            r.raise_for_status()
            data = r.json()["observations"]
            return float(data[-1]["value"])

        inflation = fred_val("CPIAUCSL")
        unemp = fred_val("UNRATE")
        fed_rate = fred_val("FEDFUNDS")

        return f"📊 Inflation: {inflation:.1f} | Unemployment: {unemp:.1f}% | Fed Rate: {fed_rate:.2f}%"

    except Exception:
        return "Macro data unavailable"


# =============== STOCK LOOKUP ===============
def get_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        info = stock.info

        if hist.empty:
            return None, None

        return info, hist
    except:
        return None, None


# =============== UI HEADER ===============
st.set_page_config(page_title="NOVA 😊", layout="wide")

st.markdown("<h1 style='text-align:center;'>NOVA 😊</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;'>Your self-directing agentic assistant — streamlined and focused.</p>",
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦 Weather")
    st.write(get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    st.write(get_macro())

with col3:
    boston_time = datetime.datetime.now(pytz.timezone("America/New_York"))
    now = boston_time.strftime("%A, %B %d, %Y %I:%M %p")
    st.markdown("### 🕓 Time")
    st.write(now)

st.divider()

# =============== CHAT HISTORY ===============
if "history" not in st.session_state:
    st.session_state.history = []


# =============== DISPLAY CHAT HISTORY ===============
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# =============== USER INPUT ===============
user_input = st.chat_input("Ask NOVA anything (stocks, email, calendar…)")

if user_input:
    # Show user message
    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Check for stock queries
    words = user_input.strip().upper().split()

    # naive stock detection
    if len(words) == 1 and words[0].isalpha() and len(words[0]) <= 5:
        ticker = words[0]
        info, hist = get_stock(ticker)

        if info is None:
            bot_reply = f"No data found for {ticker}."
        else:
            price = info.get("regularMarketPrice", "N/A")
            bot_reply = f"**{ticker} Stock**\nPrice: {price}"

            st.line_chart(hist["Close"])

    else:
        # OpenAI response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are NOVA, a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        bot_reply = response.choices[0].message.content

    # Show bot reply
    st.session_state.history.append({"role": "assistant", "content": bot_reply})

    with st.chat_message("assistant"):
        st.write(bot_reply)
