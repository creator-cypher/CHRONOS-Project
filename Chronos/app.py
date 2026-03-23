"""
Chronos — Adaptive Ambient Display System
==========================================
Streamlit entry point.

Run with:
    streamlit run app.py

UI Layout
---------
  Full-screen  : Cinematic image frame (CSS background of the entire app)
  Bottom-centre: Reasoning overlay (glassmorphism HTML card)
  Sidebar      : Control dashboard (Streamlit native widgets)
  Top bar      : Time-period indicator (HTML injected above main content)

The page auto-refreshes every 5 minutes via an injected <meta> tag.
Manual "Refresh Now" reruns the Streamlit script immediately.
"""

import csv
import io
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# ─── Page config — MUST be the first Streamlit call ──────────────────────────
st.set_page_config(
    page_title="Chronos",
    page_icon="\U0001F319",
    layout="wide",
    initial_sidebar_state="auto",
)

# ─── Internal imports (after page config) ────────────────────────────────────
import pandas as pd
from database.queries import (
    get_all_images, add_image, get_preferences, update_preferences,
    get_recent_logs, deactivate_image, save_interaction,
    search_images, deactivate_images, get_image_interaction_summary,
    get_mood_distribution, get_hourly_usage, get_mood_over_time,
    get_display_config, update_display_config,
    get_presets, save_preset, delete_preset, apply_preset,
    update_image_error, update_image_schedule,
)
from logic.context              import get_current_context
from logic.engine               import select_best_image
from services.vision            import analyze_image
from services.cloudinary_upload import upload_image as cloudinary_upload
from auth                       import init_auth_state, render_auth_page, logout, get_theme_overrides

# Database tables are created lazily on first query (SQLAlchemy handles this)
# No need for explicit init_database() call on startup

# No local upload directory — images are stored on Cloudinary


# ─── Cached data helpers (Enhancement 6) ─────────────────────────────────────

@st.cache_data(ttl=30)
def cached_get_all_images(user_id: str = ""):
    return get_all_images(user_id=user_id)

@st.cache_data(ttl=120)
def cached_analytics_summary(user_id: str = ""):
    return get_image_interaction_summary(user_id=user_id)

@st.cache_data(ttl=120)
def cached_mood_distribution():
    return get_mood_distribution()

@st.cache_data(ttl=120)
def cached_hourly_usage():
    return get_hourly_usage()

@st.cache_data(ttl=120)
def cached_mood_over_time(days=30):
    return get_mood_over_time(days)


# =============================================================================
# CSS Injection —dark theme
# =============================================================================

def inject_global_css(image_css_url: str, time_period: str, profile_type: str = "Standard") -> None:
    """
    Injects all custom CSS into the Streamlit page.

    Key techniques:
      - `#chronos-bg` fixed div → full-viewport image layer with fade-in animation.
        CSS `transition` on `background-image` is not animatable in any browser;
        instead we inject a fresh `<div id="chronos-bg">` on every Streamlit rerun.
        Since Streamlit replaces the full DOM, the div is always new, which causes
        `@keyframes chronosFadeIn` to fire from scratch — a true fade-in per image.
      - `.stApp` is transparent; it holds only the vignette pseudo-elements.
      - Glassmorphism via backdrop-filter + rgba backgrounds.
      - Streamlit chrome hidden via visibility:hidden / display:none.
      - `@keyframes` animations for the reasoning overlay and tags.
    """
    brightness = 0.65 if time_period == "night" else 0.85

    st.markdown(f"""
    <style>
    /* ── Import Inter + Bootstrap Icons ───────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

    /* ── Hide Streamlit chrome ───────────────────────────────────── */
    #MainMenu, header, footer, .stDeployButton,
    [data-testid="stToolbar"] {{ visibility: hidden !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}
    .viewerBadge_container__1QSob {{ display: none !important; }}

    /* ── Global reset ────────────────────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
        margin: 0; padding: 0;
        background-color: #090909;
        font-family: 'Inter', system-ui, sans-serif;
        -webkit-font-smoothing: antialiased;
        color: #f0f0f0;
    }}

    /* ── Cinematic background layer ───────────────────────────────── */
    /* Lives on a dedicated fixed div, NOT .stApp, so the keyframe    */
    /* animation fires cleanly on every Streamlit rerun / image swap. */
    /* z-index: -1 sits above the canvas (#090909 on html/body) but   */
    /* below .stApp — which MUST be transparent for this to show.     */
    @keyframes chronosFadeIn {{
        0%   {{ opacity: 0; transform: scale(1.012); }}
        100% {{ opacity: 1; transform: scale(1);     }}
    }}

    #chronos-bg {{
        position: fixed;
        inset: 0;
        background-image:    url('{image_css_url}');
        background-size:     cover;
        background-position: center center;
        background-repeat:   no-repeat;
        filter:              brightness({brightness}) saturate(1.05);
        z-index:             -1;
        animation:           chronosFadeIn 1.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    }}

    /* .stApp must be transparent so #chronos-bg (z-index:-1) shows through */
    .stApp {{
        background: transparent !important;
        min-height: 100vh;
    }}

    /* ── Vignette overlay ─────────────────────────────────────────── */
    .stApp::before {{
        content: "";
        position: fixed; inset: 0;
        background: radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.72) 100%);
        pointer-events: none;
        z-index: 0;
    }}

    /* Bottom gradient for text readability */
    .stApp::after {{
        content: "";
        position: fixed; bottom: 0; left: 0; right: 0;
        height: 45%;
        background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
        pointer-events: none;
        z-index: 0;
    }}

    /* ── Main content area ────────────────────────────────────────── */
    .main .block-container {{
        padding: 0 !important;
        max-width: 100% !important;
        position: relative;
        z-index: 1;
    }}

    /* ── Glassmorphism ─────────────────────────────────────────────── */
    .glass {{
        background: rgba(255,255,255,0.055) !important;
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 18px;
    }}

    /* ── Animations ─────────────────────────────────────────────────── */
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(14px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes slideRight {{
        from {{ opacity: 0; transform: translateX(-8px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}
    @keyframes pulseDot {{
        0%, 100% {{ opacity: 0.5; transform: scale(1); }}
        50%       {{ opacity: 1;   transform: scale(1.3); }}
    }}
    @keyframes systemPulse {{
        0%, 100% {{ opacity: 0.35; transform: scale(1);    box-shadow: 0 0 0    0   rgba(167,139,250,0);    }}
        50%       {{ opacity: 1;   transform: scale(1.45); box-shadow: 0 0 16px 4px rgba(167,139,250,0.55); }}
    }}
    /* Breathing indicator for AI recalculation in progress */
    @keyframes breatheGlow {{
        0%, 100% {{ background: rgba(167,139,250,0.2); box-shadow: 0 0 8px rgba(167,139,250,0.1); }}
        50%       {{ background: rgba(167,139,250,0.4); box-shadow: 0 0 20px rgba(167,139,250,0.3); }}
    }}
    @keyframes glowPulse {{
        0%   {{ box-shadow: 0 0 0   0   rgba(167,139,250,0);    border-color: rgba(255,255,255,0.09); }}
        50%  {{ box-shadow: 0 0 14px 2px rgba(167,139,250,0.25); border-color: rgba(167,139,250,0.55); }}
        100% {{ box-shadow: 0 0 0   0   rgba(167,139,250,0);    border-color: rgba(255,255,255,0.09); }}
    }}

    .anim-up  {{ animation: fadeInUp  0.7s cubic-bezier(0.22,1,0.36,1) forwards; }}
    .anim-in  {{ animation: slideRight 0.5s ease forwards; }}

    /* ── Top status bar ──────────────────────────────────────────────── */
    .status-bar {{
        position: fixed; top: 20px; left: 24px;
        display: flex; align-items: center; gap: 10px;
        z-index: 100;
    }}
    .status-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        animation: pulseDot 2.5s ease-in-out infinite;
    }}
    .status-text {{
        font-size: 0.65rem;
        font-weight: 400;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.5);
    }}

    /* ── Reasoning overlay card ──────────────────────────────────────── */
    .reasoning-card {{
        position: fixed;
        bottom: 36px;
        left: 50%;
        transform: translateX(-50%);
        width: min(400px, 90vw);
        padding: 18px 22px;
        z-index: 50;
        animation: fadeInUp 0.8s cubic-bezier(0.22,1,0.36,1) forwards;
    }}
    .reasoning-header {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 10px;
    }}
    .reasoning-period {{
        font-size: 0.62rem; font-weight: 500;
        letter-spacing: 0.14em; text-transform: uppercase;
        color: rgba(255,255,255,0.45);
        display: flex; align-items: center; gap: 6px;
    }}
    .reasoning-score {{
        font-size: 0.68rem; font-weight: 600;
        color: #c4b5fd; letter-spacing: 0.05em;
    }}
    .reasoning-text {{
        font-size: 0.78rem; font-weight: 300;
        color: rgba(255,255,255,0.78);
        line-height: 1.55; letter-spacing: 0.02em;
        margin-bottom: 12px;
    }}
    .score-track {{
        height: 3px; border-radius: 99px;
        background: rgba(255,255,255,0.12);
        margin-bottom: 12px; overflow: hidden;
    }}
    .score-fill {{
        height: 100%; border-radius: 99px;
        background: linear-gradient(90deg, #a78bfa, #7c3aed);
        transition: width 1.2s cubic-bezier(0.22,1,0.36,1);
    }}
    .tags-row {{
        display: flex; flex-wrap: wrap; gap: 6px;
    }}
    .tag-chip {{
        padding: 3px 10px; border-radius: 999px;
        font-size: 0.6rem; font-weight: 500;
        letter-spacing: 0.06em; text-transform: uppercase;
        background: rgba(167,139,250,0.14);
        border: 1px solid rgba(167,139,250,0.28);
        color: #c4b5fd;
        animation: slideRight 0.4s ease forwards;
    }}

    /* ── Sidebar — Frosted Obsidian (Enhanced) ──────────────────────────── */
    [data-testid="stSidebar"] {{
        background:             rgba(10,10,15,0.85) !important;
        backdrop-filter:        blur(30px) saturate(200%) contrast(110%) !important;
        -webkit-backdrop-filter:blur(30px) saturate(200%) contrast(110%) !important;
        border-right:           1px solid rgba(255,255,255,0.09) !important;
        z-index:                999 !important;
        box-shadow:             8px 0 64px rgba(0,0,0,0.8), inset -1px 0 2px rgba(255,255,255,0.04) !important;
    }}

    /* 2 px scrollbar */
    [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar {{ width: 2px; }}
    [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-track {{ background: transparent; }}
    [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-thumb {{
        background: rgba(255,255,255,0.10); border-radius: 99px;
    }}

    /* Base text — specific selectors, NOT * wildcard */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] div {{
        color: rgba(255,255,255,0.82) !important;
    }}

    /* Tiny-caps widget labels */
    [data-testid="stSidebar"] .stSelectbox    label,
    [data-testid="stSidebar"] .stSlider       label,
    [data-testid="stSidebar"] .stRadio        label,
    [data-testid="stSidebar"] .stSelectSlider label {{
        font-size:      0.5rem  !important;
        letter-spacing: 0.22em  !important;
        text-transform: uppercase !important;
        color:          rgba(255,255,255,0.28) !important;
        font-weight:    700 !important;
        margin-bottom:  5px !important;
    }}

    /* Glass dividers */
    [data-testid="stSidebar"] hr {{
        border:     none !important;
        border-top: 1px solid rgba(255,255,255,0.06) !important;
        margin:     10px 0 !important;
    }}

    /* ── Selectbox ─────────────────────────────────────────── */
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
        background:    rgba(255,255,255,0.04) !important;
        border:        1px solid rgba(255,255,255,0.09) !important;
        border-radius: 8px !important;
        min-height:    36px !important;
        transition:    border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:hover {{
        border-color: rgba(167,139,250,0.50) !important;
        box-shadow:   0 0 0 2px rgba(167,139,250,0.09), 0 0 12px rgba(167,139,250,0.10) !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * {{
        color:      rgba(255,255,255,0.82) !important;
        font-size:  0.74rem !important;
        background: transparent !important;
    }}
    [data-testid="stSidebar"] .stSelectbox svg {{ fill: rgba(255,255,255,0.3) !important; }}

    /* ── Select slider ──────────────────────────────────────── */
    [data-testid="stSidebar"] [data-testid="stSelectSlider"] > div > div {{
        background:    rgba(255,255,255,0.07) !important;
        border-radius: 99px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSelectSlider"] [role="slider"] {{
        background:  #a78bfa !important;
        box-shadow:  0 0 10px rgba(167,139,250,0.55) !important;
        border:      2px solid rgba(255,255,255,0.22) !important;
        transition:  box-shadow 0.2s ease !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSelectSlider"] [role="slider"]:hover {{
        box-shadow: 0 0 18px rgba(167,139,250,0.80) !important;
    }}

    /* ── Toggle switch ──────────────────────────────────────── */
    [data-testid="stSidebar"] [data-testid="stToggle"] label p {{
        font-size:      0.62rem !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color:          rgba(255,255,255,0.42) !important;
    }}

    /* ── Expanders ──────────────────────────────────────────── */
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        background:    rgba(255,255,255,0.022) !important;
        border:        1px solid rgba(255,255,255,0.07) !important;
        border-radius: 10px !important;
        overflow:      hidden !important;
        transition:    border-color 0.25s ease !important;
        margin-bottom: 3px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"]:hover {{
        border-color: rgba(255,255,255,0.13) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
        font-size:      0.6rem !important;
        letter-spacing: 0.14em !important;
        text-transform: uppercase !important;
        color:          rgba(255,255,255,0.42) !important;
        padding:        10px 14px !important;
        transition:     color 0.2s ease !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
        color: rgba(255,255,255,0.82) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary > svg {{
        fill:   rgba(255,255,255,0.28) !important;
        stroke: rgba(255,255,255,0.28) !important;
        transition: fill 0.2s ease !important;
    }}

    /* ── Action buttons ─────────────────────────────────────── */
    [data-testid="stSidebar"] .stButton > button {{
        background:     rgba(167,139,250,0.09) !important;
        border:         1px solid rgba(167,139,250,0.26) !important;
        color:          #c4b5fd !important;
        border-radius:  8px !important;
        font-size:      0.6rem !important;
        letter-spacing: 0.14em !important;
        text-transform: uppercase !important;
        font-weight:    600 !important;
        padding:        8px 14px !important;
        transition:     background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background:   rgba(167,139,250,0.20) !important;
        border-color: rgba(167,139,250,0.52) !important;
        box-shadow:   0 0 14px rgba(167,139,250,0.18) !important;
    }}

    /* ── Sidebar toggle buttons — suppressed; JS FAB replaces them ──────── */
    /* CSS-positioning these elements is unreliable: stSidebarCollapseButton  */
    /* lives inside the sidebar whose transform animation creates a new       */
    /* containing block for position:fixed children, so the button slides     */
    /* off-screen with the sidebar. collapsedControl rendering also varies     */
    /* across Streamlit versions. Solution: hide both natively, inject a      */
    /* plain <button> directly on document.body via inject_sidebar_fab().     */
    /* The native buttons stay in the DOM so JS can .click() them to drive    */
    /* Streamlit's sidebar state machine.                                      */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        opacity:        0 !important;
        pointer-events: none !important;
    }}

    /* Noise texture overlay — z-index below FAB to prevent visibility issues */
    /* FAB (z-index:99999) must remain visible at all times, even with sidebar open */
    body::after {{
        content: "";
        position: fixed; inset: 0;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        opacity: 0.025;
        pointer-events: none;
        z-index: 10;
        mix-blend-mode: overlay;
    }}

    /* ═══════════════════ RESPONSIVE LAYER ════════════════════════ */

    /* Prevent horizontal overflow on narrow viewports */
    html {{ overflow-x: hidden; }}

    /* Dynamic viewport height — adjusts when mobile browser chrome
       (address bar, nav bar) appears / disappears.
       100dvh shrinks correctly; 100vh would overshoot. */
    .stApp {{ min-height: 100dvh; }}

    /* Reasoning card: keep above phone home-indicator safe area */
    .reasoning-card {{
        bottom: calc(36px + env(safe-area-inset-bottom, 0px));
    }}

    /* Remove 300 ms tap delay on touch devices */
    button, [role="button"], summary {{ touch-action: manipulation; }}

    /* Momentum scrolling in sidebar on iOS */
    [data-testid="stSidebar"] > div:first-child {{
        -webkit-overflow-scrolling: touch;
    }}

    /* ── Tablet  ≤ 900 px ───────────────────────────────────────── */
    @media (max-width: 900px) {{
        .status-bar     {{ top: 14px; left: 16px; }}
        .reasoning-card {{ bottom: calc(24px + env(safe-area-inset-bottom, 0px));
                           padding: 14px 18px; }}
    }}

    /* ── Mobile  ≤ 640 px ───────────────────────────────────────── */
    @media (max-width: 640px) {{
        /* Status bar: tighter position, smaller text */
        .status-bar  {{ top: 12px; left: 12px; gap: 7px; }}
        .status-dot  {{ width: 6px; height: 6px; }}
        .status-text {{ font-size: 0.55rem; letter-spacing: 0.08em; }}

        /* Reasoning card: stretch edge-to-edge with 12 px gutters */
        .reasoning-card {{
            left: 12px; right: 12px;
            bottom: calc(12px + env(safe-area-inset-bottom, 0px));
            width: auto; transform: none;
            padding: 12px 14px; border-radius: 14px;
        }}
        .reasoning-text   {{ font-size: 0.70rem; line-height: 1.5; margin-bottom: 10px; }}
        .reasoning-period {{ font-size: 0.56rem; }}
        .reasoning-score  {{ font-size: 0.60rem; }}
        .score-track      {{ margin-bottom: 10px; }}
        .tag-chip         {{ font-size: 0.52rem; padding: 2px 8px; }}

        /* Sidebar: tighter horizontal padding on overlay modal */
        [data-testid="stSidebar"] > div:first-child {{
            padding-left:  12px !important;
            padding-right: 12px !important;
        }}

        /* FAB: smaller pill, safe-area-aware for notched phones.
           !important overrides the JS inline style on mobile. */
        #chronos-fab {{
            top:    calc(12px + env(safe-area-inset-top,   0px)) !important;
            right:  calc(12px + env(safe-area-inset-right, 0px)) !important;
            width:  36px !important;
            height: 36px !important;
        }}
    }}

    /* ── Very small  ≤ 400 px ───────────────────────────────────── */
    @media (max-width: 400px) {{
        .reasoning-card {{ padding: 10px 12px; border-radius: 12px; }}
        .reasoning-text {{ font-size: 0.65rem; }}
        .tags-row       {{ gap: 4px; }}
        .tag-chip       {{ font-size: 0.50rem; padding: 2px 6px; }}
    }}

    </style>
    <div id="chronos-bg"></div>
    """, unsafe_allow_html=True)

    # ── Profile-based theme overrides ─────────────────────────────────────
    theme_css = get_theme_overrides(profile_type)
    if theme_css:
        st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)

    # Auto-refresh every 5 minutes via meta tag (ambient display behaviour)
    st.markdown('<meta http-equiv="refresh" content="300">', unsafe_allow_html=True)


# =============================================================================
# Sidebar FAB (JS injection)
# =============================================================================

def inject_sidebar_fab() -> None:
    """
    Injects a persistent toggle FAB directly onto document.body via a
    sandboxed iframe script (st.components.v1.html).

    Enhanced to overcome z-index stacking context issues:
    - FAB is appended to document.body (root stacking context)
    - Uses z-index:99999 with will-change:transform to create new stacking context
    - Actively monitors sidebar state and updates visual feedback
    - Robust fallback detection for different Streamlit versions

    Why not pure CSS?
    -----------------
    Streamlit's sidebar uses a CSS `transform` for its slide animation.
    Any child with `position:fixed` anchors relative to that transformed
    ancestor, not the viewport — so the button slides off-screen with the
    sidebar.  `collapsedControl` rendering also varies across versions.
    """
    import streamlit.components.v1 as _components  # type: ignore[import-untyped]
    _components.html(
        """
        <script>
        (function () {
            var pd = window.parent.document;
            if (pd.getElementById('chronos-fab')) return;   // one instance only

            /* ── Build FAB ───────────────────────────────────────────────── */
            var fab = pd.createElement('button');
            fab.id    = 'chronos-fab';
            fab.title = 'Toggle sidebar';
            fab.setAttribute('aria-label', 'Toggle sidebar');

            /* Hamburger icon — same meaning for open and close */
            fab.innerHTML =
                '<svg width="17" height="13" viewBox="0 0 17 13" fill="none" aria-hidden="true">'
                + '<rect width="17" height="2"   rx="1" fill="rgba(255,255,255,.90)"/>'
                + '<rect y="5.5" width="17" height="2"   rx="1" fill="rgba(255,255,255,.90)"/>'
                + '<rect y="11"  width="17" height="2"   rx="1" fill="rgba(255,255,255,.90)"/>'
                + '</svg>';

            /* Enhanced: will-change:transform creates new stacking context for z-index */
            fab.style.cssText =
                'position:fixed;top:16px;right:16px;left:auto;'
                + 'z-index:99999;width:40px;height:40px;'
                + 'background:rgba(9,9,14,.80);'
                + 'border:1px solid rgba(255,255,255,.14);border-radius:11px;'
                + 'cursor:pointer;display:flex;align-items:center;justify-content:center;'
                + '-webkit-backdrop-filter:blur(16px) saturate(180%);'
                + 'backdrop-filter:blur(16px) saturate(180%);'
                + 'box-shadow:0 4px 20px rgba(0,0,0,.50);'
                + 'transition:background .2s,border-color .2s,box-shadow .2s,'
                + 'transform .18s cubic-bezier(.34,1.56,.64,1);'
                + 'user-select:none;will-change:transform;'
                + 'padding:0;';  /* Ensure no padding distorts the button */

            /* ── Sidebar state detection ─────────────────────────────────── */
            function sidebarOpen() {
                var sb = pd.querySelector('[data-testid="stSidebar"]');
                return sb ? sb.getBoundingClientRect().width > 60 : false;
            }

            /* ── Toggle click with safety checks ──────────────────────────── */
            fab.addEventListener('click', function (e) {
                e.preventDefault();
                var collapseBtn = pd.querySelector(
                    '[data-testid="stSidebarCollapseButton"] button');
                var expandBtn = pd.querySelector(
                    '[data-testid="collapsedControl"] button');

                if (sidebarOpen()) {
                    if (collapseBtn) {
                        collapseBtn.click();
                    }
                } else {
                    if (expandBtn) {
                        expandBtn.click();
                    } else if (collapseBtn) {
                        collapseBtn.click();
                    }
                }
            });

            /* ── Hover / active states with improved feedback ──────────────── */
            fab.addEventListener('mouseenter', function () {
                this.style.background  = 'rgba(255,255,255,.10)';
                this.style.borderColor = 'rgba(255,255,255,.28)';
                this.style.boxShadow   = '0 4px 24px rgba(0,0,0,.60),0 0 14px rgba(167,139,250,.15)';
                this.style.transform   = 'scale(1.08)';
            });
            fab.addEventListener('mouseleave', function () {
                this.style.background  = 'rgba(9,9,14,.80)';
                this.style.borderColor = 'rgba(255,255,255,.14)';
                this.style.boxShadow   = '0 4px 20px rgba(0,0,0,.50)';
                this.style.transform   = 'scale(1)';
            });
            fab.addEventListener('mousedown', function () {
                this.style.transform = 'scale(.93)';
            });
            fab.addEventListener('mouseup', function () {
                this.style.transform = sidebarOpen() ? 'scale(1.08)' : 'scale(1)';
            });

            /* Append to body root stacking context (never inside transformed ancestor) */
            pd.body.appendChild(fab);

            /* ── Monitor sidebar state for visual feedback updates ─────────── */
            setInterval(function () {
                if (sidebarOpen()) {
                    fab.style.borderColor = 'rgba(167,139,250,.35)';
                } else {
                    fab.style.borderColor = 'rgba(255,255,255,.14)';
                }
            }, 250);
        }());
        </script>
        """,
        height=0,
        scrolling=False,
    )


# =============================================================================
# Icon Helper — Bootstrap Icons
# =============================================================================

def bi(name: str, size: str = "1em", color: str = "") -> str:
    """Returns an inline Bootstrap Icon HTML span for use in st.markdown."""
    style = f"font-size:{size}"
    if color:
        style += f";color:{color}"
    return f'<i class="bi bi-{name}" style="{style}"></i>'


# Map time periods to Bootstrap Icon names (replacing emoji)
PERIOD_ICONS_BI = {
    "dawn":      "sunrise",
    "morning":   "sun",
    "afternoon": "cloud-sun",
    "evening":   "sunset",
    "night":     "moon-stars",
}


# =============================================================================
# UI Helpers
# =============================================================================

def get_image_css_url(image: dict) -> str:
    """
    Returns a CSS-embeddable URL for the given image dict.
    Images are stored on Cloudinary so we return the secure_url directly —
    no base64 encoding needed.
    """
    return image.get("image_url", "") or ""


def render_status_bar(context: dict) -> None:
    """Fixed top-left ambient time indicator."""
    period = context.get("time_period", "now")
    hour   = context.get("hour", 0)
    minute = context.get("minute", 0)

    dot_colors = {
        "dawn": "#fb923c", "morning": "#fbbf24", "afternoon": "#34d399",
        "evening": "#a78bfa", "night": "#60a5fa",
    }
    dot_color = dot_colors.get(period, "#a78bfa")
    period_icon = bi(PERIOD_ICONS_BI.get(period, "clock"), "0.85em")

    st.markdown(f"""
    <div class="status-bar">
      <span class="status-dot" style="background:{dot_color}"></span>
      <span class="status-text">{period_icon} {period.capitalize()} &nbsp;·&nbsp; {hour}:{minute:02d}</span>
    </div>
    """, unsafe_allow_html=True)


def render_reasoning_overlay(result) -> None:
    """Glassmorphism card that explains the current selection with confidence score."""
    if result is None:
        return

    period       = result.context.get("time_period", "now")
    period_icon  = bi(PERIOD_ICONS_BI.get(period, "clock"), "1.1em")
    score_pct    = int(result.total_score * 100)
    confidence   = getattr(result, "confidence_pct", score_pct)  # Fallback to score if confidence not set
    tags_html    = "".join(
        f'<span class="tag-chip">{t}</span>'
        for t in (result.matched_tags or [])[:5]
    )

    st.markdown(f"""
    <div class="reasoning-card glass anim-up">
      <div class="reasoning-header">
        <div class="reasoning-period">
          <span>{period_icon}</span>
          <span>{period.capitalize()}</span>
        </div>
        <div class="reasoning-score">{confidence}% Match</div>
      </div>
      <div class="reasoning-text">{result.reasoning_text}</div>
      <div class="score-track">
        <div class="score-fill" style="width:{confidence}%"></div>
      </div>
      <div class="tags-row">{tags_html}</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# Sidebar — Control Dashboard
# =============================================================================

def _invalidate_caches():
    """Clear all Streamlit data caches after mutations."""
    cached_get_all_images.clear()
    cached_analytics_summary.clear()
    cached_mood_distribution.clear()
    cached_hourly_usage.clear()
    cached_mood_over_time.clear()


def _run_analysis(image_id: str, source_url: str):
    """Run Gemini analysis on an image and save results. Returns AnalysisResult."""
    from database.queries import update_image_analysis
    # Load AI analysis settings
    config = get_display_config()
    r = analyze_image(
        source_url,
        depth=config.get("analysis_depth", "standard"),
        focus=config.get("analysis_focus", ""),
        custom=config.get("custom_prompt", ""),
    )
    if r.success:
        update_image_analysis(
            image_id=image_id,
            description=r.description,
            primary_mood=r.primary_mood,
            optimal_time=r.optimal_time,
            base_score=r.base_score,
            dominant_colors=r.dominant_colors,
            tags=r.tags,
        )
        return r
    else:
        update_image_error(image_id, r.error_message, 0)
        return r


def render_sidebar(context: dict, result, user_id: str = "", profile_type: str = "Standard") -> None:
    """
    Renders the Control Dashboard in the Streamlit sidebar.
    Handles: mood selection, sensitivity, override toggle, image upload,
             AI analysis trigger, and recent history.
    """
    prefs = get_preferences(user_id=user_id)

    with st.sidebar:
        # ── User header + logout ─────────────────────────────────────────
        user_display = st.session_state.get("user_name", "") or st.session_state.get("username", "")
        profile_badge = {"Kids": "\u2605 Kids", "Professional": "\u25C8 Pro"}.get(profile_type, "")
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:14px 0 6px">
          <div>
            <p style="font-size:0.62rem;font-weight:400;margin:0;color:rgba(255,255,255,0.65)">
              {user_display}
              {"<span style='margin-left:6px;font-size:0.5rem;padding:2px 8px;border-radius:99px;"
               "background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.25);"
               "color:#7dd3fc;letter-spacing:0.1em;text-transform:uppercase;font-weight:600'>"
               + profile_badge + "</span>" if profile_badge else ""}
            </p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign Out", key="logout_btn"):
            logout()

        st.divider()

        # ── Header ───────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="padding:4px 0 16px">
          <p style="font-size:0.5rem;letter-spacing:0.24em;text-transform:uppercase;
                    color:rgba(255,255,255,0.22);margin:0 0 12px;font-weight:700">
            Chronos Control
          </p>
          <div style="display:flex;align-items:flex-end;gap:10px;margin-bottom:6px">
            <p style="font-size:2.2rem;font-weight:200;letter-spacing:-0.03em;
                      margin:0;line-height:1;color:#ffffff">
              {context.get('hour',0)}:{context.get('minute',0):02d}
            </p>
            <span style="
              display:inline-block;
              width:7px;height:7px;border-radius:50%;
              background:#a78bfa;margin-bottom:8px;flex-shrink:0;
              animation:systemPulse 2.6s ease-in-out infinite;
            " title="AI active"></span>
          </div>
          <p style="font-size:0.52rem;text-transform:uppercase;letter-spacing:0.18em;
                    color:rgba(255,255,255,0.22);margin:0;font-weight:600">
            {context.get('day_of_week','')} &nbsp;·&nbsp; {context.get('time_period','').capitalize()}
          </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Now Displaying ────────────────────────────────────────────────
        if result:
            img = result.image
            st.markdown(f"""
            <div style="margin-bottom:16px">
              <p style="font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;
                        color:rgba(255,255,255,0.3);margin:0 0 4px">Now Displaying</p>
              <p style="font-size:0.85rem;font-weight:300;margin:0;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                {img.get('title') or 'Untitled'}
              </p>
              <p style="font-size:0.6rem;color:rgba(255,255,255,0.3);margin:2px 0 0;
                        text-transform:uppercase;letter-spacing:0.1em">
                {img.get('primary_mood','—')} · {img.get('optimal_time','—')}
              </p>
            </div>
            """, unsafe_allow_html=True)

            # ── Manual Override Navigation or Standard Feedback ──────────────
            override_active = bool(prefs.get("override_active", 0))

            if override_active:
                # Manual mode: show Prev/Next for sequential navigation
                prev_col, next_col, like_col = st.columns(3)
                all_imgs = cached_get_all_images(user_id=user_id)

                with prev_col:
                    if st.button("\u276E  Prev", key=f"prev_{img['id']}", use_container_width=True, disabled=len(all_imgs) < 2):
                        if all_imgs and len(all_imgs) > 1:
                            current_idx = next((i for i, im in enumerate(all_imgs) if im["id"] == img["id"]), 0)
                            prev_idx = (current_idx - 1) % len(all_imgs)
                            update_preferences(user_id, override_image_id=all_imgs[prev_idx]["id"])
                            st.toast(f"← {all_imgs[prev_idx].get('title', 'Image')}")
                            st.rerun()

                with next_col:
                    if st.button("Next  \u276F", key=f"next_{img['id']}", use_container_width=True, disabled=len(all_imgs) < 2):
                        if all_imgs and len(all_imgs) > 1:
                            current_idx = next((i for i, im in enumerate(all_imgs) if im["id"] == img["id"]), 0)
                            next_idx = (current_idx + 1) % len(all_imgs)
                            update_preferences(user_id, override_image_id=all_imgs[next_idx]["id"])
                            st.toast(f"{all_imgs[next_idx].get('title', 'Image')} →")
                            st.rerun()

                with like_col:
                    if st.button("\u2764  Like", key=f"like_{img['id']}", use_container_width=True):
                        save_interaction(img["id"], "like")
                        st.toast("Liked — this image will score higher.")
                        st.rerun()
            else:
                # Auto mode: standard Like/Skip feedback
                like_col, skip_col = st.columns(2)
                with like_col:
                    if st.button("\u2764  Like", key=f"like_{img['id']}", use_container_width=True):
                        save_interaction(img["id"], "like")
                        st.toast("Liked — this image will score higher.")
                        st.rerun()
                with skip_col:
                    if st.button("\u2716  Skip", key=f"skip_{img['id']}", use_container_width=True):
                        save_interaction(img["id"], "skip")
                        st.toast("Skipped — this image will show less often.")
                        st.rerun()

        st.divider()

        # ── Mood Preference ───────────────────────────────────────────────
        MOODS = ["calm", "energetic", "joyful", "melancholic", "mysterious", "neutral"]
        current_mood = prefs.get("preferred_mood", "calm")
        new_mood = st.selectbox(
            "Preferred Mood",
            MOODS,
            index=MOODS.index(current_mood) if current_mood in MOODS else 0,
            key="mood_select",
        )
        if new_mood != current_mood:
            update_preferences(user_id, preferred_mood=new_mood)
            prefs["preferred_mood"] = new_mood

        # ── AI Sensitivity ────────────────────────────────────────────────
        SENS        = ["low", "medium", "high"]
        SENS_LABELS = ["Manual", "Balanced", "Full AI"]
        current_sens = prefs.get("sensitivity", "medium")
        sens_idx     = SENS.index(current_sens) if current_sens in SENS else 1
        new_sens_idx = st.radio(
            "AI Sensitivity",
            SENS_LABELS,
            index=sens_idx,
            key="sens_radio",
            horizontal=True,
        )
        new_sens = SENS[SENS_LABELS.index(new_sens_idx)]
        if new_sens != current_sens:
            update_preferences(user_id, sensitivity=new_sens)
            prefs["sensitivity"] = new_sens

        # ── Quick Presets (Enhancement 8) ─────────────────────────────────
        presets = get_presets()
        if presets:
            preset_names = ["— Select Preset —"] + [p["name"] for p in presets]
            selected_preset = st.selectbox(
                "Quick Presets", preset_names,
                index=0, key="preset_select", label_visibility="collapsed",
            )
            if selected_preset != "— Select Preset —":
                preset = next(p for p in presets if p["name"] == selected_preset)
                apply_preset(preset["id"])
                st.toast(f"Applied: {selected_preset}")
                st.rerun()

        with st.popover("Save Current as Preset", use_container_width=True):
            preset_name = st.text_input("Preset name", key="new_preset_name")
            if preset_name and st.button("Save Preset", key="save_preset_btn"):
                save_preset(preset_name, new_mood, new_sens)
                st.toast(f"Preset '{preset_name}' saved!")
                st.rerun()
            # Delete custom presets
            custom = [p for p in presets if not p.get("is_default")]
            if custom:
                st.caption("Delete a custom preset:")
                for p in custom:
                    if st.button(f"\u2715 {p['name']}", key=f"delpreset_{p['id']}"):
                        delete_preset(p["id"])
                        st.toast(f"Deleted preset '{p['name']}'")
                        st.rerun()

        st.divider()

        # ── Manual Override ───────────────────────────────────────────────
        override_on = st.toggle(
            "Manual Override",
            value=bool(prefs.get("override_active", 0)),
            help="When ON, the AI is bypassed entirely. Use Prev/Next to navigate.",
        )
        if override_on != bool(prefs.get("override_active", 0)):
            if override_on:
                all_imgs = cached_get_all_images(user_id=user_id)
                if not all_imgs:
                    st.warning("No images in library. Upload one first to use Manual Override.")
                    st.rerun()
                    return
                update_preferences(user_id, override_active=1, override_image_id=all_imgs[0]["id"])
            else:
                update_preferences(user_id, override_active=0, override_image_id=None)
            st.rerun()

        # ── Refresh ────────────────────────────────────────────────────────
        if st.button("\u27F3  Refresh Now", use_container_width=True):
            _invalidate_caches()
            st.rerun()

        st.divider()

        # ── Upload Image ──────────────────────────────────────────────────
        with st.expander("\u2912  Upload Image", expanded=False):
            uploaded = st.file_uploader(
                "Choose an image",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed",
            )
            title = st.text_input("Title (optional)", placeholder="e.g. Misty Forest Dawn")

            if uploaded and st.button("Save & Analyse", use_container_width=True):
                with st.spinner("Uploading to Cloudinary…"):
                    cloud = cloudinary_upload(
                        uploaded.getvalue(),
                        filename=uploaded.name,
                    )

                if not cloud["success"]:
                    st.error(f"Upload failed: {cloud['error']}")
                    st.stop()

                image_id = add_image(
                    title=title or uploaded.name,
                    image_url=cloud["secure_url"],
                    user_id=user_id,
                )

                with st.spinner("Analysing with Gemini…"):
                    r = _run_analysis(image_id, cloud["secure_url"])

                if r.success:
                    st.success(f"Analysed! Mood: {r.primary_mood} · Time: {r.optimal_time}")
                else:
                    st.error(f"Analysis failed: {r.error_message}")
                    st.info("Image saved — you can re-analyse later.")

                _invalidate_caches()
                time.sleep(1)
                st.rerun()

        # ── Add by URL ────────────────────────────────────────────────────
        with st.expander("\u2750  Add by URL", expanded=False):
            url_input  = st.text_input("Image URL", placeholder="https://…")
            url_title  = st.text_input("Title", placeholder="e.g. Aurora Borealis", key="url_title")
            if url_input and st.button("Add & Analyse URL", use_container_width=True):
                # Validate URL
                if not url_input.startswith(("http://", "https://")):
                    st.error("URL must start with http:// or https://")
                else:
                    try:
                        # Quick connectivity check (HEAD request with timeout)
                        import urllib.request
                        req = urllib.request.Request(url_input, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            content_type = resp.headers.get("Content-Type", "")
                            if not content_type.startswith("image/"):
                                st.error("URL does not point to an image. Check the URL and try again.")
                            else:
                                # URL is valid, proceed
                                image_id = add_image(title=url_title or url_input[:40], image_url=url_input, user_id=user_id)
                                with st.spinner("Analysing with Gemini…"):
                                    r = _run_analysis(image_id, url_input)
                                if r.success:
                                    st.success(f"✅ Added! Mood: {r.primary_mood}")
                                else:
                                    st.warning(f"⚠️ Saved without analysis: {r.error_message}")
                                _invalidate_caches()
                                time.sleep(1)
                                st.rerun()
                    except urllib.error.URLError as e:
                        st.error(f"Cannot access URL: {str(e)[:100]}")
                    except urllib.error.HTTPError as e:
                        st.error(f"HTTP error {e.code}: {e.reason}")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:100]}")

        st.divider()

        # ── Image Library with Search & Filtering (Enhancements 1 & 2) ───
        with st.expander("\u25A6  Image Library", expanded=False):
            # Search & Filter controls
            lib_search = st.text_input(
                "Search", placeholder="Search title or tags…",
                key="lib_search", label_visibility="collapsed",
            )
            filt_col1, filt_col2 = st.columns(2)
            with filt_col1:
                mood_filter = st.selectbox(
                    "Mood", ["All", "calm", "energetic", "joyful", "melancholic", "mysterious", "neutral"],
                    key="lib_mood_filter", label_visibility="collapsed",
                )
            with filt_col2:
                time_filter = st.selectbox(
                    "Time", ["All", "dawn", "morning", "afternoon", "evening", "night", "any"],
                    key="lib_time_filter", label_visibility="collapsed",
                )

            # Fetch images (filtered or all)
            has_filter = lib_search or mood_filter != "All" or time_filter != "All"
            if has_filter:
                images = search_images(
                    text=lib_search,
                    mood=mood_filter if mood_filter != "All" else "",
                    time_period=time_filter if time_filter != "All" else "",
                    user_id=user_id,
                )
            else:
                images = cached_get_all_images(user_id=user_id)

            st.caption(f"{len(images)} image{'s' if len(images) != 1 else ''}")

            if not images:
                st.caption("No images match — upload one above.")
            else:
                # Bulk selection controls
                if "selected_ids" not in st.session_state:
                    st.session_state.selected_ids = set()

                sa_col, da_col = st.columns(2)
                with sa_col:
                    if st.button("Select All", key="sel_all", use_container_width=True):
                        st.session_state.selected_ids = {img["id"] for img in images}
                        st.rerun()
                with da_col:
                    if st.button("Deselect All", key="desel_all", use_container_width=True):
                        st.session_state.selected_ids = set()
                        st.rerun()

                # Image list with checkboxes
                for img in images:
                    analyzed = bool(img.get("is_analyzed"))
                    cb_col, info_col, act_col = st.columns([0.5, 3, 1.5])
                    with cb_col:
                        checked = st.checkbox(
                            "sel", value=img["id"] in st.session_state.selected_ids,
                            key=f"cb_{img['id']}", label_visibility="collapsed",
                        )
                        if checked:
                            st.session_state.selected_ids.add(img["id"])
                        else:
                            st.session_state.selected_ids.discard(img["id"])
                    with info_col:
                        mood = img.get("primary_mood", "—")
                        tag  = f'{bi("check-circle", "0.7em", "#34d399")}' if analyzed else f'{bi("hourglass-split", "0.7em", "rgba(255,255,255,0.3)")}'
                        err  = img.get("analysis_error", "")
                        err_badge = f" {bi('x-circle', '0.7em', '#f87171')}" if err else ""
                        st.markdown(
                            f"<p style='font-size:0.72rem;margin:0;font-weight:300'>"
                            f"{tag} {img.get('title') or 'Untitled'}{err_badge}</p>"
                            f"<p style='font-size:0.58rem;color:rgba(255,255,255,0.3);margin:0'>"
                            f"{mood}</p>",
                            unsafe_allow_html=True,
                        )
                    with act_col:
                        btn_cols = st.columns(2)
                        with btn_cols[0]:
                            if not analyzed:
                                if st.button("\u21BB", key=f"re_{img['id']}", help="Re-analyse"):
                                    src = img.get("image_url") or ""
                                    if src:
                                        with st.spinner("Analysing…"):
                                            r = _run_analysis(img["id"], src)
                                        if r.success:
                                            st.success(f"{r.primary_mood}")
                                        else:
                                            st.error(r.error_message[:40])
                                        _invalidate_caches()
                                        st.rerun()
                        with btn_cols[1]:
                            if st.button("\u2715", key=f"del_{img['id']}", help="Remove"):
                                deactivate_image(img["id"])
                                st.session_state.selected_ids.discard(img["id"])
                                _invalidate_caches()
                                st.rerun()

                # Bulk action buttons
                selected = st.session_state.selected_ids
                if selected:
                    st.warning(f"{len(selected)} selected")
                    b1, b2 = st.columns(2)

                    with b1:
                        if "confirm_bulk_delete" not in st.session_state:
                            st.session_state.confirm_bulk_delete = False

                        if not st.session_state.confirm_bulk_delete:
                            if st.button("Delete Selected", key="bulk_del", use_container_width=True):
                                st.session_state.confirm_bulk_delete = True
                                st.rerun()
                        else:
                            st.error(f"Delete {len(selected)} images?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("Confirm", key="confirm_del"):
                                    deactivate_images(list(selected))
                                    st.session_state.selected_ids = set()
                                    st.session_state.confirm_bulk_delete = False
                                    _invalidate_caches()
                                    st.toast(f"Deleted {len(selected)} images")
                                    st.rerun()
                            with c2:
                                if st.button("Cancel", key="cancel_del"):
                                    st.session_state.confirm_bulk_delete = False
                                    st.rerun()

                    with b2:
                        if st.button("Re-analyse Selected", key="bulk_re", use_container_width=True):
                            sel_imgs = [i for i in images if i["id"] in selected]
                            progress = st.progress(0)
                            for idx, si in enumerate(sel_imgs):
                                src = si.get("image_url") or ""
                                if src:
                                    _run_analysis(si["id"], src)
                                progress.progress((idx + 1) / len(sel_imgs))
                            _invalidate_caches()
                            st.toast(f"Re-analysed {len(sel_imgs)} images")
                            st.session_state.selected_ids = set()
                            st.rerun()

        # ── Image Gallery Preview (Enhancement 3) ────────────────────────
        with st.expander("\u29C9  Gallery View", expanded=False):
            gallery_imgs = cached_get_all_images(user_id=user_id)
            if not gallery_imgs:
                st.caption("No images yet.")
            else:
                MOOD_COLORS = {
                    "calm": "#60a5fa", "energetic": "#fbbf24", "joyful": "#34d399",
                    "melancholic": "#c084fc", "mysterious": "#818cf8", "neutral": "#94a3b8",
                }
                cols = st.columns(3)
                for i, gimg in enumerate(gallery_imgs):
                    with cols[i % 3]:
                        url = gimg.get("image_url", "")
                        if url:
                            st.image(url, width=90)
                        mood = gimg.get("primary_mood", "neutral")
                        analyzed = bool(gimg.get("is_analyzed"))
                        color = MOOD_COLORS.get(mood, "#94a3b8")
                        status_icon = bi("check-circle-fill", "0.6em", color) if analyzed else bi("hourglass-split", "0.6em", "rgba(255,255,255,0.3)")
                        st.markdown(
                            f"<p style='font-size:0.55rem;margin:0;text-align:center'>"
                            f"<span style='color:{color}'>{status_icon} {mood}</span></p>",
                            unsafe_allow_html=True,
                        )
                        if st.button("Display", key=f"gal_{gimg['id']}", use_container_width=True):
                            update_preferences(user_id, override_active=1, override_image_id=gimg["id"])
                            st.toast(f"Displaying: {gimg.get('title', 'Image')}")
                            st.rerun()

        st.divider()

        # ── Image Scheduling (Enhancement 9) ─────────────────────────────
        with st.expander("\u29D6  Image Scheduling", expanded=False):
            sched_imgs = cached_get_all_images(user_id=user_id)
            if not sched_imgs:
                st.caption("No images to schedule.")
            else:
                sched_target = st.selectbox(
                    "Select image",
                    options=sched_imgs,
                    format_func=lambda x: x.get("title") or "Untitled",
                    key="sched_image_select",
                    label_visibility="collapsed",
                )
                if sched_target:
                    sid = sched_target["id"]
                    current_window = sched_target.get("time_window") or "any"

                    s_start = st.date_input("Start date", value=None, key=f"sched_s_{sid}")
                    s_end = st.date_input("End date", value=None, key=f"sched_e_{sid}")

                    all_periods = ["dawn", "morning", "afternoon", "evening", "night"]
                    current_periods = all_periods if current_window == "any" else [
                        p.strip() for p in current_window.split(",") if p.strip() in all_periods
                    ]
                    s_window = st.multiselect(
                        "Show during", all_periods,
                        default=current_periods,
                        key=f"sched_w_{sid}",
                    )

                    if st.button("Save Schedule", key=f"sched_save_{sid}", use_container_width=True):
                        window_str = "any" if set(s_window) == set(all_periods) or not s_window else ",".join(s_window)
                        update_image_schedule(
                            sid,
                            str(s_start) if s_start else "",
                            str(s_end) if s_end else "",
                            window_str,
                        )
                        _invalidate_caches()
                        st.toast("Schedule saved!")
                        st.rerun()

        st.divider()

        # ── Analytics Dashboard (Enhancement 4) ──────────────────────────
        with st.expander("\u2261  Analytics", expanded=False):
            analytics_view = st.selectbox(
                "View", ["Interactions", "Mood Trends", "Usage Patterns"],
                key="analytics_view", label_visibility="collapsed",
            )

            if analytics_view == "Interactions":
                data = cached_analytics_summary(user_id=user_id)
                if data:
                    df = pd.DataFrame(data)
                    if not df.empty and "likes" in df.columns:
                        chart_df = df.set_index("title")[["likes", "skips"]].head(10)
                        if chart_df[["likes", "skips"]].sum().sum() > 0:
                            st.bar_chart(chart_df)
                        # Leaderboards
                        st.markdown("<p style='font-size:0.6rem;color:rgba(255,255,255,0.4);"
                                    "margin:8px 0 2px'>Most Liked</p>", unsafe_allow_html=True)
                        for _, row in df.nlargest(3, "likes").iterrows():
                            st.markdown(f"<p style='font-size:0.65rem;margin:2px 0;font-weight:300'>"
                                        f"{bi('heart-fill', '0.65em', '#f472b6')} {row['likes']} — {row['title']}</p>",
                                        unsafe_allow_html=True)
                        st.markdown("<p style='font-size:0.6rem;color:rgba(255,255,255,0.4);"
                                    "margin:8px 0 2px'>Most Skipped</p>", unsafe_allow_html=True)
                        for _, row in df.nlargest(3, "skips").iterrows():
                            st.markdown(f"<p style='font-size:0.65rem;margin:2px 0;font-weight:300'>"
                                        f"{bi('skip-forward-fill', '0.65em', '#94a3b8')} {row['skips']} — {row['title']}</p>",
                                        unsafe_allow_html=True)
                else:
                    st.caption("No interaction data yet.")

            elif analytics_view == "Mood Trends":
                data = cached_mood_over_time(30)
                if data:
                    df = pd.DataFrame(data)
                    if not df.empty and df["count"].sum() > 0:
                        pivot = df.pivot_table(
                            index="date", columns="mood", values="count",
                            fill_value=0, aggfunc="sum",
                        )
                        # Only render if at least one cell is non-zero
                        if not pivot.empty and pivot.values.sum() > 0:
                            st.area_chart(pivot)
                    else:
                        st.caption("No mood history yet.")
                else:
                    st.caption("No mood history yet.")

            elif analytics_view == "Usage Patterns":
                data = cached_hourly_usage()
                if data:
                    df = pd.DataFrame(data)
                    if not df.empty and df["count"].sum() > 0:
                        st.bar_chart(df.set_index("hour")["count"])
                    else:
                        st.caption("No usage data yet.")
                else:
                    st.caption("No usage data yet.")

        # ── AI Analysis Settings (Enhancement 10) ────────────────────────
        with st.expander("\u2699  AI Analysis Settings", expanded=False):
            config = get_display_config()

            depth = st.radio(
                "Analysis Depth",
                ["Quick", "Standard"],
                index=0 if config.get("analysis_depth") == "quick" else 1,
                key="analysis_depth_radio",
                horizontal=True,
            )

            focus_options = ["composition", "color_palette", "emotional_depth",
                             "lighting", "texture", "symbolism"]
            current_focus = [f for f in config.get("analysis_focus", "").split(",") if f in focus_options]
            focus = st.multiselect("Focus Areas", focus_options, default=current_focus, key="analysis_focus_ms")

            custom = st.text_area(
                "Custom Instructions",
                value=config.get("custom_prompt", ""),
                placeholder="e.g. Pay attention to architectural elements",
                key="custom_prompt_ta",
                height=68,
            )

            if st.button("Save AI Settings", use_container_width=True, key="save_ai_settings"):
                update_display_config(
                    analysis_depth=depth.lower(),
                    analysis_focus=",".join(focus),
                    custom_prompt=custom,
                )
                st.toast("AI settings saved!")
                st.rerun()

        st.divider()

        # ── Recent History ─────────────────────────────────────────────────
        with st.expander("\u2630  Recent History", expanded=False):
            logs = get_recent_logs(limit=8, user_id=user_id)
            if not logs:
                st.caption("No decisions recorded yet.")
            for log in logs:
                score = int((log.get("selection_score") or 0) * 100)
                title = log.get("image_title") or "Unknown"
                _ts   = log.get("timestamp") or ""
                ts    = str(_ts)[:16] if _ts else ""
                override_badge = f" {bi('arrow-repeat', '0.6em', 'rgba(255,255,255,0.5)')}" if log.get("was_override") else ""
                st.markdown(
                    f"<div style='margin-bottom:8px'>"
                    f"<p style='font-size:0.68rem;margin:0;font-weight:300'>{title}{override_badge}</p>"
                    f"<p style='font-size:0.58rem;color:rgba(255,255,255,0.3);margin:0'>"
                    f"{ts} · {score}%</p></div>",
                    unsafe_allow_html=True,
                )

            # ── Export logs as CSV ────────────────────────────────────────
            all_logs = get_recent_logs(limit=500, user_id=user_id)
            if all_logs:
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow([
                    "timestamp", "image", "time_period",
                    "score", "t_time", "t_mood", "t_pref",
                    "t_quality", "t_recency", "t_interaction", "override",
                ])
                for lg in all_logs:
                    bd = lg.get("score_breakdown") or {}
                    writer.writerow([
                        str(lg.get("timestamp") or "")[:19],
                        lg.get("image_title") or "Unknown",
                        lg.get("time_period") or "",
                        f"{lg.get('selection_score', 0):.3f}",
                        f"{bd.get('time', 0):.3f}",
                        f"{bd.get('mood', 0):.3f}",
                        f"{bd.get('preference', 0):.3f}",
                        f"{bd.get('quality', 0):.3f}",
                        f"{bd.get('recency', 0):.3f}",
                        f"{bd.get('interaction', 0):.3f}",
                        "yes" if lg.get("was_override") else "no",
                    ])
                st.download_button(
                    "\u2913 Export All Logs (CSV)",
                    data=buf.getvalue(),
                    file_name="chronos_context_logs.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


# =============================================================================
# No-Image Placeholder
# =============================================================================

PLACEHOLDER_CSS_URL = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='1' height='1'%3E%3Crect fill='%23090909'/%3E%3C/svg%3E"
)


def render_empty_state() -> None:
    """Shown when no analysed images exist in the database."""
    moon_icon = bi('moon-stars', '2.5rem', 'rgba(255,255,255,0.6)')
    st.markdown(f"""
    <div style="
        position: fixed; top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        text-align: center; z-index: 10;
        animation: fadeInUp 1s ease forwards;
    ">
      <p style="font-size:2.5rem;margin:0">{moon_icon}</p>
      <p style="font-size:1rem;font-weight:200;letter-spacing:0.1em;margin:12px 0 6px">
        Chronos is ready.
      </p>
      <p style="font-size:0.75rem;color:rgba(255,255,255,0.4);font-weight:300;
                max-width:280px;line-height:1.6;margin:0 auto">
        Open the sidebar and upload your first image.<br>
        Gemini will analyse it and the display will come alive.
      </p>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# Main Application
# =============================================================================

def main() -> None:
    """
    Orchestrates the full Chronos display loop:
      0. Authenticate user (login/register gate)
      1. Determine context (time of day, mood)
      2. Select the best image via the Decision Engine (user-scoped, profile-aware)
      3. Inject the image as the full-viewport CSS background with themed overrides
      4. Render the status bar, reasoning overlay, and sidebar controls
    """
    # ── 0. Authentication gate ─────────────────────────────────────────────
    try:
        init_auth_state()
    except RuntimeError as e:
        st.error(f"**Database not configured:** {e}")
        st.info("Add `DATABASE_URL` to your `.env` file and restart the app.")
        st.stop()

    if not st.session_state.get("authenticated"):
        render_auth_page()
        return

    user_id      = st.session_state.get("user_id", "")
    profile_type = st.session_state.get("profile_type", "Standard")

    # ── 1. Context & Engine ────────────────────────────────────────────────
    context = get_current_context()
    result  = select_best_image(context, user_id=user_id, profile_type=profile_type)

    # ── 2. Determine background ───────────────────────────────────────────
    if result and result.image:
        css_url = get_image_css_url(result.image)
    else:
        css_url = PLACEHOLDER_CSS_URL

    # ── 3. Inject CSS (includes the background image + profile theme) ─────
    inject_global_css(css_url, context.get("time_period", "day"), profile_type=profile_type)

    # ── Persistent sidebar FAB (JS-injected, immune to CSS transform issues)
    inject_sidebar_fab()

    # ── 4. Fixed UI elements (rendered as HTML, position:fixed) ───────────
    render_status_bar(context)
    render_reasoning_overlay(result)

    # ── Sidebar ───────────────────────────────────────────────────────────
    try:
        render_sidebar(context, result, user_id=user_id, profile_type=profile_type)
    except RuntimeError as _db_err:
        with st.sidebar:
            st.warning(f"Database temporarily unavailable: {_db_err}")

    # ── Empty state ───────────────────────────────────────────────────────
    if result is None:
        render_empty_state()

    # ── Invisible spacer: gives the page height so scrolling doesn't break
    st.markdown(
        "<div style='height:100vh;pointer-events:none'></div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
