# =========================
# FILE: gmail_calendar.py
# =========================

import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

CLIENT_ID = st.secrets["client_id"]
CLIENT_SECRET = st.secrets["client_secret"]
REDIRECT_URI = st.secrets["redirect_uri"]

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]


def google_auth_flow():
    return Flow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


def get_calendar_events(creds):
    service = build("calendar", "v3", credentials=creds)
    events = service.events().list(calendarId="primary", maxResults=10).execute()
    return events.get("items", [])


def get_gmail_messages(creds):
    service = build("gmail", "v1", credentials=creds)
    msgs = service.users().messages().list(userId="me", maxResults=5).execute()
    return msgs.get("messages", [])


def send_email(creds, to, subject, body):
    from email.mime.text import MIMEText
    import base64

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = build("gmail", "v1", credentials=creds)
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
