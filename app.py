# ===============================
# NOVA — Agentic Streamlit App
# ===============================

import os
import re
import requests
import datetime as dt

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

from gmail_calendar import read_last_5_emails, get_calendar_events
from agentic_agent import AgenticTextAssistant, render_reasoning_block


# ---------------------------------------------------
# SAFE OPENAI INITIALIZATION
# ---------------------------------------------------
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()
client = None

def get_openai_client():
    """
    Safely initialize OpenAI client ONLY when needed.
    Fixes Streamlit's proxy injection bug.
    """
    global client

    if client is not None:
        return client

    if not OPENAI_KEY:
        return None

    os.environ["OPENAI_API_KEY"] = OPENAI_KEY

    try:
        from openai import OpenAI
        client = OpenAI(http_client=None)   # prevents the 'proxies' error
        return client
    except Exception as e:
        st.error(f"OpenAI initialization error: {e}")
        return None


# ---------------------------------------------------
# STREAMLIT CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="NOVA",
    page_icon="✨",
    layout="wide"
)

st.title("✨ NOVA")


# ---------------------------------------------------
# SNAPSHOT: Weather + Time + Date
# ---------------------------------------------------
col1, col2 = st.columns([1, 1])

# TIME + DATE
with col1:
    now = dt.datetime.now()
    st.markdown(f"### 🕒 {now.strftime('%A, %B %d — %I:%M %p')}")

# WEATHER
with col2:
    WEATHER_KEY = st.secrets.get("WEATHER_API_KEY", "")
    DEFAULT_CITY = "Boston"

    if WEATHER_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={DEFAULT_CITY}&appid={WEATHER_KEY}&units=metric"
            data = requests.get(url).json()
            temp = data["main"]["temp"]
            cond = data["weather"][0]["description"].title()
            st.markdown(f"### 🌤 {DEFAULT_CITY}")
            st.markdown(f"**{temp}°C — {cond}**")
        except:
            st.markdown("### 🌤 Weather unavailable")
    else:
        st.markdown("### 🌤 Weather key missing")


# ---------------------------------------------------
# SIDEBAR STATUS
# ---------------------------------------------------
with st.sidebar:
    st.subheader("Status")

    st.markdown(f"- OpenAI: {'✅' if OPENAI_KEY else '❌ Missing OPENAI_API_KEY'}")

    google_ok = all(
        st.secrets.get(k, "").strip() 
        for k in ["client_id", "client_secret", "refresh_token", "redirect_uri"]
    )
    st.markdown(f"- Google APIs: {'✅' if google_ok else '❌ Missing Google credentials'}")

    st.markdown("---")
    st.subheader("Commands")
    st.markdown("""
- **Stocks:**  
  - “Price of AAPL”  
  - “Check TSLA + MSFT”

- **Emails:**  
  - “Read my inbox”

- **Calendar:**  
  - “Upcoming events”

- **Chat:**  
  - Anything else
""")


# ---------------------------------------------------
# TICKER EXTRACTION
# ---------------------------------------------------
def extract_tickers(text):
    tokens = re.split(r"[,\s]+", text.upper())
    tickers = [t for t in tokens if t.isalpha() and 1 <= len(t) <= 5]

    seen = set()
    result = []
    for t in tickers:
        if t not in seen:
            result.append(t)
            seen.add(t)
    return result


# ---------------------------------------------------
# STOCK HANDLER
# ---------------------------------------------------
def handle_stocks(msg):
    tickers = extract_tickers(msg)
    if not tickers:
        return {"mode": "stocks", "text": "Which stock?", "stocks": []}

    results = []

    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="1mo", interval="1d")
            if hist.empty:
                results.append({"ticker": t, "price": None, "hist": None,
                                "error": "No data available."})
                continue

            last = float(hist["Close"].iloc[-1])
            df = hist[["Close"]].rename(columns={"Close": "close"}).reset_index()

            results.append({"ticker": t, "price": last, "hist": df, "error": None})

        except Exception as e:
            results.append({"ticker": t, "price": None, "hist": None, "error": str(e)})

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
# EMAIL HANDLER
# ---------------------------------------------------
def handle_emails():
    try:
        emails = read_last_5_emails()
        return {
            "mode": "emails",
            "text": f"I pulled your last {len(emails)} emails:",
            "emails": emails
        }
    except Exception as e:
        return {"mode": "emails", "text": f"Email error: {e}", "emails": []}


# ---------------------------------------------------
# CALENDAR HANDLER
# ---------------------------------------------------
def handle_calendar():
    try:
        events = get_calendar_events(max_events=10)
        return {
            "mode": "calendar",
            "text": f"Here are your next {len(events)} events:",
            "events": events
        }
    except Exception as e:
        return {"mode": "calendar", "text": f"Calendar error: {e}", "events": []}


# ---------------------------------------------------
# FALLBACK CHAT
# ---------------------------------------------------
def handle_chat(msg):
    client = get_openai_client()
    if client is None:
        return {"mode": "chat", "text": "Missing OPENAI_API_KEY."}

    try:
        out = client.responses.create(
            model="gpt-4.1-mini",
            input=msg
        )
        return {"mode": "chat", "text": out.output_text}
    except Exception as e:
        return {"mode": "chat", "text": f"AI error: {e}"}


# ---------------------------------------------------
# DISPATCHER
# ---------------------------------------------------
def nova_dispatch(msg):
    low = msg.lower()

    if any(k in low for k in ["stock", "price", "quote", "chart"]):
        return handle_stocks(msg)

    if any(k in low for k in ["email", "inbox", "gmail"]):
        return handle_emails()

    if any(k in low for k in ["calendar", "schedule", "events"]):
        return handle_calendar()

    return handle_chat(msg)


# ---------------------------------------------------
# RENDER BLOCK
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
            fig = px.line(r["hist"], x="Date", y="close",
                          title=f"{r['ticker']} — last 1 month")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    elif mode == "emails":
        st.markdown(result["text"])
        for e in result["emails"]:
            with st.container(border=True):
                st.markdown(f"**Subject:** {e['subject']}")
                st.markdown(f"*From:* {e['from_']}")
                st.markdown(f"*Date:* {e['date']}")
                st.write(e["snippet"])

    elif mode == "calendar":
        st.markdown(result["text"])
        for ev in result["events"]:
            with st.container(border=True):
                st.markdown(f"**{ev['summary']}**")
                st.markdown(f"*Start:* {ev['start']} → *End:* {ev['end']}")
                if ev["location"]:
                    st.markdown(f"*Location:* {ev['location']}")

    else:
        st.markdown(result["text"])


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
if "history" not in st.session_state:
    st.session_state["history"] = []

if "agentic_assistant" not in st.session_state:
    st.session_state["agentic_assistant"] = AgenticTextAssistant()

if "agentic_history" not in st.session_state:
    st.session_state["agentic_history"] = []


# ---------------------------------------------------
# TABS: NOVA + AGENTIC REASONING
# ---------------------------------------------------
tab_nova, tab_agentic = st.tabs(["✨ NOVA Chat", "🧠 Agentic Reasoning"])


# === TAB 1 — NOVA CHAT ===
with tab_nova:
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


# === TAB 2 — AGENTIC REASONING ===
with tab_agentic:
    st.markdown("Type something to see NOVA's internal reasoning, intents, entities, and plan.")
    text_query = st.text_input(
        "Your text:",
        placeholder="e.g., Summarize the benefits of renewable energy"
    )

    if st.button("Run Agentic Reasoning", disabled=not text_query.strip()):
        assistant = st.session_state["agentic_assistant"]
        res = assistant.process(text_query.strip())
        st.session_state["agentic_history"].append(res)

    for res in reversed(st.session_state["agentic_history"]):
        with st.container(border=True):
            render_reasoning_block(st, res)
