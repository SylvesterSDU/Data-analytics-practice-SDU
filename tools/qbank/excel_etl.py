"""Excel part 2: ETL cases 1-4 (Analytics mindset)."""
import csv
import re

import pandas as pd

from .common import FILES, Num, Text, question

# ---------- Case 1: identifying data problems ----------
F1 = "Analytics_mindset_case_studies_ETL_Case1.csv"
raw = list(csv.reader(open(FILES / F1, encoding="utf-8-sig")))
header, body = raw[0], raw[1:]
extra_fields = sum(len(r) > len(header) for r in body)
fixed = [[r[0], r[1] + "," + r[2]] + r[3:] if len(r) > len(header) else r for r in body]
dupes = sum(r in fixed[:i] for i, r in enumerate(fixed))
blank_ticker = sum(not r[0].strip() for r in fixed)
spaced_ticker = sum(r[0].strip() != r[0].replace(" ", "") for r in fixed)
c1 = pd.DataFrame(fixed, columns=header)
c1_nodup = c1[~c1.duplicated()].copy()


def to_num(v):
    v = str(v).strip()
    if v in ("", "-"):
        return 0.0
    neg = v.startswith("(") and v.endswith(")")
    v = v.strip("()").replace(",", "")
    mult = 1
    m = re.fullmatch(r"([\d.]+)\s*([MK])", v)
    if m:
        v, mult = m.group(1), {"M": 1e6, "K": 1e3}[m.group(2)]
    return (-1 if neg else 1) * float(v) * mult


def naive_sum(series):
    """What Excel's SUM gives if text cells are left as text (they are ignored)."""
    out = 0.0
    for v in series:
        try:
            out += float(str(v).strip())
        except ValueError:
            pass
    return out


cash18 = c1_nodup[c1_nodup.Year == "2018"].Cash
q1 = "XL-ETL1"
question(f"{q1}-01", "Excel", "ETL case 1: balance sheet data", F1, "Data profiling & cleaning", 4,
         "Open the CSV and identify the data problems. How many rows have more fields than the header (a comma inside a company name that is not in quotes)? How many rows are exact duplicates of an earlier row? How many rows have a blank Ticker?",
         [Num("Rows with too many fields", extra_fields),
          Num("Exact duplicate rows", dupes),
          Num("Rows with a blank Ticker", blank_ticker,
              mistakes=[(blank_ticker + spaced_ticker, "That includes tickers with spaces inside (e.g. 'A M Z N'). Those are malformed but not blank.")])])

question(f"{q1}-02", "Excel", "ETL case 1: balance sheet data", F1, "Data profiling & cleaning", 6,
         "Clean the Cash column: convert values written as '20500 M' (millions) or '900 K' (thousands) to full dollar amounts and remove the duplicate row. What is total Cash for 2018 across all companies, in dollars?",
         [Num("Total 2018 Cash (dollars)", cash18.map(to_num).sum(),
              mistakes=[(naive_sum(cash18), "Your total skips the cells written with M or K. SUM ignores text, so convert those to numbers first."),
                        (c1[c1.Year == "2018"].Cash.map(to_num).sum(), "Your total includes the duplicate row. Remove exact duplicates first.")])],
         note="Watch the Apple rows: the unquoted comma in 'Apple, Inc.' shifts every value one column to the right.")

dep = c1_nodup["Total Depreciation"]
question(f"{q1}-03", "Excel", "ETL case 1: balance sheet data", F1, "Data profiling & cleaning", 5,
         "Total Depreciation uses two formats for negative numbers: a minus sign and parentheses, e.g. (14200000000). Convert all values to proper negative numbers and remove the duplicate row. What is the sum of Total Depreciation across all rows?",
         [Num("Sum of Total Depreciation", dep.map(to_num).sum(),
              mistakes=[(naive_sum(dep), "Your sum skips the values in parentheses, which are stored as text. Convert them to negative numbers first."),
                        (c1["Total Depreciation"].map(to_num).sum(), "Your sum includes the duplicate row. Remove it first.")])])

# ---------- Case 2: text extraction ----------
F2 = "Analytics_mindset_case_studies_ETL_Case2_Excel.xlsx"
c2 = pd.read_excel(FILES / F2, sheet_name="Case 2")
c2[["Loc", "Emp", "Plant", "Pay"]] = c2.EmployeeCode.str.extract(r"^([A-Z]{3})(\d+)-(\d+)([WM])$")
c2["LP"] = c2.Loc + "-" + c2.Plant
q2 = "XL-ETL2"
jap = c2[c2.Loc == "JAP"]
question(f"{q2}-01", "Excel", "ETL case 2: employee codes", F2, "Text functions & extraction", 4,
         "Split EmployeeCode (e.g. JAP1080-19M) into Location, EmpID, PlantID and PayPeriod. How many employees work in Japan, and how many of them are paid weekly?",
         [Num("Employees in Japan (JAP)", len(jap)), Num("Of these, paid weekly (W)", (jap.Pay == "W").sum())],
         note="LEFT for Location, MID for EmpID, MID + FIND(\"-\") for PlantID, RIGHT for PayPeriod.")

lp = c2.LP.value_counts()
question(f"{q2}-02", "Excel", "ETL case 2: employee codes", F2, "Text functions & extraction", 5,
         "Create the LocationPlantID (Location and PlantID joined with a hyphen, e.g. USA-12). How many distinct LocationPlantIDs are there? Which one has the most employees, and how many?",
         [Num("Distinct LocationPlantIDs", c2.LP.nunique(),
              mistakes=[(c2.Plant.nunique(), "That is the number of distinct PlantIDs. Plant numbers repeat across countries, which is why the combined ID is needed.")]),
          Text("LocationPlantID with most employees", lp.index[0]),
          Num("Employees at that plant", lp.iloc[0])])

question(f"{q2}-03", "Excel", "ETL case 2: employee codes", F2, "Text functions & extraction", 4,
         "Hash total: after extracting EmpID, what is the sum of all EmpIDs? (Accountants use a sum of an ID column as a control total to prove that every record was transferred.)",
         [Num("Sum of EmpID", c2.Emp.astype(int).sum(),
              mistakes=[(0, "SUM returns 0 because MID returns text. Wrap it in VALUE() or multiply by 1.")])])

# ---------- Case 3: messier codes ----------
F3 = "Analytics_mindset_case_studies_ETL_Case3_Excel.xlsx"
c3 = pd.read_excel(FILES / F3, sheet_name="Case 3 data")
c3[["Loc", "Emp", "Plant", "Pay"]] = c3.EmployeeCode.str.extract(r"^([A-Za-z]+)(\d+)-(\d+)([A-Za-z]+)$")
c3["P"] = c3.Pay.str[0]
c3["LP"] = c3.Loc + "-" + c3.Plant
q3 = "XL-ETL3"
question(f"{q3}-01", "Excel", "ETL case 3: messy employee codes", F3, "Text functions & extraction", 5,
         "In case 3 the pay period is recorded as W or We (weekly) and M or Mo (monthly). How many employees are paid monthly, and how many weekly?",
         [Num("Monthly (M or Mo)", (c3.P == "M").sum(),
              mistakes=[((c3.Pay == "M").sum(), "You only counted 'M'. 'Mo' also means monthly."),
                        ((c3.Pay == "Mo").sum(), "You only counted 'Mo'. 'M' also means monthly.")]),
          Num("Weekly (W or We)", (c3.P == "W").sum())])

question(f"{q3}-02", "Excel", "ETL case 3: messy employee codes", F3, "Text functions & extraction", 6,
         "Location codes now have different lengths (e.g. US, ARG, Canada, Japan), so LEFT with a fixed length does not work. Extract the Location. How many employees work in Canada, and how many employees in Japan are paid weekly?",
         [Num("Employees in Canada", (c3.Loc == "Canada").sum()),
          Num("Japan, paid weekly", ((c3.Loc == "Japan") & (c3.P == "W")).sum())],
         note="Hint: find the position of the first digit, e.g. with MIN(FIND({0,1,2,3,4,5,6,7,8,9}, code&\"0123456789\")).")

question(f"{q3}-03", "Excel", "ETL case 3: messy employee codes", F3, "Text functions & extraction", 5,
         "Extract EmpID and build LocationPlantID (e.g. US-15). What is the hash total (sum) of EmpID, and how many distinct LocationPlantIDs are there?",
         [Num("Sum of EmpID", c3.Emp.astype(int).sum(), mistakes=[(0, "SUM returns 0 because the extracted IDs are text. Use VALUE().")]),
          Num("Distinct LocationPlantIDs", c3.LP.nunique())])

# ---------- Case 4: joining data ----------
F4 = "Analytics_mindset_case_studies_ETL_Case4_Excel.xlsx"
x = pd.read_excel(FILES / F4, sheet_name=None)
je, bu, src = x["JELineItems"], x["BusinessUnits"], x["Source"].drop_duplicates("SourceID")
coa, pi = x["ChartOfAccounts"].iloc[:, :4], x["PreparerInfo"]
j = (je.merge(bu, on="BusinessUnitID", how="left").merge(coa, on="GLAccountNumber", how="left")
       .merge(src, on="SourceID", how="left").merge(pi, on=["PreparerID", "BusinessUnitID"], how="left"))
assert len(j) == len(je)
wrong_pi = je.merge(pi.drop_duplicates("PreparerID"), on="PreparerID", how="left")
q4 = "XL-ETL4"
at = j.groupby("AccountType").Amount.sum()
question(f"{q4}-01", "Excel", "ETL case 4: journal entries", F4, "Joins & lookups", 5,
         "Look up AccountType for every journal entry line from the ChartOfAccounts tab. What is the total Amount for Revenue accounts and for Expenses accounts?",
         [Num("Total Amount, Revenue", at["Revenue"], 2), Num("Total Amount, Expenses", at["Expenses"], 2)],
         note="Two GL account numbers are stored as text (e.g. 70300-HP). Make sure your lookup matches them too.")

name = "Carolyn Slater"
right_n = j.PreparerName.fillna("").str.startswith(name).sum()
wrong_n = wrong_pi.PreparerName.fillna("").str.startswith(name).sum()
question(f"{q4}-02", "Excel", "ETL case 4: journal entries", F4, "Joins & lookups", 6,
         f"Look up PreparerName. PreparerID is not unique: it restarts in every business unit, so the key is PreparerID + BusinessUnitID. How many journal entry lines were prepared by {name}, and how many lines have no matching preparer?",
         [Num(f"Lines prepared by {name}", right_n,
              mistakes=[(wrong_n, "You matched on PreparerID only. The same ID belongs to different people in different business units. Match on PreparerID and BusinessUnitID together (INDEX/MATCH with two criteria).")]),
          Num("Lines with no matching preparer", j.PreparerName.isna().sum(),
              mistakes=[(wrong_pi.PreparerName.isna().sum(), "With a one-key lookup every line finds someone, but often the wrong person. Use both keys.")])])

srcs = j.Source.value_counts()
question(f"{q4}-03", "Excel", "ETL case 4: journal entries", F4, "Joins & lookups", 4,
         "Look up the Source description for each line. Which source has the most journal entry lines, and how many? What is the total debit amount (control total) across all lines?",
         [Text("Source with most lines", srcs.index[0]), Num("Lines from that source", srcs.iloc[0]),
          Num("Total debits", je.Debit.sum(), 2, mistakes=[(je.Amount.sum(), "That is the net Amount, which is 0 because debits equal credits. Sum the Debit column.")])])

ac = j.groupby("AccountClass").Amount.sum()
bu_n = j.groupby("BusinessUnit").size()
question(f"{q4}-04", "Excel", "ETL case 4: journal entries", F4, "Joins & lookups", 5,
         "Add AccountClass and BusinessUnit to the flat file. What is the total Amount for the account class Sales-Hotel, and how many lines belong to the HOTEL business unit?",
         [Num("Total Amount, Sales-Hotel", ac["Sales-Hotel"], 2), Num("Lines in HOTEL business unit", bu_n["HOTEL"])])

# ---------- Quick questions (fit the 8-minute exam format) ----------
question(f"{q1}-04", "Excel", "ETL case 1: balance sheet data", F1, "Data profiling & cleaning", 2,
         "How many data rows does the file have, and how many different companies (by Name) after fixing the Apple rows?",
         [Num("Data rows", len(body), mistakes=[(len(raw), "Off by one: the header row is not a data row.")]),
          Num("Different companies", c1.Name.nunique())])

question(f"{q2}-04", "Excel", "ETL case 2: employee codes", F2, "Text functions & extraction", 2,
         "Using the last character of EmployeeCode (RIGHT), how many employees are paid monthly (M)? How many work in the USA?",
         [Num("Paid monthly", (c2.Pay == "M").sum()), Num("Employees in USA", (c2.Loc == "USA").sum())])

question(f"{q3}-04", "Excel", "ETL case 3: messy employee codes", F3, "Text functions & extraction", 3,
         "How many employees have a location code that is not exactly three characters long (e.g. US, Canada, Japan)?",
         [Num("Employees with a non-3-character location", (c3.Loc.str.len() != 3).sum(),
              mistakes=[((c3.Loc.str.len() > 3).sum(), "That misses the two-letter code US. Count codes shorter and longer than three characters.")])])

question(f"{q4}-05", "Excel", "ETL case 4: journal entries", F4, "Data profiling & cleaning", 2,
         "How many journal entry lines are in JELineItems, and how many different journal entries (distinct JENumber)?",
         [Num("Journal entry lines", len(je)), Num("Distinct JENumber", je.JENumber.nunique(),
                                                     mistakes=[(len(je), "That counts lines. Each journal entry has at least two lines (debit and credit). Count distinct JENumber.")])])

question(f"{q4}-06", "Excel", "ETL case 4: journal entries", F4, "Group & aggregate", 2,
         "Control totals: what is the sum of the Credit column, and the sum of the Amount column?",
         [Num("Sum of Credit", je.Credit.sum(), 2), Num("Sum of Amount", je.Amount.sum(), 2)],
         note="Debits and credits should balance, so the Amount column should net to zero.")
