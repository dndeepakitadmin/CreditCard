
# parsers/idfc.py
import re, pandas as pd
from .utils import parse_date_any, clean_amount

def parse_idfc_pdf(text: str) -> pd.DataFrame:
    # e.g. 12-09-2025 Merchant Desc Dr 345.00
    pat = re.compile(r'(?P<date>\d{1,2}-\d{1,2}-\d{2,4})\s+(?P<desc>.+?)\s+(?P<dc>Dr|Cr)\s+(?P<amt>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', re.IGNORECASE)
    rows = []
    for ln in text.splitlines():
        m = pat.search(ln)
        if m:
            amt = clean_amount(m.group("amt"))
            amt = -abs(amt) if m.group("dc").lower()=="dr" else abs(amt)
            rows.append({
                "date": parse_date_any(m.group("date")),
                "description": m.group("desc"),
                "amount": amt
            })
    return pd.DataFrame(rows)
