from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from components.tables import dataframe_with_downloads
from utils import make_excel, section

REQUIRED = {
    "banks": ["bank_id", "bank", "bank_category", "registration_status", "reporting_archetype", "activity_factor"],
    "transactions": ["transaction_id", "transaction_date", "bank_id", "bank", "transaction_type", "category", "amount", "status"],
    "liquidity": ["report_id", "bank_id", "bank", "reporting_period", "reporting_month", "reporting_deadline", "submission_date", "reporting_status", "compliance_status", "remarks"],
    "cashflow": ["report_id", "bank_id", "bank", "reporting_period", "reporting_month", "reporting_deadline", "submission_date", "reporting_status", "projected_cash_inflow", "projected_cash_outflow", "cash_withdrawal_projection", "cash_deposit_projection", "net_cashflow", "remarks"],
}
DATE_COLUMNS = {
    "transactions": ["transaction_date"],
    "liquidity": ["reporting_period", "reporting_deadline", "submission_date"],
    "cashflow": ["reporting_period", "reporting_deadline", "submission_date"],
}
PRIMARY_KEYS = {"transactions": "transaction_id", "liquidity": "report_id", "cashflow": "report_id"}
DATASET_LABELS = {"transactions": "Transactions", "liquidity": "Liquidity reports", "cashflow": "Cashflow reports"}


def _read_upload(file) -> pd.DataFrame:
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


def _validate(frame: pd.DataFrame, kind: str) -> tuple[pd.DataFrame | None, str]:
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = [c for c in REQUIRED[kind] if c not in frame.columns]
    if missing:
        return None, "Missing required columns: " + ", ".join(missing)
    frame = frame[REQUIRED[kind]].copy()
    for column in DATE_COLUMNS.get(kind, []):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if kind == "transactions":
        if frame.transaction_id.duplicated().any():
            return None, "Transaction IDs must be unique."
        if not 10_000 <= len(frame) <= 20_000:
            return None, "Transaction dataset must contain between 10,000 and 20,000 rows."
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
        if frame["amount"].isna().any() or (frame["amount"] < 0).any():
            return None, "Transaction amounts must be valid non-negative numbers."
    if kind == "cashflow":
        numeric = ["projected_cash_inflow", "projected_cash_outflow", "cash_withdrawal_projection", "cash_deposit_projection", "net_cashflow"]
        for column in numeric:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[numeric].isna().any().any():
            return None, "Cashflow projection values must be numeric."
        expected = frame.projected_cash_inflow - frame.projected_cash_outflow
        if not np.allclose(expected.to_numpy(), frame.net_cashflow.to_numpy(), rtol=0, atol=0):
            return None, "net_cashflow must equal projected_cash_inflow − projected_cash_outflow."
    if kind == "banks":
        if frame.bank_id.duplicated().any() or frame.bank.duplicated().any():
            return None, "Bank IDs and bank names must be unique."
        if len(frame) != 55:
            return None, "The master dataset must contain exactly 55 banks."
    return frame, f"Validated {len(frame):,} rows."


def _search_records(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query.strip():
        return frame
    mask = frame.astype("string").apply(
        lambda column: column.str.contains(query.strip(), case=False, na=False, regex=False)
    ).any(axis=1)
    return frame.loc[mask]


def _new_record_id(kind: str, frame: pd.DataFrame) -> str:
    key = PRIMARY_KEYS[kind]
    prefix = {"transactions": "TX-CRUD", "liquidity": "LIQ-CRUD", "cashflow": "CF-CRUD"}[kind]
    existing = set(frame[key].astype(str))
    number = 1
    while f"{prefix}-{number:05d}" in existing:
        number += 1
    return f"{prefix}-{number:05d}"


def _record_editor(kind: str, frame: pd.DataFrame, record: pd.Series | None, operation: str) -> dict | None:
    key = PRIMARY_KEYS[kind]
    source = record if record is not None else frame.iloc[-1]
    values = {}
    with st.form(f"crud_form_{kind}_{operation}"):
        st.markdown(f"**{operation} {DATASET_LABELS[kind].lower()} record**")
        cols = st.columns(2)
        for index, column in enumerate(frame.columns):
            default = source[column]
            with cols[index % 2]:
                if column == key:
                    value = _new_record_id(kind, frame) if operation == "Create" else str(default)
                    values[column] = st.text_input(column.replace("_", " ").title(), value=value, disabled=True, key=f"crud_{kind}_{operation}_{column}")
                elif column in DATE_COLUMNS.get(kind, []):
                    default_text = "" if pd.isna(default) else pd.Timestamp(default).strftime("%Y-%m-%d")
                    values[column] = st.text_input(
                        column.replace("_", " ").title(),
                        value=default_text,
                        placeholder="YYYY-MM-DD (leave blank if not submitted)",
                        key=f"crud_{kind}_{operation}_{column}",
                    )
                elif pd.api.types.is_numeric_dtype(frame[column]):
                    numeric_default = 0.0 if operation == "Create" and column != "activity_factor" else (float(default) if pd.notna(default) else 0.0)
                    values[column] = st.number_input(
                        column.replace("_", " ").title(),
                        value=numeric_default,
                        step=1.0 if pd.api.types.is_float_dtype(frame[column]) else 1000.0,
                        format="%.3f" if pd.api.types.is_float_dtype(frame[column]) else "%.0f",
                        key=f"crud_{kind}_{operation}_{column}",
                    )
                else:
                    default_text = "" if pd.isna(default) else str(default)
                    values[column] = st.text_input(
                        column.replace("_", " ").title(),
                        value=default_text,
                        key=f"crud_{kind}_{operation}_{column}",
                    )
        submitted = st.form_submit_button("Create record" if operation == "Create" else "Save changes", type="primary")
    return values if submitted else None


def _cast_record(values: dict, frame: pd.DataFrame, kind: str) -> tuple[dict | None, str | None]:
    converted = {}
    for column, value in values.items():
        if column in DATE_COLUMNS.get(kind, []):
            parsed = pd.to_datetime(str(value).strip(), errors="coerce")
            if str(value).strip() and pd.isna(parsed):
                return None, f"{column} must use YYYY-MM-DD format."
            if column in ["transaction_date", "reporting_period", "reporting_deadline"] and pd.isna(parsed):
                return None, f"{column} is required."
            converted[column] = parsed
        elif pd.api.types.is_numeric_dtype(frame[column]):
            converted[column] = int(value) if pd.api.types.is_integer_dtype(frame[column]) else float(value)
        else:
            converted[column] = str(value).strip()
    if kind == "transactions" and converted.get("amount", 0) < 0:
        return None, "Transaction amount cannot be negative."
    if kind == "cashflow":
        expected = converted.get("projected_cash_inflow", 0) - converted.get("projected_cash_outflow", 0)
        if converted.get("net_cashflow") != expected:
            return None, "net_cashflow must equal projected_cash_inflow − projected_cash_outflow."
    return converted, None


def _save_override(kind: str, frame: pd.DataFrame) -> None:
    overrides = dict(st.session_state.get("uploaded_overrides", {}))
    overrides[kind] = frame.reset_index(drop=True)
    st.session_state["uploaded_overrides"] = overrides


def render(data: dict, filters: dict) -> None:
    st.markdown("## Data Management")
    st.caption("Browse, search, create, update, and delete session records. Exports, validated uploads, and reset-to-synthetic are also available.")
    if st.button("Reset to synthetic dataset", type="secondary", key="reset_synthetic"):
        st.session_state["uploaded_overrides"] = {}
        st.success("Synthetic seed dataset restored.")
        st.rerun()
    overrides = st.session_state.get("uploaded_overrides", {})
    if overrides:
        st.warning("One or more synthetic tables are currently replaced by uploaded or edited session data.")

    section("Record workspace", "Search · CRUD")
    crud_tab, browse_tab, upload_tab = st.tabs(["Record CRUD", "Browse & export", "Upload datasets"])
    with crud_tab:
        kind = st.selectbox("Dataset", list(DATASET_LABELS), format_func=lambda value: DATASET_LABELS[value], key="crud_dataset")
        frame = data[kind].copy()
        key = PRIMARY_KEYS[kind]
        search = st.text_input("Search records", placeholder="ID, bank, category, or status", key=f"crud_search_{kind}")
        matches = _search_records(frame, search)
        st.caption(f"{len(matches):,} records match · {len(frame):,} total records")
        operation = st.radio("Action", ["Create", "Update", "Delete"], horizontal=True, key=f"crud_action_{kind}")
        selected = None
        record_key = None
        if operation in ("Update", "Delete"):
            if matches.empty:
                st.info("No matching records. Adjust the search or select Create to add a new row.")
            else:
                page_count = max(1, (len(matches) + 99) // 100)
                page_no = st.selectbox("Result page", list(range(1, page_count + 1)), key=f"crud_page_{kind}")
                page_rows = matches.iloc[(page_no - 1) * 100 : page_no * 100]
                record_key = st.selectbox("Select record", page_rows[key].astype(str).tolist(), key=f"crud_record_{kind}")
                selected = frame.loc[frame[key].astype(str) == str(record_key)].iloc[0]
                st.dataframe(pd.DataFrame([selected]), width="stretch", hide_index=True)
        if operation == "Delete" and selected is not None:
            confirm = st.checkbox(f"Confirm permanent deletion of {record_key} for this session", key=f"crud_delete_confirm_{kind}")
            if st.button("Delete selected record", type="primary", disabled=not confirm, key=f"crud_delete_{kind}"):
                _save_override(kind, frame.loc[frame[key].astype(str) != str(record_key)].copy())
                st.success(f"Record {record_key} deleted from the active session dataset.")
                st.rerun()
        elif operation == "Create" or (operation == "Update" and selected is not None):
            values = _record_editor(kind, frame, selected, operation)
            if values is not None:
                converted, error = _cast_record(values, frame, kind)
                if error:
                    st.error(error)
                elif operation == "Create" and converted[key] in set(frame[key].astype(str)):
                    st.error(f"{key} already exists. Create a record with a unique identifier.")
                else:
                    if operation == "Create":
                        updated = pd.concat([frame, pd.DataFrame([converted])], ignore_index=True)
                    else:
                        updated = frame.copy()
                        mask = updated[key].astype(str) == str(record_key)
                        for column, value in converted.items():
                            if column != key:
                                updated.loc[mask, column] = value
                    if kind in ("liquidity", "cashflow") and updated.duplicated(["bank_id", "reporting_period"]).any():
                        st.error("A bank can only have one report per reporting period. This change would create a duplicate.")
                    else:
                        _save_override(kind, updated)
                        st.success("Record created." if operation == "Create" else "Record updated.")
                        st.rerun()

    with browse_tab:
        section("Dataset inventory", "Current working data")
        inventory = pd.DataFrame([{"Dataset": name.title(), "Rows": len(frame), "Columns": len(frame.columns)} for name, frame in data.items()])
        st.dataframe(inventory, width="stretch", hide_index=True)
        workbook = make_excel(data)
        st.download_button("Export all datasets to Excel", workbook, "bank_monitoring_all_datasets.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="all_data_excel")
        table_search = st.text_input("Search all dataset previews", placeholder="Bank, ID, status, category", key="dataset_search")
        tabs = st.tabs(["Banks", "Transactions", "Liquidity reports", "Cashflow reports"])
        for tab, table_kind in zip(tabs, ["banks", "transactions", "liquidity", "cashflow"]):
            with tab:
                table = data[table_kind]
                if table_search.strip():
                    table = _search_records(table, table_search)
                st.caption(f"Showing {min(len(table), 250):,} of {len(table):,} matching records · {len(table.columns)} fields")
                st.dataframe(table.head(250), width="stretch", height=330, hide_index=True)
                csv = table.to_csv(index=False).encode("utf-8-sig")
                st.download_button(f"Download {table_kind} CSV", csv, f"{table_kind}.csv", "text/csv", key=f"{table_kind}_download_csv")
                xlsx = make_excel({table_kind.title(): table})
                st.download_button(f"Download {table_kind} Excel", xlsx, f"{table_kind}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{table_kind}_download_xlsx")

    with upload_tab:
        section("Upload and validate", "Replace working data")
        st.markdown("Upload CSV or Excel files using the required column names. Uploaded datasets replace the selected synthetic table for this Streamlit session.")
        cols = st.columns(2)
        kinds = ["banks", "transactions", "liquidity", "cashflow"]
        for i, upload_kind in enumerate(kinds):
            with cols[i % 2]:
                file = st.file_uploader(f"Upload {upload_kind} (.csv / .xlsx)", type=["csv", "xlsx"], key=f"upload_{upload_kind}")
                if file is not None:
                    try:
                        uploaded = _read_upload(file)
                        valid, message = _validate(uploaded, upload_kind)
                        if valid is None:
                            st.error(message)
                        else:
                            if upload_kind != "banks":
                                master = st.session_state.get("uploaded_overrides", {}).get("banks", data["banks"])
                                unknown_ids = set(valid.bank_id.dropna()) - set(master.bank_id.dropna())
                                if unknown_ids:
                                    st.error(f"Unknown bank IDs: {', '.join(sorted(unknown_ids)[:8])}")
                                    continue
                            if upload_kind in ("liquidity", "cashflow"):
                                if valid.duplicated(["bank_id", "reporting_period"]).any():
                                    st.error("Only one report row per bank and reporting period is allowed.")
                                    continue
                                expected_ids = set(st.session_state.get("uploaded_overrides", {}).get("banks", data["banks"]).bank_id)
                                if valid.bank_id.nunique() != 55 or len(valid) != 55 * 12 or set(valid.bank_id) != expected_ids:
                                    st.error("Monthly reports must contain exactly one row for each of the 55 banks in each of 12 periods.")
                                    continue
                            st.session_state.setdefault("uploaded_overrides", {})[upload_kind] = valid
                            st.success(message + " Applied to the dashboard session.")
                            st.rerun()
                    except Exception as exc:
                        st.error(f"Could not read file: {exc}")
        section("Data integrity notes", "Simulation conventions")
        st.markdown("- The built-in data is deterministic and generated locally with a fixed seed.\n- Transaction amounts are synthetic Rupiah values; transaction volume is 16,500 rows.\n- Liquidity and cashflow compliance use each report's deadline and submission date.\n- Compliance rate uses only obligations whose deadlines have passed.\n- Net cashflow equals projected inflow minus projected outflow.")
