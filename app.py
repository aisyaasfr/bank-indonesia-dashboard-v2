from __future__ import annotations

import streamlit as st

from components.sidebar import render_sidebar
from data_generator import generate_datasets
from pages import _bank_performance, _cashflow_projection, _data_management, _executive, _integrated_compliance, _liquidity_compliance, _transaction_analytics
from utils import DISCLAIMER, inject_theme

st.set_page_config(
    page_title="Bank Intelligence | Simulation",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Official BI header logo, confirmed on https://www.bi.go.id/.
BI_LOGO_URL = "https://www.bi.go.id/Style%20Library/biweb2025/src/img/logo-bi.png"
OWNER_NAME = "Aisyah Ayu Shafira Putri"
OWNER_EMAIL = "aisyahasp8@gmail.com"


def effective_data() -> dict:
    base = generate_datasets()
    overrides = st.session_state.get("uploaded_overrides", {})
    return {**base, **overrides}


def page_wrapper(view, app_data, shared_filters):
    def render_view():
        view(app_data, shared_filters)
    return render_view


data = {}
views = [
    ("Executive Dashboard", "executive", _executive.render),
    ("Transaction Analytics", "transactions", _transaction_analytics.render),
    ("Bank Performance", "banks", _bank_performance.render),
    ("Liquidity Compliance", "liquidity", _liquidity_compliance.render),
    ("Cashflow Projection", "cashflow", _cashflow_projection.render),
    ("Integrated Compliance", "integrated", _integrated_compliance.render),
    ("Data Management", "data-management", _data_management.render),
]
filters = {}
pages = [
    st.Page(page_wrapper(view, data, filters), title=title, url_path=path, default=(i == 0))
    for i, (title, path, view) in enumerate(views)
]
selected_page = st.navigation(pages, position="sidebar")
with st.sidebar:
    st.markdown("### BANK INDONESIA")
    st.caption("BUSINESS INTELLIGENCE · SIMULATION")
data.update(effective_data())
filters.update(render_sidebar(sorted(data["banks"]["bank"].dropna().unique().tolist())))
inject_theme(filters["dark"])

st.markdown(
    f"""<header class="bi-masthead">
      <div class="bi-brand">
        <div class="bi-logo-wrap"><img src="{BI_LOGO_URL}" alt="Logo resmi Bank Indonesia" /></div>
        <div class="bi-heading">
          <div class="eyebrow">Business intelligence · monitoring system</div>
          <h1>Banking Monitoring Dashboard</h1>
          <p>Transaction activity · liquidity compliance · currency cashflow projections · 2026</p>
        </div>
      </div>
      <div class="bi-state">
        <div class="pill"><span class="dot"></span> SIMULATION MODE</div>
        <div class="source">Independent prototype · not an official BI system</div>
      </div>
    </header>""",
    unsafe_allow_html=True,
)
selected_page.run()
st.markdown(
    f'''<div class="sim-disclaimer">{DISCLAIMER}<br>Logo Bank Indonesia bersumber dari situs resmi <a href="https://www.bi.go.id/" target="_blank" rel="noopener noreferrer">bi.go.id</a>; penggunaan di sini hanya sebagai identitas visual prototype.</div>
    <footer class="identity-footer"><div><strong>Dashboard prototype oleh {OWNER_NAME}</strong><br><span>Business Intelligence · Synthetic Data Project</span></div><a href="mailto:{OWNER_EMAIL}">{OWNER_EMAIL}</a></footer>''',
    unsafe_allow_html=True,
)
