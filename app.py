import os, requests, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from dotenv import load_dotenv

# local modules (you’ll add these next)
from analysis import compute_market_mood, decision_signal, get_finance_news
from report import generate_daily_report

load_dotenv()
st.set_page_config(page_title="Agentic AI Market Assistant", page_icon="🧠", layout="wide")

# ---------- UTILITIES ----------
def get_stock_data(ticker: str, period: str = "1mo"):
    """Fetch price history for any U.S. ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return None
        price = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else price
        change = price - prev
        pct = (change / prev) * 100
        hist = hist.reset_index()[["Date", "Close"]]
        return {"ticker": ticker.upper(), "price": round(price,2),
                "change": round(change,2), "pct": round(pct,2), "history": hist}
    except Exception:
        return None

@st.cache_data(ttl=600)
def get_macro_snapshot():
    """Pull basic U.S. macro indicators from FRED."""
    fred_api = os.getenv("FRED_API_KEY")
    if not fred_api:
        return {"Inflation": "3.4%", "Unemployment": "3.9%", "FedRate": "5.25%"}
    try:
        base = "https://api.stlouisfed.org/fred/series/observations"
        def fred_series(series_id):
            r = requests.get(base, params={"series_id": series_id,
                                           "api_key": fred_api, "file_type":"json"})
            data = r.json()["observations"][-1]["value"]
            return float(data)
        inflation = fred_series("CPIAUCSL")
        unemp = fred_series("UNRATE")
        fed = fred_series("FEDFUNDS")
        return {"Inflation": f"{inflation:.1f}%", "Unemployment": f"{unemp:.1f}%", "FedRate": f"{fed:.2f}%"}
    except Exception:
        return {"Inflation": "N/A", "Unemployment": "N/A", "FedRate": "N/A"}

# ---------- PAGE HEADER ----------
st.markdown("<h1>🧠 Agentic AI Market Intelligence Assistant</h1>", unsafe_allow_html=True)
st.caption("Data from Yahoo Finance, NewsAPI, and the U.S. Federal Reserve (FRED).")

# Sidebar – portfolio & macro data
st.sidebar.header("📊 Macro Snapshot")
macros = get_macro_snapshot()
for k,v in macros.items():
    st.sidebar.metric(k, v)

portfolio_tickers = st.sidebar.text_input("My Portfolio", "AAPL, MSFT, NVDA, TSLA, AMZN")
user_tickers = [t.strip().upper() for t in portfolio_tickers.split(",") if t.strip()]

# Tabs
tab1, tab2, tab3 = st.tabs(["📈 Market Overview", "📥 Inbox Assistant (Demo)", "📄 Daily Report"])

# ---------- TAB 1: Market Overview ----------
with tab1:
    st.subheader("Market Overview & Sentiment Analysis")
    period = st.selectbox("Select time range", ["7d","1mo","3mo","6mo","1y","ytd","max"], index=2)
    topic = st.text_input("Market topic focus", "tech, inflation, energy, yields")

    if st.button("Run Market Analysis 🚀"):
        stocks = [s for s in (get_stock_data(t, period) for t in user_tickers) if s]
        if not stocks:
            st.error("No valid stock data found.")
        else:
            avg = sum(s["pct"] for s in stocks) / len(stocks)
            sentiment = "Cautious" if avg < 0 else "Constructive"
            st.metric("Market Outlook", sentiment, f"{avg:.2f}% avg daily move")

            for s in stocks:
                df = pd.DataFrame(s["history"])
                fig = px.line(df, x="Date", y="Close", title=f"{s['ticker']} ({period})")
                st.plotly_chart(fig, use_container_width=True)
                sig = decision_signal(df.rename(columns={"Close":"close"}))
                st.caption(f"Signal: {sig}")

            # credible news + mood
            news = get_finance_news(topic)
            st.markdown("### 📰 Top Headlines (Reuters, Bloomberg, WSJ, CNBC, MarketWatch)")
            for n in news:
                st.write(f"• **{n['title']}** — {n['source']}")
            mood = compute_market_mood(news)
            st.metric("Market Mood", f"{mood}/100")

# ---------- TAB 2: Inbox Assistant ----------
with tab2:
    st.subheader("Inbox Intelligence Assistant (Demo Inbox)")
    demo_emails = [
        {"from":"Sarah Chen <sarah@recruiter.com>",
         "subject":"Data Analyst Internship – Quick Intro Call",
         "body":"Are you free for a 15-minute call next week?",
         "category":"To Reply"},
        {"from":"Investment Club <club@bentley.edu>",
         "subject":"Tonight: Semiconductor Outlook Discussion",
         "body":"Bring one slide on NVDA/TSMC outlook.",
         "category":"Finance"},
        {"from":"Mom <mom@example.com>",
         "subject":"Proud of you!",
         "body":"Call me when you can. Love, Mom",
         "category":"Personal"},
    ]
    if st.button("Analyze Inbox 🧠"):
        for email in demo_emails:
            st.markdown(f"### {email['category']}")
            with st.container(border=True):
                st.markdown(f"**{email['subject']}**")
                st.caption(email["from"])
                st.write(email["body"])
                if email["category"] in ["To Reply","Finance"]:
                    st.code(
                        f"Hi, thanks for your message about '{email['subject']}'. I'll follow up soon.\n\nBest,\nMichael",
                        language="markdown"
                    )

# ---------- TAB 3: Daily Report ----------
with tab3:
    st.subheader("Generate Personalized Daily Market Report")
    if st.button("📄 Generate PDF Report"):
        news = get_finance_news("markets")
        mood = compute_market_mood(news)
        outlooks = {t: "OK" for t in user_tickers}
        fname = "daily_report.pdf"
        generate_daily_report(fname, mood, outlooks, news)
        with open(fname,"rb") as f:
            st.download_button("Download Report", f, file_name=fname)
