from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.charts import apply_plotly_theme
from components.kpi_cards import render_metrics
from utils import filter_reports, filter_transactions, number, percent, rupiah, section, timely_rate


def render(data: dict, filters: dict) -> None:
    st.markdown("## Executive Dashboard")
    st.caption("A consolidated view of simulated transaction activity, reporting discipline, and cashflow projections.")
    tx = filter_transactions(data["transactions"], filters)
    liq_base = filter_reports(data["liquidity"], {**filters, "report_status": "All"}, include_status=False)
    liq = liq_base.copy()
    if filters["report_status"] != "All":
        liq = liq[liq.reporting_status == filters["report_status"]]
    cf = filter_reports(data["cashflow"], filters, include_status=False)
    if filters["report_status"] != "All":
        cf = cf[cf.reporting_status == filters["report_status"]]
    if filters["compliance"] == "Compliant":
        liq = liq[liq["reporting_status"] == "PATUH"]
    elif filters["compliance"] == "Non-compliant":
        liq = liq[liq["reporting_status"].isin(["TERLAMBAT", "TIDAK MELAPOR"])]

    incoming = float(tx.loc[tx.transaction_type == "Incoming", "amount"].sum())
    outgoing = float(tx.loc[tx.transaction_type == "Outgoing", "amount"].sum())
    volume = len(tx)
    timely, due, compliance_rate = timely_rate(liq_base)
    latest_cf = cf[cf["reporting_status"].isin(["PATUH", "TERLAMBAT"])]
    reporting_banks = latest_cf["bank"].nunique()
    not_reporting = cf[cf["reporting_status"] == "TIDAK MELAPOR"]["bank"].nunique()
    success = (tx["status"] == "Successful").mean() * 100 if volume else 0
    render_metrics([
        ("Total transaction value", rupiah(tx.amount.sum(), True), None),
        ("Incoming transaction value", rupiah(incoming, True), None),
        ("Outgoing transaction value", rupiah(outgoing, True), None),
        ("Net transaction", rupiah(incoming - outgoing, True), "Incoming − outgoing"),
        ("Transaction volume", number(volume), None),
        ("Successful rate", percent(success), None),
        ("Registered banks", number(data["banks"].bank_id.nunique()), None),
        ("Liquidity compliance", percent(compliance_rate), f"{timely:,} / {due:,} due reports"),
        ("Banks reporting cashflow", number(reporting_banks), None),
        ("Banks not reporting", number(not_reporting), None),
    ], columns=5)

    section("Operating pulse", "Executive analytics")
    monthly = tx.assign(month=tx.transaction_date.dt.to_period("M").dt.to_timestamp()).groupby(["month", "transaction_type"], as_index=False).agg(value=("amount", "sum"), volume=("transaction_id", "count"))
    liq_monthly = liq_base.groupby("reporting_period", as_index=False).agg(
        due=("reporting_status", lambda x: int((x != "BELUM JATUH TEMPO").sum())),
        timely=("reporting_status", lambda x: int((x == "PATUH").sum())),
        received=("submission_date", "count"),
        late=("reporting_status", lambda x: int((x == "TERLAMBAT").sum())),
        missing=("reporting_status", lambda x: int((x == "TIDAK MELAPOR").sum())),
    )
    liq_monthly["rate"] = liq_monthly.apply(lambda r: r.timely / r.due * 100 if r.due else None, axis=1)
    a, b = st.columns(2)
    with a:
        fig = px.line(monthly, x="month", y="value", color="transaction_type", markers=True, color_discrete_map={"Incoming": "#23865B", "Outgoing": "#C6A15B"}, title="Monthly incoming vs outgoing value")
        fig.update_yaxes(title="Transaction value (IDR)", tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with b:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=liq_monthly.reporting_period, y=liq_monthly.rate, name="Compliance rate", mode="lines+markers", line={"color": "#23865B", "width": 3}))
        fig.add_trace(go.Bar(x=liq_monthly.reporting_period, y=liq_monthly.missing, name="Missing reports", marker_color="#D9534F", opacity=0.72, yaxis="y2"))
        fig.update_layout(title="Liquidity reporting compliance & missing reports", yaxis={"title": "Compliance (%)", "range": [0, 105]}, yaxis2={"title": "Missing reports", "overlaying": "y", "side": "right"})
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    c, d = st.columns(2)
    with c:
        section("Transaction mix")
        mix = tx.groupby("transaction_type", as_index=False).agg(value=("amount", "sum"), volume=("transaction_id", "count"))
        fig = px.pie(mix, names="transaction_type", values="value", hole=0.62, color="transaction_type", color_discrete_map={"Incoming": "#23865B", "Outgoing": "#C6A15B"})
        fig.update_layout(title="Incoming vs outgoing value")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with d:
        section("Cashflow outlook")
        cf_month = cf.groupby("reporting_period", as_index=False).agg(inflow=("projected_cash_inflow", "sum"), outflow=("projected_cash_outflow", "sum"), net=("net_cashflow", "sum"))
        fig = px.area(cf_month, x="reporting_period", y=["inflow", "outflow"], title="Monthly cashflow projection", labels={"value": "IDR", "reporting_period": "Period", "variable": "Measure"}, color_discrete_sequence=["#163A5F", "#C6A15B"])
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Transaction value ranking", "Bank performance")
    ranking = tx.groupby(["bank_id", "bank"], as_index=False).agg(transaction_value=("amount", "sum"), incoming=("amount", lambda s: s[tx.loc[s.index, "transaction_type"].eq("Incoming")].sum()), volume=("transaction_id", "count"))
    top = ranking.nlargest(10, "transaction_value").sort_values("transaction_value")
    fig = px.bar(top, x="transaction_value", y="bank", orientation="h", color="transaction_value", color_continuous_scale=["#B8C9D9", "#163A5F"], title="Top 10 banks by transaction value")
    fig.update_xaxes(tickprefix="Rp ", tickformat=".2s")
    st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    followup = liq.assign(priority=liq.reporting_status.map({"TIDAK MELAPOR": "High", "TERLAMBAT": "Medium", "PATUH": "Low", "BELUM JATUH TEMPO": "Low"}))
    followup = followup[followup.reporting_status.isin(["TIDAK MELAPOR", "TERLAMBAT"])].sort_values(["reporting_status", "reporting_period"])
    section("Banks needing follow-up", "Action queue")
    if followup.empty:
        st.success("No due liquidity reports currently require follow-up under the selected filters.")
    else:
        st.dataframe(followup[["bank", "reporting_month", "reporting_deadline", "submission_date", "reporting_status", "priority"]].head(12), width="stretch", hide_index=True)
