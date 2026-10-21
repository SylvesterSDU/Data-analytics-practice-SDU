"""Shared helpers for building the question bank.

Each check stores only a SHA-256 hash of the correct value (rounded to the
stated decimals), plus hashes of known wrong values with a hint that
explains the likely cause. The browser hashes what the student types and
compares. Must stay in sync with site/app.js.
"""
import hashlib
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FILES = ROOT / "site" / "files"
SALT = "dataanalytics-practice-v1"

TOPICS = [
    "Data profiling & cleaning",
    "Filter & count",
    "Sort & top-N",
    "Group & aggregate",
    "Dates & durations",
    "Text functions & extraction",
    "Joins & lookups",
    "Calculated fields (IF / CASE)",
    "Multi-step queries",
    "Control & fraud tests",
]


# ---------- canonical forms ----------
def canon_number(x, decimals):
    return f"{round(float(x) + 0.0, decimals):.{decimals}f}"


def canon_text(s):
    return " ".join(str(s).strip().lower().split())


def canon_date(d, with_time):
    d = pd.Timestamp(d)
    return d.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")


def _h(qid, idx, canon):
    return hashlib.sha256(f"{SALT}|{qid}|{idx}|{canon}".encode()).hexdigest()


# ---------- check builders ----------
# A check is created without qid/idx; Question() fills them in and hashes.
class Num:
    def __init__(self, label, value, decimals=0, mistakes=(), percent=False, accept=()):
        self.label, self.value, self.decimals = label, value, decimals
        self.mistakes, self.percent, self.accept = list(mistakes), percent, list(accept)

    def canon(self, v):
        return canon_number(v, self.decimals)

    def spec(self):
        return {"type": "number", "decimals": self.decimals, "percent": self.percent}


class Text:
    def __init__(self, label, value, mistakes=(), accept=()):
        self.label, self.value, self.mistakes, self.accept = label, value, list(mistakes), list(accept)

    def canon(self, v):
        return canon_text(v)

    def spec(self):
        return {"type": "text"}


class Date:
    def __init__(self, label, value, with_time=False, mistakes=(), accept=()):
        self.label, self.value, self.with_time = label, value, with_time
        self.mistakes, self.accept = list(mistakes), list(accept)

    def canon(self, v):
        return canon_date(v, self.with_time)

    def spec(self):
        return {"type": "date", "time": self.with_time}


REGISTRY = []
ANSWER_LOG = []  # plain values, written to a local file that is NOT deployed


def question(qid, subject, source, files, topic, minutes, prompt, checks, note=None):
    assert topic in TOPICS, topic
    assert qid not in {q["id"] for q in REGISTRY}, qid
    out = []
    for idx, c in enumerate(checks):
        right = c.canon(c.value)
        accepted = sorted({c.canon(a) for a in c.accept} - {right})
        mistakes = []
        for wrong, hint in c.mistakes:
            w = c.canon(wrong)
            if w != right and w not in accepted and all(m["_c"] != w for m in mistakes):
                mistakes.append({"_c": w, "hash": _h(qid, idx, w), "hint": hint})
        out.append({"label": c.label, **c.spec(), "hash": _h(qid, idx, right),
                    **({"accept": [_h(qid, idx, a) for a in accepted]} if accepted else {}),
                    "mistakes": [{k: v for k, v in m.items() if k != "_c"} for m in mistakes]})
        ANSWER_LOG.append((qid, c.label, right, [m["_c"] for m in mistakes], accepted))
    REGISTRY.append({
        "id": qid, "subject": subject, "source": source,
        "files": [files] if isinstance(files, str) else list(files),
        "topic": topic, "minutes": minutes, "prompt": prompt,
        **({"note": note} if note else {}), "checks": out,
    })


# ---------- data access ----------
_tmp = Path(tempfile.mkdtemp(prefix="qbank-"))


def db_path(name):
    """Path to a SQLite file in site/files, unzipping .zip downloads first."""
    p = FILES / name
    if p.suffix == ".zip":
        with zipfile.ZipFile(p) as z:
            inner = z.namelist()[0]
            target = _tmp / inner
            if not target.exists():
                z.extract(inner, _tmp)
        return target
    return p


_cons = {}


def sql(db, query, one=False):
    if db not in _cons:
        _cons[db] = sqlite3.connect(f"file:{db_path(db)}?mode=ro", uri=True)
    rows = _cons[db].execute(query).fetchall()
    return rows[0] if one else rows


def val(db, query):
    return sql(db, query, one=True)[0]
