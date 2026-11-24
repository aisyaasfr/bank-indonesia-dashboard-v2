from __future__ import annotations

import pandas as pd
import streamlit as st

from utils import make_excel


def dataframe_with_downloads(frame: pd.DataFrame, key: str, title: str | None = None, height: int = 360) -> None:
    if title:
        st.markdown(f"**{title}**")
    left, right = st.columns([1, 1])
    csv = frame.to_csv(index=False).encode("utf-8-sig")
    left.download_button("Download CSV", csv, f"{key}.csv", "text/csv", key=f"{key}_csv")
    xlsx = make_excel({"Data": frame})
    right.download_button("Download Excel", xlsx, f"{key}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{key}_xlsx")
    st.dataframe(frame, width="stretch", height=height, hide_index=True)
