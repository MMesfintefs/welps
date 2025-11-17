import streamlit as st
import requests
import urllib.parse

st.title("Google OAuth Refresh Token Generator")

CLIENT_ID = st.secrets.get("client_id", "")
CLIENT_SECRET = st.secrets.get("client_secret", "")
REDIRECT_URI = st.secrets.get("redirect_uri", "")

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    st.error("Missing client_id, client_secret, or redirect_uri in Streamlit secrets.")
    st.stop()

scope = urllib.parse.quote(
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/calendar.readonly"
)

auth_url = (
    f"https://accounts.google.com/o/oauth2/v2/auth?"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={REDIRECT_URI}&"
    f"response_type=code&"
    f"scope={scope}&"
    f"access_type=offline&"
    f"prompt=consent"
)

st.markdown("### Step 1 — Click to generate OAuth login URL")
if st.button("Generate URL"):
    st.code(auth_url)

st.markdown("### Step 2 — Paste the code Google gives you below")
auth_code = st.text_input("Authorization code:")

if st.button("Get Refresh Token"):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    r = requests.post(token_url, data=data)
    response = r.json()

    if "refresh_token" in response:
        st.success("Here is your refresh token:")
        st.code(response["refresh_token"])
    else:
        st.error("Failed to get refresh token.")
        st.json(response)
