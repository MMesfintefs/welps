import os
import re
import time
import json
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
      /* Remove default top padding */
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

      /* Right-aligned agent nav */
      .agent-nav { text-align: right; }
      .agent-nav button { margin-left: .25rem; }

      /* Drop-up history button (fixed bottom-right) */
      .dropup-btn {
        position: fixed; 
        bottom: 14px; 
        right: 18px; 
        z-index: 200;
      }
      .dropup-panel {
        position: fixed;
        bottom: 54px;
        right: 18px;
        width: 380px;
        max-height: 50vh;
        overflow: auto;
        background: #0e1117;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 8px 10px;
        z-index: 199;
        box-shadow: 0 8px 26px rgba(0,0,0,.45);
      }

      /* News ticker: fixed bottom-left */
      .news-ticker {
        position: fixed;
        left: 18px;
        bottom: 14px;
        width: 480px;
        z-index: 200;
        background: #0e1117;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 8px 10px;
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
# --------- STATE/SECRETS ---------
# =================================
if "history" not in st.session_state:
    st.session_state.history = []

if "dropup_open" not in st.session_state:
    st.session_state.dropup_open = False

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

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
    if cmd.lower().startswith("lookup"):
        m = re.match(r"lookup\s+([A-Za-z\.\-]+)(?:\s+(\d+[dwmy]))?$", cmd, re.IGNORECASE)
        if m:
            ticker = m.group(1).upper()
            period = m.group(2) or "3mo"
            return {"type": "stock_lookup", "ticker": ticker, "period": period}
    if "email" in cmd.lower():
        return {"type": "inbox_list", "query": cmd}
    if cmd.lower().startswith("news"):
        # optionally: news about topic
        topic = cmd[4:].strip() or "markets"
        return {"type": "news", "topic": topic}
    # fallback
    return {"type": "unknown", "text": cmd}


def record_history(command: str):
    ts = int(time.time())
    st.session_state.history.append({"t": ts, "cmd": command})


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
    fig.update_layout(height=350, margin=dict(l=10,r=10,t=40,b=10))
    st.plotly_chart(fig, use_container_width=True)


def fetch_news(n=3, rotate_index=0, topic="markets"):
    """
    Returns up to n headlines. If NEWS_API_KEY missing, returns informative placeholders.
    rotate_index selects which slice to display (for rotation every minute).
    """
    if not NEWS_API_KEY:
        return [{"title": "Add NEWS_API_KEY in secrets to enable live headlines.", "url": "#"}]

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
        # rotate window of length n
        if not articles:
            return [{"title": "No headlines found.", "url": "#"}]
        start = rotate_index % max(1, len(articles))
        window = []
        for i in range(n):
            a = articles[(start + i) % len(articles)]
            window.append({"title": a.get("title") or "(untitled)", "url": a.get("url") or "#"})
        return window
    except Exception as e:
        return [{"title": f"News error: {e}", "url": "#"}]


def inbox_list_preview():
    """
    Placeholder for a realistic inbox panel.
    Replace with IMAP/OAuth integration (Gmail/Outlook). We mock today's messages.
    """
    # TODO: Plug real email here. This is a sane UI that lists sender + subject first.
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
        # If “Open” clicked, show body preview + actions
        if st.session_state.get(f"open_{i}"):
            with st.expander("Preview / Respond"):
                st.write("_Message preview goes here…_")
                st.text_area("Reply", placeholder="Type your reply…")
                colA, colB = st.columns(2)
                colA.button("Send reply", key=f"send_{i}")
                colB.button("Add to calendar", key=f"addcal_{i}")
                st.caption("Calendar check placeholder: _We’ll verify conflicts before adding._")


def render_market_overview():
    st.write("### Market Overview & Sentiment Analysis ↪")
    # You can hang your higher-level agent planning/orchestration here if desired.
    st.info("Type your intent in the search bar (top-center), e.g. `lookup NVDA 6mo` or `news about rates`.")


def render_daily_report():
    st.subheader("Daily Report")
    st.write("A compact downloadable report would be generated here (PDF/markdown).")
    st.caption("Hook this to your synthesis pipeline and schedule a daily job if needed.")


# =================================
# --------- TOP BAR (UI) ----------
# =================================
with st.container():
    cols = st.columns([1,2,1], gap="small")
    with cols[0]:
        st.markdown("<div class='topbar'><div style='grid-column:1/4'></div></div>", unsafe_allow_html=True)
    # top bar content must render outside markup:
st.markdown("<div class='topbar'>", unsafe_allow_html=True)

# Title (left)
left, mid, right = st.columns([1,2,1], gap="small")
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
    run_now = st.button("Run 🚀", use_container_width=False)
    if run_now and user_cmd.strip():
        record_history(user_cmd)

# Agent directory (right)
with right:
    # cheap right-aligned nav via columns
    cc1, cc2, cc3 = st.columns([1,1,1])
    with cc1:
        mv = st.button("Market Overview")
    with cc2:
        ib = st.button("Inbox")
    with cc3:
        dr = st.button("Daily Report")

st.markdown("</div>", unsafe_allow_html=True)  # end topbar

# =================================
# ---- SIDEBAR: STOCK LOOKUP ------
# =================================
st.sidebar.header("Stock Lookup")
ticker = st.sidebar.text_input("Ticker", "AAPL")
period = st.sidebar.selectbox("Period", ["1mo","3mo","6mo","1y","2y","5y"], index=1)
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
# Decide which panel to show based on top-right clicks OR parsed command
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
    elif parsed["type"] == "inbox_list":
        panel = "inbox"
    elif parsed["type"] == "news":
        panel = "market"
        st.subheader(f"News about **{parsed['topic']}**")
        res = fetch_news(n=3, topic=parsed["topic"])
        for item in res:
            st.markdown(f"- [{item['title']}]({item['url']})")
    else:
        panel = "market"
        st.info("I parsed that as a general request. Try `lookup NVDA 6mo` or `news about energy`.")

# Render selected panel
if panel == "market":
    render_market_overview()
elif panel == "inbox":
    inbox_list_preview()
elif panel == "daily":
    render_daily_report()

# =================================
# -------- DROP-UP HISTORY --------
# =================================
def toggle_dropup():
    st.session_state.dropup_open = not st.session_state.dropup_open

st.markdown(
    f"""
    <div class='dropup-btn'>
        <button onclick="window.dispatchEvent(new Event('toggle_dropup'))">
            🔎 History
        </button>
    </div>
    """,
    unsafe_allow_html=True
)

# Tiny JS event bridge to trigger a rerun for toggling
dropup_js = """
<script>
(function(){
  // ensure we only bind once
  if (window.__dropup_bound__) return;
  window.__dropup_bound__ = true;
  window.addEventListener('toggle_dropup', () => {
    fetch('?dropup=1').then(()=>window.location.reload());
  });
})();
</script>
"""
st.markdown(dropup_js, unsafe_allow_html=True)

# react to the query param for toggling
if st.query_params.get("dropup") == "1":
    st.session_state.dropup_open = not st.session_state.dropup_open
    st.query_params.clear()

if st.session_state.dropup_open:
    with st.container():
        st.markdown("<div class='dropup-panel'>", unsafe_allow_html=True)
        st.markdown("**Search History**")
        if not st.session_state.history:
            st.caption("No history yet.")
        else:
            for h in reversed(st.session_state.history[-40:]):
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(h["t"]))
                st.markdown(f"- `{ts}` — {h['cmd']}")
        st.markdown("</div>", unsafe_allow_html=True)

# =================================
# ---------- NEWS TICKER ----------
# =================================
# Autorefresh every minute to rotate headlines
st_autorefresh_key = st.experimental_rerun  # not used; quiet flake8
st_autorefresh = st.experimental_rerun  # keep local linters happy

rotation_index = int(time.time() // 60)  # rotates every minute
headlines = fetch_news(n=3, rotate_index=rotation_index, topic="markets")

with st.container():
    st.markdown("<div class='news-ticker'>", unsafe_allow_html=True)
    st.markdown("<div class='ticker-title'>🗞️ Latest Headlines</div>", unsafe_allow_html=True)
    for h in headlines:
        st.markdown(f"<div class='ticker-item'>• <a href='{h['url']}' target='_blank'>{h['title']}</a></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
