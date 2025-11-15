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

# -------------------- CONFIG / CLIENT --------------------

st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


# -------------------- WEATHER (HEADER ONLY) --------------------

def get_weather():
    """Return a short weather string for Boston using weatherapi.com."""
    if not WEATHER_API_KEY:
        return "Missing WEATHER_API_KEY"

    city = "Boston"
    try:
        url = (
            f"http://api.weatherapi.com/v1/current.json"
            f"?key={WEATHER_API_KEY}&q={city}&aqi=no"
        )
        res = requests.get(url, timeout=10).json()
        if "error" in res:
            return "Weather unavailable"

        temp_c = res["current"]["temp_c"]
        temp_f = (temp_c * 9 / 5) + 32
        condition = res["current"]["condition"]["text"]
        return f"{city}: {temp_f:.1f}°F, {condition}"
    except Exception:
        return "Weather unavailable"


# -------------------- MACRO (HEADER ONLY) --------------------

def get_macro_snapshot():
    """Get inflation, unemployment, and Fed rate from FRED (optional)."""
    if not FRED_API_KEY:
        return "Macro data unavailable (missing FRED_API_KEY)"

    try:
        base = "https://api.stlouisfed.org/fred/series/observations"

        def fred_series(series_id: str) -> float:
            r = requests.get(
                base,
                params={
                    "series_id": series_id,
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                },
                timeout=10,
            )
            r.raise_for_status()
            obs = r.json().get("observations", [])
            if not obs:
                raise ValueError("No observations")
            return float(obs[-1]["value"])

        inflation = fred_series("CPIAUCSL")
        unemp = fred_series("UNRATE")
        fed = fred_series("FEDFUNDS")

        return (
            f"Inflation: {inflation:.1f} | "
            f"Unemployment: {unemp:.1f}% | "
            f"Fed Rate: {fed:.2f}%"
        )
    except Exception:
        return "Macro data unavailable"


# -------------------- STOCK TOOL (YAHOO FINANCE) --------------------

STOPWORDS = {
    "SHOW",
    "HOW",
    "IS",
    "THE",
    "AND",
    "STOCK",
    "STOCKS",
    "PRICE",
    "PRICES",
    "TODAY",
    "DOING",
    "OF",
    "FOR",
    "WHAT",
    "CAN",
    "YOU",
    "LOOK",
    "AT",
}


def extract_tickers(text: str):
    """
    Pull potential tickers from user text.
    We keep 1–5 letter uppercase tokens and drop common English words.
    """
    candidates = re.findall(r"\b[A-Z]{1,5}\b", text.upper())
    tickers = [c for c in candidates if c not in STOPWORDS]
    # Remove duplicates, keep order
    seen = set()
    result = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def fetch_stock_data(ticker: str, period: str = "3mo"):
    """
    Fetch OHLC data from Yahoo. Returns (df, info_string) or (None, message).
    """
    try:
        tkr = yf.Ticker(ticker)
        hist = tkr.history(period=period, interval="1d")
        if hist.empty:
            return None, f"No data found for {ticker}."

        hist = hist.reset_index()
        price_now = hist["Close"].iloc[-1]
        price_old = hist["Close"].iloc[0]
        pct_change = (price_now - price_old) / price_old * 100

        summary = (
            f"{ticker}: {price_now:.2f} USD "
            f"({pct_change:+.2f}% over last {period})."
        )
        return hist, summary
    except Exception as e:
        return None, f"Error fetching {ticker}: {e}"


def handle_stock_query(user_text: str):
    """
    Handles stock-related queries: detects tickers, fetches prices,
    draws charts, and returns a textual summary for the chat log.
    """
    tickers = extract_tickers(user_text)
    if not tickers:
        return (
            "I didn't see any tickers in that. "
            "Try something like `AAPL`, `TSLA`, or `MSFT`."
        )

    responses = []
    for t in tickers:
        hist, msg = fetch_stock_data(t)
        responses.append(msg)

        if hist is not None:
            df = pd.DataFrame(hist)
            fig = px.line(
                df,
                x="Date",
                y="Close",
                title=f"{t} closing price ({len(df)} points)",
            )
            st.plotly_chart(fig, use_container_width=True)

    return " | ".join(responses)


# -------------------- EMAIL & CALENDAR MOCK TOOLS --------------------
# These are mocks so you can see the behavior.
# Later you can swap them with real Gmail / Google Calendar calls.

FAKE_EMAILS = [
    {
        "from": "hr@example.com",
        "subject": "Interview confirmation",
        "body": "Hi Mike, confirming your interview on Friday at 2 PM EST.",
    },
    {
        "from": "alerts@broker.com",
        "subject": "Daily portfolio summary",
        "body": "Your portfolio was up 1.8% today, driven by gains in NVDA and TSLA.",
    },
    {
        "from": "professor@uni.edu",
        "subject": "Project deadline",
        "body": "Reminder that your data analytics project is due next Wednesday.",
    },
]

FAKE_EVENTS = [
    {
        "time": "Tomorrow 10:00 AM",
        "title": "Stand-up with analytics team",
        "location": "Zoom",
    },
    {
        "time": "Friday 2:00 PM",
        "title": "Finance interview",
        "location": "Office",
    },
    {
        "time": "Sunday 4:00 PM",
        "title": "Gym / training session",
        "location": "Local gym",
    },
]


def summarize_emails_with_openai():
    if not client:
        return "I can't reach OpenAI (missing OPENAI_API_KEY), but here are your mock emails:\n" + "\n".join(
            f"- {e['subject']} from {e['from']}" for e in FAKE_EMAILS
        )

    prompt = (
        "You are an assistant summarizing a user's inbox.\n"
        "Given these recent emails, provide 3–5 bullet points "
        "of what they should pay attention to and any actions they should take.\n\n"
        f"Emails JSON:\n{FAKE_EMAILS}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You summarize emails concisely."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


def summarize_calendar_with_openai():
    if not client:
        return "I can't reach OpenAI (missing OPENAI_API_KEY), but here are your mock events:\n" + "\n".join(
            f"- {e['time']}: {e['title']} @ {e['location']}" for e in FAKE_EVENTS
        )

    prompt = (
        "You are an assistant summarizing a user's upcoming schedule.\n"
        "Given these events, summarize the next few days and highlight conflicts or important items.\n\n"
        f"Events JSON:\n{FAKE_EVENTS}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You summarize calendar events."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


# -------------------- GENERAL NOVA BRAIN (LLM) --------------------

def nova_chat_reply(user_text: str):
    """
    Fallback general chat: NOVA answers normally.
    No weather/macro/time here. Those are header-only.
    """
    if not client:
        # When you're out of quota or forgot the key
        return (
            "I can't reach the OpenAI API right now (missing key or quota). "
            "I can still fetch stocks for you: try something like `AAPL` or `TSLA`."
        )

    system_prompt = (
        "You are NOVA 😊, a helpful, concise assistant. "
        "You are embedded in a dashboard that already shows:\n"
        "- Weather in Boston\n"
        "- Macro snapshot (inflation, unemployment, Fed rate)\n"
        "- Local time in Boston\n\n"
        "Do NOT try to fetch those things; just answer questions, "
        "and when users ask about stocks, emails, or calendar, "
        "you can tell them that you have special tools for that."
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    return resp.choices[0].message.content


# -------------------- HEADER LAYOUT --------------------

st.markdown(
    "<h1 style='text-align:center'>NOVA 😊</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center'>Your self-directing agentic assistant – focused on "
    "stocks, emails, and your schedule.</p>",
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦️ Weather Snapshot")
    st.metric("Current", get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    st.metric("Status", "Latest data")
    st.markdown(get_macro_snapshot())

with col3:
    st.markdown("### 🕓 Time")
    boston_time = datetime.now(pytz.timezone("America/New_York"))
    now_str = boston_time.strftime("%A, %B %d, %Y %I:%M %p")
    st.markdown(f"**{now_str}**")

st.divider()


# -------------------- CHAT STATE --------------------

if "history" not in st.session_state:
    st.session_state.history = []

# Render old messages
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------- ROUTER + CHAT INPUT --------------------

user_text = st.chat_input(
    "Ask NOVA anything (e.g. 'AAPL and TSLA performance', "
    "'summarize my emails', 'what's on my calendar?')"
)

if user_text:
    # Show user message
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    text_lower = user_text.lower()

    # 1. STOCK TOOL
    if any(
        kw in text_lower
        for kw in ["stock", "stocks", "ticker", "price", "chart"]
    ) or extract_tickers(user_text):
        with st.chat_message("assistant"):
            reply = handle_stock_query(user_text)
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # 2. EMAIL TOOL
    elif "email" in text_lower or "inbox" in text_lower:
        with st.chat_message("assistant"):
            reply = summarize_emails_with_openai()
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # 3. CALENDAR TOOL
    elif "calendar" in text_lower or "schedule" in text_lower or "agenda" in text_lower:
        with st.chat_message("assistant"):
            reply = summarize_calendar_with_openai()
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    # 4. GENERAL NOVA CHAT
    else:
        with st.chat_message("assistant"):
            reply = nova_chat_reply(user_text)
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
