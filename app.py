# =============================
# NOVA 😊 — Assistant
# =============================

import os, re, json, requests
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# -------------------- CONFIG --------------------
st.set_page_config(page_title="NOVA 😊", page_icon="💹", layout="wide")

st.markdown("<h1 style='text-align:center'>NOVA 😊</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Your assistant — ask about stocks, prices, trends, or news.</p>", unsafe_allow_html=True)

# -------------------- API KEYS --------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not OPENAI_API_KEY:
    st.error("⚠️ Missing OpenAI API key in your `.streamlit/secrets.toml` file.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------- FUNCTIONS --------------------

def nova_brain(prompt: str, context: str = "") -> str:
    """Handles NOVA's chat responses."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are NOVA 😊 — a conversational market t who provides finance insights, explains data clearly, and answers questions naturally."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ OpenAI API error: {str(e)}"


@st.cache_data(ttl=600)
def get_stock_data(ticker: str, period: str = "6mo"):
    """Fetch stock data from Yahoo Finance."""
    try:
        data = yf.download(ticker, period=period, interval="1d", progress=False)
        if data.empty:
            return None
        data.reset_index(inplace=True)
        return data
    except Exception:
        return None


@st.cache_data(ttl=600)
def get_finance_news(topic="stocks"):
    """Fetch top news from NewsAPI."""
    try:
        if not NEWS_API_KEY:
            return []
        url = f"https://newsapi.org/v2/everything?q={topic}&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
        r = requests.get(url, timeout=10)
        articles = r.json().get("articles", [])
        return [{"title": a["title"], "source": a["source"]["name"], "url": a["url"]} for a in articles]
    except Exception:
        return []

# -------------------- CHAT MEMORY --------------------
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------- MAIN CHAT INPUT --------------------
user_text = st.chat_input("Ask NOVA anything...")

if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    text = user_text.lower()
    reply = ""

    # ---- STOCKS ----
    if any(word in text for word in ["stock", "price", "analyze", "chart", "trend"]):
        tickers = re.findall(r"\b[A-Z]{1,5}\b", user_text.upper())
        if not tickers:
            reply = "Please provide a valid stock ticker (e.g., AAPL, TSLA, MSFT)."
        else:
            for t in tickers:
                st.markdown(f"### 📈 {t} — 6-Month Performance")
                data = get_stock_data(t)
                if not data is None:
                    fig = px.line(data, x="Date", y="Close", title=f"{t} Stock Price")
                    st.plotly_chart(fig, use_container_width=True)
                    change = (data["Close"].iloc[-1] - data["Close"].iloc[0]) / data["Close"].iloc[0] * 100
                    st.caption(f"Performance: **{change:.2f}%** over 6 months.")
                else:
                    st.warning(f"Couldn’t fetch data for {t}. It might be invalid or temporarily unavailable.")

            reply = "Here’s the stock data you requested."

    # ---- NEWS ----
    elif "news" in text or "headline" in text:
        topic = re.sub(r"news|headline|about", "", text).strip() or "markets"
        news = get_finance_news(topic)
        if news:
            reply = f"🗞 **Top headlines for {topic}:**\n"
            for n in news:
                reply += f"- [{n['title']}]({n['url']}) — *{n['source']}*\n"
        else:
            reply = "Couldn't find recent financial news. Try again later."

    # ---- GENERAL QUESTIONS ----
    else:
        reply = nova_brain(user_text)

    # ---- DISPLAY ----
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.history.append({"role": "assistant", "content": reply})
