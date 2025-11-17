import streamlit as st
import requests
import urllib.parse

st.title("Google OAuth Refresh Token Generator")

CLIENT_ID = st.secrets.get("client_id", "")
CLIENT_SECRET = st.secrets.get("client_secret", "")
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

if not CLIENT_ID or not CLIENT_SECRET:
    st.error("Missing client_id or client_secret in Streamlit secrets.")
    st.stop()

st.markdown("### Step 1 — Click the button below to get your Google OAuth URL.")

scope = urllib.parse.quote(
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/calendar.readonly"
)

auth_url = (
    "https://accounts.google.com/o/oauth2/v2/auth"
    "?response_type=code"
    f"&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope={scope}"
    "&access_type=offline"
    "&prompt=consent"
)

if st.button("Generate Google OAuth URL"):
    st.code(auth_url)

st.markdown("### Step 2 — Paste the code Google gives you:")

auth_code = st.text_input("Enter authorization code here")

if st.button("Exchange code for refresh token"):
    if not auth_code:
        st.error("Please paste the authorization code first.")
    else:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": auth_code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        r = requests.post(token_url, data=data)
        result = r.json()

        if "refresh_token" in result:
            st.success("REFRESH TOKEN GENERATED!")
            st.code(result["refresh_token"])
        else:
            st.error("Failed to obtain refresh token.")
            st.json(result)
