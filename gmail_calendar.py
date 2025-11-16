import os
import streamlit as st
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# -------------------------------------------------------------
# OAuth Setup
# -------------------------------------------------------------
def load_client_config():
    """
    Builds a Google OAuth client config using Streamlit secrets.
    This replaces the JSON file Google usually gives you.
    """
    return {
        "installed": {
            "client_id": st.secrets["client_id"],
            "client_secret": st.secrets["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets["redirect_uri"]],
        }
    }


# -------------------------------------------------------------
# AUTHENTICATION HANDLER
# -------------------------------------------------------------
def ensure_google_login():
    """
    Handles login flow:
    1. If not logged in, redirect user to Google login
    2. After login, store Google OAuth tokens in session
    """

    if "google_tokens" not in st.session_state:
        st.session_state.google_tokens = None

    # Already authenticated
    if st.session_state.google_tokens:
        return st.session_state.google_tokens

    # Prompt login button
    st.warning("To enable Gmail and Calendar features, please log in with Google.")
    if st.button("Sign in with Google"):
        client_config = load_client_config()

        flow = Flow.from_client_config(
            client_config,
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/calendar.readonly",
            ],
        )

        flow.redirect_uri = st.secrets["redirect_uri"]
        auth_url, state = flow.authorization_url(prompt="consent")

        st.session_state.oauth_state = state
        st.markdown(f"[Click here to authorize Google]({auth_url})")

    return None


# -------------------------------------------------------------
# GMAIL Functions
# -------------------------------------------------------------
def gmail_service():
    tokens = st.session_state.get("google_tokens")
    if not tokens:
        return None

    creds = google.oauth2.credentials.Credentials(**tokens)
    return build("gmail", "v1", credentials=creds)


def read_latest_emails(n=5):
    """Returns the latest N emails from Gmail."""
    service = gmail_service()
    if not service:
        return "Google not authenticated."

    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=n, q="newer_than:7d")
        .execute()
    )

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        data = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="metadata")
            .execute()
        )
        headers = data.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
        emails.append(f"📩 **{subject}** — *{sender}*")

    return emails if emails else "No recent emails."


# -------------------------------------------------------------
# Calendar Functions
# -------------------------------------------------------------
def calendar_service():
    tokens = st.session_state.get("google_tokens")
    if not tokens:
        return None

    creds = google.oauth2.credentials.Credentials(**tokens)
    return build("calendar", "v3", credentials=creds)


def get_upcoming_events(n=5):
    """Returns upcoming Google Calendar events."""
    service = calendar_service()
    if not service:
        return "Google not authenticated."

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            maxResults=n,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    formatted = []

    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date"))
        summary = ev.get("summary", "(No Title)")
        formatted.append(f"📆 **{summary}** — {start}")

    return formatted if formatted else "No upcoming events found."
