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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# ─── Page config — MUST be the first Streamlit call ──────────────────────────
st.set_page_config(
    page_title="Chronos",
    page_icon="logos/chronos_logo.png",
    layout="wide",
    initial_sidebar_state="auto",
)

# ─── Internal imports (after page config) ────────────────────────────────────
import pandas as pd
from database.queries import (
    get_all_images, add_image, get_preferences, update_preferences,
    get_recent_logs, deactivate_image, hard_delete_image, save_interaction,
    search_images, deactivate_images, get_image_interaction_summary,
    get_mood_distribution, get_hourly_usage, get_mood_over_time,
    get_display_config, update_display_config,
    get_presets, save_preset, delete_preset, apply_preset,
    update_image_error, update_image_schedule,
    get_top_images_by_display, get_score_trend,
)
from logic.context              import get_current_context
from logic.engine               import WEIGHT_PROFILES
from services.vision            import analyze_image
from services.cloudinary_upload import upload_image as cloudinary_upload, delete_image as cloudinary_delete
from auth                       import init_auth_state, render_auth_page, logout, get_theme_overrides
from database                   import init_database
from services.manager           import ChronosManager

# Wrapped in cache_resource so it runs exactly once per server process,
# not on every Streamlit rerun.
@st.cache_resource
def _init_database_once():
    try:
        init_database()
    except Exception:
        pass  # DB unavailable at startup — queries will surface the error later

_init_database_once()

# No local upload directory — images are stored on Cloudinary


# ─── Cached data helpers (Enhancement 6) ─────────────────────────────────────

@st.cache_data(ttl=60)
def cached_get_all_images(user_id: str = ""):
    return get_all_images(user_id=user_id)

@st.cache_data(ttl=10)
def cached_get_preferences(user_id: str = ""):
    return get_preferences(user_id=user_id)

@st.cache_data(ttl=300)
def cached_get_display_config():
    return get_display_config()

@st.cache_data(ttl=180)
def cached_get_presets():
    return get_presets()

@st.cache_data(ttl=180)
def cached_analytics_summary(user_id: str = ""):
    return get_image_interaction_summary(user_id=user_id)

@st.cache_data(ttl=180)
def cached_mood_distribution():
    return get_mood_distribution()

@st.cache_data(ttl=180)
def cached_hourly_usage():
    return get_hourly_usage()

@st.cache_data(ttl=180)
def cached_mood_over_time(days=30, user_id=""):
    return get_mood_over_time(days, user_id=user_id)

@st.cache_data(ttl=180)
def cached_top_images_by_display(user_id="", limit=10):
    return get_top_images_by_display(user_id=user_id, limit=limit)

@st.cache_data(ttl=120)
def cached_score_trend(days=30, user_id=""):
    return get_score_trend(days=days, user_id=user_id)


# =============================================================================
# CSS Injection —dark theme
# =============================================================================

def inject_static_assets(profile_type: str = "Standard", poll_interval: int = 300) -> None:
    """
    Injects the full CSS bundle and the browser refresh meta-tag.
    """
    st.markdown(_static_styles_html(profile_type), unsafe_allow_html=True)
    # Emit meta-refresh at a fixed position so Streamlit's diff treats it as
    # the same element on every rerun and the browser timer is not reset.
    st.markdown(f'<meta http-equiv="refresh" content="{poll_interval}">', unsafe_allow_html=True)


def update_dynamic_background(image_css_url: str, time_period: str) -> None:
    """
    Injects only the tiny data-carrier div that changes on every rerun.
    The crossfade engine JS reads data-url / data-brightness and drives the
    actual background layers outside Streamlit's DOM subtree.
    """
    brightness = 0.65 if time_period == "night" else 0.85
    st.markdown(
        f'<div id="chronos-bg-src" data-url="{image_css_url}" '
        f'data-brightness="{brightness}" style="display:none"></div>',
        unsafe_allow_html=True,
    )


def inject_global_css(image_css_url: str, time_period: str, profile_type: str = "Standard", animate: bool = True, poll_interval: int = 300) -> None:
    """Thin wrapper kept for call-site compatibility."""
    inject_static_assets(profile_type, poll_interval=poll_interval)
    update_dynamic_background(image_css_url, time_period)



@st.cache_data
def _static_styles_html(profile_type: str = "Standard") -> str:
    """Returns the static page CSS as an HTML string, cached per profile_type.
    Only the tiny dynamic background block (image URL + brightness) is
    injected fresh on every rerun — everything else comes from here."""
    theme_css   = get_theme_overrides(profile_type)
    theme_block = f"<style>{theme_css}</style>" if theme_css else ""
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

#MainMenu, header, footer, .stDeployButton,
[data-testid="stToolbar"] {{ visibility: hidden !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
.viewerBadge_container__1QSob {{ display: none !important; }}

*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{
    margin: 0; padding: 0;
    background-color: #090909;
    font-family: 'Inter', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #f0f0f0;
}}

@keyframes chronosFadeIn {{
    0%   {{ opacity: 0; transform: scale(1.012); }}
    100% {{ opacity: 1; transform: scale(1);     }}
}}

.stApp {{
    background: transparent !important;
    min-height: 100vh;
}}

.stApp::before {{
    content: "";
    position: fixed; inset: 0;
    background: radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.72) 100%);
    pointer-events: none;
    z-index: 0;
}}

.stApp::after {{
    content: "";
    position: fixed; bottom: 0; left: 0; right: 0;
    height: 45%;
    background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
    pointer-events: none;
    z-index: 0;
}}

.main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
    position: relative;
    z-index: 1;
}}

.glass {{
    background: rgba(255,255,255,0.055) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 18px;
}}

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
@keyframes breatheGlow {{
    0%, 100% {{ background: rgba(167,139,250,0.2); box-shadow: 0 0 8px rgba(167,139,250,0.1); }}
    50%       {{ background: rgba(167,139,250,0.4); box-shadow: 0 0 20px rgba(167,139,250,0.3); }}
}}
@keyframes glowPulse {{
    0%   {{ box-shadow: 0 0 0   0   rgba(167,139,250,0);    border-color: rgba(255,255,255,0.09); }}
    50%  {{ box-shadow: 0 0 14px 2px rgba(167,139,250,0.25); border-color: rgba(167,139,250,0.55); }}
    100% {{ box-shadow: 0 0 0   0   rgba(167,139,250,0);    border-color: rgba(255,255,255,0.09); }}
}}

.anim-up {{ animation: fadeInUp  0.7s cubic-bezier(0.22,1,0.36,1) forwards; }}
.anim-in {{ animation: slideRight 0.5s ease forwards; }}

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
    font-size: 0.65rem; font-weight: 400;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: rgba(255,255,255,0.5);
}}

.reasoning-card {{
    position: fixed; bottom: 36px; left: 50%;
    transform: translateX(-50%);
    width: min(400px, 90vw); padding: 18px 22px;
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
.reasoning-score {{ font-size: 0.68rem; font-weight: 600; color: #c4b5fd; letter-spacing: 0.05em; }}
.reasoning-text {{
    font-size: 0.78rem; font-weight: 300;
    color: rgba(255,255,255,0.78);
    line-height: 1.55; letter-spacing: 0.02em; margin-bottom: 12px;
}}
.tags-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.tag-chip {{
    padding: 3px 10px; border-radius: 999px;
    font-size: 0.6rem; font-weight: 500;
    letter-spacing: 0.06em; text-transform: uppercase;
    background: rgba(167,139,250,0.14);
    border: 1px solid rgba(167,139,250,0.28);
    color: #c4b5fd;
    animation: slideRight 0.4s ease forwards;
}}

[data-testid="stSidebar"] {{
    background:             rgba(10,10,15,0.85) !important;
    backdrop-filter:        blur(30px) saturate(200%) contrast(110%) !important;
    -webkit-backdrop-filter:blur(30px) saturate(200%) contrast(110%) !important;
    border-right:           1px solid rgba(255,255,255,0.09) !important;
    z-index:                999 !important;
    box-shadow:             8px 0 64px rgba(0,0,0,0.8), inset -1px 0 2px rgba(255,255,255,0.04) !important;
}}
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar {{ width: 2px; }}
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-track {{ background: transparent; }}
[data-testid="stSidebar"] > div:first-child::-webkit-scrollbar-thumb {{
    background: rgba(255,255,255,0.10); border-radius: 99px;
}}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] div {{ color: rgba(255,255,255,0.82) !important; }}
[data-testid="stSidebar"] .stSelectbox    label,
[data-testid="stSidebar"] .stSlider       label,
[data-testid="stSidebar"] .stRadio        label,
[data-testid="stSidebar"] .stSelectSlider label {{
    font-size: 0.5rem !important; letter-spacing: 0.22em !important;
    text-transform: uppercase !important; color: rgba(255,255,255,0.28) !important;
    font-weight: 700 !important; margin-bottom: 5px !important;
}}
[data-testid="stSidebar"] hr {{
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.06) !important;
    margin: 10px 0 !important;
}}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 8px !important; min-height: 36px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:hover {{
    border-color: rgba(167,139,250,0.50) !important;
    box-shadow: 0 0 0 2px rgba(167,139,250,0.09), 0 0 12px rgba(167,139,250,0.10) !important;
}}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * {{
    color: rgba(255,255,255,0.82) !important;
    font-size: 0.74rem !important; background: transparent !important;
}}
[data-testid="stSidebar"] .stSelectbox svg {{ fill: rgba(255,255,255,0.3) !important; }}
[data-testid="stSidebar"] [data-testid="stSelectSlider"] > div > div {{
    background: rgba(255,255,255,0.07) !important; border-radius: 99px !important;
}}
[data-testid="stSidebar"] [data-testid="stSelectSlider"] [role="slider"] {{
    background: #a78bfa !important; box-shadow: 0 0 10px rgba(167,139,250,0.55) !important;
    border: 2px solid rgba(255,255,255,0.22) !important; transition: box-shadow 0.2s ease !important;
}}
[data-testid="stSidebar"] [data-testid="stSelectSlider"] [role="slider"]:hover {{
    box-shadow: 0 0 18px rgba(167,139,250,0.80) !important;
}}
[data-testid="stSidebar"] [data-testid="stToggle"] label p {{
    font-size: 0.62rem !important; letter-spacing: 0.12em !important;
    text-transform: uppercase !important; color: rgba(255,255,255,0.42) !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: rgba(255,255,255,0.022) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important; overflow: hidden !important;
    transition: border-color 0.25s ease !important; margin-bottom: 3px !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"]:hover {{ border-color: rgba(255,255,255,0.13) !important; }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    font-size: 0.6rem !important; letter-spacing: 0.14em !important;
    text-transform: uppercase !important; color: rgba(255,255,255,0.42) !important;
    padding: 10px 14px !important; transition: color 0.2s ease !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{ color: rgba(255,255,255,0.82) !important; }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary > svg {{
    fill: rgba(255,255,255,0.28) !important; stroke: rgba(255,255,255,0.28) !important;
    transition: fill 0.2s ease !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    background: rgba(167,139,250,0.09) !important;
    border: 1px solid rgba(167,139,250,0.26) !important;
    color: #c4b5fd !important; border-radius: 8px !important;
    font-size: 0.6rem !important; letter-spacing: 0.14em !important;
    text-transform: uppercase !important; font-weight: 600 !important;
    padding: 8px 14px !important;
    transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(167,139,250,0.20) !important;
    border-color: rgba(167,139,250,0.52) !important;
    box-shadow: 0 0 14px rgba(167,139,250,0.18) !important;
}}
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {{ opacity: 0 !important; pointer-events: none !important; }}

body::after {{
    content: "";
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    opacity: 0.025; pointer-events: none; z-index: 10; mix-blend-mode: overlay;
}}

html {{ overflow-x: hidden; }}
.stApp {{ min-height: 100dvh; }}
.reasoning-card {{ bottom: calc(36px + env(safe-area-inset-bottom, 0px)); }}
button, [role="button"], summary {{ touch-action: manipulation; }}
[data-testid="stSidebar"] > div:first-child {{ -webkit-overflow-scrolling: touch; }}

@media (max-width: 900px) {{
    .status-bar     {{ top: 14px; left: 16px; }}
    .reasoning-card {{ bottom: calc(24px + env(safe-area-inset-bottom, 0px)); padding: 14px 18px; }}
}}
@media (max-width: 640px) {{
    .status-bar  {{ top: 12px; left: 12px; gap: 7px; }}
    .status-dot  {{ width: 6px; height: 6px; }}
    .status-text {{ font-size: 0.55rem; letter-spacing: 0.08em; }}
    .reasoning-card {{
        left: 12px; right: 12px;
        bottom: calc(12px + env(safe-area-inset-bottom, 0px));
        width: auto; transform: none; padding: 12px 14px; border-radius: 14px;
    }}
    .reasoning-text   {{ font-size: 0.70rem; line-height: 1.5; margin-bottom: 10px; }}
    .reasoning-period {{ font-size: 0.56rem; }}
    .reasoning-score  {{ font-size: 0.60rem; }}
    .score-track      {{ margin-bottom: 10px; }}
    .tag-chip         {{ font-size: 0.52rem; padding: 2px 8px; }}
    [data-testid="stSidebar"] > div:first-child {{
        padding-left: 12px !important; padding-right: 12px !important;
    }}
    #chronos-fab {{
        top:   calc(12px + env(safe-area-inset-top,   0px)) !important;
        right: calc(12px + env(safe-area-inset-right, 0px)) !important;
        width: 36px !important; height: 36px !important;
    }}
}}
@media (max-width: 400px) {{
    .reasoning-card {{ padding: 10px 12px; border-radius: 12px; }}
    .reasoning-text {{ font-size: 0.65rem; }}
    .tags-row       {{ gap: 4px; }}
    .tag-chip       {{ font-size: 0.50rem; padding: 2px 6px; }}
}}

/* ── Cross-fade background layers ─────────────────────────────────────── */
/* Created and managed by inject_crossfade_engine() JS.                    */
/* They live on document.body so they're outside Streamlit's DOM subtree   */
/* and survive reruns without blinking.                                     */
.chronos-layer {{
    position: fixed; inset: 0;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    z-index: -1;
    transition: opacity 0.85s ease-in-out, filter 0.85s ease-in-out;
    will-change: opacity;
}}

/* ── Auto-hide UI ─────────────────────────────────────────────────────── */
/* Added to document.body by inject_autohide_ui() after idle timeout.      */
.chronos-ui-idle .reasoning-card,
.chronos-ui-idle .status-bar {{
    opacity: 0 !important;
    pointer-events: none !important;
    transition: opacity 2s ease !important;
}}
/* Fast reveal on interaction */
.reasoning-card, .status-bar {{
    transition: opacity 0.25s ease;
}}

/* ── Score bar — starts at 0 width, animated via JS ─────────────────── */
.score-fill {{
    width: 0% !important;   /* JS sets the real value after one rAF */
    transition: width 1.2s cubic-bezier(0.22,1,0.36,1) !important;
}}

/* ── Skeleton / shimmer loader ────────────────────────────────────────── */
@keyframes chronosShimmer {{
    0%   {{ background-position: -200% 0; }}
    100% {{ background-position:  200% 0; }}
}}
.skeleton-line {{
    border-radius: 4px;
    background: linear-gradient(
        90deg,
        rgba(255,255,255,0.04) 0%,
        rgba(255,255,255,0.11) 50%,
        rgba(255,255,255,0.04) 100%
    );
    background-size: 200% 100%;
    animation: chronosShimmer 1.6s ease-in-out infinite;
}}
</style>{theme_block}"""


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
            /* querySelector falls back to the container itself for Streamlit  */
            /* versions where stSidebarCollapseButton IS the button element.   */
            function findBtn(testId) {
                return pd.querySelector('[data-testid="' + testId + '"] button')
                    || pd.querySelector('[data-testid="' + testId + '"]');
            }

            fab.addEventListener('click', function (e) {
                e.preventDefault();
                var collapseBtn = findBtn('stSidebarCollapseButton');
                var expandBtn   = findBtn('collapsedControl');

                if (sidebarOpen()) {
                    if (collapseBtn) collapseBtn.click();
                } else {
                    if (expandBtn)        expandBtn.click();
                    else if (collapseBtn) collapseBtn.click();
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
# Cross-fade Engine (JS injection)
# =============================================================================

def inject_crossfade_engine() -> None:
    """
    Injects a persistent MutationObserver that watches #chronos-bg-src for URL
    changes and cross-fades between two background layers (A/B flip pattern).

    Why this beats a CSS animation on #chronos-bg:
    - Streamlit replaces the DOM on every rerun; a new #chronos-bg flashes in.
    - These two layers live on document.body (outside Streamlit's DOM subtree)
      so they survive reruns without being replaced.
    - We only swap when the URL actually changes; same-URL reruns (sidebar
      interactions) never trigger a transition at all.
    """
    import streamlit.components.v1 as _c
    _c.html(
        """
        <script>
        (function () {
            var pd = window.parent.document;
            if (pd.getElementById('chronos-xfade-init')) return;

            /* ── One-time init marker ─────────────────────────────────── */
            var mk = pd.createElement('span');
            mk.id = 'chronos-xfade-init';
            mk.style.display = 'none';
            pd.body.appendChild(mk);

            /* ── Build the two permanent background layers ────────────── */
            function makeLayer(id) {
                var el = pd.createElement('div');
                el.id        = id;
                el.className = 'chronos-layer';
                el.style.opacity = '0';
                pd.body.appendChild(el);
                return el;
            }
            var layerA = makeLayer('chronos-layer-a');
            var layerB = makeLayer('chronos-layer-b');
            var front  = layerA;   /* currently visible layer */
            var back   = layerB;   /* loading / inactive layer */
            var lastUrl = '';

            /* ── Cross-fade to new image ──────────────────────────────── */
            function crossfade(url, brightness) {
                if (url === lastUrl) return;   /* sidebar rerun — skip */
                lastUrl = url;
                var filter = 'brightness(' + brightness + ') saturate(1.05)';

                /* Preload on back layer, invisible */
                back.style.transition = 'none';
                back.style.backgroundImage = 'url(' + url + ')';
                back.style.filter    = filter;
                back.style.opacity   = '0';
                back.offsetHeight;   /* force reflow before re-enabling transition */

                /* Fade in back, fade out front simultaneously */
                back.style.transition  = 'opacity 0.85s ease-in-out, filter 0.85s ease-in-out';
                front.style.transition = 'opacity 0.85s ease-in-out';
                back.style.opacity  = '1';
                front.style.opacity = '0';

                /* Swap references */
                var tmp = front; front = back; back = tmp;
            }

            /* ── Watch document.body for #chronos-bg-src appearing/changing ── */
            var obs = new MutationObserver(function () {
                var src = pd.getElementById('chronos-bg-src');
                if (!src) return;
                var url  = src.getAttribute('data-url') || '';
                var br   = parseFloat(src.getAttribute('data-brightness')) || 0.85;
                crossfade(url, br);
            });
            obs.observe(pd.body, { childList: true, subtree: true });

            /* ── Also fire on initial load if element already present ─── */
            var src0 = pd.getElementById('chronos-bg-src');
            if (src0) crossfade(
                src0.getAttribute('data-url') || '',
                parseFloat(src0.getAttribute('data-brightness')) || 0.85
            );
        }());
        </script>
        """,
        height=0,
        scrolling=False,
    )


# =============================================================================
# Auto-hide UI (JS injection)
# =============================================================================

def inject_autohide_ui(timeout_ms: int = 8000) -> None:
    """
    Fades out the reasoning overlay and status bar after `timeout_ms` ms of
    inactivity (no mouse/touch/keyboard events).  Any interaction instantly
    restores them.  The CSS class 'chronos-ui-idle' drives the fade via the
    rules in _static_styles_html().
    """
    import streamlit.components.v1 as _c
    _c.html(
        f"""
        <script>
        (function () {{
            var pd = window.parent.document;
            if (pd.getElementById('chronos-autohide-init')) return;

            var mk = pd.createElement('span');
            mk.id = 'chronos-autohide-init';
            mk.style.display = 'none';
            pd.body.appendChild(mk);

            var TIMEOUT = {timeout_ms};
            var timer;

            function goIdle()  {{ pd.body.classList.add('chronos-ui-idle'); }}
            function wake()    {{
                pd.body.classList.remove('chronos-ui-idle');
                clearTimeout(timer);
                timer = setTimeout(goIdle, TIMEOUT);
            }}

            ['mousemove', 'mousedown', 'touchstart', 'keydown', 'wheel', 'scroll'].forEach(function (ev) {{
                window.parent.addEventListener(ev, wake, {{ passive: true }});
            }});

            /* Start the timer immediately */
            timer = setTimeout(goIdle, TIMEOUT);
        }}());
        </script>
        """,
        height=0,
        scrolling=False,
    )


# =============================================================================
# Score-bar Animator (JS injection)
# =============================================================================

def inject_score_animator() -> None:
    """
    Animates .score-fill from 0% → data-score value, but ONLY when the score
    value differs from the previous render (i.e. the image actually changed).
    Same-image reruns (sidebar interactions) snap to value without transition.
    """
    import streamlit.components.v1 as _c
    _c.html(
        """
        <script>
        (function () {
            var pd = window.parent.document;
            var fill = pd.querySelector('.score-fill[data-score]');
            if (!fill) return;

            var target = fill.getAttribute('data-score');
            var prev   = window.__chronosLastScore;

            if (target !== prev) {
                /* New image — animate from 0 to target */
                window.__chronosLastScore = target;
                fill.style.width = '0%';
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        fill.style.width = target;
                    });
                });
            } else {
                /* Same image — snap without transition so we don't re-animate */
                fill.style.transition = 'none';
                fill.style.width      = target;
                fill.offsetHeight;    /* flush */
                fill.style.transition = '';
            }
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


def get_gallery_thumbnail_url(url: str, width: int = 200) -> str:
    """
    Return a Cloudinary thumbnail URL by injecting transformation params
    after the /upload/ segment.  Falls back to the original URL for non-
    Cloudinary hosts (local dev with SQLite, external URLs, etc.).

    Input:  https://res.cloudinary.com/NAME/image/upload/v123/photo.webp
    Output: https://res.cloudinary.com/NAME/image/upload/w_200,c_thumb,q_auto,f_auto/v123/photo.webp
    """
    if not url:
        return url
    marker = "/upload/"
    idx = url.find(marker)
    if idx == -1:
        return url  # not a Cloudinary URL — use as-is
    transform = f"w_{width},c_thumb,q_auto,f_auto"
    return url[: idx + len(marker)] + transform + "/" + url[idx + len(marker) :]


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


def render_reasoning_overlay(result, is_new: bool = False, profile_type: str = "Standard") -> None:
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

    # Profile-based Color Themes
    theme_colors = {
        "Professional": ("#34d399", "#10b981"), # Green
        "Kids":         ("#38bdf8", "#0ea5e9"), # Blue
        "Standard":     ("#a78bfa", "#7c3aed"), # Purple
    }
    primary, secondary = theme_colors.get(profile_type, theme_colors["Standard"])

    # SVG Progress Bar - robust across all browsers/Streamlit versions
    progress_svg = f"""
    <svg width="100%" height="4" style="border-radius:2px; margin-bottom:12px; display:block;">
      <defs>
        <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" style="stop-color:{primary};stop-opacity:1" />
          <stop offset="100%" style="stop-color:{secondary};stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="100%" height="4" fill="rgba(255,255,255,0.12)" rx="2" />
      <rect width="{confidence}%" height="4" fill="url(#scoreGrad)" rx="2">
        {"<animate attributeName='width' from='0' to='" + str(confidence) + "%' dur='1.2s' fill='freeze' calcMode='spline' keySplines='0.22 1 0.36 1' />" if is_new else ""}
      </rect>
    </svg>
    """

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
      {progress_svg}
      <div class="tags-row">{tags_html}</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# Sidebar — Control Dashboard
# =============================================================================

def _invalidate_caches():
    """Clear all Streamlit data caches after mutations."""
    cached_get_all_images.clear()
    cached_get_preferences.clear()
    cached_get_display_config.clear()
    cached_get_presets.clear()
    cached_analytics_summary.clear()
    cached_mood_distribution.clear()
    cached_hourly_usage.clear()
    cached_mood_over_time.clear()
    cached_top_images_by_display.clear()
    st.session_state["_force_refresh"] = True


def _run_analysis(image_id: str, source_url: str):
    """Run Gemini analysis on an image and save results. Returns AnalysisResult."""
    from database.queries import update_image_analysis
    # Load AI analysis settings
    config = cached_get_display_config()
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


def _process_upload_file(uploaded_file, user_id: str, profile_type: str):
    """Worker: upload one file to Cloudinary, analyse, safety-check.
    Safe to run in a thread — no Streamlit calls inside.
    Returns (filename, log_line)."""
    res = ChronosManager.process_new_upload(uploaded_file.getvalue(), uploaded_file.name, user_id)
    
    if not res["success"]:
        return uploaded_file.name, f"✗ {uploaded_file.name} — {res['error']}"
    
    return uploaded_file.name, f"✓ {uploaded_file.name} — Uploaded and Analysed"


def _process_upload_url(url: str, user_id: str, profile_type: str):
    """Worker: validate URL, add image, analyse, safety-check.
    Safe to run in a thread — no Streamlit calls inside.
    Returns (url_short, log_line)."""
    label = url[:60]
    res = ChronosManager.process_url_upload(url, user_id, profile_type)
    
    if not res["success"]:
        return label, f"✗ {label} — {res['error']}"
        
    return label, f"✓ {label} — URL Added and Analysed"


def _render_user_header(context: dict, profile_type: str) -> None:
    """User badge, clock, sign-out button."""
    user_display = st.session_state.get("user_name", "") or st.session_state.get("username", "")
    _badge_cfg = {
        "Kids":         ("\u2605 Kids", "rgba(56,189,248,0.12)",  "rgba(56,189,248,0.25)",  "#7dd3fc"),
        "Professional": ("\u25C8 Pro",  "rgba(52,211,153,0.10)",  "rgba(52,211,153,0.22)",  "#6ee7b7"),
    }
    _badge_html = ""
    if profile_type in _badge_cfg:
        _label, _bg, _border, _color = _badge_cfg[profile_type]
        _badge_html = (
            f"<span style='margin-left:6px;font-size:0.5rem;padding:2px 8px;border-radius:99px;"
            f"background:{_bg};border:1px solid {_border};"
            f"color:{_color};letter-spacing:0.1em;text-transform:uppercase;font-weight:600'>"
            f"{_label}</span>"
        )
    # Official Chronos Logo
    st.image("logos/chronos_logo_trans2.png", use_container_width=True)
    
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0 6px">
      <div>
        <div style="font-size:0.62rem;font-weight:400;margin:0;color:rgba(255,255,255,0.65);
                    display:flex;align-items:center;flex-wrap:wrap;gap:4px">
          {user_display}{_badge_html}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Sign Out", key="logout_btn"):
        logout()

    st.divider()

    st.markdown(f"""
    <div style="padding:4px 0 16px">
      <p style="font-size:0.5rem;letter-spacing:0.24em;text-transform:uppercase;
                color:rgba(255,255,255,0.22);margin:0 0 12px;font-weight:700">Chronos Control</p>
      <div style="display:flex;align-items:flex-end;gap:10px;margin-bottom:6px">
        <p style="font-size:2.2rem;font-weight:200;letter-spacing:-0.03em;margin:0;line-height:1;color:#ffffff">
          {context.get('hour',0)}:{context.get('minute',0):02d}
        </p>
        <span style="display:inline-block;width:7px;height:7px;border-radius:50%;
          background:#a78bfa;margin-bottom:8px;flex-shrink:0;
          animation:systemPulse 2.6s ease-in-out infinite;" title="AI active"></span>
      </div>
      <p style="font-size:0.52rem;text-transform:uppercase;letter-spacing:0.18em;
                color:rgba(255,255,255,0.22);margin:0;font-weight:600">
        {context.get('day_of_week','')} &nbsp;·&nbsp; {context.get('time_period','').capitalize()}
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()


def _render_playback_controls(
    result,
    prefs: dict,
    user_id: str,
    profile_type: str,
    all_imgs: list,
) -> None:
    """Now-Displaying card, Like/Skip/Prev/Next, mood + sensitivity, presets,
    Pro-only Mood Schedule + Scoring Weights, Manual Override toggle, Refresh."""
    from logic.engine import KIDS_BLOCKED_MOODS

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

        override_active = bool(prefs.get("override_active", 0))
        if override_active:
            nav_imgs = all_imgs
            if profile_type == "Kids":
                _kids_blocked = {"melancholic", "mysterious"}
                nav_imgs = [i for i in nav_imgs if i.get("primary_mood") not in _kids_blocked]
            prev_col, next_col, like_col = st.columns(3)
            with prev_col:
                if st.button("\u276E  Prev", key=f"prev_{img['id']}", use_container_width=True, disabled=len(nav_imgs) < 2):
                    if len(nav_imgs) > 1:
                        cur = next((i for i, im in enumerate(nav_imgs) if im["id"] == img["id"]), 0)
                        update_preferences(user_id, override_image_id=nav_imgs[(cur - 1) % len(nav_imgs)]["id"])
                        st.toast(f"← {nav_imgs[(cur - 1) % len(nav_imgs)].get('title', 'Image')}")
                        st.session_state["_force_refresh"] = True
                        st.rerun()
            with next_col:
                if st.button("Next  \u276F", key=f"next_{img['id']}", use_container_width=True, disabled=len(nav_imgs) < 2):
                    if len(nav_imgs) > 1:
                        cur = next((i for i, im in enumerate(nav_imgs) if im["id"] == img["id"]), 0)
                        update_preferences(user_id, override_image_id=nav_imgs[(cur + 1) % len(nav_imgs)]["id"])
                        st.toast(f"{nav_imgs[(cur + 1) % len(nav_imgs)].get('title', 'Image')} →")
                        st.session_state["_force_refresh"] = True
                        st.rerun()
            with like_col:
                if st.button("\u2764  Like", key=f"like_{img['id']}", use_container_width=True):
                    save_interaction(img["id"], "like")
                    st.toast("Liked — this image will score higher.")
                    st.session_state["_force_refresh"] = True
                    st.rerun()
        else:
            like_col, skip_col = st.columns(2)
            with like_col:
                if st.button("\u2764  Like", key=f"like_{img['id']}", use_container_width=True):
                    save_interaction(img["id"], "like")
                    st.toast("Liked — this image will score higher.")
                    st.session_state["_force_refresh"] = True
                    st.rerun()
            with skip_col:
                if st.button("\u2716  Skip", key=f"skip_{img['id']}", use_container_width=True):
                    save_interaction(img["id"], "skip")
                    st.toast("Skipped — this image will show less often.")
                    st.session_state["_force_refresh"] = True
                    st.rerun()

    st.divider()

    # ── Mood Preference ───────────────────────────────────────────────
    _all_moods = ["calm", "energetic", "joyful", "melancholic", "mysterious", "neutral"]
    MOODS = [m for m in _all_moods if profile_type != "Kids" or m not in KIDS_BLOCKED_MOODS]
    current_mood = prefs.get("preferred_mood", "calm")
    if current_mood not in MOODS:
        current_mood = "calm"
    new_mood = st.selectbox("Preferred Mood", MOODS, index=MOODS.index(current_mood), key="mood_select")
    if new_mood != current_mood:
        try:
            update_preferences(user_id, preferred_mood=new_mood)
            prefs["preferred_mood"] = new_mood
            st.toast(f"Mood set to {new_mood.capitalize()}")
        except Exception as e:
            st.toast(f"Failed to save mood: {e}", icon="🚨")

    # ── AI Sensitivity ────────────────────────────────────────────────
    SENS        = ["low", "medium", "high"]
    SENS_LABELS = ["Manual", "Balanced", "Full AI"]
    current_sens = prefs.get("sensitivity", "medium")
    sens_idx     = SENS.index(current_sens) if current_sens in SENS else 1
    new_sens_idx = st.radio("AI Sensitivity", SENS_LABELS, index=sens_idx, key="sens_radio", horizontal=True)
    new_sens = SENS[SENS_LABELS.index(new_sens_idx)]
    if new_sens != current_sens:
        try:
            update_preferences(user_id, sensitivity=new_sens)
            prefs["sensitivity"] = new_sens
            _sens_label = {"low": "Manual", "medium": "Balanced", "high": "Full AI"}.get(new_sens, new_sens)
            st.toast(f"AI Sensitivity → {_sens_label}")
        except Exception as e:
            st.toast(f"Failed to save sensitivity: {e}", icon="🚨")

    # ── Quick Presets ─────────────────────────────────────────────────
    presets = cached_get_presets()
    if presets:
        preset_names = ["— Select Preset —"] + [p["name"] for p in presets]
        _pk = st.session_state.get("_preset_counter", 0)
        selected_preset = st.selectbox(
            "Quick Presets", preset_names, index=0,
            key=f"preset_select_{_pk}", label_visibility="collapsed",
        )
        if selected_preset != "— Select Preset —":
            preset = next(p for p in presets if p["name"] == selected_preset)
            apply_preset(preset["id"], user_id=user_id)
            st.toast(f"Applied: {selected_preset}")
            st.session_state["_preset_counter"] = _pk + 1
            st.session_state["_force_refresh"] = True
            st.rerun()

    with st.popover("Save Current as Preset", use_container_width=True):
        preset_name = st.text_input("Preset name", key="new_preset_name")
        if preset_name and st.button("Save Preset", key="save_preset_btn"):
            save_preset(preset_name, new_mood, new_sens)
            cached_get_presets.clear()
            st.toast(f"Preset '{preset_name}' saved!")
        custom_presets = [p for p in presets if not p.get("is_default")]
        if custom_presets:
            st.caption("Delete a custom preset:")
            for p in custom_presets:
                if st.button(f"\u2715 {p['name']}", key=f"delpreset_{p['id']}"):
                    delete_preset(p["id"])
                    cached_get_presets.clear()
                    st.toast(f"Deleted preset '{p['name']}'")

    # ── Pro: Mood Schedule ────────────────────────────────────────────
    if profile_type == "Professional":
        with st.expander("\u29BE  Mood Schedule", expanded=False):
            st.caption("Pin a mood to each time period. Takes priority over your global preference.")
            _all_moods_pro = ["calm", "energetic", "joyful", "melancholic", "mysterious", "neutral"]
            _periods_cfg   = ["dawn", "morning", "afternoon", "evening", "night"]
            _time_map      = dict(prefs.get("time_mood_map") or {})
            _new_map: dict = {}
            for _period in _periods_cfg:
                _c1, _c2 = st.columns([1.1, 2])
                with _c1:
                    st.markdown(
                        f"<div style='font-size:0.62rem;padding-top:8px;color:rgba(255,255,255,0.7)'>"
                        f"{bi(PERIOD_ICONS_BI[_period], '0.85em')} {_period.capitalize()}</div>",
                        unsafe_allow_html=True,
                    )
                with _c2:
                    _opts = ["— Auto —"] + _all_moods_pro
                    _cur  = _time_map.get(_period, "— Auto —")
                    if _cur not in _opts:
                        _cur = "— Auto —"
                    _sel = st.selectbox("", _opts, index=_opts.index(_cur),
                                        key=f"tmm_{_period}", label_visibility="collapsed")
                    if _sel != "— Auto —":
                        _new_map[_period] = _sel
            if "__weights" in _time_map:
                _new_map["__weights"] = _time_map["__weights"]
            if st.button("Save Schedule", use_container_width=True, key="save_mood_schedule"):
                try:
                    update_preferences(user_id, time_mood_map=_new_map)
                    cached_get_preferences.clear()
                    st.toast("Mood schedule saved")
                except Exception as e:
                    st.toast(f"Failed to save schedule: {e}", icon="\U0001F6A8")

    # ── Pro: Scoring Weights ──────────────────────────────────────────
    if profile_type == "Professional":
        with st.expander("\u29C6  Scoring Weights", expanded=False):
            st.caption("Fine-tune how each factor is weighted when the AI picks an image.")
            _time_map_w = dict(prefs.get("time_mood_map") or {})
            _saved_w    = _time_map_w.get("__weights") or {}
            _default_w  = WEIGHT_PROFILES.get(prefs.get("sensitivity", "medium"), WEIGHT_PROFILES["medium"])
            _w_time = st.slider("Time Match",      0.0, 1.0, float(_saved_w.get("time",       _default_w["time"])),       0.05, key="pro_w_time")
            _w_mood = st.slider("Mood Match",      0.0, 1.0, float(_saved_w.get("mood",       _default_w["mood"])),       0.05, key="pro_w_mood")
            _w_pref = st.slider("Preference",      0.0, 1.0, float(_saved_w.get("preference", _default_w["preference"])), 0.05, key="pro_w_pref")
            _w_qual = st.slider("Image Quality",   0.0, 1.0, float(_saved_w.get("quality",    _default_w["quality"])),    0.05, key="pro_w_qual")
            _w_rec  = st.slider("Recency Penalty", 0.0, 1.0, float(prefs.get("recency_weight", 0.2)),                     0.05, key="pro_w_rec")
            _total  = _w_time + _w_mood + _w_pref + _w_qual
            _total_color = "#34d399" if 0.95 <= _total <= 1.05 else "#fbbf24"
            st.markdown(
                f"<div style='font-size:0.58rem;color:{_total_color};margin-top:4px'>"
                f"Total weight: {_total:.2f} &nbsp;·&nbsp; ideally 1.0</div>",
                unsafe_allow_html=True,
            )
            _wc1, _wc2 = st.columns(2)
            with _wc1:
                if st.button("Save", use_container_width=True, key="save_pro_weights"):
                    try:
                        _map_upd = {k: v for k, v in _time_map_w.items() if not k.startswith("__")}
                        _map_upd["__weights"] = {"time": _w_time, "mood": _w_mood,
                                                  "preference": _w_pref, "quality": _w_qual, "recency": _w_rec}
                        update_preferences(user_id, time_mood_map=_map_upd, recency_weight=_w_rec)
                        cached_get_preferences.clear()
                        st.toast("Scoring weights saved")
                    except Exception as e:
                        st.toast(f"Failed: {e}", icon="\U0001F6A8")
            with _wc2:
                if st.button("Reset", use_container_width=True, key="reset_pro_weights"):
                    try:
                        _map_rst = {k: v for k, v in _time_map_w.items() if not k.startswith("__")}
                        update_preferences(user_id, time_mood_map=_map_rst, recency_weight=0.2)
                        cached_get_preferences.clear()
                        st.toast("Weights reset to defaults")
                    except Exception as e:
                        st.toast(f"Failed: {e}", icon="\U0001F6A8")

    st.divider()

    # ── Manual Override toggle ────────────────────────────────────────
    override_on = st.toggle(
        "Manual Override",
        value=bool(prefs.get("override_active", 0)),
        help="When ON, the AI is bypassed entirely. Use Prev/Next to navigate.",
    )
    if override_on != bool(prefs.get("override_active", 0)):
        try:
            if override_on:
                if not all_imgs:
                    st.warning("No images in library. Upload one first to use Manual Override.")
                    return
                update_preferences(user_id, override_active=1, override_image_id=all_imgs[0]["id"])
                st.toast("Manual Override ON — AI bypassed")
            else:
                update_preferences(user_id, override_active=0, override_image_id=None)
                st.toast("Manual Override OFF — AI resumed")
            st.session_state["_force_refresh"] = True
            st.rerun()
        except Exception as e:
            st.toast(f"Failed to toggle override: {e}", icon="🚨")

    if st.button("\u27F3  Refresh Now", use_container_width=True):
        _invalidate_caches()
        st.rerun()

    st.divider()


def _render_image_library(user_id: str, profile_type: str, all_imgs: list) -> None:
    """Upload, Add by URL, Image Library (paginated), Gallery View, Scheduling."""

    # ── Upload Image ──────────────────────────────────────────────────
    with st.expander("\u2912  Upload Image", expanded=False):
        uploaded_files = st.file_uploader(
            "Choose images (up to 10 MB each)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files and st.button("Save & Analyse All", use_container_width=True):
            total        = len(uploaded_files)
            progress_bar = st.progress(0, text=f"0 / {total} processed")
            status_box   = st.empty()
            results_log  = []
            done         = 0
            with ThreadPoolExecutor(max_workers=min(total, 5)) as pool:
                futures = {pool.submit(_process_upload_file, f, user_id, profile_type): f.name
                           for f in uploaded_files}
                for future in as_completed(futures):
                    name, line = future.result()
                    results_log.append(line)
                    done += 1
                    progress_bar.progress(done / total, text=f"{done} / {total} processed")
                    status_box.caption(f"Completed: {name}")
            status_box.empty()
            _invalidate_caches()
            ok  = sum(1 for ln in results_log if ln.startswith("✓"))
            blk = sum(1 for ln in results_log if ln.startswith("🚫"))
            st.toast(f"Done — {ok} added, {blk} blocked, {total - ok - blk} failed")
            with st.expander("Upload report", expanded=True):
                for line in results_log:
                    st.caption(line)

    # ── Add by URL ────────────────────────────────────────────────────
    with st.expander("\u2750  Add by URL", expanded=False):
        st.caption("Paste one URL per line")
        url_area = st.text_area(
            "Image URLs",
            placeholder="https://example.com/image1.jpg\nhttps://example.com/image2.png",
            height=100, label_visibility="collapsed", key="url_area",
        )
        if url_area.strip() and st.button("Add & Analyse URLs", use_container_width=True):
            raw_urls = [u.strip() for u in url_area.splitlines() if u.strip()]
            total    = len(raw_urls)
            prog_bar   = st.progress(0, text=f"0 / {total} processed")
            url_status = st.empty()
            url_log    = []
            done       = 0
            with ThreadPoolExecutor(max_workers=min(total, 5)) as pool:
                futures = {pool.submit(_process_upload_url, url, user_id, profile_type): url
                           for url in raw_urls}
                for future in as_completed(futures):
                    label, line = future.result()
                    url_log.append(line)
                    done += 1
                    prog_bar.progress(done / total, text=f"{done} / {total} processed")
                    url_status.caption(f"Completed: {label}")
            url_status.empty()
            _invalidate_caches()
            ok  = sum(1 for ln in url_log if ln.startswith("✓"))
            blk = sum(1 for ln in url_log if ln.startswith("🚫"))
            st.toast(f"Done — {ok} added, {blk} blocked, {total - ok - blk} failed")
            with st.expander("URL import report", expanded=True):
                for line in url_log:
                    st.caption(line)

    st.divider()

    # ── Image Library ─────────────────────────────────────────────────
    with st.expander("\u25A6  Image Library", expanded=False):
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

        has_filter = lib_search or mood_filter != "All" or time_filter != "All"
        images = search_images(
            text=lib_search,
            mood=mood_filter if mood_filter != "All" else "",
            time_period=time_filter if time_filter != "All" else "",
            user_id=user_id,
        ) if has_filter else all_imgs

        total_images = len(images)
        st.caption(f"{total_images} image{'s' if total_images != 1 else ''}")

        if not images:
            st.caption("No images match — upload one above.")
        else:
            PAGE_SIZE = 20
            if "lib_page" not in st.session_state:
                st.session_state.lib_page = 0
            filter_key = (lib_search, mood_filter, time_filter)
            if st.session_state.get("_lib_last_filter") != filter_key:
                st.session_state.lib_page = 0
                st.session_state["_lib_last_filter"] = filter_key

            page_start  = st.session_state.lib_page * PAGE_SIZE
            page_end    = page_start + PAGE_SIZE
            page_imgs   = images[page_start:page_end]
            total_pages = max(1, -(-total_images // PAGE_SIZE))

            if total_images > PAGE_SIZE:
                pg_col1, pg_col2, pg_col3 = st.columns([1, 2, 1])
                with pg_col1:
                    if st.button("◀", key="lib_prev_pg", disabled=st.session_state.lib_page == 0):
                        st.session_state.lib_page -= 1
                with pg_col2:
                    st.caption(f"Page {st.session_state.lib_page + 1} / {total_pages}")
                with pg_col3:
                    if st.button("▶", key="lib_next_pg", disabled=page_end >= total_images):
                        st.session_state.lib_page += 1

            if "selected_ids" not in st.session_state:
                st.session_state.selected_ids = set()

            sa_col, da_col = st.columns(2)
            with sa_col:
                if st.button("Select All", key="sel_all", use_container_width=True):
                    st.session_state.selected_ids = {img["id"] for img in images}
            with da_col:
                if st.button("Deselect All", key="desel_all", use_container_width=True):
                    st.session_state.selected_ids = set()

            for img in page_imgs:
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
                    err  = img.get("analysis_error", "")
                    if not analyzed:
                        err_icon = f' {bi("x-circle", "0.65em", "#f87171")}' if err else ""
                        st.markdown(
                            f"<p style='font-size:0.72rem;margin:0 0 4px;font-weight:300;opacity:0.6'>"
                            f"{bi('hourglass-split','0.7em','rgba(255,255,255,0.3)')} "
                            f"{img.get('title') or 'Untitled'}{err_icon}</p>"
                            f"<div class='skeleton-line' style='height:7px;width:70%;margin-bottom:3px'></div>"
                            f"<div class='skeleton-line' style='height:7px;width:42%'></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<p style='font-size:0.72rem;margin:0;font-weight:300'>"
                            f"{bi('check-circle','0.7em','#34d399')} {img.get('title') or 'Untitled'}</p>"
                            f"<p style='font-size:0.58rem;color:rgba(255,255,255,0.3);margin:0'>{mood}</p>",
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
                                        st.toast(f"Analysed: {r.primary_mood} · {r.optimal_time}")
                                    else:
                                        st.toast(f"Analysis failed: {r.error_message[:60]}", icon="🚨")
                                    _invalidate_caches()
                    with btn_cols[1]:
                        if st.button("\u2715", key=f"del_{img['id']}", help="Remove"):
                            try:
                                deactivate_image(img["id"])
                                st.session_state.selected_ids.discard(img["id"])
                                st.toast(f"Removed: {img.get('title') or 'Image'}")
                                _invalidate_caches()
                            except Exception as e:
                                st.toast(f"Failed to remove image: {e}", icon="🚨")

            failed_imgs = [i for i in images if not i.get("is_analyzed") or i.get("analysis_error")]
            if failed_imgs:
                st.caption(f"{len(failed_imgs)} image{'s' if len(failed_imgs) != 1 else ''} need analysis")
                if st.button("Re-analyse Failed", key="reanalyse_failed", use_container_width=True):
                    fail_prog = st.progress(0, text=f"0 / {len(failed_imgs)} re-analysed")
                    for fi, fimg in enumerate(failed_imgs):
                        src = fimg.get("image_url") or ""
                        if src:
                            _run_analysis(fimg["id"], src)
                        fail_prog.progress((fi + 1) / len(failed_imgs),
                                           text=f"{fi + 1} / {len(failed_imgs)} re-analysed")
                    _invalidate_caches()
                    st.toast(f"Re-analysed {len(failed_imgs)} image{'s' if len(failed_imgs) != 1 else ''}")

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
                        with c2:
                            if st.button("Cancel", key="cancel_del"):
                                st.session_state.confirm_bulk_delete = False
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

    # ── Gallery View ──────────────────────────────────────────────────
    with st.expander("\u29C9  Gallery View", expanded=False):
        gallery_imgs = all_imgs
        if profile_type == "Kids":
            _kids_blocked = {"melancholic", "mysterious"}
            gallery_imgs = [i for i in gallery_imgs if i.get("primary_mood") not in _kids_blocked]
        if not gallery_imgs:
            st.caption("No images yet.")
        else:
            MOOD_COLORS = {
                "calm": "#60a5fa", "energetic": "#fbbf24", "joyful": "#34d399",
                "melancholic": "#c084fc", "mysterious": "#818cf8", "neutral": "#94a3b8",
            }
            GAL_PAGE_SIZE = 15
            if "gal_page" not in st.session_state:
                st.session_state.gal_page = 0
            gal_total = len(gallery_imgs)
            gal_total_pages = max(1, -(-gal_total // GAL_PAGE_SIZE))
            # Clamp page in case images were deleted
            st.session_state.gal_page = min(st.session_state.gal_page, gal_total_pages - 1)
            gal_start = st.session_state.gal_page * GAL_PAGE_SIZE
            gal_end   = gal_start + GAL_PAGE_SIZE
            page_imgs = gallery_imgs[gal_start:gal_end]

            if gal_total > GAL_PAGE_SIZE:
                pg1, pg2, pg3 = st.columns([1, 2, 1])
                with pg1:
                    if st.button("◀", key="gal_prev_pg", disabled=st.session_state.gal_page == 0):
                        st.session_state.gal_page -= 1
                        st.rerun()
                with pg2:
                    st.caption(f"Page {st.session_state.gal_page + 1} / {gal_total_pages}  ({gal_total} images)")
                with pg3:
                    if st.button("▶", key="gal_next_pg", disabled=gal_end >= gal_total):
                        st.session_state.gal_page += 1
                        st.rerun()

            cols = st.columns(3)
            for i, gimg in enumerate(page_imgs):
                with cols[i % 3]:
                    url = gimg.get("image_url", "")
                    if url:
                        thumb_url = get_gallery_thumbnail_url(url, width=200)
                        st.image(thumb_url, width=90)
                    mood  = gimg.get("primary_mood", "neutral")
                    color = MOOD_COLORS.get(mood, "#94a3b8")
                    s_icon = (bi("check-circle-fill", "0.6em", color)
                              if gimg.get("is_analyzed")
                              else bi("hourglass-split", "0.6em", "rgba(255,255,255,0.3)"))
                    st.markdown(
                        f"<p style='font-size:0.55rem;margin:0;text-align:center'>"
                        f"<span style='color:{color}'>{s_icon} {mood}</span></p>",
                        unsafe_allow_html=True,
                    )
                    if st.button("Display", key=f"gal_{gimg['id']}", use_container_width=True):
                        update_preferences(user_id, override_active=1, override_image_id=gimg["id"])
                        st.toast(f"Displaying: {gimg.get('title', 'Image')}")
                        st.session_state["_force_refresh"] = True
                        st.rerun()

    st.divider()

    # ── Image Scheduling ──────────────────────────────────────────────
    with st.expander("\u29D6  Image Scheduling", expanded=False):
        if not all_imgs:
            st.caption("No images to schedule.")
        else:
            sched_target = st.selectbox(
                "Select image", options=all_imgs,
                format_func=lambda x: x.get("title") or "Untitled",
                key="sched_image_select", label_visibility="collapsed",
            )
            if sched_target:
                sid            = sched_target["id"]
                current_window = sched_target.get("time_window") or "any"
                s_start        = st.date_input("Start date", value=None, key=f"sched_s_{sid}")
                s_end          = st.date_input("End date",   value=None, key=f"sched_e_{sid}")
                all_periods    = ["dawn", "morning", "afternoon", "evening", "night"]
                current_periods = all_periods if current_window == "any" else [
                    p.strip() for p in current_window.split(",") if p.strip() in all_periods
                ]
                s_window = st.multiselect("Show during", all_periods,
                                          default=current_periods, key=f"sched_w_{sid}")
                if st.button("Save Schedule", key=f"sched_save_{sid}", use_container_width=True):
                    try:
                        window_str = ("any" if set(s_window) == set(all_periods) or not s_window
                                      else ",".join(s_window))
                        update_image_schedule(sid,
                                              str(s_start) if s_start else "",
                                              str(s_end)   if s_end   else "",
                                              window_str)
                        _invalidate_caches()
                        st.toast(f"Schedule saved for {sched_target.get('title') or 'image'}")
                    except Exception as e:
                        st.toast(f"Failed to save schedule: {e}", icon="🚨")

    st.divider()


def _render_analytics(user_id: str, profile_type: str, prefs: dict) -> None:
    """Analytics, AI Analysis Settings, Evaluation Mode, Recent History + CSV export."""

    # ── Analytics Dashboard ───────────────────────────────────────────
    with st.expander("\u2261  Analytics", expanded=False):
        _pro_views = ["Display Stats", "Score Trend"] if profile_type == "Professional" else []
        analytics_view = st.selectbox(
            "View", ["Interactions", "Mood Trends", "Usage Patterns"] + _pro_views,
            key="analytics_view", label_visibility="collapsed",
        )
        if analytics_view == "Interactions":
            data = cached_analytics_summary(user_id=user_id)
            if data:
                df = pd.DataFrame(data)
                if not df.empty and "likes" in df.columns:
                    chart_df = df.set_index("title")[["likes", "skips"]].head(10)
                    # Drop columns that are all-zero — Vega-Lite produces
                    # [Infinity, -Infinity] extent warnings for zero-only columns.
                    chart_df = chart_df.loc[:, chart_df.max() > 0]
                    if not chart_df.empty:
                        st.bar_chart(chart_df)
                    st.markdown("<p style='font-size:0.6rem;color:rgba(255,255,255,0.4);"
                                "margin:8px 0 2px'>Most Liked</p>", unsafe_allow_html=True)
                    for _, row in df.nlargest(3, "likes").iterrows():
                        st.markdown(f"<p style='font-size:0.65rem;margin:2px 0;font-weight:300'>"
                                    f"{bi('heart-fill','0.65em','#f472b6')} {row['likes']} — {row['title']}</p>",
                                    unsafe_allow_html=True)
                    st.markdown("<p style='font-size:0.6rem;color:rgba(255,255,255,0.4);"
                                "margin:8px 0 2px'>Most Skipped</p>", unsafe_allow_html=True)
                    for _, row in df.nlargest(3, "skips").iterrows():
                        st.markdown(f"<p style='font-size:0.65rem;margin:2px 0;font-weight:300'>"
                                    f"{bi('skip-forward-fill','0.65em','#94a3b8')} {row['skips']} — {row['title']}</p>",
                                    unsafe_allow_html=True)
            else:
                st.caption("No interaction data yet.")

        elif analytics_view == "Mood Trends":
            _days_opts = {"7 days": 7, "30 days": 30, "60 days": 60, "90 days": 90}
            _days_key  = (st.selectbox("Window", list(_days_opts.keys()), index=1,
                                       key="mood_trend_window", label_visibility="collapsed")
                          if profile_type == "Professional" else "30 days")
            data = cached_mood_over_time(_days_opts.get(_days_key, 30), user_id=user_id)
            if data:
                df = pd.DataFrame(data)
                if not df.empty and df["count"].sum() > 0:
                    pivot = df.pivot_table(index="date", columns="mood", values="count",
                                           fill_value=0, aggfunc="sum")
                    # Drop mood columns that are all-zero to prevent Vega-Lite
                    # infinite-extent warnings in the area chart scale binder.
                    pivot = pivot.loc[:, pivot.max() > 0]
                    if not pivot.empty:
                        st.area_chart(pivot)
                    else:
                        st.caption("No mood history yet.")
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

        elif analytics_view == "Display Stats":
            data = cached_top_images_by_display(user_id=user_id, limit=10)
            if data:
                df = pd.DataFrame(data)
                MOOD_COLORS = {
                    "calm": "#60a5fa", "energetic": "#fbbf24", "joyful": "#34d399",
                    "melancholic": "#c084fc", "mysterious": "#818cf8", "neutral": "#94a3b8",
                }
                if not df.empty and df["display_count"].sum() > 0:
                    st.bar_chart(df.set_index("title")["display_count"])
                for _, row in df.iterrows():
                    mood_c = MOOD_COLORS.get(row["primary_mood"], "#94a3b8")
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:center;margin:3px 0'>"
                        f"<span style='font-size:0.65rem;font-weight:300'>{row['title']}</span>"
                        f"<span style='font-size:0.60rem;color:{mood_c}'>"
                        f"{row['display_count']} &nbsp;{bi('display','0.65em',mood_c)}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No display data yet.")

        elif analytics_view == "Score Trend":
            _st_opts = {"7 days": 7, "30 days": 30, "60 days": 60, "90 days": 90}
            _st_key  = st.selectbox("Window", list(_st_opts.keys()), index=1,
                                    key="score_trend_window", label_visibility="collapsed")
            data = cached_score_trend(_st_opts.get(_st_key, 30), user_id=user_id)
            if data:
                df = pd.DataFrame(data)
                if not df.empty and df["avg_score"].sum() > 0:
                    st.line_chart(df.set_index("date")["avg_score"])
                    st.markdown(
                        f"<div style='font-size:0.60rem;color:rgba(255,255,255,0.4);margin-top:4px'>"
                        f"Avg confidence: {df['avg_score'].mean():.1%} &nbsp;·&nbsp; "
                        f"{df['decisions'].sum()} decisions</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("No score data yet.")
            else:
                st.caption("No score data yet.")

    # ── Display Settings ──────────────────────────────────────────────
    with st.expander("\u25D3  Display Settings", expanded=False):
        config = cached_get_display_config()
        
        # 1. Refresh Interval
        current_poll = int(config.get("poll_interval_seconds") or 300)
        # Map seconds to user-friendly options
        poll_opts = {
            "30s": 30, "1m": 60, "2m": 120, "5m": 300, 
            "10m": 600, "15m": 900, "30m": 1800, "1h": 3600
        }
        # Find index of current value or default to 5m
        curr_idx = list(poll_opts.values()).index(current_poll) if current_poll in poll_opts.values() else 3
        
        def _on_poll_change():
            val = poll_opts[st.session_state.new_poll_key]
            update_display_config(poll_interval_seconds=val)
            cached_get_display_config.clear()
            st.toast(f"Interval updated to {st.session_state.new_poll_key}")

        def _on_hide_change():
            val = st.session_state.new_hide_val
            update_display_config(overlay_auto_hide_seconds=val)
            cached_get_display_config.clear()
            st.toast(f"Auto-hide set to {val}s")

        new_poll_key = st.selectbox(
            "Auto-Refresh Interval", 
            options=list(poll_opts.keys()),
            index=curr_idx,
            key="new_poll_key",
            on_change=_on_poll_change,
            help="How long each image stays on screen before Chronos re-evaluates the context."
        )
        
        # 2. Overlay Auto-Hide
        current_hide = int(config.get("overlay_auto_hide_seconds") or 8)
        new_hide = st.slider(
            "Overlay Auto-Hide (s)", 0, 30, current_hide, 
            key="new_hide_val",
            on_change=_on_hide_change,
            help="Seconds before the reasoning card fades out. Set to 0 to keep visible."
        )
        
        st.caption("Changes are saved automatically.")

    # ── AI Analysis Settings ──────────────────────────────────────────
    with st.expander("\u2699  AI Analysis Settings", expanded=False):
        config = cached_get_display_config()
        def _on_ai_change():
            update_display_config(
                analysis_depth=st.session_state.ai_depth_radio.lower(),
                analysis_focus=",".join(st.session_state.ai_focus_ms),
                custom_prompt=st.session_state.ai_prompt_ta
            )
            cached_get_display_config.clear()
            st.toast("AI analysis updated")

        depth_val = config.get("analysis_depth", "standard").capitalize()
        depth = st.radio(
            "Analysis Depth", ["Quick", "Standard"],
            index=0 if depth_val == "Quick" else 1,
            key="ai_depth_radio",
            on_change=_on_ai_change,
            horizontal=True,
        )
        focus_options  = ["composition", "color_palette", "emotional_depth",
                          "lighting", "texture", "symbolism"]
        current_focus  = [f for f in config.get("analysis_focus", "").split(",") if f in focus_options]
        focus  = st.multiselect(
            "Focus Areas", focus_options, 
            default=current_focus, 
            key="ai_focus_ms",
            on_change=_on_ai_change
        )
        custom = st.text_area(
            "Custom Instructions", value=config.get("custom_prompt", ""),
            placeholder="e.g. Pay attention to architectural elements",
            key="ai_prompt_ta", height=68,
            on_change=_on_ai_change
        )
        st.caption("AI settings are saved automatically.")

    st.divider()

    # ── Evaluation Mode ───────────────────────────────────────────────
    with st.expander("⚗  Evaluation Mode", expanded=False):
        st.caption("For academic comparison only. Switches AI scoring off — images cycle by round-robin regardless of context.")
        if "baseline_toggle" not in st.session_state:
            st.session_state["baseline_toggle"] = bool(prefs.get("baseline_mode", 0))
        new_baseline = st.toggle("Static Baseline (no AI)", key="baseline_toggle")
        baseline_on  = bool(prefs.get("baseline_mode", 0))
        if new_baseline != baseline_on:
            update_preferences(user_id, baseline_mode=1 if new_baseline else 0)
            st.toast("Static baseline ON — round-robin active" if new_baseline else "Adaptive AI restored")
            cached_get_preferences.clear()

    st.divider()

    # ── Recent History ────────────────────────────────────────────────
    with st.expander("\u2630  Recent History", expanded=False):
        logs = get_recent_logs(limit=8, user_id=user_id)
        if not logs:
            st.caption("No decisions recorded yet.")
        for log in logs:
            score = int((log.get("selection_score") or 0) * 100)
            title = log.get("image_title") or "Unknown"
            ts    = str(log.get("timestamp") or "")[:16]
            override_badge = (f" {bi('arrow-repeat','0.6em','rgba(255,255,255,0.5)')}"
                              if log.get("was_override") else "")
            st.markdown(
                f"<div style='margin-bottom:8px'>"
                f"<p style='font-size:0.68rem;margin:0;font-weight:300'>{title}{override_badge}</p>"
                f"<p style='font-size:0.58rem;color:rgba(255,255,255,0.3);margin:0'>"
                f"{ts} · {score}%</p></div>",
                unsafe_allow_html=True,
            )

        all_logs = get_recent_logs(limit=500, user_id=user_id)
        if all_logs:
            buf    = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["timestamp", "selection_mode", "image", "image_mood",
                              "time_period", "detected_mood", "score",
                              "t_time", "t_mood", "t_pref",
                              "t_quality", "t_recency", "t_interaction", "override"])
            for lg in all_logs:
                bd = lg.get("score_breakdown") or {}
                writer.writerow([
                    str(lg.get("timestamp") or "")[:19],
                    bd.get("mode", "adaptive"),
                    lg.get("image_title") or "Unknown",
                    lg.get("image_mood") or "",
                    lg.get("time_period") or "",
                    lg.get("detected_mood") or "",
                    f"{lg.get('selection_score', 0):.3f}",
                    f"{bd.get('time', 0):.3f}",       f"{bd.get('mood', 0):.3f}",
                    f"{bd.get('preference', 0):.3f}", f"{bd.get('quality', 0):.3f}",
                    f"{bd.get('recency', 0):.3f}",    f"{bd.get('interaction', 0):.3f}",
                    "yes" if lg.get("was_override") else "no",
                ])
            csv_data = buf.getvalue()
            buf.close()
            st.download_button(
                "\u2913 Export All Logs (CSV)",
                data=csv_data,
                file_name="chronos_context_logs.csv",
                mime="text/csv",
                use_container_width=True,
            )


def render_sidebar(context: dict, result, user_id: str = "", profile_type: str = "Standard") -> None:
    """
    Renders the Control Dashboard in the Streamlit sidebar.
    Called inside a `with st.sidebar:` block from main().

    all_imgs is fetched exactly once here and forwarded to every sub-function
    that needs it, eliminating redundant cache lookups across the branches.
    """
    prefs    = cached_get_preferences(user_id=user_id)
    all_imgs = cached_get_all_images(user_id=user_id)

    _render_user_header(context, profile_type)
    _render_playback_controls(result, prefs, user_id, profile_type, all_imgs)
    _render_image_library(user_id, profile_type, all_imgs)
    _render_analytics(user_id, profile_type, prefs)


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
    # Center the logo and text
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.image("logos/chronos_logo_trans2.png", use_container_width=True)
        st.markdown(f"""
        <div style="text-align: center; animation: fadeInUp 1s ease forwards;">
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

    # ── 1. Context ─────────────────────────────────────────────────────────
    context = get_current_context()
    _config = cached_get_display_config()

    # ── 2. Manager — handles context and decision engine coordination.
    _now = time.time()
    _last_sel_time = st.session_state.get("_last_sel_time", 0)
    _poll_interval = int(_config.get("poll_interval_seconds") or 300)
    
    _should_refresh = st.session_state.pop("_force_refresh", False)
    
    # If the poll interval has passed since the last selection, trigger a fresh one.
    # This ensures that browser meta-refreshes actually change the image.
    if (_now - _last_sel_time) >= _poll_interval:
        _should_refresh = True

    if _should_refresh or "_sel_result" not in st.session_state:
        result = ChronosManager.get_next_display_state(user_id=user_id, profile_type=profile_type)
        st.session_state["_sel_result"] = result
        st.session_state["_last_sel_time"] = _now
        # Show Kids safety filter notes as toasts on every fresh selection
        if result and result.filter_notes:
            for note in result.filter_notes:
                st.toast(note, icon="🔒")
    else:
        result = st.session_state["_sel_result"]

    # ── 3. Determine background ────────────────────────────────────────────
    if result and result.image:
        css_url = get_image_css_url(result.image)
    else:
        css_url = PLACEHOLDER_CSS_URL

    # ── 4. Smart animation — only fade-in when the displayed image changes.
    #    Sidebar interactions (toggle, button clicks) rerun the script but
    #    should NOT re-fire the 0.5s fade animation — that causes flicker.
    _last_url = st.session_state.get("_last_image_url", "")
    _animate  = css_url != _last_url
    if _animate:
        st.session_state["_last_image_url"] = css_url

    # ── 5. Inject CSS (static cached chunk + data-carrier div for crossfade) ─
    try:
        inject_global_css(
            css_url, 
            context.get("time_period", "day"), 
            profile_type=profile_type, 
            animate=_animate,
            poll_interval=_poll_interval
        )
    except Exception as _e:
        pass  # CSS injection failure is cosmetic — continue rendering

    # ── Persistent JS engines (iframes survive reruns; guard against re-init)
    try:
        inject_sidebar_fab()
    except Exception as _e:
        pass  # FAB unavailable — sidebar toggle still works via native button

    try:
        inject_crossfade_engine()
    except Exception as _e:
        pass  # Crossfade unavailable — background updates without transition

    # Auto-hide timeout from display config (default 8 s; 0 = disabled)
    _autohide_secs = int(_config.get("overlay_auto_hide_seconds") or 8)
    if _autohide_secs > 0:
        try:
            inject_autohide_ui(timeout_ms=_autohide_secs * 1000)
        except Exception as _e:
            pass  # Auto-hide unavailable — overlay remains visible

    # ── 6. Fixed UI elements (rendered as HTML, position:fixed) ───────────
    try:
        render_status_bar(context)
    except Exception as _e:
        pass  # Status bar is decorative — do not crash on failure

    try:
        render_reasoning_overlay(result, is_new=_animate, profile_type=profile_type)
    except Exception as _e:
        pass  # Reasoning overlay is non-critical


    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        try:
            render_sidebar(context, result, user_id=user_id, profile_type=profile_type)
        except RuntimeError as _db_err:
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
