from __future__ import annotations

import plotly.express as px
import pandas as pd
import streamlit as st

from components.charts import apply_plotly_theme
from components.kpi_cards import render_metrics
from utils import filter_reports, filter_transactions, number, rupiah, section


def render(data: dict, filters: dict) -> None:
    st.markdown("## Bank Performance")
    st.caption("Compare simulated activity across 55 registered entities and inspect an individual bank profile.")
    tx = filter_transactions(data["transactions"], filters)
    if tx.empty:
        st.info("No transactions match the current filters.")
        return
    grouped = tx.groupby(["bank_id", "bank"], as_index=False).agg(transaction_value=("amount", "sum"), volume=("transaction_id", "count"))
    inout = tx.pivot_table(index=["bank_id", "bank"], columns="transaction_type", values="amount", aggfunc="sum", fill_value=0).reset_index()
    if "Incoming" not in inout.columns:
        inout["Incoming"] = 0
    if "Outgoing" not in inout.columns:
        inout["Outgoing"] = 0
    perf = grouped.merge(inout[["bank_id", "Incoming", "Outgoing"]], on="bank_id", how="left")
    perf["net_transaction"] = perf["Incoming"] - perf["Outgoing"]
    perf = perf.merge(data["banks"][["bank_id", "bank_category", "registration_status"]], on="bank_id", how="left")

    section("Network ranking", "Bank performance")
    choices = st.selectbox("Ranking metric", ["Transaction value", "Incoming value", "Outgoing value", "Transaction volume"], key="ranking_metric")
    metric_col = {"Transaction value": "transaction_value", "Incoming value": "Incoming", "Outgoing value": "Outgoing", "Transaction volume": "volume"}[choices]
    top = perf.nlargest(10, metric_col).sort_values(metric_col)
    fig = px.bar(top, x=metric_col, y="bank", orientation="h", color=metric_col, color_continuous_scale=["#C6A15B", "#163A5F"], title=f"Top 10 banks by {choices.lower()}")
    if metric_col != "volume":
        fig.update_xaxes(tickprefix="Rp ", tickformat=".2s")
    st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    low = perf.nsmallest(1, "transaction_value").iloc[0]
    render_metrics([
        ("Banks in selection", number(perf.bank.nunique()), None),
        ("Highest transaction value", str(perf.nlargest(1, "transaction_value").iloc[0].bank), rupiah(perf.transaction_value.max(), True)),
        ("Lowest transaction value", str(low.bank), rupiah(low.transaction_value, True)),
        ("Selected-period network value", rupiah(perf.transaction_value.sum(), True), None),
    ], columns=4)

    a, b = st.columns(2)
    with a:
        fig = px.bar(perf.sort_values("transaction_value", ascending=False), x="bank", y="transaction_value", title="Transaction value per bank", color="transaction_value", color_continuous_scale=["#C6A15B", "#163A5F"])
        fig.update_xaxes(tickangle=-55)
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with b:
        long = perf.melt(id_vars="bank", value_vars=["Incoming", "Outgoing"], var_name="direction", value_name="value")
        fig = px.bar(long, x="bank", y="value", color="direction", barmode="group", title="Incoming vs outgoing by bank", color_discrete_map={"Incoming": "#23865B", "Outgoing": "#C6A15B"})
        fig.update_xaxes(tickangle=-55)
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    monthly = tx.assign(month=tx.transaction_date.dt.to_period("M").dt.to_timestamp()).groupby(["month", "bank"], as_index=False).agg(value=("amount", "sum"))
    leaders = perf.nlargest(8, "transaction_value").bank.tolist()
    fig = px.line(monthly[monthly.bank.isin(leaders)], x="month", y="value", color="bank", markers=True, title="Monthly performance — top 8 banks")
    fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
    st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Bank detail", "Individual profile")
    options = sorted(perf.bank.unique())
    preferred = filters["banks"][0] if len(filters["banks"]) == 1 else options[0]
    selected = st.selectbox("Select bank", options, index=options.index(preferred) if preferred in options else 0, key="bank_detail_select")
    bank = data["banks"].loc[data["banks"].bank == selected].iloc[0]
    one = perf.loc[perf.bank == selected].iloc[0]
    render_metrics([
        ("Bank ID", bank.bank_id, str(bank.bank_category)),
        ("Transaction volume", number(one.volume), None),
        ("Incoming", rupiah(one["Incoming"], True), None),
        ("Outgoing", rupiah(one["Outgoing"], True), None),
        ("Net transaction", rupiah(one.net_transaction, True), None),
    ], columns=5)
    tx_bank = tx[tx.bank == selected].sort_values("transaction_date", ascending=False)
    st.markdown("**Recent transactions**")
    st.dataframe(tx_bank[["transaction_id", "transaction_date", "transaction_type", "category", "amount", "status"]].head(30), width="stretch", hide_index=True)
    liq = filter_reports(data["liquidity"], {**filters, "banks": [selected], "report_status": "All"}, include_status=False)
    cf = filter_reports(data["cashflow"], {**filters, "banks": [selected], "report_status": "All"}, include_status=False)
    tab1, tab2 = st.tabs(["Liquidity history", "Cashflow history"])
    with tab1:
        st.dataframe(liq[["reporting_month", "reporting_deadline", "submission_date", "reporting_status", "remarks"]], width="stretch", hide_index=True)
    with tab2:
        st.dataframe(cf[["reporting_month", "submission_date", "reporting_status", "projected_cash_inflow", "projected_cash_outflow", "net_cashflow"]], width="stretch", hide_index=True)
