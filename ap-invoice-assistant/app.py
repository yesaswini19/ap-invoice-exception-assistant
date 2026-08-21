import json
import tempfile
import os

import streamlit as st

from extraction import extract_invoice
from comparison import compare_invoice_to_po
from chat import answer_query


# Get the folder where this app.py file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")


st.set_page_config(
    page_title="AP Invoice Exception Assistant",
    layout="wide"
)

st.title("📄 AP Invoice Exception Assistant")
st.caption(
    "Upload a vendor invoice + PO, review flagged exceptions, "
    "and ask the assistant why each one was raised."
)


# -----------------------------
# 1. Inputs
# -----------------------------
with st.sidebar:
    st.header("1. Inputs")

    invoice_file = st.file_uploader(
        "Vendor invoice (PDF)",
        type=["pdf"]
    )

    st.markdown("**Purchase order**")

    po_source = st.radio(
        "PO source",
        ["Use sample PO", "Upload PO JSON"],
        label_visibility="collapsed"
    )

    if po_source == "Upload PO JSON":
        po_file = st.file_uploader(
            "PO JSON",
            type=["json"]
        )

        po = json.load(po_file) if po_file else None

    else:
        # Use a path relative to app.py
        po_path = os.path.join(
            SAMPLE_DATA_DIR,
            "sample_po.json"
        )

        with open(po_path, "r") as f:
            po = json.load(f)

        st.json(po, expanded=False)

    st.divider()

    use_sample_invoice = st.button(
        "Use bundled sample invoice instead"
    )


# -----------------------------
# Session state
# -----------------------------
if "comparison" not in st.session_state:
    st.session_state.comparison = None
    st.session_state.invoice_data = None
    st.session_state.chat_history = []


# -----------------------------
# Invoice file handling
# -----------------------------
pdf_path = None

if invoice_file is not None:

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )

    tmp.write(invoice_file.read())
    tmp.close()

    pdf_path = tmp.name

elif use_sample_invoice:

    # Use a path relative to app.py
    pdf_path = os.path.join(
        SAMPLE_DATA_DIR,
        "invoice.pdf"
    )


# -----------------------------
# Extraction + Comparison
# -----------------------------
if pdf_path and po:

    with st.spinner(
        "Extracting line items and comparing to PO..."
    ):

        try:

            invoice_data = extract_invoice(pdf_path)

            comparison = compare_invoice_to_po(
                invoice_data,
                po
            )

            st.session_state.invoice_data = invoice_data
            st.session_state.comparison = comparison
            st.session_state.chat_history = []

        except Exception as e:

            st.error(
                f"Extraction/comparison failed: {e}"
            )


# -----------------------------
# Retrieve session data
# -----------------------------
invoice_data = st.session_state.invoice_data
comparison = st.session_state.comparison


# -----------------------------
# Display results
# -----------------------------
if invoice_data and comparison:

    st.header("2. Extracted Invoice")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Invoice #",
        invoice_data.get("invoice_number") or "—"
    )

    c2.metric(
        "PO Reference",
        invoice_data.get("po_reference") or "—"
    )

    c3.metric(
        "Extraction method",
        invoice_data.get(
            "extraction_method",
            "—"
        )
    )


    # -----------------------------
    # PO reference mismatch
    # -----------------------------
    if comparison["po_reference_mismatch"]:

        st.warning(
            f"⚠️ Invoice references PO "
            f"'{invoice_data.get('po_reference')}' "
            f"which does not match the loaded PO "
            f"'{po['po_number']}'."
        )


    # -----------------------------
    # Line-level comparison
    # -----------------------------
    st.header("3. Line-Level Comparison")

    s = comparison["summary"]

    st.info(
        f"**{s['flagged_lines']} of "
        f"{s['total_lines']} lines flagged** · "
        f"{s['clean_lines']} clean · "
        f"{s['missing_from_invoice']} PO line(s) "
        f"never invoiced"
    )


    for lr in comparison["line_results"]:

        flagged = bool(lr["exceptions"])

        icon = "🔴" if flagged else "🟢"

        with st.expander(
            f"{icon} Line {lr['line_no']} — "
            f"{lr['sku']} — "
            f"{lr['description']}",
            expanded=flagged
        ):

            cols = st.columns(2)

            with cols[0]:

                st.markdown("**Invoice**")

                st.json(
                    lr["invoice"],
                    expanded=False
                )

            with cols[1]:

                st.markdown("**PO**")

                st.json(
                    lr["po"] or {
                        "note": "no matching PO line found"
                    },
                    expanded=False
                )

            if flagged:

                for exc in lr["exceptions"]:

                    st.markdown(
                        f"- **[{exc['type']}]** "
                        f"{exc['detail']}"
                    )

            else:

                st.success(
                    "Matches PO within tolerance."
                )


    # -----------------------------
    # Missing PO lines
    # -----------------------------
    if comparison["missing_po_lines"]:

        st.subheader("PO lines never invoiced")

        for l in comparison["missing_po_lines"]:

            st.markdown(
                f"- {l['sku']} — "
                f"{l['description']} "
                f"(qty {l['qty']} @ {l['unit_price']})"
            )


    # -----------------------------
    # Chat assistant
    # -----------------------------
    st.header("4. Ask the Assistant")

    st.caption(
        'e.g. "Why was line 1 flagged?" or '
        f'"Why was invoice '
        f'{invoice_data.get("invoice_number")} flagged?"'
    )


    # Display previous chat messages
    for role, msg in st.session_state.chat_history:

        with st.chat_message(role):

            st.markdown(msg)


    query = st.chat_input(
        "Ask about a flagged line..."
    )


    if query:

        st.session_state.chat_history.append(
            ("user", query)
        )

        with st.chat_message("user"):

            st.markdown(query)


        answer = answer_query(
            query,
            comparison
        )


        st.session_state.chat_history.append(
            ("assistant", answer)
        )


        with st.chat_message("assistant"):

            st.markdown(answer)


else:

    st.info(
        "Upload an invoice PDF "
        "(or click 'Use bundled sample invoice') "
        "and select a PO to get started."
    )