import os, re, requests, datetime, json
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from openai import OpenAI

# -------------------- imports from your modules --------------------
from analysis import compute_market_mood, decision_signal, get_finance_news
from report import generate_daily_report

# -------------------- page setup --------------------
st.set_page_config(page_title="NOVA", page_icon="😊", layout="wide")

# -------------------- OpenAI brain --------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def nova_brain(prompt, context=""):
    system_prompt = """You are NOVA 😊 — a conversational market assistant.
    You greet users, explain insights clearly, and can fetch stock data, news, or macro info.
    If unclear, ask clarifying questions. Speak naturally with a hint of personality.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": context},
        ]
    )
    return response.choices[0].message.content

# -------------------- helpers --------------------
VALID_PERIODS = ["7d","1mo","3mo","6mo","1y","ytd","max"]

@st.cache_data(ttl=600)
def get_macro_snapshot():
    fred_key = os.getenv("FRED_API_KEY")
    if not fred_key:
        return {"Inflation": "N/A", "Unemployment": "N/A", "FedRate": "N/A"}
    try:
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

def get_stock_data(ticker: str, period: str = "1mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return None
        price = hist["Close"].iloc[-1]
        prev  = hist["Close"].iloc[-2] if len(hist) > 1 else price
        pct   = (price - prev) / prev * 100 if prev else 0
        return {
            "ticker": ticker.upper(),
            "pct": round(pct,2),
            "history": hist.reset_index()[["Date","Close"]],
        }
    except Exception:
        return None

def summarize_emails():
    fake_emails = [
        {"subject": "Market Update", "body": "Inflation fell slightly this month."},
        {"subject": "Tesla Earnings", "body": "Tesla beats estimates with higher delivery numbers."}
    ]
    return nova_brain("Summarize these emails:\n" + json.dumps(fake_emails))

# -------------------- UI --------------------
left, mid, right = st.columns([1,2,1])
with mid:
    st.markdown("<h1 style='text-align:center'>NOVA 😊</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Your conversational market assistant. Ask about stocks, news, macro, or reports.</p>", unsafe_allow_html=True)

with left:
    st.markdown("### Macro Snapshot")
    macro = get_macro_snapshot()
    for k,v in macro.items():
        st.metric(k, v)

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

    # --- Decide intent ---
    text = user_text.lower()

    if "stock" in text or "analyze" in text or "price" in text:
        tickers = re.findall(r"\b[A-Z]{1,5}(?:-[A-Z]{2,4})?\b", user_text.upper())
        if not tickers:
            reply = "Please mention one or more tickers, e.g., `AAPL, MSFT`."
        else:
            period = "1mo"
            reply = f"Analyzing {', '.join(tickers)} for {period}..."
            st.markdown(reply)
            for t in tickers:
                data = get_stock_data(t, period)
                if data:
                    df = pd.DataFrame(data["history"])
                    fig = px.line(df, x="Date", y="Close", title=f"{t} ({period})")
                    st.plotly_chart(fig, use_container_width=True)
                    sig = decision_signal(df.rename(columns={"Close":"close"}))
                    st.caption(f"Signal: {sig}")
        st.session_state.history.append({"role": "assistant", "content": reply})

    elif "news" in text:
        topic = re.sub(r"news|headline|about", "", text).strip() or "markets"
        news = get_finance_news(topic)
        if news:
            reply = f"**Top headlines for {topic}:**\n"
            for n in news[:5]:
                reply += f"• **{n['title']}** — {n['source']}\n"
            mood = compute_market_mood(news)
            reply += f"\nMarket Mood: {mood}/100"
        else:
            reply = "Couldn't find recent news."
        st.session_state.history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    elif "email" in text:
        reply = summarize_emails()
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})

    elif "macro" in text:
        reply = "**Latest macro snapshot:**"
        st.markdown(reply)
        cols = st.columns(3)
        for (k,v), c in zip(macro.items(), cols):
            with c: st.metric(k, v)
        st.session_state.history.append({"role": "assistant", "content": reply})

    else:
        reply = nova_brain(user_text)
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
