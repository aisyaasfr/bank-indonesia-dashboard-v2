from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.charts import apply_plotly_theme
from components.kpi_cards import render_metrics
from components.tables import dataframe_with_downloads
from utils import filter_transactions, number, percent, rupiah, section


def render(data: dict, filters: dict) -> None:
    st.markdown("## Transaction Analytics")
    st.caption("Explore transaction value, direction, channel mix, status, and daily activity across the synthetic bank network.")
    tx = filter_transactions(data["transactions"], filters)
    status_choice = st.selectbox("Transaction status", ["All", "Successful", "Pending", "Failed"], key="transaction_status_local")
    if status_choice != "All":
        tx = tx[tx["status"] == status_choice]
    incoming = float(tx.loc[tx.transaction_type == "Incoming", "amount"].sum())
    outgoing = float(tx.loc[tx.transaction_type == "Outgoing", "amount"].sum())
    success = int((tx.status == "Successful").sum())
    render_metrics([
        ("Transaction value", rupiah(tx.amount.sum(), True), None),
        ("Incoming", rupiah(incoming, True), None),
        ("Outgoing", rupiah(outgoing, True), None),
        ("Net transaction", rupiah(incoming - outgoing, True), "Incoming − outgoing"),
        ("Volume", number(len(tx)), None),
        ("Average value", rupiah(tx.amount.mean() if len(tx) else 0), None),
        ("Successful", number(success), None),
        ("Failed", number((tx.status == "Failed").sum()), None),
        ("Pending", number((tx.status == "Pending").sum()), None),
    ], columns=3)

    section("Transaction trends", "Value · volume · mix")
    tx = tx.copy()
    tx["month"] = tx.transaction_date.dt.to_period("M").dt.to_timestamp()
    monthly = tx.groupby(["month", "transaction_type"], as_index=False).agg(value=("amount", "sum"), volume=("transaction_id", "count"))
    daily = tx.groupby(tx.transaction_date.dt.floor("D")).size().rename("volume").reset_index().rename(columns={"transaction_date": "date"})
    left, right = st.columns(2)
    with left:
        fig = px.bar(monthly, x="month", y="value", color="transaction_type", barmode="group", color_discrete_map={"Incoming": "#23865B", "Outgoing": "#C6A15B"}, title="Monthly incoming vs outgoing")
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with right:
        fig = px.line(daily, x="date", y="volume", title="Daily transaction volume", markers=False, color_discrete_sequence=["#163A5F"])
        fig.update_yaxes(title="Transactions")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    left, right = st.columns(2)
    with left:
        cat = tx.groupby("category", as_index=False).agg(value=("amount", "sum"), volume=("transaction_id", "count")).sort_values("value", ascending=False)
        fig = px.bar(cat, x="category", y="value", color="value", color_continuous_scale=["#C6A15B", "#163A5F"], title="Transaction value by category")
        fig.update_xaxes(tickangle=-25)
        fig.update_yaxes(tickprefix="Rp ", tickformat=".2s")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with right:
        counts = tx.status.value_counts().rename_axis("status").reset_index(name="count")
        fig = px.pie(counts, names="status", values="count", hole=0.58, color="status", color_discrete_map={"Successful": "#23865B", "Pending": "#E5A000", "Failed": "#D9534F"}, title="Transaction status distribution")
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    monthly_total = tx.groupby("month", as_index=False).agg(value=("amount", "sum"))
    monthly_total["growth_pct"] = monthly_total.value.pct_change() * 100
    fig = px.line(monthly_total, x="month", y="growth_pct", markers=True, title="Month-over-month transaction value growth", color_discrete_sequence=["#C6A15B"])
    fig.add_hline(y=0, line_dash="dot", line_color="#9CA3AF")
    st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Transaction monitoring", "Search · filter · export")
    search = st.text_input("Search transaction ID", placeholder="e.g. TX-0000123")
    table = tx.copy()
    if search.strip():
        table = table[table.transaction_id.str.contains(search.strip(), case=False, na=False)]
    sort_desc = st.toggle("Sort by amount (highest first)", value=True, key="transaction_sort")
    table = table.sort_values("amount", ascending=not sort_desc)
    display = table[["transaction_id", "transaction_date", "bank", "transaction_type", "category", "amount", "status"]].rename(columns={
        "transaction_id": "Transaction ID", "transaction_date": "Date", "bank": "Bank", "transaction_type": "Type", "category": "Category", "amount": "Amount (IDR)", "status": "Status"
    })
    st.caption(f"Showing {len(display):,} of {len(tx):,} transactions. Adjust the sidebar filters to narrow the population.")
    dataframe_with_downloads(display, "transactions_filtered", height=420)
