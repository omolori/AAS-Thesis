"""Shared styles, colors, and Plotly layout defaults for the dashboard."""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st

# --- Color palette (user-defined) ---
TEAL      = "#0097b2"   # primary brand
YELLOW    = "#ffde59"   # highlight / warning
LIGHT_BLUE = "#9ed1fe"  # secondary
GREY      = "#ccd7e2"   # text / neutral
PURPLE    = "#cb6ce6"   # accent
ORANGE    = "#ff914d"   # Run B / candidate
GREEN     = "#86e85c"   # success

COLOR_A   = TEAL        # Run A baseline
COLOR_B   = ORANGE      # Run B candidate

BG        = "#0E1117"
CARD_BG   = "#161C27"
BORDER    = "#232B3B"

JOINT_COLORS = [TEAL, YELLOW, LIGHT_BLUE, PURPLE, ORANGE, GREEN]

PIPELINE_COLORS = {
    "sim_no_aas": TEAL,
    "sim_aas":    LIGHT_BLUE,
    "real":       ORANGE,
}

# --- Plotly base layout ---
PLOT_LAYOUT = dict(
    paper_bgcolor=CARD_BG,
    plot_bgcolor=BG,
    font=dict(color=GREY, family="Inter, Arial, sans-serif", size=13),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER),
    legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)", y=-0.22),
    margin=dict(l=60, r=20, t=36, b=70),
)


def apply_plot_style(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, **PLOT_LAYOUT)
    return fig


CSS = """
<style>
/* Metric cards */
div[data-testid="metric-container"] {
    background: #161C27;
    border: 1px solid #232B3B;
    border-radius: 8px;
    padding: 14px 18px;
}
div[data-testid="metric-container"] label {
    color: #7a8fa6 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    font-weight: 600;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    color: #ccd7e2 !important;
}

/* Headings */
h1 { color: #ccd7e2 !important; font-weight: 800 !important; letter-spacing: -0.01em; }
h2 { color: #0097b2 !important; font-weight: 700 !important; letter-spacing: 0.01em; border-bottom: 1px solid #232B3B; padding-bottom: 6px; }
h3 { color: #9ed1fe !important; font-weight: 600 !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0B1018 !important;
    border-right: 1px solid #232B3B;
}
[data-testid="stSidebar"] * { color: #ccd7e2 !important; }

/* Tables */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* Divider */
hr { border-color: #232B3B !important; margin: 1.5rem 0 !important; }

/* Primary button */
[data-testid="baseButton-primary"] {
    background: #0097b2 !important;
    color: #0E1117 !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    letter-spacing: 0.04em;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #232B3B !important;
    border-radius: 8px !important;
    background: #161C27 !important;
}

/* Selectbox */
[data-baseweb="select"] > div {
    background: #161C27 !important;
    border-color: #232B3B !important;
    border-radius: 6px !important;
}

/* Info / success / warning boxes */
[data-testid="stAlert"] { border-radius: 8px !important; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def pipeline_badge(pipeline: str) -> str:
    color = PIPELINE_COLORS.get(pipeline, GREY)
    return (
        f'<span style="background:{color};color:#0E1117;padding:2px 10px;'
        f'border-radius:4px;font-size:0.78rem;font-weight:700;'
        f'letter-spacing:0.05em">{pipeline}</span>'
    )


def section_header(title: str, subtitle: str = "") -> None:
    sub = f'<div style="color:#7a8fa6;font-size:0.85rem;margin-top:2px">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="margin:1.5rem 0 0.8rem">'
        f'<div style="font-size:1.05rem;font-weight:700;color:#9ed1fe;letter-spacing:0.03em">{title}</div>'
        f'{sub}</div>',
        unsafe_allow_html=True,
    )
