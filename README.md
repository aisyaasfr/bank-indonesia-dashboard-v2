# Bank Indonesia — Business Intelligence & Monitoring System

A GitHub-ready Streamlit dashboard prototype for monitoring simulated transaction activity, liquidity-reporting compliance, and bank cashflow/currency projections across 55 fictional bank entities. All values and reporting statuses are generated locally; no official Bank Indonesia data or external database is used.

> **Permanent disclaimer:** Dashboard ini merupakan prototype Business Intelligence berbasis data simulasi (synthetic data) dan tidak merepresentasikan data, sistem, maupun laporan resmi Bank Indonesia.

## Features

- Seven routed views: Executive Dashboard, Transaction Analytics, Bank Performance, Liquidity Compliance, Cashflow Projection, Integrated Compliance, and Data Management.
- Deterministic synthetic dataset: 55 banks, 16,500 transactions, and up to 660 monthly records each for liquidity and cashflow reporting.
- Shared filters for year, month, transaction date range, banks, transaction type/category, reporting status, and liquidity compliance; light/dark appearance toggle.
- Interactive Plotly visualizations and drill-down tables.
- CSV and Excel downloads, full-dataset workbook export, and validated CSV/XLSX replacement uploads held in the active Streamlit session.
- Record-level create, read/search, update, and delete workflows for transactions, liquidity reports, and cashflow reports; edits are session-only and can be reset to the synthetic seed.
- BI-inspired, responsive UI with Poppins typography, a high-contrast light/dark switch, a sourced BI logo, and a project-owner footer. The visual identity is explicitly labeled as an independent simulation, not an official BI system.
- Reset to the built-in synthetic dataset at any time.
- Deadline-aware reporting statuses. A report is “BELUM JATUH TEMPO” until its deadline has passed; timely, late, and missing obligations are distinct.

## Synthetic-data conventions

The generator uses a fixed NumPy seed. Bank reporting behavior varies across archetypes, including always-on-time, frequently late, intermittent, improving, declining, never-reporting, and variable patterns. Each report has its own deadline and submission date.

Liquidity compliance rate is calculated as the number of timely reports divided by report obligations whose deadlines have passed. Late reports and missing reports are shown separately. Never-reporting banks remain within the due-obligation population. Cashflow is defined from the bank-network perspective: projected cash inflow enters the network, projected cash outflow leaves it, and `net_cashflow = projected_cash_inflow - projected_cash_outflow`. Cash deposit and withdrawal projections are components of those network flows.

The simulation uses the current date (capped at December 31, 2026) to determine whether a report deadline has passed. Future periods remain “BELUM JATUH TEMPO.”

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

The application generates the synthetic data on first load. It does not require prebuilt data files, API keys, paid APIs, XAMPP, or a database.

## Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, create a new app and connect the repository.
3. Set the main file path to `app.py`.
4. Deploy. Dependencies are installed from `requirements.txt`; the dataset is generated when the app starts.

## Project layout

```text
bank-indonesia-dashboard/
├── app.py
├── data_generator.py
├── utils.py
├── requirements.txt
├── README.md
├── pages/
│   ├── _executive.py
│   ├── _transaction_analytics.py
│   ├── _bank_performance.py
│   ├── _liquidity_compliance.py
│   ├── _cashflow_projection.py
│   ├── _integrated_compliance.py
│   └── _data_management.py
├── components/
│   ├── sidebar.py
│   ├── kpi_cards.py
│   ├── charts.py
│   └── tables.py
└── data/
    └── README.md
```

View modules are imported by the explicit `st.navigation` router. The leading underscore in the view filenames prevents Streamlit from registering a second automatic page list.

## UI identity and record CRUD

The header logo is the image linked by Bank Indonesia’s official website: `https://www.bi.go.id/Style%20Library/biweb2025/src/img/logo-bi.png`. The dashboard identifies itself as an independent prototype, carries the synthetic-data disclaimer, and credits the logo source. Poppins is loaded from Google Fonts with an Arial fallback. Light and dark themes use separate background, text, surface, border, and input colors; chart typography also uses Poppins.

Data Management includes search and create/update/delete actions for transaction, liquidity, and cashflow records. The 55-bank synthetic master is retained as the reference population; replacing that master remains available through validated upload. CRUD edits and uploaded data are kept in Streamlit session state and are not persisted to an external database.
