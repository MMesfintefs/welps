import os, re, json, datetime, requests
import pandas as pd
import yfinance as yf
import plotly.express as px
import streamlit as st
from openai import OpenAI

# --------------- PAGE SETUP ---------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

# --------------- API KEYS -----------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# --------------- AI FUNCTION ---------------
def nova_brain(prompt):
    system_prompt = """You are NOVA 😊 — a smart conversational market and productivity assistant.
You can explain stocks, summarize text, or respond naturally to any query."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {e}"

# --------------- HELPERS -----------------
def get_stock_data(ticker, period="1mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return None
        return hist.reset_index()[["Date", "Close"]]
    except Exception:
        return None

def get_finance_news(topic="markets"):
    if not NEWSAPI_KEY:
        return [{"title": "Add a NEWSAPI_KEY to get news.", "source": "System"}]
    try:
        url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize=5&apiKey={NEWSAPI_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("articles", [])
            return [{"title": a["title"], "source": a["source"]["name"]} for a in data[:5]]
        else:
            return []
    except Exception:
        return []

# --------------- UI TABS -----------------
tab1, tab2 = st.tabs(["📈 Finance & Stocks", "💼 Assistant Tools"])

# ---------- TAB 1: FINANCE ----------
with tab1:
    st.markdown("## 📊 Market Insights")
    ticker = st.text_input("Enter Stock Symbol (e.g. AAPL, TSLA, MSFT):")
    period = st.selectbox("Select Period", ["7d", "1mo", "3mo", "6mo", "1y", "ytd", "max"], index=1)

    if ticker:
        data = get_stock_data(ticker, period)
        if data is not None:
            fig = px.line(data, x="Date", y="Close", title=f"{ticker.upper()} Stock Trend ({period})")
            st.plotly_chart(fig, use_container_width=True)
            st.success("✅ Data fetched successfully!")
        else:
            st.warning("⚠️ Could not fetch stock data. Try again later.")

    st.markdown("### 📰 Latest Market News")
    topic = st.text_input("Enter topic (optional):", "markets")
    news = get_finance_news(topic)
    for n in news:
        st.markdown(f"**{n['title']}** — *{n['source']}*")

# ---------- TAB 2: ASSISTANT TOOLS ----------
with tab2:
    st.markdown("## 💼 NOVA Productivity Suite")
    st.caption("Ask NOVA to summarize emails, analyze text, or perform lookups.")
    user_input = st.text_area("Enter your request here:")

    if st.button("Run NOVA"):
        if user_input.strip():
            with st.spinner("NOVA is thinking..."):
                reply = nova_brain(user_input)
                st.markdown(reply)
        else:
            st.warning("Please type something first.")
