from __future__ import annotations

import streamlit as st


def render_metrics(metrics: list[tuple[str, str, str | None]], columns: int = 4) -> None:
    columns = min(max(columns, 1), 4)
    for start in range(0, len(metrics), columns):
        row = metrics[start : start + columns]
        cols = st.columns(len(row))
        for col, (label, value, delta) in zip(cols, row):
            col.metric(label, value, delta=delta)
