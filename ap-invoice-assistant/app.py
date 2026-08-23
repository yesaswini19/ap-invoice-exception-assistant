import json
import tempfile
import os

import streamlit as st

from extraction import extract_invoice
from comparison import compare_invoice_to_po
from chat import answer_query

# Anchor all sample-data paths to this script's own folder, not the
# terminal's current working directory — this is what makes "Use bundled
# sample invoice instead" and "Use sample PO" work no matter where you run
# `streamlit run app.py` from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")

st.set_page_config(page_title="AP Invoice Exception Assistant", layout="wide", page_icon="📄")


PRIMARY_NAVY = "#0F1F3D"
ACCENT_BLUE = "#2563EB"
BG = "#F5F7FA"
CARD = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#1E293B"
MUTED = "#64748B"
SUCCESS = "#15803D"
SUCCESS_BG = "#F0FDF4"
SUCCESS_BORDER = "#BBF7D0"
DANGER = "#B91C1C"
DANGER_BG = "#FEF2F2"
DANGER_BORDER = "#FECACA"
INFO_BG = "#EFF6FF"
INFO_BORDER = "#BFDBFE"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

.stApp {{
    background: {BG};
}}

#MainMenu, footer, header[data-testid="stHeader"] {{
    visibility: hidden;
    height: 0;
}}

.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}}

/* ---------- App header ---------- */
.app-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: {PRIMARY_NAVY};
    border-radius: 14px;
    padding: 22px 28px;
    margin-bottom: 24px;
    box-shadow: 0 4px 14px rgba(15, 31, 61, 0.18);
}}
.app-header-left {{ display: flex; align-items: center; gap: 14px; }}
.app-header-logo {{
    width: 42px; height: 42px;
    background: {ACCENT_BLUE};
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
}}
.app-header-title {{ color: #FFFFFF; font-size: 20px; font-weight: 700; margin: 0; letter-spacing: -0.01em; }}
.app-header-subtitle {{ color: #94A3B8; font-size: 13px; margin: 2px 0 0 0; font-weight: 400; }}
.app-status-pill {{
    display: flex; align-items: center; gap: 7px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.14);
    color: #E2E8F0;
    padding: 7px 14px;
    border-radius: 20px;
    font-size: 12.5px;
    font-weight: 500;
    white-space: nowrap;
}}
.app-status-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: #22C55E;
    box-shadow: 0 0 0 3px rgba(34,197,94,0.25);
}}

/* ---------- Section headings ---------- */
.section-title {{
    font-size: 15.5px;
    font-weight: 700;
    color: {TEXT};
    margin: 30px 0 3px 0;
    display: flex; align-items: center; gap: 8px;
}}
.section-subtitle {{
    font-size: 13px;
    color: {MUTED};
    margin: 0 0 14px 0;
}}

/* ---------- Generic card ---------- */
.card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}

/* Streamlit bordered containers -> card look */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 12px !important;
    border: 1px solid {BORDER} !important;
    background: {CARD} !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}

.upload-slot-label {{
    display: flex; align-items: center; gap: 8px;
    font-weight: 600; font-size: 13.5px; color: {TEXT};
    margin-bottom: 2px;
}}
.upload-slot-icon {{
    width: 26px; height: 26px; border-radius: 7px;
    background: {INFO_BG}; color: {ACCENT_BLUE};
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; flex-shrink: 0;
}}
.upload-slot-caption {{ font-size: 12px; color: {MUTED}; margin: 0 0 10px 34px; }}
.file-status-chip {{
    display: inline-flex; align-items: center; gap: 6px;
    background: {SUCCESS_BG}; color: {SUCCESS};
    border: 1px solid {SUCCESS_BORDER};
    padding: 4px 10px; border-radius: 6px;
    font-size: 12px; font-weight: 600; margin-top: 8px;
}}

/* ---------- Metric cards ---------- */
.metric-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}
.metric-label {{ font-size: 12px; color: {MUTED}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 6px 0; }}
.metric-value {{ font-size: 22px; font-weight: 700; color: {TEXT}; margin: 0; }}
.metric-value.ok {{ color: {SUCCESS}; }}
.metric-value.warn {{ color: {DANGER}; }}

/* ---------- Exception line cards ---------- */
.line-card {{
    border-radius: 12px;
    border: 1px solid {BORDER};
    margin-bottom: 12px;
    overflow: hidden;
}}
.line-card-header {{
    padding: 13px 18px;
    font-weight: 600; font-size: 13.5px;
    display: flex; align-items: center; gap: 9px;
}}
.line-card-header.flagged {{ background: {DANGER_BG}; color: {DANGER}; border-bottom: 1px solid {DANGER_BORDER}; }}
.line-card-header.clean {{ background: {SUCCESS_BG}; color: {SUCCESS}; border-bottom: 1px solid {SUCCESS_BORDER}; }}

.exception-row {{
    border-left: 3px solid {DANGER};
    background: #FFFBFB;
    padding: 10px 14px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    color: {TEXT};
}}
.exception-tag {{
    display: inline-block;
    background: {DANGER};
    color: white;
    font-size: 10.5px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 5px;
    margin-right: 8px;
    letter-spacing: 0.03em;
}}

.field-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.field-table th {{
    text-align: left; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.03em; color: {MUTED}; font-weight: 600;
    padding: 4px 8px 6px 8px; border-bottom: 1px solid {BORDER};
}}
.field-table td {{ padding: 5px 8px; border-bottom: 1px solid #F1F5F9; color: {TEXT}; }}

/* ---------- Buttons ---------- */
.stButton > button {{
    background: {ACCENT_BLUE};
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13.5px;
    padding: 8px 16px;
    box-shadow: 0 1px 2px rgba(37,99,235,0.25);
    transition: background 0.15s ease;
}}
.stButton > button:hover {{ background: #1D4ED8; color: white; }}

/* ---------- File uploader ---------- */
div[data-testid="stFileUploaderDropzone"] {{
    background: #FAFBFD;
    border: 1.5px dashed {BORDER};
    border-radius: 10px;
}}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {{
    background: {PRIMARY_NAVY};
}}
section[data-testid="stSidebar"] * {{ color: #E2E8F0 !important; }}
section[data-testid="stSidebar"] .stRadio label {{ color: #E2E8F0 !important; }}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background: #FFFFFF !important;
    border-radius: 10px !important;
    padding: 4px !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {{
    background: #FFFFFF !important;
    border: 1.5px dashed #CBD5E1 !important;
    border-radius: 10px !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] p,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] div {{
    color: {TEXT} !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] small {{
    color: {MUTED} !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] svg {{
    fill: {ACCENT_BLUE} !important;
    color: {ACCENT_BLUE} !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button[kind="secondary"] {{
    background: {ACCENT_BLUE} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button span,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button p,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button div {{
    color: #FFFFFF !important;
}}

section[data-testid="stSidebar"] [data-testid="stJson"] {{
    background: #FFFFFF !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    padding: 8px !important;
}}
section[data-testid="stSidebar"] [data-testid="stJson"] * {{
    color: {TEXT} !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12); }}
.sidebar-brand {{ font-size: 15px; font-weight: 700; color: white !important; margin-bottom: 2px; }}
.sidebar-brand-sub {{ font-size: 11.5px; color: #94A3B8 !important; margin-bottom: 18px; }}

/* ---------- Chat ---------- */
div[data-testid="stChatMessage"] {{
    border-radius: 12px;
    border: 1px solid {BORDER};
    background: {CARD};
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
}}
.chip-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 6px 0 16px 0; }}

/* ---------- Alerts ---------- */
div[data-testid="stAlert"] {{ border-radius: 10px; }}

/* ---------- Expander ---------- */
details {{ border-radius: 10px !important; border: 1px solid {BORDER} !important; }}
summary {{ font-weight: 600 !important; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="app-header">
    <div class="app-header-left">
        <div class="app-header-logo">📄</div>
        <div>
            <p class="app-header-title">AP Invoice Exception Assistant</p>
            <p class="app-header-subtitle">Automated invoice validation and exception analysis</p>
        </div>
    </div>
    <div class="app-status-pill"><span class="app-status-dot"></span>System Ready</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar (same inputs/logic as before, restyled)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="sidebar-brand">AP Exception Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-brand-sub">Document inputs</p>', unsafe_allow_html=True)

    st.markdown("**Vendor invoice (PDF)**")
    invoice_file = st.file_uploader("Vendor invoice (PDF)", type=["pdf"], label_visibility="collapsed")

    st.markdown("**Purchase order**")
    po_source = st.radio("PO source", ["Use sample PO", "Upload PO JSON"], label_visibility="collapsed")
    if po_source == "Upload PO JSON":
        po_file = st.file_uploader("PO JSON", type=["json"], label_visibility="collapsed")
        po = json.load(po_file) if po_file else None
    else:
        po_path = os.path.join(SAMPLE_DATA_DIR, "sample_po.json")
        with open(po_path) as f:
            po = json.load(f)
        st.json(po, expanded=False)

    st.divider()
    use_sample_invoice = st.button("Use bundled sample invoice instead")

if "comparison" not in st.session_state:
    st.session_state.comparison = None
    st.session_state.invoice_data = None
    st.session_state.chat_history = []
    st.session_state.po = None

pdf_path = None
if invoice_file is not None:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(invoice_file.read())
    tmp.close()
    pdf_path = tmp.name
elif use_sample_invoice:
    pdf_path = os.path.join(SAMPLE_DATA_DIR, "invoice.pdf")

# ---------------------------------------------------------------------------
# Upload Documents card (visual status summary; sidebar widgets above are
# still the actual inputs used for pdf_path / po)
# ---------------------------------------------------------------------------
st.markdown('<p class="section-title">📥 Upload Documents</p>', unsafe_allow_html=True)
st.markdown('<p class="section-subtitle">Upload a vendor invoice and purchase order to begin validation.</p>', unsafe_allow_html=True)

uc1, uc2 = st.columns(2)
with uc1:
    with st.container(border=True):
        st.markdown("""
        <div class="upload-slot-label"><div class="upload-slot-icon">📄</div>Vendor Invoice</div>
        <p class="upload-slot-caption">PDF uploaded via sidebar</p>
        """, unsafe_allow_html=True)
        if invoice_file is not None:
            st.markdown(f'<span class="file-status-chip">✓ {invoice_file.name}</span>', unsafe_allow_html=True)
        elif use_sample_invoice or (pdf_path == os.path.join(SAMPLE_DATA_DIR, "invoice.pdf")):
            st.markdown('<span class="file-status-chip">✓ sample invoice.pdf</span>', unsafe_allow_html=True)
        else:
            st.caption("No invoice uploaded yet — use the sidebar, or click *Use bundled sample invoice*.")
with uc2:
    with st.container(border=True):
        st.markdown("""
        <div class="upload-slot-label"><div class="upload-slot-icon">🧾</div>Purchase Order</div>
        <p class="upload-slot-caption">Source selected via sidebar</p>
        """, unsafe_allow_html=True)
        if po:
            label = po.get("po_number", "PO loaded")
            st.markdown(f'<span class="file-status-chip">✓ {label}</span>', unsafe_allow_html=True)
        else:
            st.caption("No PO loaded yet — select or upload one in the sidebar.")

if pdf_path and po:
    with st.spinner("Extracting line items and comparing to PO..."):
        try:
            invoice_data = extract_invoice(pdf_path)
            comparison = compare_invoice_to_po(invoice_data, po)
            st.session_state.invoice_data = invoice_data
            st.session_state.comparison = comparison
            st.session_state.chat_history = []
            st.session_state.po = po
        except Exception as e:
            st.error(f"Extraction/comparison failed: {e}")

invoice_data = st.session_state.invoice_data
comparison = st.session_state.comparison
po = st.session_state.po

if invoice_data and comparison:
    # -----------------------------------------------------------------
    # Summary cards
    # -----------------------------------------------------------------
    s = comparison["summary"]
    invoice_total = sum(l["line_total"] for l in invoice_data["lines"])
    po_total = sum(l["qty"] * l["unit_price"] for l in po["lines"])
    status_ok = s["flagged_lines"] == 0 and not comparison["po_reference_mismatch"]

    st.markdown('<p class="section-title">📊 Validation Summary</p>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Invoice Status</p>
            <p class="metric-value {'ok' if status_ok else 'warn'}">{'✓ Valid' if status_ok else '⚠ Exceptions'}</p>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Exceptions Found</p>
            <p class="metric-value {'ok' if s['flagged_lines'] == 0 else 'warn'}">{s['flagged_lines']} / {s['total_lines']}</p>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">Invoice Total</p>
            <p class="metric-value">${invoice_total:,.2f}</p>
        </div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">PO Total</p>
            <p class="metric-value">${po_total:,.2f}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <p class="section-subtitle" style="margin-top:12px;">
        Invoice&nbsp;#: <b>{invoice_data.get("invoice_number") or "—"}</b> ·
        PO Reference: <b>{invoice_data.get("po_reference") or "—"}</b> ·
        Extraction method: <b>{invoice_data.get("extraction_method", "—")}</b>
    </p>
    """, unsafe_allow_html=True)

    if comparison["po_reference_mismatch"]:
        st.warning(f"⚠️ Invoice references PO '{invoice_data.get('po_reference')}' which does not match the loaded PO '{po['po_number']}'.")

    # -----------------------------------------------------------------
    # Invoice Exceptions
    # -----------------------------------------------------------------
    st.markdown('<p class="section-title">⚠️ Invoice Exceptions</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Line-by-line comparison against the purchase order.</p>', unsafe_allow_html=True)

    if s["flagged_lines"] == 0:
        st.markdown(f"""
        <div class="card" style="border-color:{SUCCESS_BORDER}; background:{SUCCESS_BG};">
            <b style="color:{SUCCESS};">✓ No Exceptions Found</b>
            <p style="margin:4px 0 0 0; color:{TEXT}; font-size:13.5px;">The invoice matches the purchase order.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<p class="section-subtitle" style="margin-top:-6px;">{s["flagged_lines"]} of {s["total_lines"]} lines flagged · {s["clean_lines"]} clean · {s["missing_from_invoice"]} PO line(s) never invoiced</p>', unsafe_allow_html=True)

    for lr in comparison["line_results"]:
        flagged = bool(lr["exceptions"])
        state_class = "flagged" if flagged else "clean"
        icon = "⚠" if flagged else "✓"

        st.markdown(f"""
        <div class="line-card">
            <div class="line-card-header {state_class}">{icon} Line {lr['line_no']} — {lr['sku']} — {lr['description']}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("View field-level comparison", expanded=flagged):
            inv = lr["invoice"]
            po_line = lr["po"]
            cols = st.columns(2)
            with cols[0]:
                st.markdown(f"""
                <table class="field-table">
                <tr><th colspan="2">Invoice</th></tr>
                <tr><td>Qty</td><td>{inv.get('qty', '—')}</td></tr>
                <tr><td>Unit Price</td><td>{inv.get('unit_price', '—')}</td></tr>
                <tr><td>Line Total</td><td>{inv.get('line_total', '—')}</td></tr>
                <tr><td>Tax</td><td>{inv.get('tax', '—')}</td></tr>
                </table>
                """, unsafe_allow_html=True)
            with cols[1]:
                if po_line:
                    st.markdown(f"""
                    <table class="field-table">
                    <tr><th colspan="2">Purchase Order</th></tr>
                    <tr><td>Qty</td><td>{po_line.get('qty', '—')}</td></tr>
                    <tr><td>Unit Price</td><td>{po_line.get('unit_price', '—')}</td></tr>
                    <tr><td colspan="2" style="color:{MUTED};">Line {po_line.get('line_no','—')}</td></tr>
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f'<p style="color:{MUTED}; font-size:13px;">No matching PO line found.</p>', unsafe_allow_html=True)

            if flagged:
                for exc in lr["exceptions"]:
                    st.markdown(f"""
                    <div class="exception-row">
                        <span class="exception-tag">{exc['type']}</span>{exc['detail']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f'<p style="color:{SUCCESS}; font-size:13px; font-weight:600;">Matches PO within tolerance.</p>', unsafe_allow_html=True)

    if comparison["missing_po_lines"]:
        st.markdown('<p class="section-title" style="margin-top:22px;">📋 PO Lines Never Invoiced</p>', unsafe_allow_html=True)
        rows = "".join(
            f"<tr><td>{l['sku']}</td><td>{l['description']}</td><td>{l['qty']}</td><td>{l['unit_price']}</td></tr>"
            for l in comparison["missing_po_lines"]
        )
        st.markdown(f"""
        <div class="card">
        <table class="field-table" style="width:100%;">
        <tr><th>SKU</th><th>Description</th><th>Qty</th><th>Unit Price</th></tr>
        {rows}
        </table>
        </div>
        """, unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # Exception Assistant (chat) — same answer_query() call as before
    # -----------------------------------------------------------------
    st.markdown('<p class="section-title" style="margin-top:28px;">💬 Exception Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-subtitle">Ask why an invoice was flagged.</p>', unsafe_allow_html=True)

    suggested = [
        "Why was this invoice flagged?",
        "Explain the price mismatch",
        "Explain all exceptions",
    ]
    chip_cols = st.columns(len(suggested))
    clicked_suggestion = None
    for col, label in zip(chip_cols, suggested):
        with col:
            if st.button(label, key=f"chip_{label}", use_container_width=True):
                clicked_suggestion = label

    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    query = st.chat_input("Ask about a flagged line...")
    final_query = query or clicked_suggestion
    if final_query:
        st.session_state.chat_history.append(("user", final_query))
        with st.chat_message("user"):
            st.markdown(final_query)
        answer = answer_query(final_query, comparison)
        st.session_state.chat_history.append(("assistant", answer))
        with st.chat_message("assistant"):
            st.markdown(answer)
else:
    st.markdown(f"""
    <div class="card" style="text-align:center; padding:40px 20px; margin-top:10px;">
        <p style="font-size:15px; font-weight:600; color:{TEXT}; margin-bottom:4px;">No document loaded yet</p>
        <p style="font-size:13.5px; color:{MUTED}; margin:0;">Upload an invoice PDF (or click "Use bundled sample invoice") and select a PO in the sidebar to begin.</p>
    </div>
    """, unsafe_allow_html=True)