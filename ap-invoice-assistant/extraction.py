
import json
import re
import os
import pdfplumber

INVOICE_SCHEMA_HINT = """
Return ONLY valid JSON (no markdown, no commentary) matching this shape:
{
  "invoice_number": "string",
  "po_reference": "string",
  "invoice_date": "string",
  "lines": [
    {"line_no": int, "sku": "string", "description": "string", "qty": number,
     "unit_price": number, "line_total": number, "tax": number}
  ]
}
"""


def _parse_header_text(full_text: str) -> dict:
    header = {"invoice_number": None, "po_reference": None, "invoice_date": None}
    m = re.search(r"Invoice\s*#\s*:?\s*([A-Za-z0-9\-]+)", full_text, re.I)
    if m:
        header["invoice_number"] = m.group(1)
    m = re.search(r"PO\s*Reference\s*:?\s*([A-Za-z0-9\-]+)", full_text, re.I)
    if m:
        header["po_reference"] = m.group(1)
    m = re.search(r"Invoice\s*Date\s*:?\s*([0-9\-/]+)", full_text, re.I)
    if m:
        header["invoice_date"] = m.group(1)
    return header


def _extract_via_table(pdf_path: str) -> dict | None:
    """Deterministic path: works when the PDF has a real ruled table (our sample invoice)."""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        header = _parse_header_text(full_text)

        lines = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                header_row = [c.strip().lower() if c else "" for c in table[0]]
                if not any("sku" in c or "line" in c for c in header_row):
                    continue  # not the line-items table
                col_idx = {name: i for i, name in enumerate(header_row)}

                def get(row, key, default=""):
                    for k in col_idx:
                        if key in k:
                            idx = col_idx[k]
                            return row[idx] if idx < len(row) else default
                    return default

                for row in table[1:]:
                    if not row or not any(row):
                        continue
                    try:
                        lines.append({
                            "line_no": int(re.sub(r"[^\d]", "", str(get(row, "line") or "0")) or 0),
                            "sku": str(get(row, "sku")).strip(),
                            "description": str(get(row, "description")).strip(),
                            "qty": float(re.sub(r"[^\d.]", "", str(get(row, "qty")) or "0") or 0),
                            "unit_price": float(re.sub(r"[^\d.]", "", str(get(row, "unit price")) or "0") or 0),
                            "line_total": float(re.sub(r"[^\d.]", "", str(get(row, "line total")) or "0") or 0),
                            "tax": float(re.sub(r"[^\d.]", "", str(get(row, "tax")) or "0") or 0),
                        })
                    except (ValueError, TypeError):
                        continue
        if not lines:
            return None
        return {**header, "lines": lines}


def _extract_via_llm(pdf_path: str) -> dict:
    """Fallback path for messy/scanned invoices: raw text -> Claude -> strict JSON."""
    import anthropic

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    client = anthropic.Anthropic()  # expects ANTHROPIC_API_KEY in env
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": f"Extract structured data from this invoice text.\n\n{INVOICE_SCHEMA_HINT}\n\nInvoice text:\n{full_text}",
        }],
    )
    text = resp.content[0].text.strip()
    text = re.sub(r"^```json|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def extract_invoice(pdf_path: str) -> dict:
    """
    Public entry point. Returns:
    {
      "invoice_number": str, "po_reference": str, "invoice_date": str,
      "lines": [ {line_no, sku, description, qty, unit_price, line_total, tax}, ... ],
      "extraction_method": "table" | "llm"
    }
    """
    result = _extract_via_table(pdf_path)
    if result is not None:
        result["extraction_method"] = "table"
        return result

    if os.environ.get("ANTHROPIC_API_KEY"):
        result = _extract_via_llm(pdf_path)
        result["extraction_method"] = "llm"
        return result

    raise RuntimeError(
        "Could not find a ruled table in the PDF, and no ANTHROPIC_API_KEY is set "
        "for the LLM fallback extractor. Set the env var to handle scanned/irregular invoices."
    )
