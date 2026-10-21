"""Build site/data/exams.json: full data manipulation practice exams.

Each exam mirrors the oral exam format: 5 questions, Excel + SQL, drawn from one
Excel case and one SQL case, 8 minutes. Only quick questions (<= 3 min) are used;
longer assignment-style tasks stay in the question bank. Questions come from the verified bank, so every exam
question can be checked with "Check my result". Deterministic (fixed seed).

Run after build_questions.py:  python3 tools/build_exams.py
"""
import json
import random
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
bank = json.loads((ROOT / "site" / "data" / "questions.json").read_text())["questions"]

EXCEL_GROUPS = {"NYC film permits": "XL-NYC", "ETL cases": "XL-ETL", "IntegrateCo payroll": "XL-INT"}
SQL_GROUPS = {"Songs & movies": ("SQL-SNG", "SQL-MOV"), "Chinook": ("SQL-CHN",), "Purchasing cards": ("SQL-PC",)}
PER_COMBO = 4
EXAM_MINUTES = 8   # as on the reference site: one full manipulation exam in the 20-minute oral exam
QUICK = 3          # only questions estimated at 3 minutes or less fit 5-in-8-minutes

rng = random.Random(2026)
exams, seen = [], set()
for (xl_name, xl_prefix), (sql_name, sql_prefixes) in product(EXCEL_GROUPS.items(), SQL_GROUPS.items()):
    xl = [q for q in bank if q["id"].startswith(xl_prefix) and q["minutes"] <= QUICK]
    sq = [q for q in bank if q["id"].startswith(sql_prefixes) and q["minutes"] <= QUICK]
    made = 0
    while made < PER_COMBO:
        n_xl = rng.choice([2, 3])
        pick = rng.sample(xl, n_xl) + rng.sample(sq, 5 - n_xl)
        key = frozenset(q["id"] for q in pick)
        topics = {q["topic"] for q in pick}
        if key in seen or len(topics) < 3:  # avoid duplicates and one-topic exams
            continue
        seen.add(key)
        made += 1
        pick.sort(key=lambda q: (q["subject"] != "Excel", q["id"]))
        files = list(dict.fromkeys(f for q in pick for f in q["files"]))
        exams.append({"id": f"EX{len(exams) + 1:02d}", "excel": xl_name, "sql": sql_name,
                      "questions": [q["id"] for q in pick], "files": files,
                      "minutes": EXAM_MINUTES, "estimate": sum(q["minutes"] for q in pick)})

(ROOT / "site" / "data" / "exams.json").write_text(json.dumps({"exams": exams}, indent=1))
print(f"{len(exams)} exams, {EXAM_MINUTES} min each; summed estimates {min(e['estimate'] for e in exams)}-{max(e['estimate'] for e in exams)} min")
