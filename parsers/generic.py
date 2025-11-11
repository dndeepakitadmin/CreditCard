
# parsers/generic.py
import re, pandas as pd
from .utils import parse_date_any, clean_amount

def parse_generic_pdf(text: str) -> pd.DataFrame:
    rows = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    date_pat = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    amt_pat = r'(-?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'
    for ln in lines:
        if re.search(date_pat, ln) and re.search(amt_pat, ln):
            d = re.search(date_pat, ln).group(1)
            am = list(re.finditer(amt_pat, ln))[-1].group(1)
            desc = ln
            desc = desc.replace(d, "").replace(am, "").strip()
            df_row = {
                "date": parse_date_any(d),
                "description": desc,
                "amount": clean_amount(am)
            }
            rows.append(df_row)
    df = pd.DataFrame(rows)
    # Try to infer DR/CR tags
    if not df.empty:
        def sign_fix(desc, amt):
            D = (desc or "").upper()
            if any(x in D for x in [" CR", "CR ", " CREDIT"]):
                return abs(amt)
            if any(x in D for x in [" DR", "DR ", " DEBIT"]):
                return -abs(amt)
            return amt
        df["amount"] = df.apply(lambda r: sign_fix(r["description"], r["amount"]), axis=1)
    return df
