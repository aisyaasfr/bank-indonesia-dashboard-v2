from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import apply_plotly_theme
from components.kpi_cards import render_metrics
from utils import STATUS_COLORS, STATUS_ORDER, filter_reports, number, percent, section, show_status_legend, timely_rate


def _priority(status: str, late_count: int, missing_count: int) -> str:
    if missing_count >= 3 or (status == "TIDAK MELAPOR" and late_count >= 2):
        return "High priority"
    if missing_count >= 1 or late_count >= 2:
        return "Medium priority"
    return "Low priority"


def render(data: dict, filters: dict) -> None:
    st.markdown("## Liquidity Reporting Compliance")
    st.caption("Monthly liquidity-report attendance and deadline compliance for the simulated 55-bank population.")
    metric_reports = filter_reports(data["liquidity"], {**filters, "report_status": "All"}, include_status=False)
    reports = metric_reports.copy()
    if filters["report_status"] != "All":
        reports = reports[reports.reporting_status == filters["report_status"]]
    if filters["compliance"] == "Compliant":
        reports = reports[reports.reporting_status == "PATUH"]
    elif filters["compliance"] == "Non-compliant":
        reports = reports[reports.reporting_status.isin(["TERLAMBAT", "TIDAK MELAPOR"])]

    due = metric_reports[metric_reports.reporting_status != "BELUM JATUH TEMPO"]
    timely, obligations, rate = timely_rate(metric_reports)
    received = int(metric_reports.submission_date.notna().sum())
    banks = data["banks"].loc[data["banks"].bank.isin(metric_reports.bank.unique())]
    late = int((due.reporting_status == "TERLAMBAT").sum())
    missing = int((due.reporting_status == "TIDAK MELAPOR").sum())
    never_reported = 0
    full_due = data["liquidity"].query("reporting_status != 'BELUM JATUH TEMPO'")
    for bank_name in banks.bank:
        subset = full_due[full_due.bank == bank_name]
        if len(subset) and subset.submission_date.isna().all():
            never_reported += 1
    late_days = (due.loc[due.reporting_status == "TERLAMBAT", "submission_date"] - due.loc[due.reporting_status == "TERLAMBAT", "reporting_deadline"]).dt.days
    avg_late = float(late_days.mean()) if not late_days.empty else 0.0
    render_metrics([
        ("Registered banks", number(banks.bank.nunique()), None),
        ("Banks with timely reports", number(due.loc[due.reporting_status == "PATUH", "bank"].nunique()), None),
        ("Late reports", number(late), None),
        ("Missing reports", number(missing), None),
        ("Never reported", number(never_reported), None),
        ("Reports received", number(received), None),
        ("Overall compliance", percent(rate), f"{timely:,} / {obligations:,} due"),
        ("Average delay", f"{avg_late:.1f} days", "Late reports only"),
    ], columns=4)
    st.caption("Compliance rate = reports submitted on time ÷ obligations whose deadline has passed. Late and missing reports remain separate categories.")

    section("Reporting attendance", "Bank × reporting month")
    search = st.text_input("Find bank in matrix", placeholder="Type a bank name")
    matrix_data = reports.copy()
    if search.strip():
        matrix_data = matrix_data[matrix_data.bank.str.contains(search.strip(), case=False, na=False)]
    matrix_data["month_name"] = matrix_data.reporting_period.dt.month.map(lambda m: pd.Timestamp(2026, int(m), 1).strftime("%b"))
    matrix = matrix_data.pivot(index="bank", columns="month_name", values="reporting_status")
    cols = [pd.Timestamp(2026, m, 1).strftime("%b") for m in range(1, 13) if pd.Timestamp(2026, m, 1).strftime("%b") in matrix.columns]
    matrix = matrix.reindex(columns=cols).sort_index()
    show_status_legend()
    def style_status(value):
        color = STATUS_COLORS.get(value, "transparent")
        return f"background-color: {color}; color: white; font-weight: 600;" if value else ""
    st.dataframe(matrix.style.map(style_status), width="stretch", height=480)

    section("Monthly compliance analysis", "Timeliness trend")
    monthly = metric_reports.groupby("reporting_period", as_index=False).agg(
        due=("reporting_status", lambda s: int((s != "BELUM JATUH TEMPO").sum())),
        timely=("reporting_status", lambda s: int((s == "PATUH").sum())),
        received=("submission_date", "count"),
        late=("reporting_status", lambda s: int((s == "TERLAMBAT").sum())),
        missing=("reporting_status", lambda s: int((s == "TIDAK MELAPOR").sum())),
    )
    monthly["compliance_rate"] = monthly.apply(lambda r: r.timely / r.due * 100 if r.due else np.nan, axis=1)
    a, b = st.columns(2)
    with a:
        fig = px.line(monthly, x="reporting_period", y="compliance_rate", markers=True, title="Monthly compliance rate", color_discrete_sequence=["#23865B"])
        fig.update_yaxes(range=[0, 105], ticksuffix="%")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with b:
        plot = monthly.melt(id_vars="reporting_period", value_vars=["received", "late", "missing"], var_name="status", value_name="reports")
        fig = px.bar(plot, x="reporting_period", y="reports", color="status", barmode="group", title="Reports received, late, and missing", color_discrete_map={"received": "#163A5F", "late": "#E5A000", "missing": "#D9534F"})
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    counts = metric_reports.reporting_status.value_counts().reindex(STATUS_ORDER, fill_value=0).rename_axis("status").reset_index(name="count")
    a, b = st.columns(2)
    with a:
        fig = px.pie(counts, names="status", values="count", hole=.55, title="Reporting status distribution", color="status", color_discrete_map=STATUS_COLORS)
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with b:
        per_bank = due.assign(timely=(due.reporting_status == "PATUH").astype(int)).groupby("bank", as_index=False).agg(rate=("timely", "mean"), late=("reporting_status", lambda s: int((s == "TERLAMBAT").sum())), missing=("reporting_status", lambda s: int((s == "TIDAK MELAPOR").sum())))
        rank = per_bank.nsmallest(15, "rate").sort_values("rate")
        fig = px.bar(rank, x="rate", y="bank", orientation="h", title="Lowest bank compliance ranking", color="rate", color_continuous_scale=["#D9534F", "#E5A000", "#23865B"])
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Non-compliance monitoring", "Follow-up priorities")
    per_bank = metric_reports.groupby("bank", as_index=False).agg(
        late_count=("reporting_status", lambda s: int((s == "TERLAMBAT").sum())),
        missing_count=("reporting_status", lambda s: int((s == "TIDAK MELAPOR").sum())),
        timely_count=("reporting_status", lambda s: int((s == "PATUH").sum())),
    )
    per_bank["compliance_rate"] = per_bank.apply(lambda r: r.timely_count / (r.timely_count + r.late_count + r.missing_count) * 100 if (r.timely_count + r.late_count + r.missing_count) else np.nan, axis=1)
    per_bank["priority"] = per_bank.apply(lambda r: _priority("TIDAK MELAPOR" if r.missing_count else "TERLAMBAT", r.late_count, r.missing_count), axis=1)
    per_bank["priority_rank"] = per_bank.priority.map({"High priority": 0, "Medium priority": 1, "Low priority": 2})
    attention = per_bank[(per_bank.late_count > 0) | (per_bank.missing_count > 0)].sort_values(["priority_rank", "missing_count", "late_count"], ascending=[True, False, False])
    if attention.empty:
        st.success("No due exceptions match these filters.")
    else:
        st.dataframe(attention, width="stretch", hide_index=True)

    section("Selected bank history", "Monthly report detail")
    bank_options = sorted(metric_reports.bank.unique())
    if not bank_options:
        st.info("No banks are available for this filter combination.")
        return
    preferred = filters["banks"][0] if len(filters["banks"]) == 1 else bank_options[0]
    selected = st.selectbox("Bank history", bank_options, index=bank_options.index(preferred) if preferred in bank_options else 0, key="liquidity_bank_detail")
    history = metric_reports.loc[metric_reports.bank == selected].copy()
    st.dataframe(history[["reporting_month", "reporting_deadline", "submission_date", "reporting_status", "remarks"]], width="stretch", hide_index=True)
