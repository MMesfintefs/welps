import os, re, json, requests, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")
st.markdown("<h1 style='text-align:center'>NOVA 😊</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Your conversational market and productivity assistant.</p>", unsafe_allow_html=True)

# -------------------- API CLIENT SETUP --------------------
client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
except Exception:
    client = None

# -------------------- WEATHER API --------------------
def get_weather(city="Boston", country="US"):
    try:
        key = os.getenv("WEATHER_API_KEY")
        if not key:
            return "No key"
        url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={city},{country}"
        res = requests.get(url, timeout=10).json()
        temp = res["current"]["temp_c"]
        cond = res["current"]["condition"]["text"]
        return f"{temp}°C, {cond}"
    except Exception as e:
        return "Weather unavailable"

# -------------------- MACRO SNAPSHOT --------------------
def get_macro_snapshot():
    try:
        fred_key = os.getenv("FRED_API_KEY")
        base = "https://api.stlouisfed.org/fred/series/observations"

        def fred_series(series_id):
            r = requests.get(base, params={
                "series_id": series_id,
                "api_key": fred_key,
                "file_type": "json"
            }, timeout=10)
            r.raise_for_status()
            return float(r.json()["observations"][-1]["value"])

        return {
            "Inflation": f"{fred_series('CPIAUCSL'):.1f} (CPI idx)",
            "Unemployment": f"{fred_series('UNRATE'):.1f}%",
            "FedRate": f"{fred_series('FEDFUNDS'):.2f}%"
        }
    except Exception:
        return {"Inflation": "N/A", "Unemployment": "N/A", "FedRate": "N/A"}

# -------------------- STOCK DATA --------------------
def get_stock_data(ticker: str, period="1mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return None
        price = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else price
        pct = (price - prev) / prev * 100 if prev else 0
        return {
            "ticker": ticker.upper(),
            "price": price,
            "pct": round(pct, 2),
            "history": hist.reset_index()[["Date", "Close"]]
        }
    except Exception:
        return None

# -------------------- AI BRAIN --------------------
def nova_brain(prompt, context=""):
    if not client:
        return "⚠️ No AI key detected. Running in data-only mode."
    try:
        system_prompt = """You are NOVA 😊 — a smart, conversational market and productivity assistant.
        You analyze finance, summarize data, and respond with clarity and insight."""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": context},
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to OpenAI: {e}"

# -------------------- UI LAYOUT --------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦️ Weather")
    st.metric("Current", get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    macro = get_macro_snapshot()
    for k, v in macro.items():
        st.metric(k, v)

with col3:
    st.markdown("### ⏱️ Date & Time")
    now = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    st.markdown(f"**{now}**")

st.divider()

# -------------------- CHAT SECTION --------------------
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_text = st.chat_input("Ask NOVA about stocks, weather, or markets...")

if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # Decide intent
    text = user_text.lower()

    if any(word in text for word in ["stock", "price", "analyze"]):
        tickers = re.findall(r"\b[A-Z]{1,5}\b", user_text.upper())
        if not tickers:
            reply = "Please mention a stock ticker symbol (e.g., AAPL, MSFT, TSLA)."
        else:
            for t in tickers:
                data = get_stock_data(t)
                if data:
                    df = pd.DataFrame(data["history"])
                    st.markdown(f"### {t} — ${data['price']:.2f} ({data['pct']}%)")
                    fig = px.line(df, x="Date", y="Close", title=f"{t} ({data['pct']}%)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"No data found for {t}.")
            reply = f"Here’s your live market data, {' ,'.join(tickers)} analyzed."

    else:
        reply = nova_brain(user_text)

    st.session_state.history.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
