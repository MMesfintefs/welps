# =========================================================
# NOVA – Stocks, Trips, Fitness, Weather, Finance & Flights
# =========================================================

import os
import re
import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pytz

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
# WEATHER FUNCTION (REAL API)
# =========================================================

def get_weather(city: str):
    api_key = st.secrets.get("WEATHER_API_KEY", "")
    if not api_key:
        return {"error": "Missing WEATHER_API_KEY in Streamlit secrets."}

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            return {"error": f"No weather info for {city}"}

        weather_info = {
            "city": city.title(),
            "temp": round(data["main"]["temp"]),
            "condition": data["weather"][0]["description"].title(),
            "wind": data["wind"]["speed"],
            "humidity": data["main"]["humidity"]
        }
        return weather_info

    except Exception as e:
        return {"error": str(e)}


# =========================================================
# WEATHER + TIME DASHBOARD (TOP OF APP)
# =========================================================
col1, col2 = st.columns([1, 2])

# Time and date for Boston
with col1:
    try:
        tz = pytz.timezone("America/New_York")
        now = datetime.now(tz)
        st.markdown(
            f"""
            <div style="font-size:20px; color:#C2F8CB;">
                📅 <b>{now.strftime("%A, %B %d")}</b><br>
                ⏰ {now.strftime("%I:%M %p")}
            </div>
            """,
            unsafe_allow_html=True
        )
    except:
        pass

# Weather snapshot for Boston
with col2:
    weather = get_weather("Boston")
    if "error" in weather:
        st.markdown(
            f"<div style='font-size:18px; color:#FF8080;'>🌤️ Weather unavailable — {weather['error']}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="font-size:20px; color:#C2F8CB;">
                🌤️ <b>{weather['city']}</b><br>
                {weather['condition']} — {weather['temp']}°F<br>
                💨 Wind: {weather['wind']} mph | 💧 Humidity: {weather['humidity']}%
            </div>
            """,
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
# FINANCE COACH
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
