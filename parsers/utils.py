
# parsers/utils.py
import pandas as pd
import re

def parse_date_any(s: str):
    try:
        return pd.to_datetime(s, dayfirst=True, errors="coerce")
    except Exception:
        return pd.NaT

def clean_amount(x):
    if x is None: return None
    s = str(x).strip().replace(",","")
    s = s.replace("₹","").replace("INR","").strip()
    s = re.sub(r'\b(DR|CR)\b', '', s, flags=re.IGNORECASE).strip()
    try:
        return float(s)
    except:
        return None
