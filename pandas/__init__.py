# Minimal pandas-like stub for testing without external dependency.
import csv
import io
from typing import Any, Iterable, List


class Series:
    def __init__(self, data: Iterable[Any]):
        self.data = list(data)

    # basic indexing
    def __getitem__(self, idx):
        return self.data[idx]

    def __setitem__(self, idx, value):
        self.data[idx] = value

    def __len__(self):
        return len(self.data)

    def tolist(self) -> List[Any]:
        return list(self.data)

    def map(self, func):
        return Series([func(x) for x in self.data])

    def dropna(self):
        return Series([x for x in self.data if x is not None])

    def fillna(self, value):
        return Series([value if x is None else x for x in self.data])

    def astype(self, typ):
        if typ in (str, 'str', 'string'):
            return Series(["" if x is None else str(x) for x in self.data])
        raise NotImplementedError

    class _StrAccessor:
        def __init__(self, series):
            self.series = series

        def contains(self, kw, case=True, na=False, regex=False):
            pat = str(kw)
            if not case:
                pat = pat.lower()
            res = []
            for x in self.series.data:
                if x is None:
                    res.append(na)
                    continue
                s = str(x)
                if not case:
                    s = s.lower()
                res.append(pat in s)
            return Series(res)

        def strip(self):
            return Series(["" if x is None else str(x).strip() for x in self.series.data])

    @property
    def str(self):
        return Series._StrAccessor(self)

    def __eq__(self, other):
        return Series([x == other for x in self.data])


class DataFrame:
    def __init__(self, data):
        if isinstance(data, list):
            if not data:
                self._data = {}
                self.columns = []
                return
            self.columns = list(data[0].keys())
            self._data = {c: [row.get(c) for row in data] for c in self.columns}
            return
        self._data = {k: list(v) for k, v in data.items()}
        self.columns = list(data.keys())

    @property
    def iloc(self):
        df = self
        class _ILoc:
            def __getitem__(self, idx):
                r, c = idx
                if isinstance(c, int):
                    c = df.columns[c]
                return df._data[c][r]
            def __setitem__(self, idx, value):
                r, c = idx
                if isinstance(c, int):
                    c = df.columns[c]
                df._data[c][r] = value
        return _ILoc()

    @property
    def loc(self):
        df = self
        class _Loc:
            def __getitem__(self, idx):
                r, c = idx
                return df._data[c][r]
            def __setitem__(self, idx, value):
                r, c = idx
                df._data[c][r] = value
        return _Loc()

    def __getitem__(self, col):
        return Series(self._data[col])

    def __setitem__(self, col, value):
        if isinstance(value, Series):
            value = value.data
        elif not isinstance(value, list):
            value = [value] * self.n_rows
        self._data[col] = list(value)
        if col not in self.columns:
            self.columns.append(col)

    @property
    def n_rows(self):
        if not self._data:
            return 0
        return len(next(iter(self._data.values())))

    def to_csv(self, index: bool = False) -> str:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(self.columns)
        for i in range(self.n_rows):
            writer.writerow([self._data[c][i] for c in self.columns])
        return out.getvalue()


def DataFrame_from_rows(headers: list[str], rows: list[list[str]], decimal: str):
    cols = {h: [] for h in headers}
    for row in rows:
        for h, val in zip(headers, row):
            if val == "":
                cols[h].append(None)
                continue
            v = val
            if decimal != '.':
                v = v.replace(decimal, '.')
            try:
                cols[h].append(float(v))
            except ValueError:
                cols[h].append(v)
    return DataFrame(cols)


def read_csv(file, sep: str = ',', decimal: str = '.') -> DataFrame:
    if hasattr(file, 'read'):
        file.seek(0)
        text = file.read()
        if isinstance(text, bytes):
            text = text.decode()
    else:
        with open(file, 'r', encoding='utf-8') as f:
            text = f.read()
    reader = csv.reader(io.StringIO(text), delimiter=sep)
    rows = list(reader)
    if not rows:
        return DataFrame({})
    headers = rows[0]
    return DataFrame_from_rows(headers, rows[1:], decimal)


def Series_from_list(lst: list[Any]) -> Series:
    return Series(lst)

__all__ = ['DataFrame', 'Series', 'read_csv', 'Series_from_list']
