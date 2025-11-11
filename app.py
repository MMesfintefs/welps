import os, re, requests, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# Brains you already have
from analysis import compute_market_mood, decision_signal, get_finance_news
from report import generate_daily_report

st.set_page_config(page_title="NOVA", page_icon="😊", layout="wide")

# -------------------- helpers --------------------
VALID_PERIODS = ["7d","1mo","3mo","6mo","1y","ytd","max"]

@st.cache_data(ttl=600)
def get_macro_snapshot():
    """FRED snapshot; falls back to placeholders if no key."""
    fred_key = os.getenv("FRED_API_KEY")
    if not fred_key:
        return {"Inflation": "N/A", "Unemployment": "N/A", "FedRate": "N/A"}
    try:
        base = "https://api.stlouisfed.org/fred/series/observations"
        def fred_series(series_id):
            r = requests.get(base, params={"series_id": series_id,
                                           "api_key": fred_key, "file_type":"json"}, timeout=10)
            r.raise_for_status()
            return float(r.json()["observations"][-1]["value"])
        # These are representative; tweak to what you prefer
        unemp = fred_series("UNRATE")
        fed = fred_series("FEDFUNDS")
        # CPIAUCSL is an index; keep simple and show latest level
        cpi = fred_series("CPIAUCSL")
        return {"Inflation": f"{cpi:.1f} (CPI idx)", "Unemployment": f"{unemp:.1f}%", "FedRate": f"{fed:.2f}%"}
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

def parse_request(text: str):
    """
    Very light intent parser.
    Returns dict like {"intent":"analyze","tickers":[...],"period":"1mo"}
                    or {"intent":"news","topic":"..."}
                    or {"intent":"macro"}
                    or {"intent":"report","tickers":[...]}
    """
    t = text.strip().lower()

    # report
    if t.startswith("report"):
        tickers = re.findall(r"[a-zA-Z]{1,5}(?:-[A-Z]{2,4})?", text.upper())
        return {"intent":"report", "tickers": list(dict.fromkeys(tickers)) or []}

    # macro
    if t.startswith("macro"):
        return {"intent":"macro"}

    # news
    if t.startswith("news") or t.startswith("headline"):
        topic = t.split(":",1)[1].strip() if ":" in t else t.replace("news","").strip()
        topic = topic or "markets"
        return {"intent":"news", "topic": topic}

    # analyze stocks
    if "analyze" in t or "for" in t or "," in t:
        # find period keyword
        period = None
        for p in VALID_PERIODS:
            if re.search(rf"\b{p}\b", t):
                period = p
                break
        if not period: period = "1mo"

        # extract tickers (AAPL, MSFT, BTC-USD, etc.)
        tickers = re.findall(r"\b[A-Z]{1,5}(?:-[A-Z]{2,4})?\b", text.upper())
        tickers = [x for x in tickers if x not in VALID_PERIODS]
        tickers = list(dict.fromkeys(tickers))  # de-dupe, preserve order
        return {"intent":"analyze", "tickers": tickers or [], "period": period}

    return {"intent":"help"}

def render_help():
    st.markdown("""
**Try these:**
- `analyze AAPL, NVDA for 3mo`
- `news: inflation and energy`
- `macro`
- `report for AAPL, MSFT, TSLA`
""")

# -------------------- UI --------------------
# Title row
left, mid, right = st.columns([1,2,1])
with mid:
    st.markdown("<h1 style='text-align:center'>NOVA 😊</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Your agentic market assistant. Ask for analysis, news, macro, or a report.</p>", unsafe_allow_html=True)

# Macro snapshot on the left as lightweight context
with left:
    st.markdown("### Macro Snapshot")
    macro = get_macro_snapshot()
    for k,v in macro.items():
        st.metric(k, v)

# Chat history container
if "chat" not in st.session_state:
    st.session_state.chat = []
chat_box = st.container()

# Replay prior messages
with chat_box:
    for role, content in st.session_state.chat:
        with st.chat_message(role):
            st.markdown(content)

# Input
user_text = st.chat_input("Type a request... e.g., analyze AAPL, NVDA for 1mo")
if user_text:
    # user message
    st.session_state.chat.append(("user", user_text))
    with st.chat_message("user"):
        st.markdown(user_text)

    intent = parse_request(user_text)

    with st.chat_message("assistant"):
        if intent["intent"] == "help":
            render_help()

        elif intent["intent"] == "macro":
            st.markdown("**Latest macro snapshot:**")
            cols = st.columns(3)
            for (k,v), c in zip(macro.items(), cols):
                with c: st.metric(k, v)

        elif intent["intent"] == "news":
            topic = intent["topic"]
            st.markdown(f"**Headlines for:** `{topic}`")
            news = get_finance_news(topic)
            for n in news:
                st.write(f"• **{n['title']}** — {n['source']}")
            mood = compute_market_mood(news)
            st.metric("Market Mood", f"{mood}/100")

        elif intent["intent"] == "analyze":
            tickers = intent["tickers"]
            period  = intent["period"]
            if not tickers:
                st.warning("Give me at least one ticker. Example: `analyze AAPL, MSFT for 3mo`")
            else:
                st.markdown(f"**Analyzing:** {', '.join(tickers)}  |  **Range:** {period}")
                results = []
                for tk in tickers:
                    data = get_stock_data(tk, period)
                    if not data:
                        st.warning(f"{tk}: no data.")
                        continue
                    results.append(data)
                    df = pd.DataFrame(data["history"])
                    fig = px.line(df, x="Date", y="Close", title=f"{tk} ({period})")
                    st.plotly_chart(fig, use_container_width=True)
                    sig = decision_signal(df.rename(columns={"Close":"close"}))
                    st.caption(f"Signal: {sig}")

                if results:
                    avg = sum(r["pct"] for r in results) / len(results)
                    stance = "Cautious" if avg < 0 else "Constructive"
                    st.metric("Market Outlook", stance, f"{avg:.2f}% avg daily move")

        elif intent["intent"] == "report":
            tickers = intent["tickers"]
            if not tickers:
                st.info("Report needs tickers. Example: `report for AAPL, MSFT, NVDA`")
            else:
                st.markdown(f"**Generating PDF report for:** {', '.join(tickers)}")
                news = get_finance_news("markets")
                mood = compute_market_mood(news)
                outlooks = {t: "OK" for t in tickers}
                name = f"daily_report_{datetime.date.today()}.pdf"
                generate_daily_report(name, mood, outlooks, news)
                with open(name,"rb") as f:
                    st.download_button("Download report", f, file_name=name)

        else:
            render_help()
