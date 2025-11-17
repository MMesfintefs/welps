# ===============================
# NOVA — Expanded Streamlit Agent
# ===============================

import os
import re
import datetime as dt

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

from gmail_calendar import read_last_5_emails, get_calendar_events


# ---------------------------------------------------
# OPENAI SAFE INITIALIZATION (critical for Streamlit!)
# ---------------------------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()
client = None

def get_openai_client():
    """
    We only initialize OpenAI when needed.
    This avoids the TypeError crash you experienced on Streamlit Cloud.
    """
    global client

    if client is not None:
        return client

    if not OPENAI_KEY:
        return None

    # Must set this BEFORE constructing OpenAI()
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY

    try:
        from openai import OpenAI
        client = OpenAI()
        return client
    except Exception as e:
        st.error(f"OpenAI initialization error: {e}")
        return None


# ---------------------------------------------------
# STREAMLIT PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="NOVA — Agentic Assistant",
    page_icon="✨",
    layout="wide",
)

st.title("✨ NOVA — Agentic AI Assistant")
st.caption("Stocks · Gmail · Calendar · Smart Chat")


# ---------------------------------------------------
# SIDEBAR STATUS
# ---------------------------------------------------
with st.sidebar:
    st.subheader("Status")
    st.markdown(f"- OpenAI: {'✅' if OPENAI_KEY else '❌ missing OPENAI_API_KEY'}")

    google_ok = all(
        k in st.secrets and st.secrets[k] 
        for k in ["client_id", "client_secret", "refresh_token", "redirect_uri"]
    )
    st.markdown(f"- Google APIs: {'✅' if google_ok else '❌ missing Google credentials'}")

    st.markdown("---")
    st.subheader("Commands")
    st.markdown("""
- **Stocks**  
  - “Price of AAPL”  
  - “Check TSLA and MSFT”
- **Emails**  
  - “Read my inbox”
- **Calendar**  
  - “Upcoming events”
- **Chat**  
  - Anything else
""")


# ---------------------------------------------------
# Utility: extract tickers
# ---------------------------------------------------
def extract_tickers(text):
    tokens = re.split(r"[,\s]+", text.upper())
    tickers = [t for t in tokens if t.isalpha() and 1 <= len(t) <= 5]

    seen = set()
    ordered = []
    for t in tickers:
        if t not in seen:
            ordered.append(t)
            seen.add(t)

    return ordered


# ---------------------------------------------------
# HANDLER: Stocks
# ---------------------------------------------------
def handle_stocks(msg):
    tickers = extract_tickers(msg)

    if not tickers:
        return {
            "mode": "stocks",
            "text": "Which stock symbol? Example: AAPL, TSLA, NVDA.",
            "stocks": [],
        }

    results = []

    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="1mo", interval="1d")
            if hist.empty:
                results.append({
                    "ticker": t,
                    "price": None,
                    "hist": None,
                    "error": "No data available."
                })
                continue

            last_close = float(hist["Close"].iloc[-1])
            df = hist[["Close"]].rename(columns={"Close": "close"}).reset_index()

            results.append({
                "ticker": t,
                "price": last_close,
                "hist": df,
                "error": None
            })

        except Exception as e:
            results.append({
                "ticker": t,
                "price": None,
                "hist": None,
                "error": str(e)
            })

    lines = []
    for r in results:
        if r["error"]:
            lines.append(f"• {r['ticker']} — ❌ {r['error']}")
        else:
            lines.append(f"• {r['ticker']}: **${r['price']:.2f}**")

    return {
        "mode": "stocks",
        "text": "Here’s what I found:\n\n" + "\n".join(lines),
        "stocks": results,
    }


# ---------------------------------------------------
# HANDLER: Emails
# ---------------------------------------------------
def handle_emails():
    try:
        emails = read_last_5_emails()
        if not emails:
            return {
                "mode": "emails",
                "text": "No recent emails found.",
                "emails": []
            }

        return {
            "mode": "emails",
            "text": f"I pulled your last {len(emails)} emails:",
            "emails": emails,
        }

    except Exception as e:
        return {"mode": "emails", "text": f"Email error: {e}", "emails": []}


# ---------------------------------------------------
# HANDLER: Calendar
# ---------------------------------------------------
def handle_calendar():
    try:
        events = get_calendar_events(max_events=10)
        if not events:
            return {
                "mode": "calendar",
                "text": "No upcoming events found.",
                "events": []
            }

        return {
            "mode": "calendar",
            "text": f"Here are your next {len(events)} events:",
            "events": events,
        }

    except Exception as e:
        return {"mode": "calendar", "text": f"Calendar error: {e}", "events": []}


# ---------------------------------------------------
# HANDLER: Fallback AI
# ---------------------------------------------------
def handle_chat(msg):
    client = get_openai_client()
    if client is None:
        return {"mode": "chat", "text": "AI not configured. Missing OPENAI_API_KEY."}

    try:
        out = client.responses.create(
            model="gpt-4.1-mini",
            input=msg
        )
        return {"mode": "chat", "text": out.output_text}

    except Exception as e:
        return {"mode": "chat", "text": f"AI error: {e}"}


# ---------------------------------------------------
# Dispatcher
# ---------------------------------------------------
def nova_dispatch(msg):
    low = msg.lower()

    if any(k in low for k in ["stock", "price", "quote", "chart"]):
        return handle_stocks(msg)

    if any(k in low for k in ["email", "inbox", "gmail"]):
        return handle_emails()

    if any(k in low for k in ["calendar", "schedule", "event", "events"]):
        return handle_calendar()

    return handle_chat(msg)


# ---------------------------------------------------
# Rendering UI blocks
# ---------------------------------------------------
def render(result):
    mode = result["mode"]

    if mode == "stocks":
        st.markdown(result["text"])
        for r in result["stocks"]:
            if r["error"]:
                st.markdown(f"**{r['ticker']}** — {r['error']}")
                continue

            st.markdown(f"### {r['ticker']} — ${r['price']:.2f}")

            df = r["hist"]
            fig = px.line(df, x="Date", y="close", title=f"{r['ticker']} — last 1 month")
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))

            st.plotly_chart(fig, use_container_width=True)

    elif mode == "emails":
        st.markdown(result["text"])
        for e in result["emails"]:
            with st.container(border=True):
                st.markdown(f"**Subject:** {e['subject']}")
                st.markdown(f"*From:* {e['from_']}")
                if e["date"]:
                    st.markdown(f"*Date:* {e['date']}")
                if e["snippet"]:
                    st.write(e["snippet"])

    elif mode == "calendar":
        st.markdown(result["text"])
        for ev in result["events"]:
            with st.container(border=True):
                st.markdown(f"**{ev['summary']}**")
                st.markdown(f"*Start:* {ev['start']}  →  *End:* {ev['end']}")
                if ev["location"]:
                    st.markdown(f"*Location:* {ev['location']}")

    else:  # chat
        st.markdown(result["text"])


# ---------------------------------------------------
# CHAT SESSION STATE
# ---------------------------------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []

for turn in st.session_state["history"]:
    st.chat_message("user").write(turn["user"])
    with st.chat_message("assistant"):
        render(turn["result"])

user_input = st.chat_input("Ask NOVA something...")

if user_input:
    result = nova_dispatch(user_input)
    st.session_state["history"].append({"user": user_input, "result": result})

    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        render(result)
