from __future__ import annotations

from datetime import date

import streamlit as st


def _reset_filters() -> None:
    defaults = {
        "month_filter": "All months",
        "date_filter": (date(2026, 1, 1), date(2026, 12, 31)),
        "bank_filter": [],
        "type_filter": "All",
        "category_filter": "All",
        "report_status_filter": "All",
        "compliance_filter": "All",
        "global_search": "",
    }
    for key, value in defaults.items():
        st.session_state[key] = value


def render_sidebar(bank_names: list[str]) -> dict:
    with st.sidebar:
        st.markdown("#### Dashboard controls")
        st.caption("FILTER DATA · EXPLORE REPORTS")
        st.text_input(
            "Search bank or transaction ID",
            placeholder="Bank 12 or TX-0001234",
            key="global_search",
            help="Search narrows transaction records by bank or transaction ID and reporting records by bank.",
        )
        st.selectbox("Reporting year", [2026], index=0, key="year_filter")
        month = st.selectbox(
            "Month",
            ["All months", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
            key="month_filter",
        )
        date_range = st.date_input(
            "Period range",
            value=(date(2026, 1, 1), date(2026, 12, 31)),
            min_value=date(2026, 1, 1),
            max_value=date(2026, 12, 31),
            key="date_filter",
        )
        banks = st.multiselect("Banks (blank = all)", bank_names, default=[], key="bank_filter")
        with st.expander("Advanced filters", expanded=False):
            tx_type = st.selectbox("Transaction type", ["All", "Incoming", "Outgoing"], key="type_filter")
            category = st.selectbox("Transaction category", ["All", "Transfer", "Kliring", "RTGS", "BI-FAST", "Setoran", "Penarikan", "Other Transactions"], key="category_filter")
            report_status = st.selectbox("Reporting status", ["All", "PATUH", "TERLAMBAT", "TIDAK MELAPOR", "BELUM JATUH TEMPO"], key="report_status_filter")
            compliance = st.selectbox("Liquidity compliance", ["All", "Compliant", "Non-compliant"], key="compliance_filter")
        dark = st.toggle("Dark mode", key="theme_dark", help="Switch between high-contrast light and dark themes.")
        st.button("Reset filters", width="stretch", on_click=_reset_filters)
        st.divider()
        st.caption("Prototype independen · Data sintetis 2026")
    if not isinstance(date_range, (list, tuple)):
        date_range = (date_range, date_range)
    elif len(date_range) == 1:
        date_range = (date_range[0], date_range[0])
    return {
        "selected_month": month,
        "date_range": date_range,
        "banks": banks,
        "transaction_type": tx_type,
        "category": category,
        "report_status": report_status,
        "compliance": compliance,
        "search_query": st.session_state.get("global_search", ""),
        "dark": dark,
    }
