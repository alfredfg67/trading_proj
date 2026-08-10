import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Helper functions ---

API_BASE = "http://localhost:8000/api/v1"

def get_headers():
    """Return auth headers if token exists."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def is_admin():
    """Check if the logged-in user is an admin."""
    return st.session_state.get("role") == "admin"

# --- Page config ---
st.set_page_config(page_title="Admin Panel", layout="wide")

# --- Token validation / input ---
# If token is not in session state or is invalid, show the input field.
valid_token = False
if "token" in st.session_state:
    # Test the token by trying to fetch users
    headers = get_headers()
    try:
        resp = requests.get(f"{API_BASE}/admin/users", headers=headers)
        if resp.status_code == 200:
            valid_token = True
        else:
            # Token invalid, clear it
            del st.session_state.token
            if "role" in st.session_state:
                del st.session_state.role
    except:
        pass

if not valid_token:
    st.warning("Please enter your admin token to access this page.")
    token_input = st.text_input("Admin Token", type="password")
    if token_input:
        # Verify token
        headers = {"Authorization": f"Bearer {token_input}"}
        try:
            resp = requests.get(f"{API_BASE}/admin/users", headers=headers)
            if resp.status_code == 200:
                st.session_state.token = token_input
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error(f"Invalid token: {resp.text}")
        except Exception as e:
            st.error(f"Error: {e}")
    st.stop()

# --- Check admin role ---
if not is_admin():
    st.error("Access denied: Admin privileges required.")
    st.stop()

st.title("👥 Admin Panel – User Management")

# --- Fetch users ---
@st.cache_data(ttl=60)
def fetch_users():
    headers = get_headers()
    try:
        resp = requests.get(f"{API_BASE}/admin/users", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Failed to fetch users: {resp.text}")
            return []
    except Exception as e:
        st.error(f"Error: {e}")
        return []

users = fetch_users()

if users:
    df = pd.DataFrame(users)
    # Select columns to display
    display_cols = ["id", "email", "role", "is_active", "is_locked", "failed_login_attempts", "last_login_at"]
    st.dataframe(df[display_cols], use_container_width=True)

    # --- Action buttons per user ---
    st.subheader("User Actions")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        user_id = st.number_input("User ID", min_value=1, step=1)
    with col2:
        if st.button("Unlock"):
            headers = get_headers()
            resp = requests.patch(f"{API_BASE}/admin/users/{user_id}/unlock", headers=headers)
            if resp.status_code == 200:
                st.success(f"User {user_id} unlocked.")
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")
    with col3:
        new_role = st.selectbox("New Role", ["user", "admin"], key="role_select")
        if st.button("Change Role"):
            headers = get_headers()
            resp = requests.patch(f"{API_BASE}/admin/users/{user_id}/role", headers=headers, json={"role": new_role})
            if resp.status_code == 200:
                st.success(f"User {user_id} role updated to {new_role}.")
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")
    with col4:
        if st.button("Delete (deactivate)"):
            headers = get_headers()
            resp = requests.delete(f"{API_BASE}/admin/users/{user_id}", headers=headers)
            if resp.status_code == 204:
                st.success(f"User {user_id} deactivated.")
                st.rerun()
            else:
                st.error(f"Failed: {resp.text}")
    with col5:
        if st.button("Reset Password"):
            headers = get_headers()
            resp = requests.post(f"{API_BASE}/admin/users/{user_id}/reset-password", headers=headers)
            if resp.status_code == 200:
                temp = resp.json().get("temporary_password")
                st.success(f"Temporary password for user {user_id}: **{temp}**")
            else:
                st.error(f"Failed: {resp.text}")

    # --- Create new user ---
    st.subheader("Create New User")
    with st.form("create_user_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        phone = st.text_input("Phone (optional)")
        whatsapp = st.text_input("WhatsApp (optional)")
        telegram = st.text_input("Telegram (optional)")
        submitted = st.form_submit_button("Create User")
        if submitted:
            if not email or not password:
                st.error("Email and password are required.")
            else:
                payload = {
                    "email": email,
                    "password": password,
                    "role": role,
                    "phone": phone or None,
                    "whatsapp": whatsapp or None,
                    "telegram": telegram or None
                }
                headers = get_headers()
                resp = requests.post(f"{API_BASE}/admin/users", headers=headers, json=payload)
                if resp.status_code == 201:
                    st.success(f"User {email} created.")
                    st.rerun()
                else:
                    st.error(f"Failed: {resp.text}")

else:
    st.info("No users found.")