# ===============================
# NOVA — Expanded Streamlit Agent
# ===============================

import os
import re
import datetime as dt

import streamlit as st
from openai import OpenAI
import yfinance as yf
import pandas as pd
import plotly.express as px

from gmail_calendar import read_last_5_emails, get_calendar_events


# ------------------------------
# OpenAI client (new SDK)
# ------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY

client = OpenAI() if OPENAI_KEY else None


# ------------------------------
# Streamlit page config
# ------------------------------
st.set_page_config(
    page_title="NOVA — Agentic Assistant",
    page_icon="✨",
    layout="wide",
)

st.title("✨ NOVA — Agentic AI Assistant")
st.caption("Stocks · Gmail · Calendar · Smart Chat")


# ------------------------------
# Sidebar: status & commands
# ------------------------------
with st.sidebar:
    st.subheader("Status")

    st.markdown(
        f"- OpenAI: {'✅ configured' if OPENAI_KEY else '❌ missing OPENAI_API_KEY'}"
    )
    has_google = all(
        k in st.secrets
        for k in ("client_id", "client_secret", "refresh_token", "redirect_uri")
    )
    st.markdown(f"- Google (Gmail/Calendar): {'✅ configured' if has_google else '❌ missing Google secrets'}")

    st.markdown("---")
    st.subheader("How to talk to NOVA")
    st.markdown(
        """
- **Stocks**  
  - “Price of AAPL”  
  - “Check TSLA and MSFT”  
  - “Stock lookup NVDA”
- **Emails**  
  - “Read my last 5 emails”  
  - “Summarize my inbox”
- **Calendar**  
  - “Show upcoming events”  
  - “What’s on my schedule?”
- **Chat (fallback)**  
  - Anything else: general Q&A, advice, explanations
        """
    )


# ------------------------------
# Utility: ticker extraction
# ------------------------------
def extract_tickers(text: str) -> list[str]:
    """
    Very simple heuristic:
    - split on whitespace and commas
    - uppercase, alphabetic, length 1-5
    """
    raw_tokens = re.split(r"[,\s]+", text.upper())
    tickers = [t for t in raw_tokens if t.isalpha() and 1 <= len(t) <= 5]
    # de-duplicate, preserve order
    seen = set()
    ordered = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


# ------------------------------
# Handlers
# ------------------------------
def handle_stocks(user_message: str) -> dict:
    tickers = extract_tickers(user_message)
    if not tickers:
        return {
            "mode": "stocks",
            "text": "Which stock are you interested in? Try something like: `AAPL`, `TSLA`, or `NVDA`.",
            "stocks": [],
        }

    results = []
    for symbol in tickers:
        try:
            hist = yf.Ticker(symbol).history(period="1mo", interval="1d")
            if hist.empty:
                results.append(
                    {
                        "ticker": symbol,
                        "price": None,
                        "hist": None,
                        "error": "No data returned for this ticker.",
                    }
                )
                continue

            last_close = float(hist["Close"].iloc[-1])
            df = hist[["Close"]].rename(columns={"Close": "close"}).reset_index()
            results.append(
                {
                    "ticker": symbol,
                    "price": last_close,
                    "hist": df,
                    "error": None,
                }
            )
        except Exception as e:
            results.append(
                {
                    "ticker": symbol,
                    "price": None,
                    "hist": None,
                    "error": str(e),
                }
            )

    lines = []
    for r in results:
        if r["error"]:
            lines.append(f"• {r['ticker']}: ❌ {r['error']}")
        elif r["price"] is not None:
            lines.append(f"• {r['ticker']}: **${r['price']:.2f}**")
        else:
            lines.append(f"• {r['ticker']}: data not available.")

    header_text = "Here’s what I found:\n\n" + "\n".join(lines)

    return {
        "mode": "stocks",
        "text": header_text,
        "stocks": results,
    }


def handle_emails() -> dict:
    try:
        emails = read_last_5_emails()
        if not emails:
            return {
                "mode": "emails",
                "text": "Your inbox looks empty or I couldn’t find any messages.",
                "emails": [],
            }

        return {
            "mode": "emails",
            "text": f"I pulled your last **{len(emails)}** emails:",
            "emails": emails,
        }
    except Exception as e:
        return {
            "mode": "emails",
            "text": f"Email error: {e}",
            "emails": [],
        }


def handle_calendar() -> dict:
    try:
        events = get_calendar_events(max_events=10)
        if not events:
            return {
                "mode": "calendar",
                "text": "No upcoming events found on your primary calendar.",
                "events": [],
            }

        return {
            "mode": "calendar",
            "text": f"Here are your next **{len(events)}** events:",
            "events": events,
        }
    except Exception as e:
        return {
            "mode": "calendar",
            "text": f"Calendar error: {e}",
            "events": [],
        }


def handle_chat(user_message: str) -> dict:
    if client is None:
        return {
            "mode": "chat",
            "text": "AI chat is not configured because `OPENAI_API_KEY` is missing in secrets.",
        }

    try:
        completion = client.responses.create(
            model="gpt-4.1-mini",
            input=f"You are NOVA, an AI assistant embedded in a Streamlit app. "
                  f"User message: {user_message}",
        )
        reply_text = completion.output_text
        return {
            "mode": "chat",
            "text": reply_text,
        }
    except Exception as e:
        return {
            "mode": "chat",
            "text": f"AI error: {e}",
        }


# ------------------------------
# Router
# ------------------------------
def nova_dispatch(user_message: str) -> dict:
    msg = user_message.lower()

    # Stock intent: look for words or obvious ticker patterns
    if any(k in msg for k in ["stock", "stocks", "price", "quote", "chart"]):
        return handle_stocks(user_message)

    # Email intent
    if any(k in msg for k in ["email", "inbox", "gmail"]):
        return handle_emails()

    # Calendar intent
    if any(k in msg for k in ["calendar", "schedule", "event", "events", "meeting"]):
        return handle_calendar()

    # Fallback chat
    return handle_chat(user_message)


# ------------------------------
# UI rendering helpers
# ------------------------------
def render_result(result: dict):
    mode = result.get("mode", "chat")

    if mode == "stocks":
        st.markdown(result["text"])
        stocks = result.get("stocks", [])
        for s in stocks:
            if s["error"]:
                st.markdown(f"**{s['ticker']}** — ❌ {s['error']}")
                continue

            if s["price"] is None or s["hist"] is None:
                st.markdown(f"**{s['ticker']}** — data not available.")
                continue

            st.markdown(f"#### {s['ticker']} — ${s['price']:.2f}")
            df = s["hist"]
            fig = px.line(
                df,
                x="Date",
                y="close",
                title=f"{s['ticker']} — last 1 month",
            )
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    elif mode == "emails":
        st.markdown(result["text"])
        emails = result.get("emails", [])
        if not emails:
            return
        for e in emails:
            with st.container(border=True):
                st.markdown(f"**Subject:** {e.get('subject', '(No subject)')}")
                st.markdown(f"*From:* {e.get('from_', '(Unknown sender)')}")
                if e.get("date"):
                    st.markdown(f"*Date:* {e['date']}")
                snippet = e.get("snippet", "")
                if snippet:
                    st.write(snippet)

    elif mode == "calendar":
        st.markdown(result["text"])
        events = result.get("events", [])
        if not events:
            return
        for ev in events:
            with st.container(border=True):
                st.markdown(f"**{ev.get('summary', '(No title)')}**")
                start = ev.get("start")
                end = ev.get("end")
                location = ev.get("location")
                if start or end:
                    st.markdown(
                        f"*Time:* {start or 'N/A'} → {end or 'N/A'}"
                    )
                if location:
                    st.markdown(f"*Location:* {location}")

    else:  # generic chat
        st.markdown(result.get("text", ""))


# ------------------------------
# Session state for chat history
# ------------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []  # list of dicts: {"user": str, "result": dict}


# ------------------------------
# Chat loop
# ------------------------------
for turn in st.session_state["history"]:
    st.chat_message("user").write(turn["user"])
    with st.chat_message("assistant"):
        render_result(turn["result"])

user_input = st.chat_input("Ask NOVA something...")

if user_input:
    result = nova_dispatch(user_input)
    st.session_state["history"].append({"user": user_input, "result": result})

    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        render_result(result)
