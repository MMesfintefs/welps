import os
import re
import time
import json
import random
from datetime import datetime, timedelta

import requests
import pandas as pd
import yfinance as yf
import plotly.express as px
import streamlit as st

# ==============================
# ----------- THEME ------------
# ==============================
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
      /* Compact global paddings */
      .block-container { padding-top: 0.8rem; padding-bottom: 2.5rem; }

      /* Top bar: title left, search center, directory right */
      .topbar { 
        display: grid; 
        grid-template-columns: 1fr 2fr 1fr; 
        align-items: center; 
        gap: 1rem; 
        position: sticky; 
        top: 0; 
        z-index: 100; 
        background: #0e1117; 
        padding: .6rem .4rem .8rem .4rem; 
        border-bottom: 1px solid rgba(255,255,255,.06)
      }
      .agent-nav { text-align: right; }

      /* Drop-up history: fixed bottom-right */
      .dropup-wrap {
        position: fixed; 
        bottom: 14px; 
        right: 18px; 
        z-index: 200;
      }
      .dropup-panel {
        position: fixed;
        bottom: 54px;
        right: 18px;
        width: 420px;
        max-height: 54vh;
        overflow: auto;
        background: #0e1117;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px 12px;
        z-index: 199;
        box-shadow: 0 8px 26px rgba(0,0,0,.45);
      }

      /* News ticker: fixed bottom-left */
      .news-ticker {
        position: fixed;
        left: 18px;
        bottom: 14px;
        width: 520px;
        z-index: 200;
        background: #0e1117;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px 12px;
        box-shadow: 0 8px 26px rgba(0,0,0,.45);
      }
      .ticker-title { font-weight: 600; opacity: .8; font-size: .9rem; margin-bottom: 6px; }
      .ticker-item a { color: #e3e8f2; text-decoration: none; }
      .ticker-item a:hover { text-decoration: underline; }

      /* Tiny helper for subtle labels */
      .muted { opacity:.7; font-size:.85rem; }
    </style>
    """,
    unsafe_allow_html=True
)

# =================================
# --------- STATE/SECRETS ---------
# =================================
if "history" not in st.session_state:
    st.session_state.history = []               # [{t:int, cmd:str}]
if "dropup_open" not in st.session_state:
    st.session_state.dropup_open = False
if "calendar" not in st.session_state:
    # naive "calendar" to check conflicts
    st.session_state.calendar = []              # [{title, start, end}]
if "inbox_messages" not in st.session_state:
    # a more realistic same-day inbox list
    now = datetime.now()
    st.session_state.inbox_messages = [
        {"from_name": "HR", "from_email": "hr@company.com", "subject": "Benefits open enrollment closes Tuesday", "time": (now - timedelta(minutes=25)).strftime("%H:%M")},
        {"from_name": "Prof. Lee", "from_email": "lee@univ.edu", "subject": "Guest talk invite – travel details & honorarium", "time": (now - timedelta(minutes=49)).strftime("%H:%M")},
        {"from_name": "Morgan", "from_email": "morgan@funds.io", "subject": "Friday agenda: market backdrop + positioning", "time": (now - timedelta(hours=2)).strftime("%H:%M")},
        {"from_name": "Calendly", "from_email": "no-reply@calendly.com", "subject": "Invite: Client update at 2:30 PM", "time": (now - timedelta(hours=3)).strftime("%H:%M")},
    ]

# read secrets/env without crashing on HF or Streamlit Cloud
NEWS_API_KEY = (st.secrets.get("NEWS_API_KEY", None) if hasattr(st, "secrets") else None) or os.getenv("NEWS_API_KEY", "")

# =================================
# ----------- UTILITIES -----------
# =================================
def parse_command(cmd: str) -> dict:
    """
    Lightweight parser. Examples:
      - "lookup TSLA 6mo"
      - "lookup AAPL"
      - "email from today"
      - "news about energy"
    """
    cmd = cmd.strip()
    if not cmd:
        return {"type": "empty"}

    # stock lookup
    if cmd.lower().startswith("lookup"):
        m = re.match(r"lookup\s+([A-Za-z\.\-]+)(?:\s+(\d+[dwmy]))?$", cmd, re.IGNORECASE)
        if m:
            ticker = m.group(1).upper()
            period = m.group(2) or "3mo"
            return {"type": "stock_lookup", "ticker": ticker, "period": period}

    # inbox query
    if "email" in cmd.lower() and "today" in cmd.lower():
        return {"type": "inbox_today"}

    # news
    if cmd.lower().startswith("news"):
        topic = cmd[4:].strip() or "markets"
        return {"type": "news", "topic": topic}

    # fallback
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
    Returns up to n headlines. If NEWS_API_KEY missing, returns informative placeholders.
    rotate_index selects which slice to display (for rotation every minute).
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
        data = r.json()
        articles = data.get("articles", [])[:12]
        if not articles:
            return [{"title": "No headlines found.", "url": "#"}]
        start = rotate_index % max(1, len(articles))
        window = []
        for i in range(min(n, len(articles))):
            a = articles[(start + i) % len(articles)]
            window.append({
                "title": a.get("title") or "(untitled)",
                "url": a.get("url") or "#"
            })
        return window
    except Exception as e:
        return [{"title": f"News error: {e}", "url": "#"}]

def inbox_today_list():
    """Render a more realistic 'emails from today' list with reply and calendar options."""
    st.subheader("Inbox — Today")
    msgs = st.session_state.inbox_messages

    for idx, msg in enumerate(msgs, 1):
        cols = st.columns([0.06, 0.64, 0.18, 0.12])
        cols[0].markdown(f"**{idx}.**")
        cols[1].markdown(
            f"**{msg['subject']}**  \n"
            f"<span class='muted'>{msg['from_name']} &lt;{msg['from_email']}&gt;</span>",
            unsafe_allow_html=True
        )
        cols[2].markdown(f"<span class='muted'>{msg['time']}</span>", unsafe_allow_html=True)
        open_key = f"open_{idx}"
        with cols[3]:
            st.button("Open", key=open_key)

        if st.session_state.get(open_key):
            with st.expander("Preview / Respond"):
                st.write("_Message preview goes here…_")
                reply = st.text_area("Reply", placeholder="Type your reply…", key=f"reply_{idx}")
                send = st.button("Send reply", key=f"send_{idx}")
                if send:
                    st.success("Reply queued. (Mocked)")

                st.markdown("**Calendar:**")
                # quick invite time picker and conflict checker
                start_dt = st.datetime_input("Event start", datetime.now() + timedelta(hours=2), key=f"start_{idx}")
                end_dt = st.datetime_input("Event end", start_dt + timedelta(hours=1), key=f"end_{idx}")
                add = st.button("Add to calendar", key=f"addcal_{idx}")

                if add:
                    conflict = None
                    for ev in st.session_state.calendar:
                        # simple overlap check
                        if not (end_dt <= ev["start"] or start_dt >= ev["end"]):
                            conflict = ev
                            break
                    if conflict:
                        st.warning(f"Conflict with '{conflict['title']}' "
                                   f"({conflict['start'].strftime('%Y-%m-%d %H:%M')} – {conflict['end'].strftime('%H:%M')}).")
                        replace = st.button("Replace conflict with this event", key=f"replace_{idx}")
                        if replace:
                            st.session_state.calendar.remove(conflict)
                            st.session_state.calendar.append({"title": msg["subject"], "start": start_dt, "end": end_dt})
                            st.success("Replaced. Event added.")
                    else:
                        st.session_state.calendar.append({"title": msg["subject"], "start": start_dt, "end": end_dt})
                        st.success("Event added.")

def render_market_overview():
    st.write("### Market Overview & Sentiment Analysis ↪")
    st.info("Type your intent in the search bar (top-center), e.g. `lookup NVDA 6mo` or `news about rates`.")

def render_daily_report():
    st.subheader("Daily Report")
    st.write("A compact downloadable report would be generated here (PDF/markdown).")
    st.caption("Hook this to your synthesis pipeline and schedule a daily job if needed.")

# =================================
# --------- TOP BAR (UI) ----------
# =================================
st.markdown("<div class='topbar'>", unsafe_allow_html=True)

# Title (left)
left, mid, right = st.columns([1, 2, 1], vertical_alignment="center")
with left:
    st.markdown("### 🧠 Agentic AI")

# Search bar (middle)
with mid:
    user_cmd = st.text_input(
        "Type a request",
        placeholder="Examples:  lookup TSLA 6mo   •  news about energy   •  email from today",
        label_visibility="collapsed",
        key="global_command",
    )
    run_now = st.button("Run 🚀")
    if run_now and user_cmd.strip():
        record_history(user_cmd)

# Agent directory (right)
with right:
    cc1, cc2, cc3 = st.columns([1, 1, 1])
    with cc1:
        mv = st.button("Market")
    with cc2:
        ib = st.button("Inbox")
    with cc3:
        dr = st.button("Report")

st.markdown("</div>", unsafe_allow_html=True)  # end topbar

# =================================
# ---- SIDEBAR: STOCK LOOKUP ------
# =================================
st.sidebar.header("Stock Lookup")
ticker = st.sidebar.text_input("Ticker", "AAPL")
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1)
if st.sidebar.button("Analyze"):
    st.session_state.history.append({"t": int(time.time()), "cmd": f"lookup {ticker} {period}"})

info, err = stock_snapshot(ticker, period)
if err:
    st.sidebar.warning(err)
else:
    k1, k2 = st.sidebar.columns(2)
    k1.metric("Price", f"${info['price']:.2f}")
    k2.metric("Δ Day", f"{info['pct']:.2f}%")
    plot_history(info["history"], info["ticker"])

# =================================
# ----- MAIN BODY: AGENT VIEWS ----
# =================================
panel = "market"
if 'mv' in locals() and mv: panel = "market"
if 'ib' in locals() and ib: panel = "inbox"
if 'dr' in locals() and dr: panel = "daily"

# If user executed a command via Run:
if st.session_state.history and (run_now and user_cmd.strip()):
    parsed = parse_command(user_cmd)
    if parsed["type"] == "stock_lookup":
        panel = "market"
        with st.container():
            st.subheader(f"Lookup • {parsed['ticker']} ({parsed['period']})")
            info2, err2 = stock_snapshot(parsed["ticker"], parsed["period"])
            if err2:
                st.warning(err2)
            else:
                cols_ = st.columns(2)
                cols_[0].metric("Price", f"${info2['price']:.2f}")
                cols_[1].metric("Change", f"{info2['pct']:.2f}%")
                plot_history(info2["history"], info2["ticker"])
    elif parsed["type"] == "inbox_today":
        panel = "inbox"
    elif parsed["type"] == "news":
        panel = "market"
        st.subheader(f"News about **{parsed['topic']}**")
        rotation_index = int(time.time() // 60)  # rotates each minute
        res = fetch_news(n=3, rotate_index=rotation_index, topic=parsed["topic"])
        for item in res:
            st.markdown(f"- [{item['title']}]({item['url']})")
    else:
        panel = "market"
        st.info("I parsed that as a general request. Try `lookup NVDA 6mo`, `email from today`, or `news about energy`.")

# Render selected panel
if panel == "market":
    render_market_overview()
elif panel == "inbox":
    inbox_today_list()
elif panel == "daily":
    render_daily_report()

# =================================
# -------- DROP-UP HISTORY --------
# =================================
# Toggle button (Streamlit widget) + fixed-position containers via CSS/HTML
toggle_label = "🔎 History"
# Use a small form so the button toggles and reruns nicely
with st.container():
    clicked = st.button(toggle_label, key="dropup_toggle")
    if clicked:
        st.session_state.dropup_open = not st.session_state.dropup_open

# Render floating panels
st.markdown("<div class='dropup-wrap'></div>", unsafe_allow_html=True)

if st.session_state.dropup_open:
    with st.container():
        st.markdown("<div class='dropup-panel'>", unsafe_allow_html=True)
        st.markdown("**Search History**")
        if not st.session_state.history:
            st.caption("No history yet.")
        else:
            for h in reversed(st.session_state.history[-60:]):
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(h["t"]))
                st.markdown(f"- `{ts}` — {h['cmd']}")
        st.markdown("</div>", unsafe_allow_html=True)

# =================================
# ---------- NEWS TICKER ----------
# =================================
rotation_index = int(time.time() // 60)  # rotates every minute
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

# Auto-refresh the whole page every 60s so headlines rotate without clicks.
# If this annoys you, comment the next line.
st.markdown("<script>setTimeout(function(){window.location.reload();}, 60000);</script>", unsafe_allow_html=True)

# =================================
# ----- FUTURE: Voice / Agent -----
# =================================
# To add a voice/agentic loop later:
# - Build a small function `run_voice_agent(transcript: str) -> str`
# - In the top search bar, if `user_cmd` comes from a mic widget or STT,
#   pass it through your planner/reasoner and return an action/plan.
# - Render steps in the center panel and reuse stock/news/inbox helpers above.
# - This keeps UI intact and only swaps the "brains".
