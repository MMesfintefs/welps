# =======================
# NOVA — Minimal Demo App
# =======================

import os
import re
import datetime as dt

import streamlit as st
import yfinance as yf
from openai import OpenAI


# -------------------------
# Page setup
# -------------------------
st.set_page_config(page_title="NOVA", page_icon="✨")
st.title("✨ NOVA")


# -------------------------
# Secrets / API keys
# -------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()

if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    client = OpenAI()
else:
    client = None


# -------------------------
# Fake inbox + fake calendar
# -------------------------
SAMPLE_EMAILS = [
    {
        "from": "Professor Li",
        "subject": "Updated Exam Schedule",
        "snippet": "Hi everyone, the midterm has been moved to next Tuesday at 3:30pm..."
    },
    {
        "from": "Registrar",
        "subject": "Registration Confirmed",
        "snippet": "Your registration for Spring 2026 has been successfully processed..."
    },
    {
        "from": "Amazon",
        "subject": "Your Order Has Shipped",
        "snippet": "Your package with the noise-cancelling headphones is on the way..."
    },
    {
        "from": "Career Services",
        "subject": "Networking Event Reminder",
        "snippet": "Don’t forget the Analytics & AI Career Night tomorrow at 6pm..."
    },
    {
        "from": "Billing",
        "subject": "Statement Available",
        "snippet": "Your latest account statement is now available in the student portal..."
    },
]

SAMPLE_EVENTS = [
    {
        "start": "2025-11-18 15:30",
        "end": "2025-11-18 16:45",
        "title": "CS Class – Agentic AI Lecture",
        "location": "Room 204, CIS Lab"
    },
    {
        "start": "2025-11-19 09:00",
        "end": "2025-11-19 10:00",
        "title": "Team Meeting – Project NOVA",
        "location": "Zoom"
    },
    {
        "start": "2025-11-20 18:00",
        "end": "2025-11-20 20:00",
        "title": "Analytics & AI Networking Night",
        "location": "Student Center"
    },
    {
        "start": "2025-11-22 14:00",
        "end": "2025-11-22 16:00",
        "title": "Exam Review Session",
        "location": "Library 3rd Floor"
    },
]


def render_fake_inbox():
    if not SAMPLE_EMAILS:
        return "📭 Inbox is empty."

    lines = ["📬 **Recent emails (demo)**\n"]
    for e in SAMPLE_EMAILS:
        lines.append(
            f"- **From:** {e['from']}  \n"
            f"  **Subject:** {e['subject']}  \n"
            f"  _{e['snippet']}_\n"
        )
    return "\n".join(lines)


def render_fake_calendar():
    if not SAMPLE_EVENTS:
        return "📅 No upcoming events (demo)."

    lines = ["📅 **Upcoming events (demo)**\n"]
    for ev in SAMPLE_EVENTS:
        lines.append(
            f"- **{ev['start']} → {ev['end']}**  \n"
            f"  **{ev['title']}**  \n"
            f"  _{ev['location']}_\n"
        )
    return "\n".join(lines)


# -------------------------
# Stocks handler (live data)
# -------------------------
def extract_tickers(text: str):
    tokens = re.split(r"[,\s]+", text.upper())
    tickers = []
    for t in tokens:
        if t.isalpha() and 1 <= len(t) <= 5:
            if t not in ["PRICE", "OF", "CHECK", "STOCK", "STOCKS"]:
                tickers.append(t)
    # dedupe
    seen = set()
    out = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def handle_stock_query(msg: str) -> str:
    tickers = extract_tickers(msg)
    if not tickers:
        return "I didn’t see any valid tickers. Try something like: `price of AAPL and TSLA`."

    lines = ["📈 **Stock prices (last close)**\n"]
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if hist.empty:
                lines.append(f"- **{t}** — no recent data.")
            else:
                price = float(hist["Close"].iloc[-1])
                lines.append(f"- **{t}** — ${price:.2f}")
        except Exception:
            lines.append(f"- **{t}** — error fetching data.")
    return "\n".join(lines)


# -------------------------
# OpenAI chat
# -------------------------
def ai_chat(msg: str) -> str:
    if client is None:
        return "AI not configured. Please add `OPENAI_API_KEY` to Streamlit secrets."

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are NOVA, a concise helpful assistant."
                },
                {"role": "user", "content": msg},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI error: {e}"


# -------------------------
# Sidebar info
# -------------------------
with st.sidebar:
    st.subheader("Status")
    st.write(f"OpenAI: {'✅' if OPENAI_KEY else '❌ Missing OPENAI_API_KEY'}")
    st.markdown("---")
    st.subheader("How to use NOVA")
    st.markdown(
        """
**Examples:**

- 💬 Chat:  
  `What is agentic AI in simple terms?`

- 📈 Stocks:  
  `Price of AAPL and TSLA`  

- 📫 Inbox (demo):  
  `Show my recent emails`  
  `Read my inbox`  

- 📅 Calendar (demo):  
  `What events are coming up?`  
  `Show my schedule`
"""
    )


# -------------------------
# Session state (chat history)
# -------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []


# replay history
for turn in st.session_state["history"]:
    st.chat_message("user").write(turn["user"])
    st.chat_message("assistant").write(turn["bot"])


# -------------------------
# Main input
# -------------------------
user_msg = st.chat_input("Ask NOVA something...")

if user_msg:
    lower = user_msg.lower()

    # Stocks
    if any(k in lower for k in ["stock", "price", "quote"]):
        bot_reply = handle_stock_query(user_msg)

    # Fake inbox
    elif any(k in lower for k in ["email", "inbox", "mail"]):
        bot_reply = render_fake_inbox()

    # Fake calendar
    elif any(k in lower for k in ["calendar", "schedule", "event", "upcoming"]):
        bot_reply = render_fake_calendar()

    # Default: AI chat
    else:
        bot_reply = ai_chat(user_msg)

    # Save + render
    st.session_state["history"].append({"user": user_msg, "bot": bot_reply})
    st.chat_message("user").write(user_msg)
    st.chat_message("assistant").markdown(bot_reply)
