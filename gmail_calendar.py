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

# ---------------------------------------------------
# Google OAuth Flow
# ---------------------------------------------------
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

# ---------------------------------------------------
# GMAIL — Read last 5 emails
# ---------------------------------------------------
def read_last_5_emails():
    """Returns the subjects of the last 5 emails."""
    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", maxResults=5
    ).execute()

    messages = results.get("messages", [])
    email_list = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"]
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = next(
            (h["value"] for h in headers if h["name"] == "Subject"),
            "(No Subject)"
        )
        email_list.append(subject)

    return email_list

# ---------------------------------------------------
# GMAIL — Send an email
# ---------------------------------------------------
def send_email(creds, to, subject, body):
    from email.mime.text import MIMEText
    import base64

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service = build("gmail", "v1", credentials=creds)

    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

# ---------------------------------------------------
# CALENDAR — List next 10 events
# ---------------------------------------------------
def get_calendar_events():
    creds = _load_credentials()
    service = build("calendar", "v3", credentials=creds)

    events = service.events().list(
        calendarId="primary",
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    items = events.get("items", [])
    parsed = []

    for e in items:
        summary = e.get("summary", "(No Title)")
        start = e["start"].get("dateTime", e["start"].get("date"))
        parsed.append(f"{start} — {summary}")

    return parsed

# ---------------------------------------------------
# INTERNAL — Load stored credentials
# ---------------------------------------------------
def _load_credentials():
    """
    Loads the OAuth credentials stored in Streamlit secrets.
    """
    return Credentials.from_authorized_user_info(
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": st.secrets["refresh_token"],
            "token_uri": "https://oauth2.googleapis.com/token"
        },
        SCOPES
    )
