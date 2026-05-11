"""Shared sidebar rendered on every page."""
from __future__ import annotations
import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dashboard.styles import pipeline_badge, PIPELINE_COLORS, PIPELINE_LABELS


def render(db_path: Path) -> None:
    from digital_twin_core.recorder import list_runs
    runs = list_runs(db_path)

    with st.sidebar:
        st.markdown(
            '<div style="font-size:1.1rem;font-weight:800;color:#ccd7e2;'
            'letter-spacing:-0.01em;margin-bottom:2px">UR3 Digital Twin</div>'
            '<div style="font-size:0.78rem;color:#7a8fa6;margin-bottom:16px">'
            'AAU Thesis Project</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Live DB stats
        st.markdown(
            '<div style="font-size:0.72rem;font-weight:700;color:#7a8fa6;'
            'letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px">'
            'Database</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        col1.metric("Total", len(runs))
        col2.metric("No AAS", sum(1 for r in runs if r.pipeline == "sim_no_aas"))
        col1, col2 = st.columns(2)
        col1.metric("AAS", sum(1 for r in runs if r.pipeline == "sim_aas"))
        col2.metric("Real", sum(1 for r in runs if r.pipeline == "real"))

        if st.button("Refresh", use_container_width=True):
            st.rerun()

        st.markdown("---")

        # Recent runs
        if runs:
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;color:#7a8fa6;'
                'letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px">'
                'Recent Runs</div>',
                unsafe_allow_html=True,
            )
            for r in reversed(runs[-5:]):
                ts = datetime.datetime.fromtimestamp(r.started_at_unix).strftime("%d/%m/%Y %H:%M")
                color = PIPELINE_COLORS.get(r.pipeline, "#7a8fa6")
                st.markdown(
                    f'<div style="margin-bottom:8px;padding:8px;background:#0E1117;'
                    f'border-radius:6px;border:1px solid #232B3B">'
                    f'<div style="font-size:0.75rem;color:{color};font-weight:700">'
                    f'{PIPELINE_LABELS.get(r.pipeline, r.pipeline)}</div>'
                    f'<div style="font-size:0.72rem;color:#7a8fa6;margin:2px 0">{ts}</div>'
                    f'<div style="font-size:0.7rem;color:#4a5568;font-family:monospace;'
                    f'word-break:break-all">{r.run_id}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
