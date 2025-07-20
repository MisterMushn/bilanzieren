import io
import re
import csv
import collections
from typing import Any

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # fallback for non-streamlit environments
    class _Dummy:
        def cache_data(self, **kwargs):
            def decorator(func):
                return func
            return decorator
    st = _Dummy()

GER_STOP = {
    "UND", "FÜR", "FUR", "VON", "DER", "DIE", "MIT", "AUF", "IM", "AM",
    "DEN", "EIN", "EINE", "DES", "IN", "AN",
}
ENG_STOP = {
    "AND", "THE", "TO", "FOR", "OF", "IN", "AT", "ON", "BY", "MY", "PAY",
}
STOPWORDS = GER_STOP | ENG_STOP

@st.cache_data(show_spinner=False)
def most_common(df: pd.DataFrame, col: str, k: int, min_len: int = 2) -> pd.DataFrame:
    """Return *k* most frequent tokens in *df[col]* (after stop-word filtering)."""
    def normalise(txt: Any) -> list[str]:
        txt = re.sub(r"[^\w\s]", " ", str(txt).upper())
        return [t for t in txt.split() if t not in STOPWORDS and len(t) >= min_len]

    bag: collections.Counter[str] = collections.Counter()
    for tokens in df[col].dropna().map(normalise):
        bag.update(tokens)

    if not bag:
        return pd.DataFrame(columns=["keyword", "count", "share"])

    total = sum(bag.values())
    rows = [
        {"keyword": w, "count": c, "share": c / total}
        for w, c in bag.most_common(k)
    ]
    return pd.DataFrame(rows)

def try_read_csv(file_buf: io.BytesIO) -> pd.DataFrame:
    """Read German (`;` + decimal `,`) or default comma CSV automatically."""
    file_buf.seek(0)
    sample = file_buf.read(4096).decode(errors="ignore")
    file_buf.seek(0)

    dialect = csv.Sniffer().sniff(sample, delimiters=";,")
    sep = dialect.delimiter or ";"
    decimal = "," if sep == ";" else "."
    return pd.read_csv(file_buf, sep=sep, decimal=decimal)

def keyword_mask(series: pd.Series, kw: str) -> pd.Series:
    """Case-insensitive plain-string match."""
    return series.astype(str).str.contains(kw, case=False, na=False, regex=False)

def ensure_tag_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("Category", "Subcategory"):
        if col not in df.columns:
            df[col] = ""
    return df

def untagged_mask(df: pd.DataFrame) -> pd.Series:
    """True for rows whose *Category* is empty/NaN/whitespace."""
    return df["Category"].fillna("").astype(str).str.strip() == ""
