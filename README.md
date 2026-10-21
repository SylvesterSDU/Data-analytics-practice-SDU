# Data Analytics in Accounting – Practice

Practice website for the SDU course *Data Analytics in Accounting*. Students practise the same kind of exams they meet in the oral exam: one full data manipulation exam (Excel + SQL) and one full data interpretation exam (regression). All questions are based only on the course materials.

## What is on the site

- **Question bank** – 105 Excel and SQL tasks from the course cases (NYC film permits, ETL cases 1–4, IntegrateCo payroll, CS50 songs and movies, Chinook, OSU P-cards), filterable by subject, topic and source.
- **Practice exams** – 36 exams in the oral exam format: 5 questions, one Excel case + one SQL case, 8-minute timer.
- **Data interpretation** – 11 regression exams from the restaurant case (Larry's Commissary) with Excel-style output, a 5-minute timer and model answers.

## Added functionality: verified topic mastery

Every Excel/SQL question has a **Check my result** box. The student types in a few figures from their own output (a record count, a control total, a top value) and the site says whether they match the values computed from the real files. The solution itself is never shown. Known wrong values come with a hint on the likely cause (e.g. `>= 5000` instead of `> 5000`, or comparing P-card dates stored as text).

Each topic gets a check mark after 3 questions verified in a row; a wrong check resets the run. Progress is stored only in the student's own browser (localStorage). There are no accounts and nothing is sent to a server.

## How the answers are produced

Nothing is typed in by hand. `tools/qbank/` computes every expected value from the exact files students download (`site/files/`), with pandas for the Excel cases and SQLite queries for the databases. The site only receives SHA-256 hashes of the rounded values, so the answers cannot be read from the page source. Where official answers exist (PwC NYC solutions, PwC Chinook answers) the computed values match them.

```bash
pip install pandas openpyxl statsmodels
python3 tools/build_questions.py   # question bank -> site/data/questions.json
python3 tools/build_exams.py       # practice exams -> site/data/exams.json
python3 tools/regression.py        # regression exams -> site/data/regression.json
```

## Data files

`pcards.db` (99 MB) is reduced to a practice subset with calendar years 2013–2014 (`pcards_2013_2014.zip`). `movies.db` is served zipped.

## Deployment

Static site, no build step. `vercel.json` serves the `site/` folder.
