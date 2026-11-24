from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import apply_plotly_theme
from components.kpi_cards import render_metrics
from utils import filter_reports, number, percent, section


def _overall(liquidity: str, cashflow: str) -> str:
    if liquidity == "BELUM JATUH TEMPO" and cashflow == "BELUM JATUH TEMPO":
        return "BELUM JATUH TEMPO"
    if liquidity == "TIDAK MELAPOR" or cashflow == "TIDAK MELAPOR":
        return "TIDAK PATUH"
    if liquidity == "TERLAMBAT" or cashflow == "TERLAMBAT":
        return "PERLU PERHATIAN"
    if liquidity == "PATUH" and cashflow == "PATUH":
        return "PATUH"
    return "BELUM JATUH TEMPO"


def render(data: dict, filters: dict) -> None:
    st.markdown("## Integrated Compliance")
    st.caption("A period-specific view combining liquidity and cashflow report timeliness. The two obligation populations are not combined into one denominator.")
    liq = filter_reports(data["liquidity"], {**filters, "report_status": "All"}, include_status=False)
    cf = filter_reports(data["cashflow"], {**filters, "report_status": "All"}, include_status=False)
    if liq.empty or cf.empty:
        st.info("No report records match the selected filters.")
        return
    periods = sorted(set(liq.reporting_period) & set(cf.reporting_period))
    mature_periods = sorted(set(liq.loc[liq.reporting_status != "BELUM JATUH TEMPO", "reporting_period"]) & set(cf.loc[cf.reporting_status != "BELUM JATUH TEMPO", "reporting_period"]))
    chosen_period = mature_periods[-1] if mature_periods else periods[-1]
    if filters["selected_month"] != "All months":
        month_no = pd.Timestamp(f"2026-{pd.Timestamp(filters['selected_month'] + ' 1, 2026').month:02d}-01")
        if month_no in periods:
            chosen_period = month_no
    else:
        start, end = filters["date_range"]
        end_period = pd.Timestamp(end).to_period("M").to_timestamp()
        available = [p for p in periods if p <= end_period]
        mature_available = [p for p in mature_periods if p <= end_period]
        if mature_available:
            chosen_period = mature_available[-1]
        elif available:
            chosen_period = available[-1]
    l = liq.loc[liq.reporting_period == chosen_period, ["bank_id", "bank", "reporting_status"]].rename(columns={"reporting_status": "Liquidity"})
    c = cf.loc[cf.reporting_period == chosen_period, ["bank_id", "reporting_status"]].rename(columns={"reporting_status": "Cashflow"})
    table = l.merge(c, on="bank_id", how="outer").merge(data["banks"][["bank_id", "bank"]], on=["bank_id", "bank"], how="left")
    table["Overall Status"] = table.apply(lambda r: _overall(r.Liquidity, r.Cashflow), axis=1)
    table = table.rename(columns={"Liquidity": "Liquidity report", "Cashflow": "Cashflow report"})
    st.caption(f"Selected status period: {chosen_period.strftime('%B %Y')}. Each report type is assessed against its own deadline and obligation count.")

    both = int((table["Overall Status"] == "PATUH").sum())
    only_liq = int(((table["Liquidity report"] == "PATUH") & (table["Cashflow report"] != "PATUH")).sum())
    only_cf = int(((table["Cashflow report"] == "PATUH") & (table["Liquidity report"] != "PATUH")).sum())
    neither = int(table["Overall Status"].isin(["TIDAK PATUH", "PERLU PERHATIAN"]).sum())
    render_metrics([
        ("Patuh pada kedua laporan", number(both), None),
        ("Patuh hanya pada likuiditas", number(only_liq), None),
        ("Patuh hanya pada cashflow", number(only_cf), None),
        ("Tidak patuh / perlu perhatian", number(neither), None),
    ], columns=4)

    section("Combined report status", "Side-by-side assessment")
    counts = table["Overall Status"].value_counts().rename_axis("status").reset_index(name="banks")
    a, b = st.columns([1, 1.4])
    with a:
        fig = px.pie(counts, names="status", values="banks", hole=.56, title="Overall status distribution", color="status", color_discrete_map={"PATUH": "#1F754D", "PERLU PERHATIAN": "#8F5B00", "TIDAK PATUH": "#B83A36", "BELUM JATUH TEMPO": "#596579"})
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")
    with b:
        cross = table.groupby(["Liquidity report", "Cashflow report"], dropna=False).size().reset_index(name="Banks")
        fig = px.density_heatmap(cross, x="Liquidity report", y="Cashflow report", z="Banks", histfunc="sum", text_auto=True, title="Liquidity × cashflow status cross-tab", color_continuous_scale=["#E9EDF2", "#163A5F"])
        st.plotly_chart(apply_plotly_theme(fig, filters["dark"]), width="stretch")

    section("Bank-level integrated register", "Period status")
    query = st.text_input("Search bank", placeholder="Bank 1")
    display = table[["bank", "Liquidity report", "Cashflow report", "Overall Status"]].copy()
    if query.strip():
        display = display[display.bank.str.contains(query.strip(), case=False, na=False)]
    st.dataframe(display.sort_values(["Overall Status", "bank"]), width="stretch", hide_index=True)
