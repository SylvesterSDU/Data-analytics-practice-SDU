"""SQL part 2: P-card audit (OSU), Tasks 4, 5 and 7. Practice subset: calendar years 2013-2014."""
from .common import Num, Text, name_forms, question, sql, val

P = "pcards_2013_2014.zip"
SRC = "Purchasing cards"
NOTE = ("pcards_2013_2014.zip contains pcards.db with OSU transactions for calendar years 2013 and 2014. "
        "TransactionDate and PostedDate are stored as text like '7/26/2014 0:00:00'. Use the Year and Month columns for filtering.")

# Convert 'M/D/YYYY 0:00:00' text into an ISO date that SQLite can calculate with.
def iso(col):
    return (f"date(substr({col}, instr({col}, '/') + instr(substr({col}, instr({col}, '/') + 1), '/') + 1, 4) || '-' || "
            f"printf('%02d', CAST({col} AS INTEGER)) || '-' || "
            f"printf('%02d', CAST(substr({col}, instr({col}, '/') + 1) AS INTEGER)))")


TD, PD = iso("TransactionDate"), iso("PostedDate")
Y14 = "Year = 2014"
TEXT_DATE = ("TransactionDate is text (e.g. '7/26/2014 0:00:00'), so comparing it with '2014' compares characters, not dates. "
             "Use the Year column, or LIKE '%/2014 %'.")
BOTH_YEARS = "That figure covers both years in the file. Restrict to 2014."
LAST_ONLY = "You grouped on last name only. Different cardholders share a last name; use FullName (first initial + last name)."


def q(n, task, topic, minutes, prompt, checks, note=NOTE):
    question(f"SQL-PC-{task}{n:02d}", "SQL", SRC, P, topic, minutes, prompt, checks, note)


# ---------------- Task 4: querying techniques ----------------
top = sql(P, "SELECT FullName, Amount, Vendor FROM pcards ORDER BY Amount DESC LIMIT 1", one=True)
q(1, 4, "Sort & top-N", 2,
  "Task 4, Q1: Show all transactions sorted by amount, most expensive first (year, month, cardholder, amount, vendor). How many rows, and who is the cardholder and vendor in the first row?",
  [Num("Number of rows", val(P, "SELECT COUNT(*) FROM pcards")), Text("Cardholder (FullName) in row 1", top[0], accept=name_forms(top[0])),
   Text("Vendor in row 1", top[2])])

first14 = sql(P, f"SELECT FullName, Amount FROM pcards WHERE {Y14} ORDER BY Month, Amount DESC, FullName LIMIT 1", one=True)
q(2, 4, "Sort & top-N", 3,
  "Task 4, Q2: Show all 2014 transactions sorted by month, then most expensive first, then alphabetically by cardholder. How many rows, and what are the cardholder and amount in the first row?",
  [Num("Number of rows", val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14}"),
       mistakes=[(val(P, "SELECT COUNT(*) FROM pcards WHERE TransactionDate > '2014'"), TEXT_DATE)]),
   Text("Cardholder in row 1", first14[0], accept=name_forms(first14[0])), Num("Amount in row 1", first14[1], 2,
                                                mistakes=[(val(P, f"SELECT MAX(Amount) FROM pcards WHERE {Y14}"), "Sort by Month first, then by amount.")])])

r3 = sql(P, f"SELECT COUNT(*), SUM(Amount) FROM pcards WHERE {Y14} AND Amount > 3000", one=True)
q(3, 4, "Filter & count", 3,
  "Task 4, Q3: Show all 2014 transactions for more than $3,000. How many rows, and what is their total amount (control total)?",
  [Num("Number of rows", r3[0], mistakes=[(val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount >= 3000"), "You included amounts of exactly $3,000. Use > 3000."),
                                          (val(P, "SELECT COUNT(*) FROM pcards WHERE Amount > 3000"), BOTH_YEARS)]),
   Num("Total amount", r3[1], 2)])

amz = sql(P, f"SELECT COUNT(*), MIN(Amount) FROM pcards WHERE {Y14} AND Amount > 3000 AND Vendor LIKE '%amazon%'", one=True)
q(4, 4, "Text functions & extraction", 3,
  "Task 4, Q4: Show all 2014 transactions over $3,000 from a vendor with 'Amazon' anywhere in the name, smallest amount first. How many rows, and what is the amount in the first row?",
  [Num("Number of rows", amz[0],
       mistakes=[(val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount > 3000 AND Vendor = 'Amazon.com'"),
                  "You matched only 'Amazon.com'. Use LIKE '%amazon%' to find Amazon anywhere in the vendor name.")]),
   Num("Amount in row 1", amz[1], 2)])

q(5, 4, "Filter & count", 2,
  "Task 4, Q5-Q6: What is the total number of P-card transactions in the database (TotalTrans), and how many are for $5,000 or more (TotalTransGT5k)?",
  [Num("TotalTrans", val(P, "SELECT COUNT(*) FROM pcards")),
   Num("TotalTransGT5k", val(P, "SELECT COUNT(*) FROM pcards WHERE Amount >= 5000"),
       mistakes=[(val(P, "SELECT COUNT(*) FROM pcards WHERE Amount > 5000"), "The question says more than or equal to $5,000: use >= 5000.")])])

q(6, 4, "Filter & count", 3,
  "Task 4, Q7: What is the total dollar amount of returns (negative amounts) from January to March 2014, inclusive (TotalReturns2014Q1)?",
  [Num("TotalReturns2014Q1", val(P, f"SELECT SUM(Amount) FROM pcards WHERE {Y14} AND Month BETWEEN 1 AND 3 AND Amount < 0"), 2,
       mistakes=[(val(P, f"SELECT SUM(Amount) FROM pcards WHERE {Y14} AND Month BETWEEN 1 AND 2 AND Amount < 0"), "March is missing. Inclusive means months 1, 2 and 3."),
                 (val(P, f"SELECT SUM(Amount) FROM pcards WHERE {Y14} AND Month BETWEEN 1 AND 3"), "That includes purchases. Returns are rows with Amount < 0.")])],
  note=NOTE + " Returns are negative, so the answer is a negative number.")

cnt = sql(P, f"SELECT FullName, COUNT(*) FROM pcards WHERE {Y14} GROUP BY FullName ORDER BY 2 DESC")
q(7, 4, "Group & aggregate", 3,
  "Task 4, Q9 and Q11: Count 2014 transactions per cardholder (NumTrans), most first. Who has the most, and how many? How many cardholders have more than 10 transactions?",
  [Text("Cardholder with most transactions", cnt[0][0], accept=name_forms(cnt[0][0])),
   Num("NumTrans for that cardholder", cnt[0][1],
       mistakes=[(val(P, f"SELECT MAX(c) FROM (SELECT COUNT(*) c FROM pcards WHERE {Y14} GROUP BY CardholderLastName)"), LAST_ONLY)]),
   Num("Cardholders with more than 10 transactions", sum(1 for r in cnt if r[1] > 10),
       mistakes=[(sum(1 for r in cnt if r[1] >= 10), "More than 10 means > 10 in HAVING, not >= 10.")])],
  note=NOTE + " Use HAVING to filter on a COUNT.")

ret = sql(P, f"SELECT FullName, SUM(Amount), COUNT(*) FROM pcards WHERE {Y14} AND Amount < 0 GROUP BY FullName ORDER BY 2")
q(8, 4, "Group & aggregate", 4,
  "Task 4, Q10 and Q12: For 2014 returns (negative amounts), who returned the greatest dollar amount of goods? Give ReturnedGoodsValue and ReturnedGoodsCount. How many people returned more than $1,000 in total?",
  [Text("Cardholder", ret[0][0], accept=name_forms(ret[0][0])), Num("ReturnedGoodsValue (negative)", ret[0][1], 2),
   Num("ReturnedGoodsCount", ret[0][2]), Num("People with returns over $1,000", sum(1 for r in ret if r[1] < -1000))],
  note=NOTE + " Returns are negative amounts, so the greatest return is the most negative sum.")

tax = sql(P, f"SELECT MAX(Amount * 0.045), SUM(Amount * 0.045) FROM pcards WHERE {Y14} AND Month = 12", one=True)
q(9, 4, "Calculated fields (IF / CASE)", 3,
  "Task 4, Q13: Compute SalesTax = 4.5% of each amount for December 2014 transactions, largest first. What is the largest SalesTax, and what is the total SalesTax for the month?",
  [Num("Largest SalesTax", tax[0], 2, mistakes=[(tax[0] * 100, "Use 0.045, not 4.5.")]),
   Num("Total SalesTax December 2014", tax[1], 2,
       accept=[val(P, f"SELECT SUM(ROUND(Amount * 0.045, 2)) FROM pcards WHERE {Y14} AND Month = 12")])])

sv = sql(P, f"SELECT SUM(Amount), SUM(Amount) * 0.045 FROM pcards WHERE {Y14}", one=True)
q(10, 4, "Calculated fields (IF / CASE)", 4,
  "Task 4, Q14-Q15: How much did OSU avoid paying in state sales tax (4.5%) on 2014 P-card transactions? Then assume tax had to be paid out of state 30% of the time, so savings apply to only 70% of spending.",
  [Num("Total net spent 2014 (purchases minus returns)", sv[0], 2), Num("SalesTaxSaved (100%)", sv[1], 2), Num("SalesTaxSaved (70%)", sv[1] * 0.7, 2,
                                                                              mistakes=[(sv[1] * 0.3, "That is 30%. Savings apply to the 70% of spending where no tax was paid.")])])

td = sql(P, f"SELECT MAX(julianday({PD}) - julianday({TD})), AVG(julianday({PD}) - julianday({TD})) FROM pcards WHERE {Y14} AND Month = 11", one=True)
q(11, 4, "Dates & durations", 6,
  "Task 4, Q16: For November 2014, compute TimeDif = days from transaction date to posted date. What is the largest TimeDif, and what is the average (two decimals)?",
  [Num("Largest TimeDif (days)", td[0]), Num("Average TimeDif (days)", td[1], 2)],
  note=NOTE + " Convert the text dates first, e.g. rebuild them as YYYY-MM-DD with substr/instr and use julianday().")

risk = dict(sql(P, f"SELECT CASE WHEN Amount <= -1000 THEN 'High' WHEN Amount <= -500 THEN 'Medium' ELSE 'Low' END, COUNT(*) FROM pcards WHERE {Y14} AND Amount < 0 GROUP BY 1"))
risk_wrong = dict(sql(P, f"SELECT CASE WHEN Amount >= 1000 THEN 'High' WHEN Amount >= 500 THEN 'Medium' ELSE 'Low' END, COUNT(*) FROM pcards WHERE {Y14} AND Amount < 0 GROUP BY 1"))
q(12, 4, "Calculated fields (IF / CASE)", 5,
  "Task 4, Q17: Rank 2014 returns by risk: High if the return is $1,000 or more, Medium if $500 to under $1,000, Low if under $500. How many returns fall in each class?",
  [Num("High risk", risk.get("High", 0), mistakes=[(risk_wrong.get("High", 0), "Returns are negative. Compare the absolute value, ABS(Amount) >= 1000, or Amount <= -1000.")]),
   Num("Medium risk", risk.get("Medium", 0)), Num("Low risk", risk.get("Low", 0))])

amzE = "SUM(CASE WHEN Amount >= 500 THEN Amount * 0.0075 ELSE Amount * 0.005 END)"
q(13, 4, "Calculated fields (IF / CASE)", 5,
  "Task 4, Q18: OSU could earn 0.75% on Amazon.com purchases of $500 or more and 0.50% on purchases under $500. What would OSU have earned in 2014 (AmazonEarnings)? Include all Amazon.com transactions, so returns reduce the earnings. Use the vendor name Amazon.com in any capitalisation.",
  [Num("AmazonEarnings 2014", val(P, f"SELECT {amzE} FROM pcards WHERE {Y14} AND Vendor LIKE 'amazon.com'"), 2,
       mistakes=[(val(P, f"SELECT {amzE} FROM pcards WHERE {Y14} AND Vendor = 'Amazon.com'"), "You missed 'AMAZON.COM' in capitals. LIKE 'amazon.com' ignores case."),
                 (val(P, f"SELECT {amzE} FROM pcards WHERE {Y14} AND Vendor LIKE '%amazon%'"), "That includes all Amazon vendors (Marketplace, Kindle...). The question is about Amazon.com only."),
                 (val(P, f"SELECT {amzE} FROM pcards WHERE {Y14} AND Vendor LIKE 'amazon.com' AND Amount > 0"), "You left out the returns. Include all Amazon.com transactions: a return reduces the earnings.")])])

q(14, 4, "Multi-step queries", 4,
  "Task 4, Q19: Show all 2014 transactions above the 2014 average transaction amount. How many rows, and what is the 2014 average (two decimals)?",
  [Num("Number of rows", val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount > (SELECT AVG(Amount) FROM pcards WHERE {Y14})"),
       mistakes=[(val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount > (SELECT AVG(Amount) FROM pcards)"), "Your average covers both years. Compute the 2014 average.")]),
   Num("2014 average amount", val(P, f"SELECT AVG(Amount) FROM pcards WHERE {Y14}"), 2)])

vd = sql(P, """SELECT a.Vendor, a.s - b.s d FROM
               (SELECT Vendor, SUM(Amount) s FROM pcards WHERE Year = 2014 GROUP BY Vendor) a
               JOIN (SELECT Vendor, SUM(Amount) s FROM pcards WHERE Year = 2013 GROUP BY Vendor) b ON a.Vendor = b.Vendor
               ORDER BY d DESC""")
q(15, 4, "Multi-step queries", 6,
  "Task 4, Q20: For vendors with purchases in both 2013 and 2014, compute DiffSpending = 2014 total - 2013 total, largest increase first. How many vendors are in the result, which has the largest increase, and how large is it?",
  [Num("Vendors in both years", len(vd)), Text("Vendor with largest increase", vd[0][0]), Num("DiffSpending", vd[0][1], 2)])

top13 = val(P, "SELECT MAX(s) FROM (SELECT SUM(Amount) s FROM pcards WHERE Year = 2013 GROUP BY Vendor)")
v14 = sql(P, f"SELECT Vendor, SUM(Amount) s FROM pcards WHERE {Y14} GROUP BY Vendor HAVING s > {top13} ORDER BY s DESC")
q(16, 4, "Multi-step queries", 5,
  "Task 4, Q21: Which 2014 vendors had more spending (TotalSpent) than the top vendor of 2013? How many vendors qualify, and what is the top vendor's 2013 total?",
  [Num("Qualifying 2014 vendors", len(v14)), Num("Top 2013 vendor total", top13, 2)])

# ---------------- Task 5: internal control tests (2014) ----------------
y = sql(P, f"SELECT FullName, SUM(Amount) s FROM pcards WHERE {Y14} GROUP BY FullName HAVING s > 50000 ORDER BY s DESC")
q(1, 5, "Control & fraud tests", 4,
  "Task 5, control 1: a cardholder shall not spend more than $50,000 per year. How many cardholders spent more than $50,000 in 2014? Who spent the most, and how much?",
  [Num("Cardholders over $50,000", len(y),
       mistakes=[(len(sql(P, "SELECT FullName FROM pcards GROUP BY FullName HAVING SUM(Amount) > 50000")), BOTH_YEARS + " The limit is per year."),
                 (len(sql(P, f"SELECT CardholderLastName FROM pcards WHERE {Y14} GROUP BY CardholderLastName HAVING SUM(Amount) > 50000")), LAST_ONLY)]),
   Text("Top cardholder", y[0][0], accept=name_forms(y[0][0])), Num("Total spent", y[0][1], 2)])

m = sql(P, f"SELECT FullName, Month, SUM(Amount) s FROM pcards WHERE {Y14} GROUP BY FullName, Month HAVING s > 10000")
q(2, 5, "Control & fraud tests", 4,
  "Task 5, control 2: no more than $10,000 per month without approval. How many cardholder-month combinations exceeded $10,000 in 2014, and how many different cardholders are involved?",
  [Num("Cardholder-month combinations", len(m),
       mistakes=[(len(sql(P, f"SELECT FullName FROM pcards WHERE {Y14} GROUP BY FullName HAVING SUM(Amount) > 10000")),
                  "You grouped per cardholder for the whole year. Group by cardholder and month.")]),
   Num("Different cardholders", len({r[0] for r in m}))])

right = sql(P, f"SELECT COUNT(*), SUM(Amount), MAX(Amount) FROM pcards WHERE {Y14} AND Amount > 5000", one=True)
gte = sql(P, f"SELECT COUNT(*), SUM(Amount) FROM pcards WHERE {Y14} AND Amount >= 5000", one=True)
allyrs = sql(P, "SELECT COUNT(*), SUM(Amount) FROM pcards WHERE Amount > 5000", one=True)
textdate = sql(P, "SELECT COUNT(*), SUM(Amount) FROM pcards WHERE TransactionDate > '2014' AND Amount > 5000", one=True)
q(3, 5, "Control & fraud tests", 4,
  "Task 5, control 3: no single transaction may exceed $5,000. List all 2014 transactions for more than $5,000 (amount, cardholder, description, vendor, dates, MCC).",
  [Num("Number of rows (record count)", right[0],
       mistakes=[(gte[0], "You included transactions of exactly $5,000. The limit is breached only by amounts more than $5,000 (> not >=)."),
                 (allyrs[0], BOTH_YEARS), (textdate[0], TEXT_DATE)]),
   Num("Sum of Amount (control total)", right[1], 2,
       mistakes=[(gte[1], "Your total includes transactions of exactly $5,000. Use > 5000, not >= 5000."),
                 (allyrs[1], BOTH_YEARS), (textdate[1], TEXT_DATE)]),
   Num("Largest single amount", right[2], 2)])

split = sql(P, f"""SELECT COUNT(*), COUNT(DISTINCT FullName || '|' || TransactionDate || '|' || Vendor), SUM(Amount) FROM pcards p
                   JOIN (SELECT FullName f, Vendor v, TransactionDate t FROM pcards WHERE {Y14}
                         GROUP BY FullName, Vendor, TransactionDate HAVING COUNT(*) > 1 AND SUM(Amount) > 5000) g
                   ON p.FullName = g.f AND p.Vendor = g.v AND p.TransactionDate = g.t WHERE {Y14}""", one=True)
q(4, 5, "Control & fraud tests", 7,
  "Task 5, control 4: an amount over $5,000 should not be split across several swipes by the same person. Find cardholder/vendor/day groups with more than one 2014 transaction and a combined total over $5,000. How many groups, and how many transactions do they contain in total?",
  [Num("Groups (cardholder + vendor + day)", split[1]), Num("Transactions in those groups", split[0]),
   Num("Combined amount of those transactions", split[2], 2)],
  note=NOTE + " GROUP BY cardholder, vendor and TransactionDate with HAVING, then join back to list the transactions.")

# ---------------- Task 7: forensic tests (2014) ----------------
ben = dict(sql(P, f"SELECT substr(CAST(Amount AS TEXT), 1, 1) d, COUNT(*) * 100.0 / (SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount >= 1) FROM pcards WHERE {Y14} AND Amount >= 1 GROUP BY d"))
ben_all = dict(sql(P, f"SELECT substr(CAST(ABS(Amount) AS TEXT), 1, 1) d, COUNT(*) * 100.0 / (SELECT COUNT(*) FROM pcards WHERE {Y14} AND ABS(Amount) >= 1) FROM pcards WHERE {Y14} AND ABS(Amount) >= 1 GROUP BY d"))
q(1, 7, "Control & fraud tests", 6,
  "Task 7, Q1: Benford's law. For 2014 transactions of $1.00 or more, what percentage of amounts begin with the digit 1, and with the digit 9? Give three decimals. (Benford expects about 30.1% and 4.6%.)",
  [Num("Leading digit 1 (%)", ben["1"], 3, percent=True,
       mistakes=[(ben_all["1"], "You included returns. Exclude amounts under 1.00, which removes the negative amounts too.")]),
   Num("Leading digit 9 (%)", ben["9"], 3, percent=True)],
  note=NOTE + " The first character of CAST(Amount AS TEXT) gives the leading digit.")

dup_groups = f"""SELECT FullName, Vendor, TransactionDate, Amount FROM pcards WHERE {Y14} AND Amount > 0
                 GROUP BY FullName, Vendor, TransactionDate, Amount HAVING COUNT(*) > 1"""
dup = sql(P, f"""SELECT COUNT(*), COUNT(DISTINCT p.FullName) FROM pcards p JOIN ({dup_groups}) g
                 ON p.FullName = g.FullName AND p.Vendor = g.Vendor AND p.TransactionDate = g.TransactionDate AND p.Amount = g.Amount
                 WHERE p.{Y14}""", one=True)
who = sql(P, f"SELECT FullName, COUNT(*) FROM ({dup_groups}) GROUP BY FullName ORDER BY 2 DESC, FullName")
dup_incl_ret = val(P, f"SELECT COUNT(*) FROM (SELECT 1 FROM pcards WHERE {Y14} GROUP BY FullName, Vendor, TransactionDate, Amount HAVING COUNT(*) > 1)")
q(2, 7, "Control & fraud tests", 7,
  "Task 7, Q2-Q3: Possible duplicate payments in 2014: same day, same vendor, same cardholder, same amount, excluding returns. How many transactions are possible duplicates (count every transaction in a duplicate group)? How many individuals are involved, and who has the most duplicate groups?",
  [Num("Possible duplicate transactions", dup[0],
       mistakes=[(len(sql(P, dup_groups)), "That is the number of duplicate groups. Count every transaction in those groups.")]),
   Num("Individuals involved", dup[1]),
   Text("Individual with most duplicate groups", who[0][0], accept=name_forms(who[0][0]))])

rnd = val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount BETWEEN 1000 AND 9999 AND Amount = ROUND(Amount) AND Amount % 1000 = 0")
q(3, 7, "Control & fraud tests", 4,
  "Task 7, Q4: Round-number transactions can indicate fraud. How many positive 2014 transactions are a four-digit whole-dollar amount ending in 000 (exactly 1000.00, 2000.00 ... 9000.00, no cents)?",
  [Num("Round-number transactions", rnd,
       mistakes=[(val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount >= 1000 AND Amount = ROUND(Amount) AND Amount % 1000 = 0"),
                  "That includes amounts with five or more digits. Four digits means 1000 to 9999."),
                 (val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND Amount BETWEEN 1000 AND 9999 AND Amount % 1000 = 0"),
                  "SQLite's % works on whole numbers, so 1000.10 % 1000 is also 0. Also require no cents: Amount = ROUND(Amount)."),
                 (val(P, f"SELECT COUNT(*) FROM pcards WHERE {Y14} AND ABS(Amount) BETWEEN 1000 AND 9999 AND Amount = ROUND(Amount) AND CAST(Amount AS INTEGER) % 1000 = 0"),
                  "That includes returns (negative amounts). The question asks for positive transactions.")])])
