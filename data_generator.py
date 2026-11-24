from __future__ import annotations

from datetime import date, datetime
from typing import Dict

import numpy as np
import pandas as pd
import streamlit as st

SEED = 20261106
YEAR = 2026
BANK_COUNT = 55
TRANSACTION_COUNT = 16_500
MONTHS = list(range(1, 13))
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _archetype(idx: int) -> str:
    if idx < 5:
        return "always_on_time"
    if idx < 12:
        return "high_compliance"
    if idx < 21:
        return "frequently_late"
    if idx < 34:
        return "intermittent"
    if idx < 38:
        return "improving"
    if idx < 42:
        return "declining"
    if idx < 46:
        return "never_reports"
    return "variable"


def _report_probabilities(archetype: str, month: int, rng: np.random.Generator) -> tuple[float, float]:
    """Return (probability of submitting, probability timely given submitted)."""
    if archetype == "always_on_time":
        return 1.0, 1.0
    if archetype == "high_compliance":
        return 0.98, 0.94
    if archetype == "frequently_late":
        return 0.94, 0.20
    if archetype == "intermittent":
        return 0.68, 0.62
    if archetype == "improving":
        progress = (month - 1) / 11
        return 0.48 + progress * 0.48, 0.42 + progress * 0.52
    if archetype == "declining":
        progress = (month - 1) / 11
        return 0.96 - progress * 0.48, 0.94 - progress * 0.52
    if archetype == "never_reports":
        return 0.0, 0.0
    return float(rng.uniform(0.58, 0.94)), float(rng.uniform(0.45, 0.88))


def _monthly_deadline(month: int) -> pd.Timestamp:
    return pd.Timestamp(YEAR, month, 1) + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)


def _report_status(submission: pd.Timestamp | pd.NaT, deadline: pd.Timestamp, as_of: pd.Timestamp) -> str:
    if pd.notna(submission):
        return "PATUH" if submission <= deadline else "TERLAMBAT"
    return "TIDAK MELAPOR" if deadline.normalize() <= as_of.normalize() else "BELUM JATUH TEMPO"


def _make_submission(
    rng: np.random.Generator,
    submit_probability: float,
    timely_probability: float,
    deadline: pd.Timestamp,
    as_of: pd.Timestamp,
) -> pd.Timestamp | pd.NaT:
    if rng.random() > submit_probability:
        return pd.NaT
    if rng.random() < timely_probability:
        days_early = int(rng.integers(0, 8))
        candidate = deadline - pd.Timedelta(days=days_early)
    else:
        candidate = deadline + pd.Timedelta(days=int(rng.integers(1, 19)))
    return candidate if candidate.normalize() <= as_of.normalize() else pd.NaT


@st.cache_data(show_spinner="Generating reproducible synthetic data…")
def generate_datasets(as_of_iso: str | None = None) -> Dict[str, pd.DataFrame]:
    """Create all dashboard data from one fixed seed. No official data is used."""
    rng = np.random.default_rng(SEED)
    today = pd.Timestamp(as_of_iso).normalize() if as_of_iso else pd.Timestamp(date.today()).normalize()
    as_of = min(today, pd.Timestamp(YEAR, 12, 31))

    categories = ["National", "Regional", "Digital", "Specialized"]
    banks = pd.DataFrame(
        {
            "bank_id": [f"BI-{i:03d}" for i in range(1, BANK_COUNT + 1)],
            "bank": [f"Bank {i}" for i in range(1, BANK_COUNT + 1)],
            "bank_category": rng.choice(categories, BANK_COUNT, p=[0.30, 0.36, 0.18, 0.16]),
            "registration_status": ["Registered"] * BANK_COUNT,
            "reporting_archetype": [_archetype(i) for i in range(BANK_COUNT)],
            "activity_factor": np.round(rng.lognormal(0, 0.42, BANK_COUNT), 3),
        }
    )

    # Transactions: skew bank activity and amounts while retaining coverage across all banks.
    bank_weights = banks["activity_factor"].to_numpy()
    bank_weights = bank_weights / bank_weights.sum()
    tx_bank_idx = rng.choice(BANK_COUNT, TRANSACTION_COUNT, p=bank_weights)
    tx_dates = pd.to_datetime(
        rng.integers(pd.Timestamp(YEAR, 1, 1).value // 86_400_000_000_000,
                     (pd.Timestamp(YEAR, 12, 31).value // 86_400_000_000_000) + 1,
                     TRANSACTION_COUNT),
        unit="D",
    )
    tx_types = rng.choice(["Incoming", "Outgoing"], TRANSACTION_COUNT, p=[0.51, 0.49])
    tx_categories = rng.choice(
        ["Transfer", "Kliring", "RTGS", "BI-FAST", "Setoran", "Penarikan", "Other Transactions"],
        TRANSACTION_COUNT,
        p=[0.23, 0.12, 0.09, 0.22, 0.11, 0.13, 0.10],
    )
    amounts = np.clip(rng.lognormal(mean=15.0, sigma=2.15, size=TRANSACTION_COUNT), 2_500, 4_500_000_000)
    amounts = np.round(amounts / 1_000) * 1_000
    tx_status = rng.choice(["Successful", "Pending", "Failed"], TRANSACTION_COUNT, p=[0.925, 0.045, 0.03])
    transactions = pd.DataFrame(
        {
            "transaction_id": [f"TX-{i:07d}" for i in range(1, TRANSACTION_COUNT + 1)],
            "transaction_date": tx_dates,
            "bank_id": banks.loc[tx_bank_idx, "bank_id"].to_numpy(),
            "bank": banks.loc[tx_bank_idx, "bank"].to_numpy(),
            "transaction_type": tx_types,
            "category": tx_categories,
            "amount": amounts.astype("int64"),
            "status": tx_status,
        }
    )

    liquidity_rows = []
    cashflow_rows = []
    for idx, bank in banks.iterrows():
        archetype = bank["reporting_archetype"]
        activity = float(bank["activity_factor"])
        for month in MONTHS:
            period = pd.Timestamp(YEAR, month, 1)
            deadline = _monthly_deadline(month)
            p_submit, p_timely = _report_probabilities(archetype, month, rng)
            if deadline.normalize() <= as_of.normalize():
                sub_date = _make_submission(rng, p_submit, p_timely, deadline, as_of)
                cash_p_submit = min(1.0, max(0.0, p_submit + rng.normal(0, 0.04)))
                cash_p_timely = min(1.0, max(0.0, p_timely + rng.normal(0, 0.06)))
                cash_sub_date = _make_submission(rng, cash_p_submit, cash_p_timely, deadline, as_of)
            else:
                sub_date = pd.NaT
                cash_sub_date = pd.NaT

            liq_status = _report_status(sub_date, deadline, as_of)
            liquidity_rows.append(
                {
                    "report_id": f"LIQ-{idx + 1:03d}-{month:02d}",
                    "bank_id": bank["bank_id"],
                    "bank": bank["bank"],
                    "reporting_period": period,
                    "reporting_month": MONTH_NAMES[month - 1],
                    "reporting_deadline": deadline,
                    "submission_date": sub_date,
                    "reporting_status": liq_status,
                    "compliance_status": "Compliant" if liq_status == "PATUH" else ("Non-compliant" if liq_status == "TIDAK MELAPOR" else liq_status.title()),
                    "remarks": {
                        "PATUH": "Submitted on or before deadline",
                        "TERLAMBAT": "Submitted after deadline",
                        "TIDAK MELAPOR": "No submission recorded by deadline",
                        "BELUM JATUH TEMPO": "Reporting deadline has not passed",
                    }[liq_status],
                }
            )

            # Consistent perspective: inflow is cash entering the bank network; outflow leaves it.
            deposit = int(np.clip(rng.lognormal(18.05, 0.82) * activity, 500_000, 7_500_000_000))
            withdrawal = int(np.clip(rng.lognormal(18.15, 0.86) * activity, 500_000, 8_000_000_000))
            replenishment = int(np.clip(rng.lognormal(17.45, 0.65) * activity, 250_000, 3_000_000_000))
            cash_in = deposit + replenishment
            cash_out = withdrawal + int(np.clip(rng.lognormal(17.0, 0.72) * activity, 250_000, 2_500_000_000))
            cf_status = _report_status(cash_sub_date, deadline, as_of)
            cashflow_rows.append(
                {
                    "report_id": f"CF-{idx + 1:03d}-{month:02d}",
                    "bank_id": bank["bank_id"],
                    "bank": bank["bank"],
                    "reporting_period": period,
                    "reporting_month": MONTH_NAMES[month - 1],
                    "reporting_deadline": deadline,
                    "submission_date": cash_sub_date,
                    "reporting_status": cf_status,
                    "projected_cash_inflow": cash_in,
                    "projected_cash_outflow": cash_out,
                    "cash_withdrawal_projection": withdrawal,
                    "cash_deposit_projection": deposit,
                    "net_cashflow": cash_in - cash_out,
                    "remarks": {
                        "PATUH": "Submitted on or before deadline",
                        "TERLAMBAT": "Submitted after deadline",
                        "TIDAK MELAPOR": "No submission recorded by deadline",
                        "BELUM JATUH TEMPO": "Reporting deadline has not passed",
                    }[cf_status],
                }
            )

    liquidity = pd.DataFrame(liquidity_rows)
    cashflow = pd.DataFrame(cashflow_rows)
    return {"banks": banks, "transactions": transactions, "liquidity": liquidity, "cashflow": cashflow}
