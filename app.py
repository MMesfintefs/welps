# =========================================================
# NOVA – Stocks, Trips, Fitness, Weather, Finance & Flights
# =========================================================

import os
import re
import streamlit as st
import yfinance as yf
from openai import OpenAI

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="NOVA",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# hide sidebar & hamburger
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='font-size:48px; color:#d2ffd0;'>✨ NOVA</h1>",
    unsafe_allow_html=True,
)

# =========================================================
# OPENAI CLIENT
# =========================================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================================================
# STOCK HANDLING
# =========================================================
NAME_TO_TICKER = {
    "AMAZON": "AMZN", "APPLE": "AAPL", "TESLA": "TSLA",
    "GOOGLE": "GOOG", "ALPHABET": "GOOG", "MICROSOFT": "MSFT",
    "META": "META", "FACEBOOK": "META", "NVIDIA": "NVDA",
}

def extract_ticker(text):
    upper = text.upper()
    for name, symbol in NAME_TO_TICKER.items():
        if name in upper:
            return symbol

    candidates = re.findall(r"\b[A-Z]{1,5}\b", upper)
    blacklist = {"STOCK", "PRICE", "WHAT", "IS", "THE"}
    for c in candidates:
        if c not in blacklist:
            return c
    return None

def fetch_stock_history(ticker):
    data = yf.download(ticker, period="1mo", progress=False)
    if data is None or data.empty:
        return None
    return data

def handle_stock(user_input):
    ticker = extract_ticker(user_input)
    if not ticker:
        return "I couldn’t figure out the ticker. Try `AAPL`, `TSLA`, `AMZN`."

    data = fetch_stock_history(ticker)
    if data is None:
        return f"No stock data available for **{ticker}**."

    price = float(data["Close"].iloc[-1])

    with st.chat_message("assistant"):
        st.markdown(f"### 📈 {ticker} — ${price:,.2f}")
        st.line_chart(data["Close"])

    return None

# =========================================================
# TRIP PLANNING
# =========================================================
TRAVEL_KEYWORDS = [
    "trip", "travel", "vacation", "weekend", "getaway",
    "places to eat", "where to eat", "where to stay",
    "hotel", "visit", "itinerary"
]

def extract_budget(text):
    nums = re.findall(r"\$?(\d+)", text.replace(",", ""))
    return int(max(nums)) if nums else None

def handle_trip(user_input):
    budget = extract_budget(user_input)
    sys_prompt = (
        "You are NOVA, a concise travel planner. "
        "Give: summary, place to stay, food spots, things to do. "
        "Keep costs realistic and fit the budget if provided."
    )
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    return response.choices[0].message.content

# =========================================================
# FITNESS COACH
# =========================================================
FITNESS_KEYWORDS = [
    "workout", "gym", "exercise", "fitness", "routine",
    "abs", "arms", "legs", "push day", "pull day", "back day"
]

def handle_fitness(user_input):
    sys_prompt = (
        "You are NOVA, a fitness coach. "
        "Give a simple workout plan (5–7 exercises) with sets & reps. "
        "Keep it beginner-friendly and safe. No advanced jargon."
    )
    reply = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    return reply.choices[0].message.content

# =========================================================
# FAKE WEATHER (AI FORECAST)
# =========================================================
WEATHER_KEYWORDS = [
    "weather", "forecast", "cold", "hot", "rain", "sunny"
]

def handle_weather(user_input):
    sys_prompt = (
        "You are NOVA, generating a fictional but realistic weather "
        "forecast for any city. Include: temperature, conditions, and "
        "a clothing suggestion. Keep it short."
    )
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    return res.choices[0].message.content

# =========================================================
# FINANCE COACH
# =========================================================
FINANCE_KEYWORDS = [
    "budget", "save", "money", "invest", "finance",
    "expenses", "financial plan"
]

def handle_finance(user_input):
    sys_prompt = (
        "You are NOVA, a simple finance coach. "
        "Give a short budgeting plan, savings suggestions, "
        "and basic investment guidance. No complex math."
    )
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    return res.choices[0].message.content

# =========================================================
# FLIGHT LOOKUP (AI-GENERATED)
# =========================================================
FLIGHT_KEYWORDS = [
    "flight", "flights", "airline", "ticket", "fly to"
]

def handle_flights(user_input):
    sys_prompt = (
        "You are NOVA. Generate fictional but realistic flight info: "
        "routes, average prices, best departure times, and airlines. "
        "Do NOT say it's fake. Keep it short and helpful."
    )
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input},
        ]
    )
    return res.choices[0].message.content

# =========================================================
# GENERAL CHAT
# =========================================================
def handle_general(user_input):
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are NOVA. Short, warm, helpful."},
            {"role": "user", "content": user_input},
        ]
    )
    return res.choices[0].message.content

# =========================================================
# MAIN ROUTER
# =========================================================
user = st.chat_input("Ask Nova anything…")

if user:
    st.chat_message("user").write(user)
    lower = user.lower()

    if any(k in lower for k in ["stock", "price", "ticker"]):
        result = handle_stock(user)
        if result:
            st.chat_message("assistant").write(result)

    elif any(k in lower for k in TRAVEL_KEYWORDS):
        st.chat_message("assistant").write(handle_trip(user))

    elif any(k in lower for k in FITNESS_KEYWORDS):
        st.chat_message("assistant").write(handle_fitness(user))

    elif any(k in lower for k in WEATHER_KEYWORDS):
        st.chat_message("assistant").write(handle_weather(user))

    elif any(k in lower for k in FINANCE_KEYWORDS):
        st.chat_message("assistant").write(handle_finance(user))

    elif any(k in lower for k in FLIGHT_KEYWORDS):
        st.chat_message("assistant").write(handle_flights(user))

    else:
        st.chat_message("assistant").write(handle_general(user))
