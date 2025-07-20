import io
import sys
import types

import pandas as pd

# Import helpers without requiring streamlit runtime
sys.modules.setdefault('streamlit', types.SimpleNamespace(cache_data=lambda **k: (lambda f: f)))

from helpers import (
    most_common,
    try_read_csv,
    keyword_mask,
    ensure_tag_columns,
    untagged_mask,
)

def test_try_read_csv_semicolon():
    data = "A;B\n1,23;4,56\n7,89;0,12"
    df = try_read_csv(io.BytesIO(data.encode()))
    assert list(df.columns) == ["A", "B"]
    assert df.iloc[0, 0] == 1.23
    assert df.iloc[1, 1] == 0.12

def test_try_read_csv_comma():
    data = "A,B\n1.5,2.5\n3.0,4.0"
    df = try_read_csv(io.BytesIO(data.encode()))
    assert df["A"].tolist() == [1.5, 3.0]
    assert df["B"].tolist() == [2.5, 4.0]

def test_keyword_mask_case_insensitive():
    series = pd.Series(["Apple", "banana", None])
    result = keyword_mask(series, "apple")
    assert result.tolist() == [True, False, False]

def test_ensure_tag_columns_adds_missing():
    df = pd.DataFrame({"A": [1]})
    df = ensure_tag_columns(df)
    assert "Category" in df.columns and "Subcategory" in df.columns
    assert df.loc[0, "Category"] == ""

def test_untagged_mask():
    df = pd.DataFrame({"Category": ["", "x", " ", None]})
    mask = untagged_mask(df)
    assert mask.tolist() == [True, False, True, True]

def test_most_common_basic():
    df = pd.DataFrame({"desc": ["the cat", "cat and dog", "dog"]})
    result = most_common(df, "desc", 2)
    assert result.loc[0, "keyword"] in {"CAT", "DOG"}
    assert set(result["count"]) == {2}
