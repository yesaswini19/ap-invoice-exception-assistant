"""
comparison.py
Deterministic matching + exception detection between an extracted invoice
and a purchase order. No LLM involved here on purpose — the flags must be
reproducible and auditable, not a black-box model opinion.
"""

PRICE_TOLERANCE_PCT = 0.02   # 2% price variance allowed
QTY_TOLERANCE_UNITS = 0      # exact qty match required
TAX_TOLERANCE_PCT = 0.02     # 2% tax variance allowed


def _find_po_line(po: dict, sku: str) -> dict | None:
    for line in po["lines"]:
        if line["sku"].strip().upper() == (sku or "").strip().upper():
            return line
    return None


def compare_invoice_to_po(invoice: dict, po: dict) -> dict:
    """
    Returns:
    {
      "po_reference_mismatch": bool,
      "line_results": [
        {
          "line_no", "sku", "description",
          "invoice": {...}, "po": {...} | None,
          "exceptions": [ {"type": "PRICE"|"QTY"|"TAX"|"MISSING_ON_INVOICE"|"UNKNOWN_SKU",
                            "detail": str, "invoice_value": ..., "po_value": ...} ]
        }, ...
      ],
      "missing_po_lines": [ ...PO lines never invoiced... ],
      "summary": {"total_lines": int, "clean_lines": int, "flagged_lines": int}
    }
    """
    result = {
        "po_reference_mismatch": invoice.get("po_reference", "").strip() != po["po_number"].strip(),
        "line_results": [],
        "missing_po_lines": [],
    }

    matched_po_skus = set()

    for inv_line in invoice["lines"]:
        po_line = _find_po_line(po, inv_line["sku"])
        exceptions = []

        if po_line is None:
            exceptions.append({
                "type": "UNKNOWN_SKU",
                "detail": f"SKU {inv_line['sku']} does not appear on PO {po['po_number']}.",
                "invoice_value": inv_line["sku"],
                "po_value": None,
            })
        else:
            matched_po_skus.add(po_line["sku"])

            # Quantity check
            qty_diff = abs(inv_line["qty"] - po_line["qty"])
            if qty_diff > QTY_TOLERANCE_UNITS:
                exceptions.append({
                    "type": "QTY",
                    "detail": (f"Invoice bills {inv_line['qty']:.0f} units but PO {po['po_number']} "
                               f"line {po_line['line_no']} authorizes {po_line['qty']:.0f} units "
                               f"(difference of {qty_diff:.0f})."),
                    "invoice_value": inv_line["qty"],
                    "po_value": po_line["qty"],
                })

            # Unit price check
            price_diff_pct = abs(inv_line["unit_price"] - po_line["unit_price"]) / po_line["unit_price"]
            if price_diff_pct > PRICE_TOLERANCE_PCT:
                exceptions.append({
                    "type": "PRICE",
                    "detail": (f"Invoice unit price is {inv_line['unit_price']:.2f} versus the PO price of "
                               f"{po_line['unit_price']:.2f} on line {po_line['line_no']} "
                               f"({price_diff_pct*100:.1f}% variance, tolerance is {PRICE_TOLERANCE_PCT*100:.0f}%)."),
                    "invoice_value": inv_line["unit_price"],
                    "po_value": po_line["unit_price"],
                })

            # Tax check: expected tax = line_total * po tax_rate
            expected_line_total = po_line["qty"] * po_line["unit_price"]
            expected_tax = round(inv_line["line_total"] * po.get("tax_rate", 0), 2)
            tax_diff_pct = (abs(inv_line["tax"] - expected_tax) / expected_tax) if expected_tax else 0
            if tax_diff_pct > TAX_TOLERANCE_PCT:
                exceptions.append({
                    "type": "TAX",
                    "detail": (f"Invoice charges {inv_line['tax']:.2f} tax on this line, but at the PO's "
                               f"tax rate of {po.get('tax_rate', 0)*100:.0f}% on a line total of "
                               f"{inv_line['line_total']:.2f}, expected tax is {expected_tax:.2f} "
                               f"({tax_diff_pct*100:.1f}% variance)."),
                    "invoice_value": inv_line["tax"],
                    "po_value": expected_tax,
                })

        result["line_results"].append({
            "line_no": inv_line["line_no"],
            "sku": inv_line["sku"],
            "description": inv_line["description"],
            "invoice": inv_line,
            "po": po_line,
            "exceptions": exceptions,
        })

    # PO lines that were never invoiced at all
    for po_line in po["lines"]:
        if po_line["sku"] not in matched_po_skus:
            result["missing_po_lines"].append(po_line)

    total = len(result["line_results"])
    flagged = sum(1 for lr in result["line_results"] if lr["exceptions"])
    result["summary"] = {
        "total_lines": total,
        "clean_lines": total - flagged,
        "flagged_lines": flagged,
        "missing_from_invoice": len(result["missing_po_lines"]),
    }
    return result
