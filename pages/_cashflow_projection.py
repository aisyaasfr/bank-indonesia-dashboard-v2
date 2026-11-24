from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.charts import apply_plotly_theme
from components.kpi_cards import render_metrics
from utils import STATUS_COLORS, filter_reports, number, percent, rupiah, section, show_status_legend


def render(data: dict, filters: dict) -> None:
    st.markdown("## Cashflow & Currency Projection")
    st.caption("Monthly synthetic forecasts for cash deposits, withdrawals, cash entering/leaving bank networks, and reporting status.")
    cf = filter_reports(data["cashflow"], filters, include_status=False)
    if filters["report_status"] != "All":
        cf = cf[cf.reporting_status == filters["report_status"]]
    due = cf[cf.reporting_status != "BELUM JATUH TEMPO"]
    submitted = cf[cf.reporting_status.isin(["PATUH", "TERLAMBAT"])]
    late_banks = due.loc[due.reporting_status == "TERLAMBAT", "bank"].nunique()
    missing_banks = due.loc[due.reporting_status == "TIDAK MELAPOR", "bank"].nunique()
    net = int(cf.net_cashflow.sum())
    render_metrics([
        ("Banks in selection", number(cf.bank.nunique()), None),
        ("Banks already reported", number(submitted.bank.nunique()), None),
        ("Banks not reporting", number(missing_banks), None),
        ("Late reporting banks", number(late_banks), None),
        ("Projected cash inflow", rupiah(cf.projected_cash_inflow.sum(), True), None),
        ("Projected cash outflow", rupiah(cf.projected_cash_outflow.sum(), True), None),
        ("Cash withdrawal projection", rupiah(cf.cash_withdrawal_projection.sum(), True), None),
        ("Cash deposit projection", rupiah(cf.cash_deposit_projection.sum(), True), None),
        ("Net cashflow", rupiah(net, True), "Inflow − outflow"),
    ], columns=3)
    st.info("Perspective: cash inflow is cash entering the bank network; cash outflow is cash leaving it. Net cashflow = projected inflow − projected outflow. Deposit/withdrawal projections are components of network flows.")

    section("Cashflow forecast", "Liquidity outlook")
    monthly = cf.groupby("reporting_period", as_index=False).agg(
        inflow=("projected_cash_inflow", "sum"),
        outflow=("projected_cash_outflow", "sum"),
        net=("net_cashflow", "sum"),
        withdrawals=("cash_withdrawal_projection", "sum"),
        deposits=("cash_deposit_projection", "sum"),
    )
    a, b = st.columns(2)
    with a:
        long = monthly.melt(id_vars="reporting_period", value_vars=["inflow", "outflow"], var_name="measure", value_name="value")
        fig = px.line(long, x="reporting_period", y="value", color="measure", markers=True, title="Projected cash inflow vs outflow", color_discrete_map={"inflow": "#163A5F", "outflow": "#C6A15B"})
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with b:
        fig = px.bar(monthly, x="reporting_period", y=["withdrawals", "deposits"], barmode="stack", title="Monthly cash requirement components", color_discrete_sequence=["#C6A15B", "#23865B"])
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    fig = px.area(monthly, x="reporting_period", y="net", title="Monthly net cashflow", color_discrete_sequence=["#163A5F"])
    fig.add_hline(y=0, line_dash="dot", line_color="#9CA3AF")
    fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
    st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Bank-level projection", "Contribution and variation")
    selected_period = cf.reporting_period.max() if not cf.empty else pd.NaT
    if pd.notna(selected_period):
        period_cf = cf[cf.reporting_period == selected_period]
        a, b = st.columns(2)
        with a:
            top = period_cf.nlargest(10, "cash_withdrawal_projection").sort_values("cash_withdrawal_projection")
            fig = px.bar(top, x="cash_withdrawal_projection", y="bank", orientation="h", title=f"Top withdrawal projection · {selected_period.strftime('%B')}", color_discrete_sequence=["#C6A15B"])
            fig.update_xaxes(tickprefix="Rp ", tickformat=".2s")
            st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
        with b:
            top = period_cf.nlargest(10, "cash_deposit_projection").sort_values("cash_deposit_projection")
            fig = px.bar(top, x="cash_deposit_projection", y="bank", orientation="h", title=f"Top deposit projection · {selected_period.strftime('%B')}", color_discrete_sequence=["#23865B"])
            fig.update_xaxes(tickprefix="Rp ", tickformat=".2s")
            st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
        fig = px.pie(period_cf, names="bank", values="cash_withdrawal_projection", hole=.62, title="Bank contribution to total withdrawal requirement (selected period)")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Cashflow reporting matrix", "Attendance by bank and month")
    display_cf = filter_reports(data["cashflow"], {**filters, "selected_month": "All months", "report_status": "All"}, include_status=False)
    month_labels = {m: pd.Timestamp(2026, m, 1).strftime("%b") for m in range(1, 13)}
    display_cf["month"] = display_cf.reporting_period.dt.month.map(month_labels)
    matrix = display_cf.pivot(index="bank", columns="month", values="reporting_status").reindex(columns=list(month_labels.values())).sort_index()
    show_status_legend()
    def shade(value):
        color = STATUS_COLORS.get(value, "transparent")
        return f"background-color:{color};color:white;font-weight:600" if value else ""
    st.dataframe(matrix.style.map(shade), width="stretch", height=460)

    section("Cashflow monitoring alerts", "Exception queue")
    if pd.notna(selected_period):
        latest = cf[cf.reporting_period == selected_period].copy()
        previous = cf[cf.reporting_period == (selected_period - pd.offsets.MonthBegin(1))]
        previous_map = previous.set_index("bank").cash_withdrawal_projection if not previous.empty else pd.Series(dtype=float)
        latest["withdrawal_change_pct"] = latest.apply(lambda r: (r.cash_withdrawal_projection / previous_map.get(r.bank, 0) - 1) * 100 if previous_map.get(r.bank, 0) else None, axis=1)
        latest["withdrawal_change_pct"] = pd.to_numeric(latest["withdrawal_change_pct"], errors="coerce")
        latest["priority"] = latest.reporting_status.map({"TIDAK MELAPOR": "High", "TERLAMBAT": "Medium", "PATUH": "Low", "BELUM JATUH TEMPO": "Low"})
        latest["priority_rank"] = latest.priority.map({"High": 0, "Medium": 1, "Low": 2})
        alerts = latest[(latest.reporting_status.isin(["TIDAK MELAPOR", "TERLAMBAT"])) | (latest.withdrawal_change_pct.fillna(0.0) >= 25)].sort_values(["priority_rank", "cash_withdrawal_projection"], ascending=[True, False])
        st.dataframe(alerts[["bank", "reporting_status", "cash_withdrawal_projection", "cash_deposit_projection", "net_cashflow", "withdrawal_change_pct", "priority"]].head(20), width="stretch", hide_index=True)
        if not alerts.empty:
            st.caption("Projection alert threshold is a simulated month-over-month withdrawal increase of at least 25%; reporting alerts use due-date status.")

    section("Selected bank detail", "Forecast history")
    bank_options = sorted(cf.bank.unique())
    if not bank_options:
        st.info("No cashflow rows match the filters.")
        return
    preferred = filters["banks"][0] if len(filters["banks"]) == 1 else bank_options[0]
    selected = st.selectbox("Bank cashflow history", bank_options, index=bank_options.index(preferred) if preferred in bank_options else 0, key="cashflow_bank_detail")
    history = data["cashflow"].loc[data["cashflow"].bank == selected]
    st.dataframe(history[["reporting_month", "submission_date", "reporting_status", "projected_cash_inflow", "projected_cash_outflow", "cash_withdrawal_projection", "cash_deposit_projection", "net_cashflow"]], width="stretch", hide_index=True)
    fig = px.line(history, x="reporting_period", y=["cash_withdrawal_projection", "cash_deposit_projection"], markers=True, title=f"{selected}: withdrawal vs deposit projection", color_discrete_sequence=["#C6A15B", "#23865B"])
    fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
    st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
