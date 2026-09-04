# 🧾 AP Invoice Exception Assistant
### Track 4 — AI Finance Controller

**🔗 Live Demo:** https://ap-invoice-exception-assistant-pfcjkcwabe2g9w9lhmaexv.streamlit.app/

An AI-assisted Accounts Payable tool that automatically catches invoice
errors — mismatches, duplicates, missing data — **before** they get paid.
It replaces a manual, error-prone reconciliation process with an instant,
explainable exception report for the finance team.

---

## The Problem

In most finance teams, AP staff manually check every incoming invoice
against its purchase order — comparing amounts, quantities, vendor names,
and PO status by eye, often in spreadsheets. This is:

- **Slow** — doesn't scale as invoice volume grows.
- **Error-prone** — duplicate payments and overbilling slip through.
- **Reactive** — problems are usually found in an audit, months later, after
  the money is already gone.

## The Solution

**AP Invoice Exception Assistant** ingests invoices and purchase orders,
runs them through a rule engine modeled on real AP controls, and instantly
surfaces every exception with a plain-English reason — so nothing gets paid
until it's actually correct.

### Exceptions detected

| Exception type       | Business risk it catches                                   |
|-----------------------|-------------------------------------------------------------|
| `missing_po`          | Invoice references a PO that doesn't exist — possible fraud or data-entry error |
| `vendor_mismatch`     | Invoice vendor doesn't match the PO's vendor — wrong entity being paid |
| `amount_mismatch`     | Invoice amount differs from PO beyond tolerance — overbilling |
| `quantity_mismatch`   | Invoice quantity differs from PO — paying for goods not received |
| `duplicate_invoice`   | Same invoice submitted twice — duplicate payment risk |
| `missing_fields`      | Required fields blank — invoice can't be safely processed |
| `po_closed`           | Invoice against a closed/cancelled PO — should never be paid |

### What the dashboard shows

- **Live metrics**: total invoices, exception count, exception rate, dollar amount at risk
- **Filterable exception table** with severity (high/medium) and a plain-English reason per row
- **One-click CSV export** of flagged invoices for the finance team
- **Optional AI narrative summary** (Claude) — a short paragraph a controller can read in 10 seconds instead of scanning a table
- **Adjustable tolerances** — amount % and quantity thresholds are sidebar controls, not hardcoded

## Why this is a good fit for AI Finance Controller

- **Explainable, not a black box** — every flag has a human-readable reason, which matters for audit trails and trust.
- **Rule engine + AI, not AI alone** — deterministic checks catch the errors reliably; the LLM is used where it adds real value (turning a table into a narrative), not for decisions that need to be reproducible.
- **Immediately useful** — works with plain CSV exports, no ERP integration required to demo real value.
- **Extensible toward a full agent** — see "Roadmap" below for the natural next steps (three-way match, auto-routing approvals, ERP integration).

## Tech Stack

- **Frontend/App**: Streamlit
- **Data processing**: pandas
- **AI narrative layer**: Anthropic Claude API (optional)
- **Deployment**: Streamlit Community Cloud

## Project Structure

```
ap-invoice-exception-assistant/
├── app.py                       # Streamlit app (UI + orchestration)
├── utils/
│   ├── exception_rules.py       # Rule-based exception detection engine
│   └── ai_summary.py            # Optional Claude API narrative summary
├── sample_data/
│   ├── invoices.csv             # Sample invoices with built-in exceptions
│   └── purchase_orders.csv      # Sample POs
├── requirements.txt
├── .env.example
└── .gitignore
```

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Open `http://localhost:8501`, click **"Use sample data"**, and the flagged
exceptions appear immediately.

To enable the optional AI summary:
```bash
export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=your-key-here
```

### Expected CSV formats
**invoices.csv**: `invoice_id, po_number, vendor, invoice_date, amount, quantity`
**purchase_orders.csv**: `po_number, vendor, po_amount, po_quantity, status`

## Deployment

Already live on Streamlit Community Cloud at the link above. To redeploy
your own copy:
1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select repo/branch → main file `app.py`.
3. (Optional) Add `ANTHROPIC_API_KEY` under **Advanced settings → Secrets**.
4. Deploy.

## Roadmap

- **Three-way match**: add a goods-receipt file and require invoice = PO = receipt before approval.
- **Auto-routing**: send high-severity exceptions to an approver via Slack/email webhook.
- **ERP integration**: pull invoices/POs directly from NetSuite/SAP/QuickBooks instead of CSV upload.
- **Trend tracking**: store results over time and chart exception rate and $ at risk week over week.
- **AI-drafted vendor emails**: turn each exception into a ready-to-send follow-up email to the vendor.

---

*Built for the AI Finance Controller track.*
