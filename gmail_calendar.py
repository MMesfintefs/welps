import os
import streamlit as st
import datetime
from datetime import timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# -------------------------------------------------
# SCOPES
# -------------------------------------------------
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send"]
CAL_SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_credentials():
    """
    Handles OAuth login for Gmail + Calendar using Streamlit Cloud.
    Token is stored in session_state automatically.
    """
    if "google_creds" in st.session_state:
        return st.session_state.google_creds

    client_id = st.secrets["gmail"]["client_id"]
    client_secret = st.secrets["gmail"]["client_secret"]
    redirect_uri = st.secrets["gmail"]["redirect_uri"]

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=GMAIL_SCOPES + CAL_SCOPES
    )

    creds = flow.run_local_server(port=0)

    st.session_state.google_creds = creds
    return creds


# -------------------------------------------------
# EMAIL FUNCTIONS
# -------------------------------------------------
def list_recent_emails(n=5):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", maxResults=n
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        emails.append(msg_data)

    return emails


def search_emails(query):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me", q=query
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg in messages:
        data = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        emails.append(data)
    return emails


def send_email(to, subject, body):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    import base64
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    return service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()


def draft_email(to, subject, body):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    import base64
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    return service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()


# -------------------------------------------------
# CALENDAR FUNCTIONS
# -------------------------------------------------
def list_events(days=7):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + "Z"
    later = (datetime.datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

    events = service.events().list(
        calendarId="primary", timeMin=now, timeMax=later,
        singleEvents=True, orderBy="startTime"
    ).execute()

    return events.get("items", [])


def create_meeting(title, start_dt, duration_minutes=30):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }

    return service.events().insert(
        calendarId="primary", body=event
    ).execute()


def find_next_free_slot(duration=30):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.utcnow()
    end = now + timedelta(days=2)

    events = list_events(days=2)

    pointer = now

    for event in events:
        start = datetime.datetime.fromisoformat(event["start"]["dateTime"])
        if (start - pointer).total_seconds() >= duration * 60:
            return pointer
        pointer = datetime.datetime.fromisoformat(event["end"]["dateTime"])

    return pointer
