from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

DISCLAIMER = (
    "Dashboard ini merupakan prototype Business Intelligence berbasis data simulasi "
    "(synthetic data) dan tidak merepresentasikan data, sistem, maupun laporan resmi Bank Indonesia."
)
STATUS_ORDER = ["PATUH", "TERLAMBAT", "TIDAK MELAPOR", "BELUM JATUH TEMPO"]
STATUS_COLORS = {
    "PATUH": "#1F754D",
    "TERLAMBAT": "#8F5B00",
    "TIDAK MELAPOR": "#B83A36",
    "BELUM JATUH TEMPO": "#596579",
}
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def rupiah(value: float | int, compact: bool = False) -> str:
    value = float(value or 0)
    if compact:
        for threshold, suffix in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
            if abs(value) >= threshold:
                return f"Rp {value / threshold:,.1f}{suffix}"
    return f"Rp {value:,.0f}"


def number(value: float | int, decimals: int = 0) -> str:
    return f"{float(value or 0):,.{decimals}f}"


def percent(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def inject_theme(dark: bool) -> None:
    """Apply the dashboard's full light/dark palette and consistent typography."""
    palette = {
        "bg": "#0D1726" if dark else "#F3F6FA",
        "surface": "#142238" if dark else "#FFFFFF",
        "surface_alt": "#1B2B42" if dark else "#F7FAFD",
        "text": "#F4F7FB" if dark else "#183A5A",
        "body": "#D1D9E5" if dark else "#384D63",
        "muted": "#A8B6C8" if dark else "#596B7C",
        "border": "#2B3D55" if dark else "#DCE5EF",
        "input": "#1B2B42" if dark else "#FFFFFF",
        "shadow": "0 12px 30px rgba(8, 37, 68, .10)" if not dark else "0 12px 30px rgba(0, 0, 0, .22)",
        "gold": "#C6A15B",
        "navy": "#0C2E4E",
        "blue": "#145B91",
        "positive_bg": "#163E33" if dark else "#E7F5EC",
        "positive_text": "#96E1B8" if dark else "#0B5A3C",
        "negative_bg": "#4A2730" if dark else "#FBEAED",
        "negative_text": "#FFC0C8" if dark else "#8B2C3A",
    }
    st.markdown(
        f"""<style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
        :root {{
          --bi-bg:{palette['bg']}; --bi-surface:{palette['surface']}; --bi-surface-alt:{palette['surface_alt']};
          --bi-text:{palette['text']}; --bi-body:{palette['body']}; --bi-muted:{palette['muted']};
          --bi-border:{palette['border']}; --bi-input:{palette['input']}; --bi-gold:{palette['gold']};
          --bi-navy:{palette['navy']}; --bi-blue:{palette['blue']}; --bi-shadow:{palette['shadow']};
          --bi-positive-bg:{palette['positive_bg']}; --bi-positive-text:{palette['positive_text']};
          --bi-negative-bg:{palette['negative_bg']}; --bi-negative-text:{palette['negative_text']};
        }}
        html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] * {{
          font-family:'Poppins',Arial,sans-serif !important;
        }}
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
          background:var(--bi-bg) !important; color:var(--bi-body) !important;
        }}
        [data-testid="stHeader"] {{ background:transparent !important; }}
        [data-testid="stMainBlockContainer"] {{ max-width:1500px; padding-top:1.25rem; padding-bottom:2rem; }}
        [data-testid="stSidebar"] {{ background:var(--bi-surface) !important; border-right:1px solid var(--bi-border); }}
        [data-testid="stSidebar"] * {{ color:var(--bi-body); }}
        [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] label {{ color:var(--bi-text) !important; }}
        [data-testid="stSidebarNav"] {{ padding:8px 10px 12px; }}
        [data-testid="stSidebarNav"] a {{ border-radius:10px; margin:3px 0; padding:9px 11px; color:var(--bi-body) !important; font-size:12px; font-weight:600; transition:background .15s ease, transform .15s ease; }}
        [data-testid="stSidebarNav"] a:hover {{ background:var(--bi-surface-alt) !important; transform:translateX(2px); }}
        [data-testid="stSidebarNav"] a[aria-current="page"] {{ background:linear-gradient(100deg,#0C2E4E,#145B91) !important; color:#fff !important; box-shadow:0 5px 13px rgba(12,46,78,.18); }}
        h1,h2,h3,h4,h5,h6,p,li,small,span,label {{ font-family:'Poppins',Arial,sans-serif; }}
        h1,h2,h3,h4 {{ color:var(--bi-text) !important; letter-spacing:-.025em; }}
        p,li,.stMarkdown {{ color:var(--bi-body); }}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color:var(--bi-muted) !important; }}
        [data-testid="stMetric"] {{ background:var(--bi-surface) !important; border:1px solid var(--bi-border); padding:13px 14px; border-radius:15px; box-shadow:var(--bi-shadow); transition:transform .18s ease, box-shadow .18s ease; min-width:0; }}
        [data-testid="stMetric"]:hover {{ transform:translateY(-2px); box-shadow:0 15px 34px rgba(8,37,68,.15); }}
        [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{ color:var(--bi-muted) !important; font-size:12px; font-weight:500; }}
        [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ color:var(--bi-text) !important; font-weight:700; font-size:clamp(15px,1.45vw,21px) !important; line-height:1.3; white-space:normal !important; overflow:visible !important; text-overflow:clip !important; overflow-wrap:anywhere; }}
        [data-testid="stMetricDelta"] {{ font-size:11px; border-radius:999px; padding:3px 7px; background:var(--bi-positive-bg) !important; color:var(--bi-positive-text) !important; }}
        [data-testid="stMetricDelta"] *, [data-testid="stMetricDelta"] svg {{ color:var(--bi-positive-text) !important; fill:currentColor; }}
        [data-testid="stMetricDelta"] p {{ color:inherit !important; }}
        [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) {{ background:var(--bi-negative-bg) !important; color:var(--bi-negative-text) !important; }}
        [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) * {{ color:var(--bi-negative-text) !important; }}
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
        [data-testid="stTextArea"] textarea {{ background:var(--bi-input) !important; color:var(--bi-text) !important; border-color:var(--bi-border) !important; border-radius:10px !important; }}
        [data-testid="stSelectbox"] input[role="combobox"], [data-testid="stMultiSelect"] input[role="combobox"] {{ background:var(--bi-input) !important; color:var(--bi-text) !important; border:1px solid var(--bi-border) !important; border-radius:9px !important; caret-color:var(--bi-text); }}
        [data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"] {{ background:var(--bi-input) !important; color:var(--bi-text) !important; border-color:var(--bi-border) !important; border-radius:10px !important; }}
        [data-testid="stSelectbox"] button, [data-testid="stMultiSelect"] button {{ color:var(--bi-muted) !important; background:var(--bi-input) !important; }}
        [data-testid="stDateInputField"] {{ background:var(--bi-input) !important; color:var(--bi-text) !important; border:1px solid var(--bi-border) !important; border-radius:10px !important; }}
        [data-testid="stDateInputField"] [role="group"], [data-testid="stDateInputField"] [contenteditable="true"] {{ background:transparent !important; color:var(--bi-text) !important; }}
        [data-testid="stDateInputField"] button {{ color:var(--bi-muted) !important; background:transparent !important; }}
        @media(max-width:900px) {{ [data-testid="stMetric"] {{ padding:11px 10px; }} [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ font-size:15px !important; }} [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{ font-size:10px; }} }}
        [data-testid="stTextInput"] label,[data-testid="stNumberInput"] label,[data-testid="stDateInput"] label,
        [data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label,[data-testid="stRadio"] label,
        [data-testid="stToggle"] label {{ color:var(--bi-body) !important; }}
        [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {{ background:var(--bi-surface) !important; color:var(--bi-text) !important; }}
        [role="option"] {{ color:var(--bi-body) !important; }}
        [role="option"]:hover {{ background:var(--bi-surface-alt) !important; }}
        [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {{
          border:1px solid var(--bi-border); border-radius:10px; color:var(--bi-text); background:var(--bi-surface);
          font-weight:600; transition:transform .15s ease, box-shadow .15s ease, background .15s ease;
        }}
        [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {{ transform:translateY(-1px); border-color:var(--bi-blue); box-shadow:var(--bi-shadow); color:var(--bi-blue); }}
        [data-testid="stDataFrame"], [data-testid="stTable"] {{ border:1px solid var(--bi-border); border-radius:12px; overflow:hidden; background:var(--bi-surface); }}
        [data-testid="stTabs"] button {{ color:var(--bi-muted) !important; font-weight:600; }}
        [data-testid="stTabs"] button[aria-selected="true"] {{ color:var(--bi-blue) !important; border-bottom-color:var(--bi-gold) !important; }}
        [data-testid="stAlert"] {{ border-radius:12px; }}
        .bi-masthead {{ display:flex; align-items:center; justify-content:space-between; gap:24px; padding:18px 24px; margin:0 0 18px; border-radius:18px; color:#fff; background:linear-gradient(115deg,#092946 0%,#0E4D7D 60%,#176A9E 100%); box-shadow:0 14px 32px rgba(8,40,69,.22); border-bottom:3px solid var(--bi-gold); position:relative; overflow:hidden; }}
        .bi-masthead:after {{ content:''; position:absolute; right:-55px; top:-120px; width:370px; height:320px; border:1px solid rgba(255,255,255,.10); border-radius:50%; box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 62px rgba(255,255,255,.025); pointer-events:none; }}
        .bi-brand {{ display:flex; align-items:center; gap:22px; min-width:0; position:relative; z-index:1; }}
        .bi-logo-wrap {{ display:flex; align-items:center; justify-content:center; width:210px; min-width:170px; height:54px; padding:7px 10px; border-right:1px solid rgba(255,255,255,.24); }}
        .bi-logo-wrap img {{ display:block; max-width:100%; max-height:42px; object-fit:contain; }}
        .bi-heading {{ min-width:0; }}
        .bi-heading .eyebrow {{ color:#E5C98D; text-transform:uppercase; font-size:10px; letter-spacing:1.7px; font-weight:700; margin-bottom:5px; }}
        .bi-heading h1 {{ color:#fff !important; margin:0; font-size:clamp(17px,2vw,25px); line-height:1.28; letter-spacing:-.03em; }}
        .bi-heading p {{ color:#D6E5F2 !important; margin:5px 0 0; font-size:12px; }}
        .bi-state {{ position:relative; z-index:1; text-align:right; min-width:160px; }}
        .bi-state .pill {{ display:inline-flex; align-items:center; gap:7px; border:1px solid rgba(255,255,255,.3); border-radius:999px; padding:7px 11px; color:#fff; background:rgba(255,255,255,.10); font-size:10px; font-weight:700; letter-spacing:.08em; }}
        .bi-state .dot {{ width:7px; height:7px; border-radius:50%; background:#70D5A1; box-shadow:0 0 0 4px rgba(112,213,161,.16); }}
        .bi-state .source {{ color:#D0DFEC; margin-top:7px; font-size:10px; }}
        .section-kicker {{ color:var(--bi-blue); font-weight:700; text-transform:uppercase; letter-spacing:1.2px; font-size:10px; margin:12px 0 3px; }}
        .section-title {{ color:var(--bi-text); font-size:20px; font-weight:700; letter-spacing:-.025em; margin:0 0 10px; }}
        .sim-disclaimer {{ color:var(--bi-muted); border-top:1px solid var(--bi-border); margin-top:24px; padding:14px 2px 0; font-size:10px; line-height:1.7; }}
        .identity-footer {{ margin-top:8px; padding:16px 18px; border:1px solid var(--bi-border); border-radius:14px; display:flex; align-items:center; justify-content:space-between; gap:14px; color:var(--bi-body); background:var(--bi-surface); }}
        .identity-footer strong {{ color:var(--bi-text); font-size:12px; }}
        .identity-footer a {{ color:var(--bi-blue) !important; text-decoration:none; font-weight:600; font-size:12px; }}
        .identity-footer a:hover {{ text-decoration:underline; }}
        .status-chip {{ padding:4px 9px; border-radius:999px; color:#fff; font-size:10px; font-weight:700; white-space:nowrap; }}
        @media(max-width:780px) {{ .bi-masthead {{ align-items:flex-start; flex-direction:column; padding:16px; }} .bi-brand {{ gap:12px; align-items:flex-start; flex-direction:column; }} .bi-logo-wrap {{ width:170px; border-right:0; border-bottom:1px solid rgba(255,255,255,.24); justify-content:flex-start; }} .bi-state {{ text-align:left; }} .identity-footer {{ align-items:flex-start; flex-direction:column; }} }}
        @media(prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ scroll-behavior:auto !important; animation-duration:.01ms !important; transition-duration:.01ms !important; }} }}
        </style>""",
        unsafe_allow_html=True,
    )


def section(title: str, kicker: str | None = None) -> None:
    if kicker:
        st.markdown(f'<div class="section-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def filter_transactions(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    out = df
    start, end = filters["date_range"]
    out = out[(out["transaction_date"].dt.date >= start) & (out["transaction_date"].dt.date <= end)]
    if filters["selected_month"] != "All months":
        month = MONTH_NAMES.index(filters["selected_month"]) + 1
        out = out[out["transaction_date"].dt.month == month]
    if filters["banks"]:
        out = out[out["bank"].isin(filters["banks"])]
    if filters["transaction_type"] != "All":
        out = out[out["transaction_type"] == filters["transaction_type"]]
    if filters["category"] != "All":
        out = out[out["category"] == filters["category"]]
    search = str(filters.get("search_query", "")).strip()
    if search:
        out = out[
            out["transaction_id"].astype(str).str.contains(search, case=False, na=False)
            | out["bank"].astype(str).str.contains(search, case=False, na=False)
        ]
    return out


def filter_reports(df: pd.DataFrame, filters: dict[str, Any], include_status: bool = True) -> pd.DataFrame:
    out = df
    if filters["selected_month"] != "All months":
        month = MONTH_NAMES.index(filters["selected_month"]) + 1
        out = out[out["reporting_period"].dt.month == month]
    start, end = filters["date_range"]
    out = out[
        (out["reporting_period"].dt.date <= end)
        & ((out["reporting_period"] + pd.offsets.MonthEnd(0)).dt.date >= start)
    ]
    if filters["banks"]:
        out = out[out["bank"].isin(filters["banks"])]
    search = str(filters.get("search_query", "")).strip()
    if search:
        out = out[out["bank"].astype(str).str.contains(search, case=False, na=False)]
    if include_status and filters["report_status"] != "All":
        out = out[out["reporting_status"] == filters["report_status"]]
    return out


def timely_rate(df: pd.DataFrame) -> tuple[int, int, float]:
    due = df[df["reporting_status"] != "BELUM JATUH TEMPO"]
    timely = int((due["reporting_status"] == "PATUH").sum())
    denominator = len(due)
    return timely, denominator, (timely / denominator * 100) if denominator else 0.0


def make_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, index=False, sheet_name=name[:31])
    return buffer.getvalue()


def show_status_legend() -> None:
    cols = st.columns(4)
    for col, label in zip(cols, STATUS_ORDER):
        col.markdown(
            f'<span class="status-chip" style="background:{STATUS_COLORS[label]}">{label}</span>',
            unsafe_allow_html=True,
        )
