"""
Chronos — Static Slideshow Baseline
=====================================

Non-adaptive version for evaluation comparison.
Cycles through all active images in upload order with no AI scoring.

Used as the CONTROL CONDITION in scenario-based testing — shows what
the system looks like WITHOUT context-aware selection.

Run alongside the adaptive app:
    streamlit run app.py            --server.port 8501  (adaptive)
    streamlit run app_baseline.py   --server.port 8502  (baseline)
"""

import base64
import random
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(
    page_title="Chronos Baseline",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="auto",
)

from database.schema  import init_database
from database.queries import get_all_images, deactivate_image
from logic.context    import get_current_context, TIME_PERIOD_ICONS

init_database()

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"

PLACEHOLDER_CSS_URL = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='1' height='1'%3E%3Crect fill='%23090909'/%3E%3C/svg%3E"
)


# =============================================================================
# Helpers (mirrors app.py)
# =============================================================================

def get_image_css_url(image: dict) -> str:
    path = image.get("image_path", "")
    url  = image.get("image_url", "")
    if path and Path(path).exists():
        suffix   = Path(path).suffix.lower()
        mime_map = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}
        mime     = mime_map.get(suffix, "jpeg")
        b64      = base64.b64encode(Path(path).read_bytes()).decode()
        return f"data:image/{mime};base64,{b64}"
    return url or ""


def inject_css(image_css_url: str) -> None:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500&display=swap');

    #MainMenu, header, footer {{ visibility: hidden !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}

    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
        margin: 0; padding: 0;
        background-color: #090909;
        font-family: 'Inter', system-ui, sans-serif;
        color: #f0f0f0;
    }}

    .stApp {{ background: transparent !important; min-height: 100vh; }}

    #baseline-bg {{
        position: fixed; inset: 0;
        background-image:    url('{image_css_url}');
        background-size:     cover;
        background-position: center center;
        background-repeat:   no-repeat;
        filter:              brightness(0.80) saturate(1.0);
        z-index:             -1;
    }}

    .stApp::before {{
        content: "";
        position: fixed; inset: 0;
        background: radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.68) 100%);
        pointer-events: none; z-index: 0;
    }}
    .stApp::after {{
        content: "";
        position: fixed; bottom: 0; left: 0; right: 0; height: 40%;
        background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, transparent 100%);
        pointer-events: none; z-index: 0;
    }}
    .main .block-container {{
        padding: 0 !important; max-width: 100% !important;
        position: relative; z-index: 1;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: rgba(7,7,12,0.88) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        border-right: 1px solid rgba(255,255,255,0.07) !important;
        z-index: 999 !important;
    }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {{
        color: rgba(255,255,255,0.82) !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background:     rgba(255,255,255,0.07) !important;
        border:         1px solid rgba(255,255,255,0.15) !important;
        color:          rgba(255,255,255,0.82) !important;
        border-radius:  8px !important;
        font-size:      0.62rem !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        font-weight:    600 !important;
        transition:     background 0.2s ease !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(255,255,255,0.14) !important;
    }}

    /* Native toggle buttons hidden — JS FAB injected in main() replaces them */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        opacity: 0 !important;
        pointer-events: none !important;
    }}

    /* Baseline badge */
    .baseline-badge {{
        position: fixed;
        bottom: calc(28px + env(safe-area-inset-bottom, 0px));
        left: 50%;
        transform: translateX(-50%);
        padding: 6px 16px; border-radius: 999px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        backdrop-filter: blur(12px);
        font-size: 0.58rem; font-weight: 600;
        letter-spacing: 0.18em; text-transform: uppercase;
        color: rgba(255,255,255,0.45);
        z-index: 50;
    }}

    /* ═══════════════════ RESPONSIVE LAYER ════════════════════════ */
    html {{ overflow-x: hidden; }}
    .stApp {{ min-height: 100dvh; }}
    button, [role="button"], summary {{ touch-action: manipulation; }}
    [data-testid="stSidebar"] > div:first-child {{ -webkit-overflow-scrolling: touch; }}

    @media (max-width: 640px) {{
        .baseline-badge {{
            font-size: 0.50rem;
            padding: 5px 12px;
            bottom: calc(16px + env(safe-area-inset-bottom, 0px));
        }}
        [data-testid="stSidebar"] > div:first-child {{
            padding-left: 12px !important;
            padding-right: 12px !important;
        }}
        #chronos-fab {{
            top:   calc(12px + env(safe-area-inset-top,   0px)) !important;
            right: calc(12px + env(safe-area-inset-right, 0px)) !important;
            width: 36px !important; height: 36px !important;
        }}
    }}
    </style>
    <div id="baseline-bg"></div>
    """, unsafe_allow_html=True)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    context = get_current_context()
    images  = get_all_images(active_only=True)

    # ── Background ────────────────────────────────────────────────────────
    if "baseline_idx" not in st.session_state:
        st.session_state.baseline_idx = 0

    css_url = PLACEHOLDER_CSS_URL
    current = None

    if images:
        idx     = st.session_state.baseline_idx % len(images)
        current = images[idx]
        css_url = get_image_css_url(current) or PLACEHOLDER_CSS_URL

    inject_css(css_url)

    # ── Baseline badge ────────────────────────────────────────────────────
    st.markdown(
        '<div class="baseline-badge">Baseline — No AI Scoring</div>',
        unsafe_allow_html=True,
    )

    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="padding:24px 0 16px">
          <p style="font-size:0.5rem;letter-spacing:0.24em;text-transform:uppercase;
                    color:rgba(255,255,255,0.22);margin:0 0 8px;font-weight:700">
            Chronos — Baseline
          </p>
          <p style="font-size:1.4rem;font-weight:200;margin:0;color:#ffffff;
                    letter-spacing:-0.02em">
            Static Slideshow
          </p>
          <p style="font-size:0.52rem;text-transform:uppercase;letter-spacing:0.15em;
                    color:rgba(255,255,255,0.22);margin:6px 0 0;font-weight:600">
            No context-aware selection
          </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        if not images:
            st.caption("No images in the library. Add images via the main Chronos app first.")
            return

        idx = st.session_state.baseline_idx % len(images)

        # Current image info
        if current:
            st.markdown(f"""
            <div style="margin-bottom:14px">
              <p style="font-size:0.55rem;letter-spacing:0.15em;text-transform:uppercase;
                        color:rgba(255,255,255,0.3);margin:0 0 3px">Now Showing</p>
              <p style="font-size:0.85rem;font-weight:300;margin:0;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                {current.get('title') or 'Untitled'}
              </p>
              <p style="font-size:0.58rem;color:rgba(255,255,255,0.25);margin:2px 0 0">
                {idx + 1} of {len(images)}
              </p>
            </div>
            """, unsafe_allow_html=True)

        # Navigation
        prev_col, next_col = st.columns(2)
        with prev_col:
            if st.button("← Prev", use_container_width=True):
                st.session_state.baseline_idx = (idx - 1) % len(images)
                st.rerun()
        with next_col:
            if st.button("Next →", use_container_width=True):
                st.session_state.baseline_idx = (idx + 1) % len(images)
                st.rerun()

        if st.button("↺  Shuffle", use_container_width=True):
            st.session_state.baseline_idx = random.randint(0, len(images) - 1)
            st.rerun()

        st.divider()

        # Image list
        with st.expander("🖼  All Images", expanded=False):
            for i, img in enumerate(images):
                if st.button(
                    f"{'▶ ' if i == idx else ''}{img.get('title') or 'Untitled'}",
                    key=f"jump_{img['id']}",
                    use_container_width=True,
                ):
                    st.session_state.baseline_idx = i
                    st.rerun()

        st.divider()

        # Context info (shown but not used for selection)
        period = context.get("time_period", "")
        icon   = TIME_PERIOD_ICONS.get(period, "🕐")
        st.markdown(f"""
        <p style="font-size:0.52rem;text-transform:uppercase;letter-spacing:0.15em;
                  color:rgba(255,255,255,0.22);margin:0;font-weight:600">
          {icon} {period.capitalize()} — Context ignored
        </p>
        <p style="font-size:0.52rem;color:rgba(255,255,255,0.15);margin:4px 0 0;
                  letter-spacing:0.05em">
          The adaptive app uses this to select the best-matching image.
          This baseline ignores context entirely.
        </p>
        """, unsafe_allow_html=True)

    # ── Spacer ────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='height:100vh;pointer-events:none'></div>",
        unsafe_allow_html=True,
    )

    # ── Persistent sidebar FAB (JS-injected, immune to CSS transform issues)
    import streamlit.components.v1 as _components  # type: ignore[import-untyped]
    _components.html(
        """
        <script>
        (function () {
            var pd = window.parent.document;
            if (pd.getElementById('chronos-fab')) return;
            var fab = pd.createElement('button');
            fab.id = 'chronos-fab';
            fab.title = 'Toggle sidebar';
            fab.innerHTML =
                '<svg width="17" height="13" viewBox="0 0 17 13" fill="none">'
                + '<rect width="17" height="2"   rx="1" fill="rgba(255,255,255,.90)"/>'
                + '<rect y="5.5" width="17" height="2"   rx="1" fill="rgba(255,255,255,.90)"/>'
                + '<rect y="11"  width="17" height="2"   rx="1" fill="rgba(255,255,255,.90)"/>'
                + '</svg>';
            fab.style.cssText =
                'position:fixed;top:16px;right:16px;left:auto;'
                + 'z-index:99999;width:40px;height:40px;'
                + 'background:rgba(9,9,14,.80);'
                + 'border:1px solid rgba(255,255,255,.14);border-radius:11px;'
                + 'cursor:pointer;display:flex;align-items:center;justify-content:center;'
                + '-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);'
                + 'box-shadow:0 4px 20px rgba(0,0,0,.50);'
                + 'transition:background .2s,border-color .2s,transform .18s;'
                + 'user-select:none;';
            function sidebarOpen() {
                var sb = pd.querySelector('[data-testid="stSidebar"]');
                return sb ? sb.getBoundingClientRect().width > 60 : false;
            }
            fab.addEventListener('click', function () {
                if (sidebarOpen()) {
                    var b = pd.querySelector('[data-testid="stSidebarCollapseButton"] button');
                    if (b) b.click();
                } else {
                    var b = pd.querySelector('[data-testid="collapsedControl"] button');
                    if (!b) b = pd.querySelector('[data-testid="stSidebarCollapseButton"] button');
                    if (b) b.click();
                }
            });
            fab.addEventListener('mouseenter', function () {
                this.style.background = 'rgba(255,255,255,.10)';
                this.style.borderColor = 'rgba(255,255,255,.28)';
                this.style.transform = 'scale(1.08)';
            });
            fab.addEventListener('mouseleave', function () {
                this.style.background = 'rgba(9,9,14,.80)';
                this.style.borderColor = 'rgba(255,255,255,.14)';
                this.style.transform = 'scale(1)';
            });
            fab.addEventListener('mousedown', function () { this.style.transform = 'scale(.93)'; });
            fab.addEventListener('mouseup',   function () { this.style.transform = 'scale(1)'; });
            pd.body.appendChild(fab);
        }());
        </script>
        """,
        height=0,
        scrolling=False,
    )


if __name__ == "__main__":
    main()
