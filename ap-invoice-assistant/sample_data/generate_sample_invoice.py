"""
Generates a synthetic vendor invoice PDF (invoice.pdf) that intentionally
diverges from sample_po.json in a few places, so the assistant has real
exceptions to flag during the demo.

Run:  python sample_data/generate_sample_invoice.py
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os

OUT_PATH = os.path.join(os.path.dirname(__file__), "invoice.pdf")

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(OUT_PATH, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)

elements = []
elements.append(Paragraph("<b>Northwind Office Supplies Ltd.</b>", styles["Title"]))
elements.append(Paragraph("Invoice #: INV-8842", styles["Normal"]))
elements.append(Paragraph("PO Reference: PO-4521", styles["Normal"]))
elements.append(Paragraph("Invoice Date: 2026-08-15", styles["Normal"]))
elements.append(Spacer(1, 10 * mm))

# Header row + line items.
# Deliberate mismatches vs sample_po.json:
#  - NB-1001: qty invoiced 55 vs PO 50            (QTY mismatch)
#  - PN-2003: unit price 8.75 vs PO 8.00           (PRICE mismatch)
#  - MN-3300: matches PO exactly                   (no mismatch, control line)
#  - CH-4410: qty invoiced 5, unit price 210.00, but tax charged is wrong (TAX mismatch)
#  - DK-5520: line missing from invoice entirely    (MISSING line -> under-billed, still flag for review)

data = [
    ["Line", "SKU", "Description", "Qty", "Unit Price", "Line Total", "Tax"],
    ["1", "NB-1001", "A4 Notebooks (Pack of 10)", "55", "4.50", "247.50", "19.80"],
    ["2", "PN-2003", "Blue Ballpoint Pens (Box of 50)", "20", "8.75", "175.00", "14.00"],
    ["3", "MN-3300", "27-inch LED Monitor", "10", "145.00", "1450.00", "116.00"],
    ["4", "CH-4410", "Ergonomic Office Chair", "5", "210.00", "1050.00", "42.00"],
]

table = Table(data, colWidths=[12*mm, 22*mm, 62*mm, 14*mm, 24*mm, 26*mm, 18*mm])
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
]))
elements.append(table)
elements.append(Spacer(1, 8 * mm))
elements.append(Paragraph("Subtotal: 2922.50   |   Tax Total: 191.80   |   Grand Total: 3114.30", styles["Normal"]))
elements.append(Spacer(1, 4 * mm))
elements.append(Paragraph("Note: Standing Desk Converter (DK-5520) shipped separately, invoice to follow.", styles["Normal"]))

doc.build(elements)
print(f"Sample invoice written to {OUT_PATH}")
