import os, re, json, requests, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")
st.markdown("<h1 style='text-align:center'>NOVA 😊</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Your self-directing agentic assistant — ready to act and analyze.</p>", unsafe_allow_html=True)

# -------------------- API CLIENT --------------------
client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
except Exception:
    client = None

# -------------------- TOOL DEFINITIONS --------------------
def get_weather(city="Boston", country="US"):
    try:
        key = os.getenv("WEATHER_API_KEY")
        if not key:
            return "⚠️ Missing WEATHER_API_KEY."
        url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={city},{country}"
        res = requests.get(url, timeout=10).json()
        temp = res["current"]["temp_f"]
        cond = res["current"]["condition"]["text"]
        return f"🌦️ {city}: {temp}°F, {cond}"
    except Exception as e:
        return f"Weather unavailable: {e}"

def get_macro_snapshot():
    try:
        fred_key = os.getenv("FRED_API_KEY")
        if not fred_key:
            return "⚠️ Missing FRED_API_KEY."
        base = "https://api.stlouisfed.org/fred/series/observations"

        def fred_series(series_id):
            r = requests.get(base, params={
                "series_id": series_id,
                "api_key": fred_key,
                "file_type": "json"
            }, timeout=10)
            r.raise_for_status()
            return float(r.json()["observations"][-1]["value"])

        inflation = fred_series("CPIAUCSL")
        unemp = fred_series("UNRATE")
        fed = fred_series("FEDFUNDS")
        return f"📊 Inflation: {inflation:.1f} | Unemployment: {unemp:.1f}% | Fed Rate: {fed:.2f}%"
    except Exception as e:
        return f"Macro data unavailable: {e}"

def get_stock(ticker="AAPL"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            return f"No stock data found for {ticker}."
        price = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else price
        pct = (price - prev) / prev * 100 if prev else 0
        df = hist.reset_index()[["Date", "Close"]]
        fig = px.line(df, x="Date", y="Close", title=f"{ticker} ({pct:+.2f}%)")
        st.plotly_chart(fig, use_container_width=True)
        return f"💹 {ticker} latest price: ${price:.2f} ({pct:+.2f}%)"
    except Exception as e:
        return f"Stock lookup failed: {e}"

# -------------------- DEFINE TOOLS FOR OPENAI --------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city and country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "country": {"type": "string", "description": "Country code (e.g. US)"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock",
            "description": "Get live stock price and display its 1-month graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock symbol (e.g. AAPL, TSLA)"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_macro_snapshot",
            "description": "Get current macroeconomic data (Fed rate, inflation, unemployment).",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

# -------------------- AGENTIC BRAIN --------------------
def nova_agent(prompt):
    if not client:
        return "⚠️ No valid API key found. Please add your OPENAI_API_KEY."

    system_prompt = """You are NOVA, an agentic assistant that can decide when to use tools.
You can fetch stock data, weather, or macroeconomic info automatically based on user intent.
Always respond clearly and summarize results when combining multiple tools."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            tools=tools
        )

        msg = response.choices[0].message

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for call in msg.tool_calls:
                fn_name = call.function.name
                args = json.loads(call.function.arguments or "{}")
                result = globals()[fn_name](**args)
                st.info(f"🧠 NOVA used {fn_name}: {result}")
                return result

        return msg.content or "No direct response."

    except Exception as e:
        return f"Error: {e}"

# -------------------- DISPLAY SNAPSHOT --------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌦️ Weather Snapshot")
    st.metric("Current", get_weather())

with col2:
    st.markdown("### 📊 Macro Snapshot")
    st.metric("Status", "Fetching live data...")
    st.markdown(get_macro_snapshot())

with col3:
    now = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    st.markdown("### ⏱️ Time")
    st.markdown(f"**{now}**")

st.divider()

# -------------------- CHAT INTERFACE --------------------
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_text = st.chat_input("Ask NOVA anything (e.g. 'What's Tesla’s stock and Boston’s weather?')")

if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        reply = nova_agent(user_text)
        st.markdown(reply)

    st.session_state.history.append({"role": "assistant", "content": reply})
