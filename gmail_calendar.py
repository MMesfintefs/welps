# =========================
# FILE: gmail_calendar.py
# =========================
"""
Gmail & Google Calendar helpers for NOVA.

Assumes the following keys exist in st.secrets:

- client_id
- client_secret
- redirect_uri
- refresh_token

Scopes:
- Gmail readonly
- Gmail send (optional)
- Calendar read
"""

import datetime as dt
import base64
from email.utils import parsedate_to_datetime

import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Scopes must match what you used when generating the refresh token
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
]


# ---------------------------------------------------
# INTERNAL — Load stored credentials
# ---------------------------------------------------
def _get_credentials() -> Credentials:
    """
    Constructs a Credentials object from values stored in Streamlit secrets.
    Uses a refresh_token so access tokens auto-refresh in the background.
    """
    required_keys = ["client_id", "client_secret", "refresh_token", "redirect_uri"]
    for k in required_keys:
        if k not in st.secrets or not st.secrets[k]:
            raise RuntimeError(f"Missing `{k}` in Streamlit secrets.")

    client_id = st.secrets["client_id"]
    client_secret = st.secrets["client_secret"]
    refresh_token = st.secrets["refresh_token"]

    creds = Credentials.from_authorized_user_info(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=SCOPES,
    )
    return creds


# ---------------------------------------------------
# GMAIL — Read last 5 emails
# ---------------------------------------------------
def read_last_5_emails():
    """
    Returns a list of up to 5 emails from the user's inbox, each as:
    {
      "subject": str,
      "from_": str,
      "date": str (ISO-like),
      "snippet": str,
    }
    """
    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    results = service.users().messages().list(
        userId="me",
        maxResults=5,
        labelIds=["INBOX"],
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = msg_data.get("payload", {}).get("headers", [])
        subject = _get_header(headers, "Subject") or "(No subject)"
        from_ = _get_header(headers, "From") or "(Unknown sender)"
        date_raw = _get_header(headers, "Date")
        snippet = msg_data.get("snippet", "")

        date_str = None
        if date_raw:
            try:
                dt_obj = parsedate_to_datetime(date_raw)
                # normalize to local-ish string; you can format however you like
                date_str = dt_obj.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = date_raw

        emails.append(
            {
                "subject": subject,
                "from_": from_,
                "date": date_str,
                "snippet": snippet,
            }
        )

    return emails


def _get_header(headers, name):
    for h in headers:
        if h.get("name") == name:
            return h.get("value")
    return None


# ---------------------------------------------------
# GMAIL — Send an email (optional)
# ---------------------------------------------------
def send_email(to: str, subject: str, body: str):
    """
    Basic text-only email sender using Gmail API.
    Not currently wired into NOVA UI, but available if needed.
    """
    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    from email.mime.text import MIMEText

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    send_body = {"raw": raw}

    service.users().messages().send(userId="me", body=send_body).execute()


# ---------------------------------------------------
# CALENDAR — List upcoming events
# ---------------------------------------------------
def get_calendar_events(max_events: int = 10):
    """
    Returns a list of upcoming events on the primary calendar, each as:
    {
      "summary": str,
      "start": str,
      "end": str,
      "location": str | None,
    }
    """
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = dt.datetime.utcnow().isoformat() + "Z"  # 'Z' = UTC time

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_events,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    items = events_result.get("items", [])
    parsed = []

    for e in items:
        summary = e.get("summary", "(No title)")
        start = _format_event_time(e.get("start"))
        end = _format_event_time(e.get("end"))
        location = e.get("location")

        parsed.append(
            {
                "summary": summary,
                "start": start,
                "end": end,
                "location": location,
            }
        )

    return parsed


def _format_event_time(time_dict):
    if not time_dict:
        return None
    # can be all-day ("date") or specific ("dateTime")
    if "dateTime" in time_dict:
        try:
            dt_obj = dt.datetime.fromisoformat(time_dict["dateTime"].replace("Z", "+00:00"))
            return dt_obj.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return time_dict["dateTime"]
    if "date" in time_dict:
        return time_dict["date"]
    return None
