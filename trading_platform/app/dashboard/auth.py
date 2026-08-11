import streamlit as st
import requests
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings  # optional, but we can use env

API_BASE = "http://localhost:8000/api/v1"

def login(email: str, password: str) -> bool:
    """Authenticate user and store tokens in session state."""
    try:
        resp = requests.post(
            f"{API_BASE}/auth/login",
            json={"email": email, "password": password}
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.token = data["access_token"]
            st.session_state.refresh_token = data["refresh_token"]
            st.session_state.token_expiry = datetime.utcnow() + timedelta(minutes=30)  # adjust as needed
            # Fetch user info (optional) – we can get role from token or from /users/me endpoint
            # For simplicity, decode token to get role and user_id
        try:
            payload = jwt.decode(data["access_token"], key="", options={"verify_signature": False})
            st.session_state.user_id = payload.get("sub")
            st.session_state.role = payload.get("role", "user")
        except Exception as e:
            st.warning(f"Could not decode session info: {e}")
            return True
        else:
            st.error(f"Login failed: {resp.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"Connection error: {e}")
        return False

def logout():
    """Clear session state and log out."""
    for key in ["token", "refresh_token", "token_expiry", "user_id", "role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def is_authenticated() -> bool:
    """Check if user is authenticated and token is not expired."""
    if "token" not in st.session_state:
        return False
    if "token_expiry" in st.session_state:
        # Add a small buffer (e.g., 30 seconds) to refresh early
        if datetime.utcnow() > st.session_state.token_expiry - timedelta(seconds=30):
            # Token expired or about to expire – try refresh
            return refresh_token()
    return True

def refresh_token() -> bool:
    """Attempt to refresh the access token using refresh token."""
    if "refresh_token" not in st.session_state:
        return False
    try:
        resp = requests.post(
            f"{API_BASE}/auth/refresh",
            json={"refresh_token": st.session_state.refresh_token}
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.token = data["access_token"]
            st.session_state.token_expiry = datetime.utcnow() + timedelta(minutes=30)
            return True
        else:
            # Refresh failed – clear session
            logout()
            return False
    except:
        return False

def get_headers():
    """Return auth headers for API calls."""
    if is_authenticated():
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}