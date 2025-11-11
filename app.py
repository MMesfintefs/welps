import os, re, time, json, requests, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# Try both OpenAI and Groq (fallback)
from openai import OpenAI

# -------------------- CONFIG --------------------
st.set_page_config(page_title="NOVA 😊", page_icon="😊", layout="wide")

# -------------------- API KEYS --------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# -------------------- SELECT MODEL --------------------
if OPENAI_KEY:
    client = OpenAI(api_key=OPENAI_KEY)
    MODEL = "gpt-4o-mini"
    API_SOURCE = "OpenAI"
elif GROQ_KEY:
    import openai
    openai.api_key = GROQ_KEY
    openai.api_base = "https://api.groq.com/openai/v1"
    client = openai
    MODEL = "llama3-70b-8192"
    API_SOURCE = "Groq"
else:
    client = None
    MODEL = None
    API_SOURCE = "None"

# -------------------- AI CORE --------------------
def nova_brain(prompt, context=""):
    if not client:
        return "AI disabled — please add an OpenAI or Groq API key."
    time.sleep(1)
    system_prompt = """You are NOVA 😊, an agentic conversational assistant.
You can discuss stocks, markets, macroeconomics, or summarize recent news.
You’re friendly, insightful, and brief. Format clearly for Streamlit."""
    try:
        if API_SOURCE == "OpenAI":
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": context},
                ]
            )
            return response.choices[0].message.content
        else:
            response = client.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": context},
                ]
            )
            return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error connecting to {API_SOURCE}: {str(e)}"

# -------------------- HELPERS --------------------
VALID_PERIODS = ["7d","1mo","3mo","6mo","1y","ytd","max"]

@st.cache_data(ttl=600)
def get_stock_data(ticker: str, period: str = "1mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist is None or hist.empty:
            return None
        price = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else price
        pct = (price - prev) / prev * 100 if prev else 0
        return {"ticker": ticker.upper(), "pct": round(pct,2), "history": hist.reset_index()[["Date","Close"]]}
    except Exception:
        return None

def get_finance_news(topic="markets"):
    if not NEWSAPI_KEY:
        return [{"title": "No NewsAPI key provided", "source": "System"}]
    try:
        url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize=5&apiKey={NEWSAPI_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            articles = r.json().get("articles", [])
            return [{"title": a["title"], "source": a["source"]["name"]} for a in articles[:5]]
        else:
            return []
    except Exception:
        return []

def compute_market_mood(news):
    if not news: return 50
    mood = 50
    for n in news:
        title = n["title"].lower()
        if any(x in title for x in ["surge", "gain", "growth", "up"]): mood += 5
        if any(x in title for x in ["fall", "drop", "loss", "down"]): mood -= 5
    return max(0, min(100, mood))

def decision_signal(df):
    return "Bullish" if df["Close"].iloc[-1] > df["Close"].mean() else "Bearish"

# -------------------- UI --------------------
left, mid, right = st.columns([1,2,1])
with mid:
    st.markdown("<h1 style='text-align:center'>NOVA 😊</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:gray;'>Connected to: {API_SOURCE}</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Ask about stocks, news, or market trends.</p>", unsafe_allow_html=True)

# -------------------- Chat memory --------------------
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------- Chat input --------------------
user_text = st.chat_input("Ask NOVA anything...")

if user_text:
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    text = user_text.lower()

    # STOCK ANALYSIS
    if any(k in text for k in ["stock", "analyze", "price", "ticker"]):
        tickers = re.findall(r"\b[A-Z]{1,5}(?:-[A-Z]{2,4})?\b", user_text.upper())
        if not tickers:
            reply = "Please mention one or more tickers, e.g. `AAPL, MSFT`."
        else:
            period = "1mo"
            reply = f"Analyzing {', '.join(tickers)} for {period}..."
            st.markdown(reply)
            for t in tickers:
                data = get_stock_data(t, period)
                if not data:
                    st.warning(f"No data found for {t}. Try again later.")
                    continue
                df = pd.DataFrame(data["history"])
                fig = px.line(df, x="Date", y="Close", title=f"{t} ({period})")
                st.plotly_chart(fig, use_container_width=True)
                sig = decision_signal(df.rename(columns={"Close":"close"}))
                st.caption(f"Signal: {sig}")
            reply = "Here's what I found for your stocks."
        st.session_state.history.append({"role": "assistant", "content": reply})

    # NEWS
    elif "news" in text or "headline" in text:
        topic = re.sub(r"news|headline|about", "", text).strip() or "markets"
        news = get_finance_news(topic)
        if news:
            reply = f"**Top headlines for {topic}:**\n"
            for n in news:
                reply += f"• **{n['title']}** — {n['source']}\n"
            mood = compute_market_mood(news)
            reply += f"\nMarket Mood: {mood}/100"
        else:
            reply = "Couldn't fetch any recent news."
        st.session_state.history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    # GENERIC CHAT
    else:
        reply = nova_brain(user_text)
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
