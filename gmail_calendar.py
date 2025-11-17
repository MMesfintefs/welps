# =========================
# FILE: gmail_calendar.py
# =========================

import datetime as dt
import base64
from email.utils import parsedate_to_datetime

import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# SCOPES YOU MUST USE WHEN GENERATING REFRESH TOKEN
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
]


# ---------------------------------------------------
# INTERNAL — BUILD CREDS FROM SECRETS
# ---------------------------------------------------
def _get_credentials():
    required = ["client_id", "client_secret", "refresh_token"]
    for key in required:
        if key not in st.secrets or not st.secrets[key]:
            raise RuntimeError(f"Missing `{key}` in Streamlit secrets.")

    return Credentials.from_authorized_user_info(
        {
            "client_id": st.secrets["client_id"],
            "client_secret": st.secrets["client_secret"],
            "refresh_token": st.secrets["refresh_token"],
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=SCOPES,
    )


# ---------------------------------------------------
# GMAIL: Read last 5 emails (structured)
# ---------------------------------------------------
def read_last_5_emails():
    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    resp = service.users().messages().list(
        userId="me",
        maxResults=5,
        labelIds=["INBOX"],
    ).execute()

    messages = resp.get("messages", [])
    emails = []

    for m in messages:
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])

        def H(name):
            for h in headers:
                if h.get("name") == name:
                    return h.get("value")
            return None

        subject = H("Subject") or "(No subject)"
        sender = H("From") or "(Unknown sender)"
        date_raw = H("Date")
        snippet = msg.get("snippet", "")

        date_str = None
        if date_raw:
            try:
                dt_obj = parsedate_to_datetime(date_raw)
                date_str = dt_obj.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = date_raw

        emails.append({
            "subject": subject,
            "from_": sender,
            "date": date_str,
            "snippet": snippet,
        })

    return emails


# ---------------------------------------------------
# CALENDAR: List upcoming events
# ---------------------------------------------------
def get_calendar_events(max_events=10):
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = dt.datetime.utcnow().isoformat() + "Z"

    resp = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_events,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events_raw = resp.get("items", [])
    events = []

    for e in events_raw:
        summary = e.get("summary", "(No title)")
        location = e.get("location")

        start = format_time(e.get("start"))
        end = format_time(e.get("end"))

        events.append({
            "summary": summary,
            "start": start,
            "end": end,
            "location": location,
        })

    return events


def format_time(t):
    if not t:
        return None
    if "dateTime" in t:
        try:
            dt_obj = dt.datetime.fromisoformat(t["dateTime"].replace("Z", "+00:00"))
            return dt_obj.strftime("%Y-%m-%d %H:%M")
        except:
            return t["dateTime"]
    if "date" in t:
        return t["date"]
    return None
