import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import os

# Custom modules (you’ll create these next)
from analysis import compute_market_mood, decision_signal
from feeds import get_reddit_trending, next_macro_event
from report import generate_daily_report

st.set_page_config(page_title="Agentic AI Market Assistant", page_icon="🧠", layout="wide")

# ---------- BASIC FUNCTIONS ----------
def get_stock_data(ticker: str, period: str = "1mo"):
    """Fetch price history for any ticker."""
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
        return {"ticker": ticker.upper(), "price": round(price,2), "change": round(change,2),
                "pct": round(pct,2), "history": hist}
    except Exception as e:
        return None

# ---------- PAGE LAYOUT ----------
st.markdown("<h1>🧠 Agentic AI Market Intelligence Assistant</h1>", unsafe_allow_html=True)
st.caption("A personalized, multi-source, sentiment-driven market analysis platform.")

# Sidebar – user portfolio + intel
st.sidebar.header("📊 Market Intel")
portfolio_tickers = st.sidebar.text_input("My Portfolio", "AAPL, MSFT, NVDA, TSLA, AMZN")
user_tickers = [t.strip().upper() for t in portfolio_tickers.split(",") if t.strip()]
st.sidebar.write(f"Trending Reddit tickers: {', '.join(get_reddit_trending())}")
st.sidebar.write(next_macro_event())

# Tabs
tab1, tab2, tab3 = st.tabs(["📈 Market Overview", "📥 Inbox Assistant (Demo)", "📄 Daily Report"])

# ---------- TAB 1: Market Overview ----------
with tab1:
    st.subheader("Market Overview & Sentiment Analysis")
    period = st.selectbox("Select time range", ["7d", "1mo", "3mo", "6mo", "1y", "ytd", "max"], index=2)
    topic = st.text_input("Market focus", "tech, inflation, energy, yields")

    if st.button("Run Market Analysis 🚀"):
        stocks = []
        for t in user_tickers:
            data = get_stock_data(t, period)
            if data:
                stocks.append(data)

        if not stocks:
            st.error("Could not fetch stock data. Try different tickers.")
        else:
            avg = sum([s["pct"] for s in stocks]) / len(stocks)
            sentiment = "Cautious" if avg < 0 else "Constructive"
            st.metric("Market Outlook", sentiment, f"{avg:.2f}% avg daily move")

            # Charts
            for s in stocks:
                df = pd.DataFrame(s["history"])
                fig = px.line(df, x="Date", y="Close", title=f"{s['ticker']} ({period})")
                st.plotly_chart(fig, use_container_width=True)
                signal = decision_signal(df.rename(columns={"Close":"close"}))
                st.caption(f"Signal: {signal}")

            # News + mood
            from analysis import get_finance_news
            news = get_finance_news(topic)
            st.markdown("### 📰 Top Headlines")
            for n in news:
                st.write(f"• **{n['title']}** — {n['source']}")
            mood = compute_market_mood(news)
            st.metric("Market Mood", f"{mood}/100")

# ---------- TAB 2: Inbox Assistant ----------
with tab2:
    st.subheader("Inbox Intelligence Assistant (Demo Inbox)")
    demo_emails = [
        {"from": "Sarah Chen <sarah@recruiter.com>", "subject": "Data Analyst Internship - Quick Intro Call", "body": "Are you free for a 15-minute call next week?", "category": "To Reply"},
        {"from": "Investment Club <club@bentley.edu>", "subject": "Tonight: Semiconductor outlook discussion", "body": "Bring one slide on NVDA/TSMC outlook.", "category": "Finance"},
        {"from": "Mom <mom@example.com>", "subject": "Proud of you!", "body": "Call me when you can. Love, Mom", "category": "Personal"},
    ]
    if st.button("Analyze Inbox 🧠"):
        for email in demo_emails:
            st.markdown(f"### {email['category']}")
            with st.container(border=True):
                st.markdown(f"**{email['subject']}**")
                st.caption(email["from"])
                st.write(email["body"])
                if email["category"] in ["To Reply", "Finance"]:
                    st.code(
                        f"Hi, thanks for your message about '{email['subject']}'. I'll follow up soon.\n\nBest,\nMichael",
                        language="markdown"
                    )

# ---------- TAB 3: Daily Report ----------
with tab3:
    st.subheader("Generate Personalized Daily Market Report")
    if st.button("📄 Generate PDF Report"):
        from analysis import get_finance_news
        news = get_finance_news("markets")
        mood = compute_market_mood(news)
        outlooks = {t: "OK" for t in user_tickers}
        filename = "daily_report.pdf"
        generate_daily_report(filename, mood, outlooks, news)
        with open(filename, "rb") as f:
            st.download_button("Download Report", f, file_name="daily_report.pdf")
