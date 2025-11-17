# =======================
# NOVA — Minimal Version
# =======================

import os
import re
import streamlit as st
import yfinance as yf
from openai import OpenAI
from gmail_calendar import read_last_5_emails, get_calendar_events

st.set_page_config(page_title="NOVA", page_icon="✨")

st.title("✨ NOVA (Minimal Demo)")

# -------------------------
# Load secrets
# -------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()
CLIENT_ID = st.secrets.get("client_id", "").strip()
CLIENT_SECRET = st.secrets.get("client_secret", "").strip()
REFRESH_TOKEN = st.secrets.get("refresh_token", "").strip()
REDIRECT_URI = st.secrets.get("redirect_uri", "").strip()

google_ready = all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, REDIRECT_URI])
openai_ready = True if OPENAI_KEY else False

# -------------------------
# Initialize OpenAI
# -------------------------
if openai_ready:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    client = OpenAI()
else:
    client = None


# -------------------------
# Sidebar status
# -------------------------
with st.sidebar:
    st.subheader("Status")
    st.write(f"OpenAI: {'✅' if openai_ready else '❌ Missing key'}")
    st.write(f"Gmail/Calendar: {'✅' if google_ready else '❌ Missing credentials'}")

    st.markdown("---")
    st.subheader("Commands")
    st.markdown("""
**Stocks**
- price of AAPL  
- check TSLA and MSFT  

**Emails**
- read my inbox  

**Calendar**
- upcoming events  

**Chat**
- ask anything  
""")


# -------------------------
# STOCK HANDLER
# -------------------------
def extract_tickers(text):
    tokens = re.split(r"[,\s]+", text.upper())
    return [t for t in tokens if t.isalpha() and 1 <= len(t) <= 5]


def handle_stock_query(msg):
    tickers = extract_tickers(msg)
    out = []

    for t in tickers:
        try:
            data = yf.Ticker(t).history(period="1mo")
            if data.empty:
                out.append(f"**{t}** — No data")
            else:
                price = float(data["Close"].iloc[-1])
                out.append(f"**{t}** — ${price}")
        except:
            out.append(f"**{t}** — Error")

    return "\n".join(out) if out else "No tickers found."


# -------------------------
# CHAT
# -------------------------
def ai_chat(msg):
    if not client:
        return "OpenAI not configured."

    try:
        r = client.responses.create(
            model="gpt-4.1-mini",
            input=msg
        )
        return r.output_text
    except Exception as e:
        return f"AI error: {e}"


# -------------------------
# Main chat history
# -------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []

for h in st.session_state["history"]:
    st.chat_message("user").write(h["user"])
    st.chat_message("assistant").write(h["bot"])

msg = st.chat_input("Ask NOVA…")

if msg:
    low = msg.lower()

    # STOCKS
    if "price" in low or "stock" in low or any(x in low for x in ["tsla", "aapl", "msft"]):
        reply = handle_stock_query(msg)

    # EMAILS
    elif "email" in low or "inbox" in low:
        if google_ready:
            try:
                reply = read_last_5_emails()
            except Exception as e:
                reply = f"Email error: {e}"
        else:
            reply = "Google API not configured."

    # CALENDAR
    elif "calendar" in low or "event" in low:
        if google_ready:
            try:
                reply = get_calendar_events(10)
            except Exception as e:
                reply = f"Calendar error: {e}"
        else:
            reply = "Google API not configured."

    # DEFAULT AI CHAT
    else:
        reply = ai_chat(msg)

    # Save + display
    st.session_state["history"].append({"user": msg, "bot": reply})
    st.chat_message("user").write(msg)
    st.chat_message("assistant").write(reply)
