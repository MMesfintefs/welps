# ===============================
# NOVA — Minimal Working Version
# ===============================

import os
import streamlit as st
from openai import OpenAI
import yfinance as yf

from gmail_calendar import read_last_5_emails, get_calendar_events


# ------------------------------
# Load Secrets (your TOML format)
# ------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
os.environ["OPENAI_API_KEY"] = OPENAI_KEY     # REQUIRED for new SDK

# Initialize OpenAI client (no api_key argument allowed)
client = OpenAI()


# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(page_title="NOVA", page_icon="✨", layout="wide")
st.title("✨ NOVA — Your Personal AI Assistant")


# ------------------------------
# Core NOVA Logic
# ------------------------------
def nova_reply(user_message):

    msg = user_message.lower().strip()

    # ---- EMAILS ----
    if "email" in msg or "inbox" in msg:
        try:
            emails = read_last_5_emails()
            return "\n\n".join([f"- {e}" for e in emails])
        except Exception as e:
            return f"Email error: {e}"

    # ---- CALENDAR ----
    if "calendar" in msg or "event" in msg or "schedule" in msg:
        try:
            events = get_calendar_events()
            return "\n".join(events)
        except Exception as e:
            return f"Calendar error: {e}"

    # ---- STOCKS ----
    if "stock" in msg or "price" in msg:
        words = user_message.upper().split()
        tickers = [w for w in words if w.isalpha() and 1 <= len(w) <= 5]

        if not tickers:
            return "Which stock? Example: AAPL, TSLA, MSFT"

        out = []
        for t in tickers:
            try:
                data = yf.Ticker(t).history(period="1d")
                price = data["Close"].iloc[-1]
                out.append(f"{t} → ${price:.2f}")
            except:
                out.append(f"{t} → not found")

        return "\n".join(out)

    # ---- FALLBACK AI ----
    try:
        completion = client.responses.create(
            model="gpt-4.1-mini",
            input=user_message
        )
        return completion.output_text
    except Exception as e:
        return f"AI error: {e}"


# ------------------------------
# Chat interface
# ------------------------------
user_input = st.chat_input("Ask Nova anything...")

if user_input:
    st.chat_message("user").write(user_input)
    response = nova_reply(user_input)
    st.chat_message("assistant").write(response)
