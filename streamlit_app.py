# -----------------------------------------------------------
#  Credit-card transaction tagger   •   Streamlit ≥ 1.35
# -----------------------------------------------------------
"""
Run with
    streamlit run app.py

Changes in this revision
────────────────────────
• *Filter/Search* now **always shows rows that have no Category assigned**.
  If you type a keyword it narrows the view further, but only among the
  still-unassigned lines.
"""
import io
import re
import csv
import collections
import pandas as pd
import streamlit as st

# -----------------------------------------------------------
#  Config & heading
# -----------------------------------------------------------
st.set_page_config(page_title="Transaction Tagger", layout="wide")
st.title("🔖 Tag your credit-card transactions")

# -----------------------------------------------------------
#  Stop-word list  (extend freely)
# -----------------------------------------------------------
GER_STOP = {
    "UND", "FÜR", "FUR", "VON", "DER", "DIE", "MIT", "AUF", "IM", "AM",
    "DEN", "EIN", "EINE", "DES", "IN", "AN",
}
ENG_STOP = {
    "AND", "THE", "TO", "FOR", "OF", "IN", "AT", "ON", "BY", "MY", "PAY",
}
STOPWORDS = GER_STOP | ENG_STOP

# -----------------------------------------------------------
#  Helper 1: token frequency (cached)
# -----------------------------------------------------------
@st.cache_data(show_spinner=False)
def most_common(df: pd.DataFrame, col: str, k: int, min_len: int = 2) -> pd.DataFrame:
    """Return *k* most frequent tokens in *df[col]* (after stop-word filtering)."""
    def normalise(txt: str) -> list[str]:
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

# -----------------------------------------------------------
#  Helper 2: file ingest & misc utilities
# -----------------------------------------------------------

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

# ===========================================================
# 1  Upload CSV
# ===========================================================

uploaded = st.file_uploader("⬆️ Upload CSV", type="csv")
if uploaded is not None:
    df = ensure_tag_columns(try_read_csv(uploaded))
    st.session_state["df"] = df
    st.success(f"Loaded {len(df):,} rows.")

if "df" not in st.session_state:
    st.info("Upload a CSV to begin.")
    st.stop()

df = st.session_state.df

# ===========================================================
# 2  Filter & preview (only *unassigned* rows)
# ===========================================================

with st.sidebar:
    st.header("🔍 Filter unassigned rows")
    text_cols = [c for c in df.columns if df[c].dtype == object or df[c].dtype.name == "string"]
    search_col = st.selectbox("Column to search", text_cols, key="search_col")
    keyword = st.text_input("Keyword (case-insensitive)", placeholder="itunes", key="search_kw")
    if st.button("Search / Refresh", use_container_width=True):
        base = untagged_mask(df)
        st.session_state["mask"] = (
            base & keyword_mask(df[search_col], keyword) if keyword else base
        )

# default mask = all unassigned rows on initial load
mask = st.session_state.get("mask", untagged_mask(df))
hits = df[mask]

st.write(f"### {mask.sum():,} unassigned row(s) currently shown")
st.dataframe(hits, height=400, use_container_width=True)

# ===========================================================
# 3  Tagging
# ===========================================================

st.markdown("#### Apply tag to **all** visible (still-unassigned) rows")
c1, c2, c3 = st.columns([2, 3, 1])
with c1:
    cat = st.text_input("Category", placeholder="Private", key="tag_cat")
with c2:
    sub = st.text_input("Sub-category", placeholder="entertainment", key="tag_sub")
with c3:
    if st.button("Tag rows ✅", type="primary", use_container_width=True) and cat and sub and mask.any():
        df.loc[mask, "Category"] = cat.strip()
        df.loc[mask, "Subcategory"] = sub.strip()
        st.session_state["df"] = df  # persist
        # Reset mask to show *still* untagged rows after tagging
        st.session_state["mask"] = untagged_mask(df)
        st.success(f"Tagged {mask.sum():,} row(s) as {cat}/{sub}")

# ===========================================================
# 4  Keyword discovery (works on *entire* column, not just untagged)
# ===========================================================

with st.expander("🕵️‍♀️ Discover top keywords", expanded=False):
    ana_col = st.selectbox("Column to analyse", text_cols, key="kw_col")
    top_k = st.slider("Show top … keywords", 10, 100, 30, 10, key="kw_topk")
    min_len = st.slider("Minimum token length", 1, 5, 2, key="kw_minlen")
    freq_df = most_common(df, ana_col, top_k, min_len)
    st.dataframe(freq_df, use_container_width=True)

# ===========================================================
# 5  Download
# ===========================================================

st.divider()
st.download_button(
    label="📥 Download tagged CSV",
    data=df.to_csv(index=False).encode(),
    file_name="transactions_tagged.csv",
    mime="text/csv",
    use_container_width=True,
)

