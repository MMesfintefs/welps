import os
import re
import time
import requests
import pandas as pd
import yfinance as yf
import plotly.express as px
import streamlit as st

# ==============================
# ------- RUNTIME & THEME ------
# ==============================
# Silence headless/telemetry warnings typical on Spaces
os.environ["STREAMLIT_SERVER_HEADLESS"] = "1"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

st.set_page_config(
    page_title="Agentic AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- CSS: layout polish ---------------
st.markdown(
    """
    <style>
      .block-container { padding-top: 0.8rem; padding-bottom: 2.5rem; }
      .topbar { 
        display: grid; grid-template-columns: 1fr 2fr 1fr; 
        align-items: center; gap: 1rem; position: sticky; 
        top: 0; z-index: 100; background: #0e1117; 
        padding: .6rem .4rem .8rem .4rem; 
        border-bottom: 1px solid rgba(255,255,255,.06);
      }
      .agent-nav { text-align: right; }
      .dropup-btn {
        position: fixed; bottom: 14px; right: 18px; z-index: 200;
      }
      .dropup-panel {
        position: fixed; bottom: 54px; right: 18px; width: 380px;
        max-height: 50vh; overflow: auto; background: #0e1117;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px; padding: 8px 10px; z-index: 199;
        box-shadow: 0 8px 26px rgba(0,0,0,.45);
      }
      .news-ticker {
        position: fixed; left: 18px; bottom: 14px; width: 480px;
        z-index: 200; background: #0e1117;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px; padding: 8px 10px;
        box-shadow: 0 8px 26px rgba(0,0,0,.45);
      }
      .ticker-title { font-weight: 600; opacity: .8; font-size: .9rem; margin-bottom: 6px; }
      .ticker-item a { color: #e3e8f2; text-decoration: none; }
      .ticker-item a:hover { text-decoration: underline; }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# --------- STATE / KEYS ----------
# =================================
if "history" not in st.session_state:
    st.session_state.history = []
if "dropup_open" not in st.session_state:
    st.session_state.dropup_open = False

# Hugging Face Spaces exposes secrets as environment variables
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# =================================
# ----------- UTILITIES -----------
# =================================
def parse_command(cmd: str) -> dict:
    """
    Examples:
      - "lookup TSLA 6mo"
      - "lookup AAPL"
      - "email from today"
      - "news about energy"
    """
    cmd = cmd.strip()
    if cmd.lower().startswith("lookup"):
        m = re.match(r"lookup\s+([A-Za-z\.\-]+)(?:\s+(\d+[dwmy]))?$", cmd, re.IGNORECASE)
        if m:
            ticker = m.group(1).upper()
            period = m.group(2) or "3mo"
            return {"type": "stock_lookup", "ticker": ticker, "period": period}
    if "email" in cmd.lower():
        return {"type": "inbox_list", "query": cmd}
    if cmd.lower().startswith("news"):
        topic = cmd[4:].strip() or "markets"
        return {"type": "news", "topic": topic}
    return {"type": "unknown", "text": cmd}


def record_history(command: str):
    st.session_state.history.append({"t": int(time.time()), "cmd": command})


def stock_snapshot(ticker: str, period: str = "3mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return None, "No data returned for that ticker/period."
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        price = float(latest["Close"])
        pct = float(((latest["Close"] - prev["Close"]) / prev["Close"]) * 100) if prev["Close"] != 0 else 0.0
        info = {
            "ticker": ticker,
            "price": price,
            "pct": pct,
            "history": hist.reset_index(),
        }
        return info, None
    except Exception as e:
        return None, f"Error: {e}"


def plot_history(df: pd.DataFrame, ticker: str):
    fig = px.line(df, x="Date", y="Close", title=f"{ticker} — Close Price")
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)


def fetch_news(n=3, rotate_index=0, topic="markets"):
    """
    Returns up to n headlines. Uses NewsAPI if key available; otherwise returns a hint.
    rotate_index lets us rotate headlines roughly once per minute.
    """
    if not NEWS_API_KEY:
        return [{"title": "Add NEWS_API_KEY in Space → Settings → Secrets to enable live headlines.", "url": "#"}]

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": topic,
            "pageSize": 12,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": NEWS_API_KEY,
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        articles = r.json().get("articles", [])[:12]
        if not articles:
            return [{"title": "No headlines found.", "url": "#"}]
        start = rotate_index % len(articles)
        window = []
        for i in range(n):
            a = articles[(start + i) % len(articles)]
            window.append({"title": a.get("title") or "(untitled)", "url": a.get("url") or "#"})
        return window
    except Exception as e:
        return [{"title": f"News error: {e}", "url": "#"}]


def inbox_list_preview():
    """
    Placeholder inbox list UI. Swap with real Gmail/Outlook integration later.
    """
    mock_today = [
        {"from": "HR <hr@company.com>", "subject": "Benefits open enrollment reminder", "ts": "10:12"},
        {"from": "Prof. Lee <lee@univ.edu>", "subject": "Guest talk invite & travel details", "ts": "09:47"},
        {"from": "Morgan <morgan@funds.io>", "subject": "Friday meeting agenda (updated)", "ts": "08:35"},
    ]
    st.subheader("Inbox — Today")
    for i, msg in enumerate(mock_today, 1):
        cols = st.columns([0.06, 0.64, 0.18, 0.12])
        cols[0].markdown(f"**{i}.**")
        cols[1].markdown(f"**{msg['subject']}**  \n<small style='opacity:.7'>{msg['from']}</small>", unsafe_allow_html=True)
        cols[2].markdown(f"<small style='opacity:.7'>{msg['ts']}</small>", unsafe_allow_html=True)
        with cols[3]:
            st.button("Open", key=f"open_{i}")
        if st.session_state.get(f"open_{i}"):
            with st.expander("Preview / Respond"):
                st.write("_Message preview goes here…_")
                st.text_area("Reply", placeholder="Type your reply…")
                colA, colB = st.columns(2)
                colA.button("Send reply", key=f"send_{i}")
                colB.button("Add to calendar", key=f"addcal_{i}")
                st.caption("Calendar check placeholder: we’ll verify conflicts before adding.")


def render_market_overview():
    st.write("### Market Overview & Sentiment Analysis ↪")
    st.info("Type your intent in the search bar (top-center), e.g. `lookup NVDA 6mo` or `news about rates`.")


def render_daily_report():
    st.subheader("Daily Report")
    st.write("A compact downloadable report would be generated here (PDF/markdown).")


# =================================
# --------- TOP BAR (UI) ----------
# =================================
st.markdown("<div class='topbar'>", unsafe_allow_html=True)

left, mid, right = st.columns([1, 2, 1], gap="small")
with left:
    st.markdown("### 🧠 Agentic AI")

with mid:
    user_cmd = st.text_input(
        "Type a request",
        placeholder="Examples:  lookup TSLA 6mo   •   news about energy   •   email from today",
        label_visibility="collapsed",
        key="global_command",
    )
    run_now = st.button("Run 🚀")
    if run_now and user_cmd.strip():
        record_history(user_cmd)

with right:
    c1, c2, c3 = st.columns(3)
    mv = c1.button("Market")
    ib = c2.button("Inbox")
    dr = c3.button("Report")

st.markdown("</div>", unsafe_allow_html=True)

# =================================
# ---- SIDEBAR: STOCK LOOKUP ------
# =================================
st.sidebar.header("Stock Lookup")
ticker = st.sidebar.text_input("Ticker", "AAPL")
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1)
if st.sidebar.button("Analyze"):
    record_history(f"lookup {ticker} {period}")

info, err = stock_snapshot(ticker, period)
if err:
    st.sidebar.warning(err)
else:
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Price", f"${info['price']:.2f}")
    c2.metric("Δ Day", f"{info['pct']:.2f}%")
    plot_history(info["history"], info["ticker"])

# =================================
# ----- MAIN BODY: PANELS ---------
# =================================
panel = "market"
if mv: panel = "market"
if ib: panel = "inbox"
if dr: panel = "daily"

if run_now and user_cmd.strip():
    parsed = parse_command(user_cmd)
    if parsed["type"] == "stock_lookup":
        panel = "market"
        st.subheader(f"Lookup • {parsed['ticker']} ({parsed['period']})")
        info2, err2 = stock_snapshot(parsed["ticker"], parsed["period"])
        if err2:
            st.warning(err2)
        else:
            cols_ = st.columns(2)
            cols_[0].metric("Price", f"${info2['price']:.2f}")
            cols_[1].metric("Change", f"{info2['pct']:.2f}%")
            plot_history(info2["history"], info2["ticker"])
    elif parsed["type"] == "inbox_list":
        panel = "inbox"
    elif parsed["type"] == "news":
        panel = "market"
        st.subheader(f"News about **{parsed['topic']}**")
        for item in fetch_news(n=3, topic=parsed["topic"]):
            st.markdown(f"- [{item['title']}]({item['url']})")
    else:
        st.info("Try `lookup NVDA 6mo` or `news about energy`.")

if panel == "market":
    render_market_overview()
elif panel == "inbox":
    inbox_list_preview()
elif panel == "daily":
    render_daily_report()

# =================================
# ---------- NEWS TICKER ----------
# =================================
rotation_index = int(time.time() // 60)  # rotates window every minute
headlines = fetch_news(n=3, rotate_index=rotation_index, topic="markets")

with st.container():
    st.markdown("<div class='news-ticker'>", unsafe_allow_html=True)
    st.markdown("<div class='ticker-title'>🗞️ Latest Headlines</div>", unsafe_allow_html=True)
    for h in headlines:
        st.markdown(
            f"<div class='ticker-item'>• <a href='{h['url']}' target='_blank'>{h['title']}</a></div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)
