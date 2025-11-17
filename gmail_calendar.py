import os
import datetime as dt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import streamlit as st

def get_creds():
    return Credentials(
        token=None,
        refresh_token=st.secrets["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=st.secrets["client_id"],
        client_secret=st.secrets["client_secret"]
    )


# -------------------------
# Emails
# -------------------------
def read_last_5_emails():
    creds = get_creds()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", maxResults=5
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return "Inbox is empty."

    out = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject"]
        ).execute()
        headers = msg["payload"]["headers"]
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No subject")
        out.append(f"**From:** {sender}\n**Subject:** {subject}\n")

    return "\n".join(out)


# -------------------------
# Calendar
# -------------------------
def get_calendar_events(max_events=10):
    creds = get_creds()
    service = build("calendar", "v3", credentials=creds)

    now = dt.datetime.utcnow().isoformat() + "Z"
    events = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_events,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    items = events.get("items", [])
    if not items:
        return "No upcoming events."

    out = []
    for e in items:
        start = e["start"].get("dateTime", e["start"].get("date"))
        out.append(f"- **{start}** — {e.get('summary','(No title)')}")

    return "\n".join(out)
