"""
Chronos — Authentication & Personalization Engine
===================================================

Multi-user authentication system with profile-based theming.
Uses bcrypt for secure password hashing and Streamlit session state
for session management.

Profile Types
-------------
  Standard     — Frosted Obsidian theme (dark / gold-purple accent)
  Kids         — Sky Blue theme, safety-filtered content, softer UI
  Professional — Clean dark theme with muted tones

All credentials are stored locally in the SQLite database,
ensuring complete data sovereignty — no external auth providers needed.
"""

import bcrypt
import streamlit as st
import extra_streamlit_components as stx

from database.queries import (
    create_user,
    get_user_by_username,
    username_exists,
    create_session_token,
    get_session_user,
    delete_session_token,
)

_COOKIE_NAME = "chronos_session"

@st.cache_resource
def _get_cookie_manager():
    return stx.CookieManager(key="chronos_cookie_mgr")


# ---------------------------------------------------------------------------
# Password Utilities
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        # Ensure hashed is bytes (convert if it's a string)
        hashed_bytes = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
        return bcrypt.checkpw(password.encode("utf-8"), hashed_bytes)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------

def init_auth_state() -> None:
    """Initialize authentication-related session state keys.
    Auto-restores session from cookie if not already authenticated.
    """
    defaults = {
        "authenticated": False,
        "user_id": "",
        "username": "",
        "user_name": "",
        "profile_type": "Standard",
        "auth_page": "login",
        "session_token": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Auto-restore from cookie if not authenticated
    if not st.session_state.get("authenticated"):
        try:
            cm = _get_cookie_manager()
            token = cm.get(_COOKIE_NAME)
            if token:
                user = get_session_user(token)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user["id"]
                    st.session_state["username"] = user["username"]
                    st.session_state["user_name"] = user["name"]
                    st.session_state["profile_type"] = user["profile_type"]
                    st.session_state["session_token"] = token
        except Exception:
            pass  # Cookie not available yet — first render


def logout() -> None:
    """Clear the authentication session and cookie."""
    try:
        token = st.session_state.get("session_token", "")
        if token:
            delete_session_token(token)
        cm = _get_cookie_manager()
        cm.delete(_COOKIE_NAME)
    except Exception:
        pass
    for key in ["authenticated", "user_id", "username", "user_name", "profile_type", "session_token"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["authenticated"] = False
    st.rerun()


# ---------------------------------------------------------------------------
# Glassmorphism Auth CSS
# ---------------------------------------------------------------------------

_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

#MainMenu, header, footer, .stDeployButton,
[data-testid="stToolbar"] { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

*, *::before, *::after { box-sizing: border-box; }

html, body {
    margin: 0; padding: 0;
    font-family: 'Inter', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #f0f0f0;
    overflow: hidden;
}

/* Animated gradient background */
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    25%  { background-position: 100% 50%; }
    50%  { background-position: 100% 100%; }
    75%  { background-position: 0% 100%; }
    100% { background-position: 0% 50%; }
}

.stApp {
    background: linear-gradient(-45deg,
        #0a0a14, #12051f, #050d1a, #0a0f14,
        #140a1e, #0d0518, #091218, #0a0a14) !important;
    background-size: 400% 400% !important;
    animation: gradientShift 25s ease infinite !important;
    min-height: 100vh;
}

/* Noise overlay */
.stApp::after {
    content: "";
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    opacity: 0.03;
    pointer-events: none;
    z-index: 0;
}

.main .block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stMain"] > div,
.stMainBlockContainer,
section.main > div.block-container {
    max-width: 520px !important;
    padding-top: 12vh !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    margin-left: auto !important;
    margin-right: auto !important;
    position: relative;
    z-index: 1;
}

/* Glass card styling for the form */
[data-testid="stForm"] {
    background: rgba(255,255,255,0.04) !important;
    backdrop-filter: blur(40px) saturate(200%) !important;
    -webkit-backdrop-filter: blur(40px) saturate(200%) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 20px !important;
    padding: 40px 36px !important;
    box-shadow: 0 16px 64px rgba(0,0,0,0.6),
                inset 0 1px 0 rgba(255,255,255,0.05) !important;
}

/* Input fields */
[data-testid="stForm"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 10px !important;
    color: #f0f0f0 !important;
    font-size: 0.85rem !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stForm"] input:focus {
    border-color: rgba(167,139,250,0.5) !important;
    box-shadow: 0 0 0 2px rgba(167,139,250,0.1) !important;
}

/* Labels */
[data-testid="stForm"] label {
    font-size: 0.55rem !important;
    letter-spacing: 0.20em !important;
    text-transform: uppercase !important;
    color: rgba(255,255,255,0.35) !important;
    font-weight: 600 !important;
}

/* Selectbox in form */
[data-testid="stForm"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 10px !important;
}
[data-testid="stForm"] [data-baseweb="select"] * {
    color: rgba(255,255,255,0.82) !important;
    font-size: 0.82rem !important;
}

/* Submit button */
[data-testid="stForm"] button[type="submit"],
[data-testid="stForm"] .stButton > button {
    background: linear-gradient(135deg, rgba(167,139,250,0.25), rgba(124,58,237,0.35)) !important;
    border: 1px solid rgba(167,139,250,0.35) !important;
    color: #e0d4ff !important;
    border-radius: 10px !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    width: 100%;
    transition: all 0.25s ease !important;
}
[data-testid="stForm"] button[type="submit"]:hover,
[data-testid="stForm"] .stButton > button:hover {
    background: linear-gradient(135deg, rgba(167,139,250,0.40), rgba(124,58,237,0.50)) !important;
    border-color: rgba(167,139,250,0.55) !important;
    box-shadow: 0 0 20px rgba(167,139,250,0.20) !important;
}

/* Toggle link buttons (outside form) */
.stButton > button {
    background: transparent !important;
    border: none !important;
    color: rgba(167,139,250,0.7) !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    text-decoration: underline !important;
    padding: 4px 8px !important;
}
.stButton > button:hover {
    color: rgba(167,139,250,1) !important;
}

/* Hide sidebar on auth page */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>
"""


# ---------------------------------------------------------------------------
# Auth Pages
# ---------------------------------------------------------------------------

def render_auth_page() -> None:
    """Render the login or registration page with glassmorphism design."""
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    if st.session_state.get("auth_page") == "register":
        _render_register()
    else:
        _render_login()


def _render_login() -> None:
    """Login form with glassmorphism card."""
    st.markdown("""
    <div style="text-align:center;margin-bottom:32px">
      <p style="font-size:0.5rem;letter-spacing:0.30em;text-transform:uppercase;
                color:rgba(255,255,255,0.18);margin:0 0 10px;font-weight:700">
        Chronos
      </p>
      <p style="font-size:1.6rem;font-weight:200;letter-spacing:-0.02em;
                margin:0;color:rgba(255,255,255,0.9)">
        Welcome Back
      </p>
      <p style="font-size:0.62rem;color:rgba(255,255,255,0.25);margin:8px 0 0;
                letter-spacing:0.08em">
        Sign in to your ambient display
      </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                try:
                    user = get_user_by_username(username.strip().lower())
                    if user and verify_password(password, user["password_hash"]):
                        token = create_session_token(user["id"])
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"] = user["id"]
                        st.session_state["username"] = user["username"]
                        st.session_state["user_name"] = user["name"]
                        st.session_state["profile_type"] = user["profile_type"]
                        st.session_state["session_token"] = token
                        st.session_state["auth_page"] = "login"
                        cm = _get_cookie_manager()
                        cm.set(_COOKIE_NAME, token, key="login_cookie")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                except Exception as e:
                    st.error(f"Login error: {str(e)}")

    # Toggle to registration
    st.markdown("<div style='text-align:center;margin-top:12px'>", unsafe_allow_html=True)
    if st.button("Don't have an account? Register"):
        st.session_state["auth_page"] = "register"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_register() -> None:
    """Registration form with Profile Type selection."""
    st.markdown("""
    <div style="text-align:center;margin-bottom:32px">
      <p style="font-size:0.5rem;letter-spacing:0.30em;text-transform:uppercase;
                color:rgba(255,255,255,0.18);margin:0 0 10px;font-weight:700">
        Chronos
      </p>
      <p style="font-size:1.6rem;font-weight:200;letter-spacing:-0.02em;
                margin:0;color:rgba(255,255,255,0.9)">
        Create Account
      </p>
      <p style="font-size:0.62rem;color:rgba(255,255,255,0.25);margin:8px 0 0;
                letter-spacing:0.08em">
        Set up your personalised display experience
      </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        name = st.text_input("Display Name", placeholder="e.g. Alex")
        username = st.text_input("Username", placeholder="Choose a username")
        email = st.text_input("Email (optional)", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Min 6 characters")
        password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        profile_type = st.selectbox(
            "Profile Type",
            ["Standard", "Kids", "Professional"],
            help="**Standard**: Full adaptive experience.  \n"
                 "**Kids**: Safety-filtered content with vibrant, friendly UI.  \n"
                 "**Professional**: Clean, minimal aesthetic.",
        )
        submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            errors = []
            if not username or not password:
                errors.append("Username and password are required.")
            if len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if password != password_confirm:
                errors.append("Passwords do not match.")
            if username and username_exists(username.strip().lower()):
                errors.append("This username is already taken.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    user_id = create_user(
                        username=username.strip().lower(),
                        password_hash=hash_password(password),
                        name=name.strip() or username.strip(),
                        email=email.strip(),
                        profile_type=profile_type,
                    )
                    # Auto-login after registration
                    token = create_session_token(user_id)
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = user_id
                    st.session_state["username"] = username.strip().lower()
                    st.session_state["user_name"] = name.strip() or username.strip()
                    st.session_state["profile_type"] = profile_type
                    st.session_state["session_token"] = token
                    st.session_state["auth_page"] = "login"
                    cm = _get_cookie_manager()
                    cm.set(_COOKIE_NAME, token, key="register_cookie")
                    st.rerun()
                except Exception as e:
                    st.error(f"Registration error: {str(e)}")

    # Toggle to login
    st.markdown("<div style='text-align:center;margin-top:12px'>", unsafe_allow_html=True)
    if st.button("Already have an account? Sign In"):
        st.session_state["auth_page"] = "login"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Profile-Themed CSS Overrides
# ---------------------------------------------------------------------------

def get_theme_overrides(profile_type: str) -> str:
    """
    Returns additional CSS that morphs the UI based on the user's profile type.

    Standard     → Frosted Obsidian (dark / purple-gold accent) — default, no overrides needed.
    Kids         → Sky Blue accent, softer 24px radii, friendlier feel.
    Professional → Muted silver/slate tones, tighter spacing.
    """
    if profile_type == "Kids":
        return """
        /* ═══════════════════ KIDS THEME — Sky Blue ═══════════════════ */

        /* Accent colour swap: purple → sky-blue */
        [data-testid="stSidebar"] .stButton > button {
            background:   rgba(56,189,248,0.10) !important;
            border-color: rgba(56,189,248,0.28) !important;
            color:        #7dd3fc !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background:   rgba(56,189,248,0.22) !important;
            border-color: rgba(56,189,248,0.52) !important;
            box-shadow:   0 0 14px rgba(56,189,248,0.20) !important;
        }

        /* Selectbox hover */
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:hover {
            border-color: rgba(56,189,248,0.50) !important;
            box-shadow:   0 0 0 2px rgba(56,189,248,0.10) !important;
        }

        /* Slider thumb */
        [data-testid="stSidebar"] [data-testid="stSelectSlider"] [role="slider"] {
            background:  #38bdf8 !important;
            box-shadow:  0 0 10px rgba(56,189,248,0.55) !important;
        }

        /* Score fill gradient */
        .score-fill {
            background: linear-gradient(90deg, #38bdf8, #0ea5e9) !important;
        }

        /* Tag chips */
        .tag-chip {
            background:   rgba(56,189,248,0.14) !important;
            border-color: rgba(56,189,248,0.28) !important;
            color:        #7dd3fc !important;
        }

        /* Reasoning score */
        .reasoning-score { color: #7dd3fc !important; }

        /* AI pulse dot — blue instead of purple */
        @keyframes systemPulse {
            0%, 100% { opacity: 0.35; transform: scale(1);    box-shadow: 0 0 0    0   rgba(56,189,248,0); }
            50%      { opacity: 1;   transform: scale(1.45); box-shadow: 0 0 16px 4px rgba(56,189,248,0.55); }
        }

        /* Softer border-radii — friendlier feel */
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            border-radius: 20px !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 14px !important;
        }
        [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
            border-radius: 14px !important;
        }
        .glass { border-radius: 24px !important; }
        .reasoning-card { border-radius: 24px !important; }

        /* Kids safety badge — fixed bottom-right */
        body::before {
            content: "\\F4CF  Kids Mode";
            font-family: 'bootstrap-icons', 'Inter', sans-serif;
            position: fixed;
            bottom: calc(14px + env(safe-area-inset-bottom, 0px));
            right: 16px;
            padding: 5px 14px;
            border-radius: 999px;
            background: rgba(56,189,248,0.12);
            border: 1px solid rgba(56,189,248,0.25);
            backdrop-filter: blur(12px);
            font-size: 0.52rem; font-weight: 600;
            letter-spacing: 0.14em; text-transform: uppercase;
            color: rgba(125,211,252,0.7);
            z-index: 50;
        }
        """

    elif profile_type == "Professional":
        return """
        /* ═══════════════════ PROFESSIONAL THEME — Silver ════════════════ */

        /* Accent: muted silver/slate instead of purple */
        [data-testid="stSidebar"] .stButton > button {
            background:   rgba(148,163,184,0.08) !important;
            border-color: rgba(148,163,184,0.22) !important;
            color:        #cbd5e1 !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background:   rgba(148,163,184,0.16) !important;
            border-color: rgba(148,163,184,0.42) !important;
        }

        /* Slider thumb */
        [data-testid="stSidebar"] [data-testid="stSelectSlider"] [role="slider"] {
            background:  #94a3b8 !important;
            box-shadow:  0 0 8px rgba(148,163,184,0.4) !important;
        }

        /* Score fill — neutral gradient */
        .score-fill {
            background: linear-gradient(90deg, #94a3b8, #64748b) !important;
        }

        /* Tag chips */
        .tag-chip {
            background:   rgba(148,163,184,0.10) !important;
            border-color: rgba(148,163,184,0.22) !important;
            color:        #cbd5e1 !important;
        }

        .reasoning-score { color: #cbd5e1 !important; }

        /* Tighter, more structured feel */
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            border-radius: 6px !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 6px !important;
        }
        .glass { border-radius: 12px !important; }
        """

    # Standard — no overrides needed, base Frosted Obsidian theme applies.
    return ""
