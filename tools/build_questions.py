"""Build site/data/questions.json from the real course files.

Every expected value is computed by the modules in tools/qbank/ from the exact
files students download (site/files/). The site only receives SHA-256 hashes.
A plain-text answer log is written to tools/answers_log.txt (not deployed) so
the answers can be reviewed.

Run:  python3 tools/build_questions.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from qbank import common  # noqa: E402
from qbank import excel_nyc, excel_etl, excel_integrateco, sql_cs50, sql_chinook, sql_pcards  # noqa: E402,F401

out = common.ROOT / "site" / "data" / "questions.json"
out.parent.mkdir(parents=True, exist_ok=True)
for q in common.REGISTRY:
    for f in q["files"]:
        assert (common.FILES / f).exists(), f
out.write_text(json.dumps({"salt": common.SALT, "topics": common.TOPICS, "questions": common.REGISTRY}, indent=1, default=int))

log = Path(__file__).parent / "answers_log.txt"
with log.open("w") as fh:
    for qid, label, right, wrong in common.ANSWER_LOG:
        fh.write(f"{qid:14} | {label:55.55} | {right:>22} | known mistakes: {', '.join(wrong) or '-'}\n")

(Path(__file__).parent / "answers.json").write_text(json.dumps(common.ANSWER_LOG))
print(f"{len(common.REGISTRY)} questions -> {out.relative_to(common.ROOT)}")
print("By subject:", dict(Counter(q['subject'] for q in common.REGISTRY)))
for t, n in Counter(q['topic'] for q in common.REGISTRY).most_common():
    print(f"  {n:3}  {t}")
print("Checks:", sum(len(q['checks']) for q in common.REGISTRY),
      "| with mistake hints:", sum(1 for q in common.REGISTRY for c in q['checks'] if c['mistakes']))
