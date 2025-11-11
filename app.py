
# app.py
import streamlit as st
import pandas as pd
import io, re
import pdfplumber
from parsers.sbi import parse_sbi_pdf
from parsers.axis import parse_axis_pdf
from parsers.kotak import parse_kotak_pdf
from parsers.idfc import parse_idfc_pdf
from parsers.generic import parse_generic_pdf

st.set_page_config(page_title="Credit Card EXTRA — Simple", layout="wide")

st.title("💳 EXTRA Paid — Simple Analyzer")
st.caption("Select your bank ➜ Upload ONE PDF ➜ See how much extra you paid (fees, interest, GST, etc.).")

bank = st.selectbox("Select Bank", ["SBI", "Axis Bank", "Kotak", "IDFC FIRST"])
pdf = st.file_uploader("Upload ONE statement PDF", type=["pdf"], accept_multiple_files=False)

# Keyword sets
EXTRA_KEYS = {
    "Late/Overlimit Fee": ["LATE FEE","LATE PAYMENT","PAST DUE","OVERLIMIT"],
    "Interest/Finance Charge": ["INTEREST","FINANCE CHARGE","RETAIL INTEREST","CASH INTEREST"],
    "GST on Charges": ["GST","CGST","SGST","IGST","INTEGRATED GST","CENTRAL GST","STATE GST"],
    "Annual/Joining/Renewal Fee": ["ANNUAL FEE","JOINING FEE","RENEWAL FEE","MEMBERSHIP FEE"],
    "Forex Markup Fee": ["MARKUP","CROSS CURRENCY","INTERNATIONAL TRANSACTION FEE"]
}

def tag_extra_type(desc: str) -> str:
    D = (desc or "").upper()
    for label, keys in EXTRA_KEYS.items():
        if any(k in D for k in keys):
            return label
    return ""

def compute_summary(df: pd.DataFrame):
    if df.empty:
        return {
            "purchase_total": 0.0,
            "extra_total": 0.0,
            "extra_pct": 0.0,
            "extra_breakdown": pd.DataFrame(columns=["extra_type","total_extra"]),
            "transactions": df
        }
    # Define purchases vs extra
    df["extra_type"] = df["description"].apply(tag_extra_type)
    df["is_purchase"] = df["extra_type"].eq("")
    # Standard credit card convention: purchases are negative (DR)
    purchases = df[df["is_purchase"] & df["amount"].notna()]
    purchase_total = float((-purchases["amount"]).clip(lower=0).sum())  # make positive

    extra = df[df["extra_type"]!="" & df["amount"].notna()]
    extra_total = float((-extra["amount"]).clip(lower=0).sum())

    extra_breakdown = extra.groupby("extra_type")["amount"].apply(lambda s: (-s).clip(lower=0).sum()).reset_index()
    extra_breakdown = extra_breakdown.rename(columns={"amount":"total_extra"}).sort_values("total_extra", ascending=False)

    extra_pct = (extra_total / purchase_total * 100.0) if purchase_total > 0 else 0.0

    return {
        "purchase_total": purchase_total,
        "extra_total": extra_total,
        "extra_pct": extra_pct,
        "extra_breakdown": extra_breakdown,
        "transactions": df
    }

def export_excel(summary: dict) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Summary sheet
        pd.DataFrame([{
            "Purchase Total (₹)": summary["purchase_total"],
            "EXTRA Total (₹)": summary["extra_total"],
            "EXTRA %": summary["extra_pct"]
        }]).to_excel(writer, index=False, sheet_name="Summary")

        summary["extra_breakdown"].to_excel(writer, index=False, sheet_name="Extra_Breakdown")
        summary["transactions"].to_excel(writer, index=False, sheet_name="Transactions")
    output.seek(0)
    return output.read()

def read_pdf_text(file_bytes: bytes)->str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf_doc:
        pages = [(p.extract_text() or "") for p in pdf_doc.pages]
    return "\n".join(pages)

def parse_pdf_by_bank(bank_name: str, text: str) -> pd.DataFrame:
    if bank_name == "SBI":
        df = parse_sbi_pdf(text)
    elif bank_name == "Axis Bank":
        df = parse_axis_pdf(text)
    elif bank_name == "Kotak":
        df = parse_kotak_pdf(text)
    elif bank_name == "IDFC FIRST":
        df = parse_idfc_pdf(text)
    else:
        df = parse_generic_pdf(text)
    if df.empty:
        # fallback to generic
        df = parse_generic_pdf(text)
    return df

if pdf is not None:
    raw = pdf.read()
    text = read_pdf_text(raw)
    data = parse_pdf_by_bank(bank, text)

    if data.empty:
        st.error("Could not detect transactions from this PDF. Please ensure it's a digital statement for the selected bank.")
    else:
        summary = compute_summary(data)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Purchases (₹)", f"{summary['purchase_total']:,.2f}")
        col2.metric("TOTAL EXTRA Paid (₹)", f"{summary['extra_total']:,.2f}")
        col3.metric("EXTRA as % of Purchases", f"{summary['extra_pct']:.2f}%")

        st.subheader("EXTRA Breakdown")
        st.dataframe(summary["extra_breakdown"], use_container_width=True)

        with st.expander("Show transactions"):
            st.dataframe(summary["transactions"], use_container_width=True)

        xls = export_excel(summary)
        st.download_button(
            "⬇️ Download Excel (Summary + Transactions)",
            data=xls,
            file_name="extra_paid_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Select your bank and upload one PDF to analyze.")
