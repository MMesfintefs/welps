# ===============================
# NOVA — Simple, Stable Version
# ===============================

import os
import re
import requests
import datetime as dt
import streamlit as st
import yfinance as yf
import plotly.express as px
from gmail_calendar import read_last_5_emails, get_calendar_events


# ---------------------------------------------------
# OPENAI SETUP (Safe)
# ---------------------------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()
client = None

def get_openai_client():
    global client
    if client is not None:
        return client
    if not OPENAI_KEY:
        return None
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    try:
        from openai import OpenAI
        client = OpenAI(http_client=None)
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
    WEATHER_KEY = st.secrets.get("WEATHER_API_KEY", "")
    CITY = "Boston"

    if WEATHER_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_KEY}&units=metric"
            data = requests.get(url).json()
            temp = data["main"]["temp"]
            cond = data["weather"][0]["description"].title()
            st.markdown(f"### 🌤 {CITY}")
            st.markdown(f"**{temp}°C — {cond}**")
        except:
            st.markdown("### 🌤 Weather unavailable")
    else:
        st.markdown("### 🌤 Weather key missing")


# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
with st.sidebar:
    st.subheader("Status")
    st.markdown(f"- OpenAI: {'✅' if OPENAI_KEY else '❌ Missing key'}")

    google_ok = all(st.secrets.get(k, "").strip() 
        for k in ["client_id", "client_secret", "refresh_token", "redirect_uri"])
    st.markdown(f"- Google APIs: {'✅' if google_ok else '❌ Missing Google credentials'}")

    st.markdown("---")
    st.subheader("Commands")
    st.markdown("""
**Stocks**
- price of AAPL
- check TSLA

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
    return [t for t in tokens if 1 <= len(t) <= 5 and t.isalpha()]


def handle_stocks(msg):
    tickers = extract_tickers(msg)
    results = []

    for t in tickers:
        try:
            data = yf.Ticker(t).history(period="1mo")
            if data.empty:
                results.append((t, None))
            else:
                price = float(data["Close"].iloc[-1])
                results.append((t, price))
        except:
            results.append((t, None))

    return results


# ---------------------------------------------------
# EMAIL + CALENDAR HANDLER
# ---------------------------------------------------
def handle_emails():
    try:
        return read_last_5_emails()
    except Exception as e:
        return f"Email error: {e}"


def handle_calendar():
    try:
        return get_calendar_events(10)
    except Exception as e:
        return f"Calendar error: {e}"


# ---------------------------------------------------
# FALLBACK CHAT USING OPENAI
# ---------------------------------------------------
def handle_chat(msg):
    client = get_openai_client()
    if client is None:
        return "AI not configured."

    try:
        out = client.responses.create(
            model="gpt-4.1-mini",
            input=msg
        )
        return out.output_text
    except Exception as e:
        return f"AI error: {e}"


# ---------------------------------------------------
# MAIN CHAT LOGIC
# ---------------------------------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []

for turn in st.session_state["history"]:
    st.chat_message("user").write(turn["user"])
    st.chat_message("assistant").write(turn["bot"])


query = st.chat_input("Ask NOVA something...")

if query:
    # Determine mode
    q_low = query.lower()

    if "stock" in q_low or "price" in q_low:
        stocks = handle_stocks(query)
        resp = "\n".join(
            [f"**{t}** — {'$'+str(p) if p else 'No data'}" for t, p in stocks]
        )
    elif "email" in q_low or "inbox" in q_low:
        resp = handle_emails()
    elif "calendar" in q_low or "events" in q_low:
        resp = handle_calendar()
    else:
        resp = handle_chat(query)

    st.session_state["history"].append({"user": query, "bot": resp})
    st.chat_message("user").write(query)
    st.chat_message("assistant").write(resp)
