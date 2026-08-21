# AP Invoice Exception Assistant

Built for the Supervity FDE technical screening — **Problem 1: AP Invoice Exception Assistant**.

An AI Employee that ingests a vendor invoice (PDF) and a purchase order, extracts line items,
flags price / quantity / tax mismatches against the PO, and lets a reviewer ask
*"why was invoice #123 flagged?"* in a chat interface and get an answer grounded in the
actual extracted and PO fields.

## Architecture

```
invoice.pdf ──► extraction.py ──► structured line items ──┐
                                                            ├──► comparison.py ──► flagged exceptions
sample_po.json ─────────────────────────────────────────────┘                          │
                                                                                          ▼
                                                                    chat.py ──► reviewer Q&A (grounded)
                                                                                          │
                                                                                          ▼
                                                                              app.py (Streamlit UI)
```

- **`extraction.py`** — Primary path uses `pdfplumber`'s ruled-table detection (deterministic,
  no API cost, works for the sample invoice and any similarly tabular PDF). If no table is
  detected — e.g. a scanned or irregularly formatted invoice — it falls back to raw-text
  extraction plus a Claude call constrained to return strict JSON in the same schema, so the
  rest of the pipeline never has to know which path was used.
- **`comparison.py`** — Pure deterministic Python. Matches invoice lines to PO lines by SKU and
  checks quantity (exact match), unit price (2% tolerance), and tax (recomputed from the PO's
  tax rate, 2% tolerance). No LLM involved here on purpose — exception flags need to be
  reproducible and auditable, not a model's opinion. Also reports PO lines that were authorized
  but never invoiced at all.
- **`chat.py`** — Answers reviewer questions. First finds the specific line(s) being asked about
  (by line number or SKU, or all flagged lines if the question is about the invoice generally),
  then builds an answer **only** from the exception records `comparison.py` already computed.
  If `ANTHROPIC_API_KEY` is set, it asks Claude to smooth the phrasing but explicitly forbids
  introducing any fact/number not already in the grounded text — this is what keeps answers
  source-grounded instead of a generic LLM guess.
- **`app.py`** — Streamlit UI: upload an invoice + select a PO, see extracted data next to the
  PO side-by-side, see exceptions flagged inline per line, then chat with the assistant about
  any of it.

## Setup

```bash
cd ap-invoice-assistant
pip install -r requirements.txt
python3 sample_data/generate_sample_invoice.py   # regenerates the demo invoice.pdf
streamlit run app.py
```

Or just run `./run.sh` (does all three steps).

Optional: `export ANTHROPIC_API_KEY=sk-...` to enable the LLM fallback extractor
(for scanned/irregular invoices) and nicer chat phrasing. The app works fully
without it — the sample invoice uses the deterministic table-extraction path,
and the chat falls back to templated grounded answers.

## Demo flow

1. Launch the app, click **"Use bundled sample invoice instead"** (or upload your own PDF)
   with the sample PO selected.
2. Review the extracted invoice header and the line-by-line comparison — three lines are
   deliberately flagged (qty, price, and tax mismatches) and one PO line was never invoiced,
   so there's something real to demo.
3. Ask the assistant: *"why was line 1 flagged?"*, *"why was line 2 flagged?"*, or
   *"why was invoice INV-8842 flagged?"* and see grounded, field-cited answers.

## Assumptions made (per the brief's instruction to state assumptions rather than ask)

- **Matching key**: invoice lines are matched to PO lines by SKU, not by line number, since
  vendors don't reliably preserve PO line ordering on their own invoices.
- **Tolerances**: 2% variance allowed on unit price and tax (rounding/FX noise), 0 tolerance
  on quantity (partial shipments should be handled via separate PO line splits, out of scope
  here).
- **Tax validation**: since the sample PO doesn't carry a per-line tax field, expected tax is
  recomputed as `line_total × PO.tax_rate` and compared to the invoice's stated tax — this
  mirrors how a real 3-way-match tax check would work against an ERP tax code.
- **Missing lines**: a PO line that's authorized but never appears on the invoice is surfaced
  as a note (likely a partial/split shipment) rather than a hard exception, since it isn't an
  overbilling risk.
- **Extraction scope**: the primary extractor targets ruled/tabular PDF invoices (very common
  for AP automation and what the sample represents). Scanned images are explicitly handled
  via the LLM fallback path rather than OCR, to keep the core deterministic path fast and
  free of OCR noise for the common case.

## One design tradeoff (see also the demo video)

Exception detection is 100% rule-based rather than asking an LLM "does this invoice look
right?". This trades a bit of flexibility (a fuzzier LLM-only approach might catch exotic
mismatches this doesn't) for **auditability and reproducibility** — every flag traces to an
exact number and threshold, which is what an AP team actually needs to trust before it will
let an AI Employee touch real invoices. The LLM is only used for extraction fallback and for
phrasing answers, always constrained to facts the deterministic layer already computed.
