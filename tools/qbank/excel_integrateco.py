"""Excel part 3: IntegrateCo payroll (Parts 3 and 4)."""
import pandas as pd

from .common import FILES, Num, Text, name_forms, question

F15 = "Analytics_mindset_case_studies_IntegrateCo_2015payroll.xlsx"
F16 = "Analytics_mindset_case_studies_IntegrateCo_2016payroll.xlsx"
FJC = "Analytics_mindset_case_studies_IntegrateCo_jobcodes.csv"
FLOC = "Analytics_mindset_case_studies_IntegrateCo_locations.csv"
SRC = "IntegrateCo payroll"

p15 = pd.read_excel(FILES / F15)
p16 = pd.read_excel(FILES / F16)
jc = pd.read_csv(FILES / FJC, sep="|", dtype=str)
loc = pd.read_csv(FILES / FLOC, sep="|")

# Job / Project: 2-digit year, optional department (H/S), 3-digit job code, optional location code.
JOB_RE = r"^\d{2}[HS]?(\d{3})"
p15["JC"] = p15.Job.astype(str).str.extract(JOB_RE)[0]
p16["JC"] = p16.Project.astype(str).str.extract(JOB_RE)[0]
p15["JC_right3"] = p15.Job.astype(str).str[-3:]
p16["JC_right3"] = p16.Project.astype(str).str[-3:]
assert p15.JC.notna().all() and p16.JC.notna().all()
p15["Name"] = p15.First_Name + " " + p15.Last_Name
p15["Gross"] = p15.Reg_Pay + p15.OT_Pay
p15["Hrs"] = p15.Reg_Hrs + p15.OT_Hrs
p16["Hrs"] = p16.Hours + p16.OT_Hours
GROSS = " (2015 gross pay = Reg_Pay + OT_Pay.)"
REG_ONLY = "That uses Reg_Pay only. 2015 gross pay = Reg_Pay + OT_Pay."


def jc_forms(code):
    """Other ways to type a job code: 6, Service, 006 Service, 006 - Service."""
    desc = jc.set_index("Job_Code").Job_Description[code]
    return [str(int(code)), desc, f"{code} {desc}", f"{code} - {desc}", f"{int(code)} {desc}"]


RIGHT3 = "You took the last three characters. Location codes (B, SG, R) come after the job code. Extract the three digits after the year and the optional H/S."

question("XL-INT-01", "Excel", SRC, [F15, F16], "Group & aggregate", 3,
         "Noah says 2016 payroll was about $266,000 higher than 2015. Verify: what is total gross pay for the first six months of 2015 (Reg_Pay + OT_Pay) and of 2016 (Gross_Wages), and what is the difference?",
         [Num("2015 gross pay", p15.Gross.sum(), 2, mistakes=[(p15.Reg_Pay.sum(), "That is Reg_Pay only. Gross pay in 2015 = Reg_Pay + OT_Pay.")]),
          Num("2016 gross pay", p16.Gross_Wages.sum(), 2),
          Num("Difference (2016 - 2015)", p16.Gross_Wages.sum() - p15.Gross.sum(), 2,
              mistakes=[(p16.Gross_Wages.sum() - p15.Reg_Pay.sum(), "Your 2015 figure excludes overtime pay.")])])

g15 = p15.groupby("JC").agg(h=("Hrs", "sum"), g=("Gross", "sum"))
g16 = p16.groupby("JC").agg(h=("Hrs", "sum"), g=("Gross_Wages", "sum"))
r15 = p15.groupby("JC_right3").Gross.sum()
question("XL-INT-02", "Excel", SRC, [F15, F16, FJC], "Text functions & extraction", 6,
         "Extract the job code from Job (2015) and Project (2016). Format: 2-digit project year, optional department letter (H or S), 3-digit job code, optional location code. Examples: 14005, 15S002, 14S001SG, 15007B. What is 2015 gross pay for job code 001 (Office)?" + GROSS,
         [Num("2015 gross pay, job code 001", g15.loc["001", "g"], 2,
              mistakes=[(r15.get("001", -1), RIGHT3), (p15[p15.JC == "001"].Reg_Pay.sum(), REG_ONLY)])])

diff = (g16.g - g15.g.reindex(g16.index).fillna(0))
both = diff[g15.g.reindex(g16.index).fillna(0) > 0].sort_values(ascending=False)
question("XL-INT-03", "Excel", SRC, [F15, F16, FJC], "Group & aggregate", 8,
         "Build the job code comparison table (Part 3, Q1): hours and gross pay per job code for 2015 and 2016. Which job code has the largest gross pay difference (2016 - 2015) overall, and how large is it? Among job codes with pay in both years, which has the largest positive difference?",
         [Text("Job code with the largest difference overall", diff.idxmax(), accept=jc_forms(diff.idxmax())),
          Num("That difference", diff.max(), 2),
          Text("Largest positive difference, both years", both.index[0], accept=jc_forms(both.index[0]))],
         note="Type job codes as three digits, e.g. 005.")

rate = (g16.g / g16.h) - (g15.g / g15.h)
question("XL-INT-04", "Excel", SRC, [F15, F16, FJC], "Calculated fields (IF / CASE)", 6,
         "For job code 006 (Service), what is gross pay per hour in 2015 and in 2016 (gross pay divided by total hours, regular + overtime)? Give two decimals.",
         [Num("2015 pay per hour, 006", g15.loc["006", "g"] / g15.loc["006", "h"], 2,
              mistakes=[(g15.loc["006", "g"] / p15[p15.JC == "006"].Reg_Hrs.sum(), "You divided by regular hours only. Use regular + overtime hours.")]),
          Num("2016 pay per hour, 006", g16.loc["006", "g"] / g16.loc["006", "h"], 2,
              mistakes=[(g16.loc["006", "g"] / p16[p16.JC == "006"].Hours.sum(), "You divided by regular hours only. Use Hours + OT_Hours.")])])

ot = (p15.groupby(["Emp_No", "Name"]).agg(h=("OT_Hrs", "sum"), p=("OT_Pay", "sum")).reset_index())
ot = ot[ot.h > 0].sort_values("p", ascending=False)
question("XL-INT-05", "Excel", SRC, F15, "Sort & top-N", 5,
         "Part 4, Q1: Which employees earned overtime pay in the first six months of 2015? Show employees with more than zero overtime hours, sorted by overtime pay (highest first). How many employees are listed, and who earned the most overtime pay, and how much?",
         [Num("Employees with overtime", len(ot)), Text("Employee with most overtime pay", ot.iloc[0].Name, accept=name_forms(ot.iloc[0].Name)),
          Num("Overtime pay for that employee", ot.iloc[0].p, 2)])

otj = jc.merge(p15.groupby("JC").agg(h=("OT_Hrs", "sum"), p=("OT_Pay", "sum")).reset_index(),
               left_on="Job_Code", right_on="JC", how="left").fillna(0).sort_values("p", ascending=False)
otj_r3 = p15.groupby("JC_right3").OT_Pay.sum()
question("XL-INT-06", "Excel", SRC, [F15, FJC], "Joins & lookups", 6,
         "Part 4, Q2: List all 12 job codes from the job code table with their 2015 overtime hours and overtime pay, including codes with no overtime. Which job code has the most overtime pay, and how much? How many job codes have zero overtime?",
         [Text("Job code with most overtime pay (e.g. 001)", otj.iloc[0].Job_Code, accept=jc_forms(otj.iloc[0].Job_Code)),
          Num("Its overtime pay", otj.iloc[0].p, 2, mistakes=[(otj_r3.get(otj.iloc[0].Job_Code, -1), RIGHT3)]),
          Num("Job codes with zero overtime", (otj.p == 0).sum())])

ph = p16[p16.Employee_Number.isna()]
question("XL-INT-07", "Excel", SRC, F16, "Control & fraud tests", 3,
         "Part 4, Q3: How many 2016 transactions were entered without an employee number (\"phantom\" entries), and what is their total gross wage amount?",
         [Num("Phantom transactions", len(ph)), Num("Total gross wages of phantom entries", ph.Gross_Wages.sum(), 2)])

per = p15.groupby(["Name", "Pay_Date"]).agg(R=("Reg_Hrs", "sum"), O=("OT_Hrs", "sum")).reset_index()
bad = per[(per.R < 40) & (per.O > 0)]
row_level = p15[(p15.Reg_Hrs < 40) & (p15.OT_Hrs > 0)]
question("XL-INT-08", "Excel", SRC, F15, "Control & fraud tests", 7,
         "Part 4, Q4: Overtime should only be paid after 40 regular hours in a pay period. In 2015, how many employee/pay date combinations have overtime hours while total regular hours for that pay date were below 40? How many different employees does this involve? (Assume all pay on the same date is one pay period.)",
         [Num("Employee/pay date combinations", len(bad),
              mistakes=[(len(row_level), "You tested each row on its own. One employee has several job-code rows per pay date, so sum the regular hours per employee and pay date first (pivot table).")]),
          Num("Different employees", bad.Name.nunique())])

cost = p16.Gross_Wages + p16.SocSec_Medicare + p16.FUTA + p16.SUTA + p16.Work_Comp
question("XL-INT-09", "Excel", SRC, F16, "Calculated fields (IF / CASE)", 3,
         "Part 4, Q5: What was the total employee cost for all projects in 2016 (gross wages + Social Security/Medicare + FUTA + SUTA + workers' compensation)?",
         [Num("Total employee cost 2016", cost.sum(), 2,
              mistakes=[(p16.Gross_Wages.sum(), "That is gross wages only. Add the four employer cost columns."),
                        (cost.sum() - p16.Work_Comp.sum(), "You left out workers' compensation (Work_Comp).")])])

m16 = p16.merge(loc, on="Employee_Name", how="left")
bl = m16.groupby("Location").Gross_Wages.sum()
question("XL-INT-10", "Excel", SRC, [F16, FLOC], "Joins & lookups", 6,
         "Part 4, Q6: Load the pipe-delimited locations file and look up each 2016 row's location by employee name. What is total 2016 gross wages at location 1 and at location 2? How many 2016 rows find no location?",
         [Num("Gross wages, location 1", bl[1], 2), Num("Gross wages, location 2", bl[2], 2),
          Num("Rows with no location", m16.Location.isna().sum())],
         note="The file is pipe-delimited (|). In Excel use Data > From Text/CSV and choose | as the delimiter.")

mo = p15.groupby(p15.Pay_Date.dt.month).Gross.sum()
dev = mo - mo.mean()
mo_reg = p15.groupby(p15.Pay_Date.dt.month).Reg_Pay.sum()
dev_reg = mo_reg - mo_reg.mean()
question("XL-INT-11", "Excel", SRC, F15, "Dates & durations", 6,
         "Part 4, Q8: Total 2015 gross wages by month of Pay_Date. Which month is furthest above the six-month average, and by how much? How far below the average is June?" + GROSS,
         [Text("Month furthest above average (full name)", pd.Timestamp(2015, int(dev.idxmax()), 1).strftime("%B")),
          Num("Amount above average", dev.max(), 2, mistakes=[(dev_reg.max(), REG_ONLY)]),
          Num("June vs average (negative if below)", dev[6], 2, mistakes=[(dev_reg[6], REG_ONLY)])])

share = mo / mo.sum() * p16.Gross_Wages.sum()
share_reg = mo_reg / mo_reg.sum() * p16.Gross_Wages.sum()
question("XL-INT-12", "Excel", SRC, [F15, F16], "Multi-step queries", 6,
         "Part 4, Q10: The 2016 data has no dates. Estimate 2016 monthly gross wages by applying each month's share of 2015 gross wages to the 2016 total. What is the estimate for January 2016 and for May 2016?" + GROSS,
         [Num("Estimated January 2016", share[1], 2, mistakes=[(share_reg[1], REG_ONLY)]),
          Num("Estimated May 2016", share[5], 2, mistakes=[(share_reg[5], REG_ONLY)])])

# ---------- Quick questions (fit the 8-minute exam format) ----------
question("XL-INT-13", "Excel", SRC, [F15, F16], "Data profiling & cleaning", 2,
         "How many rows are in the 2015 payroll file and in the 2016 payroll file?",
         [Num("Rows 2015", len(p15), mistakes=[(len(p15) + 1, "Off by one: the header row is not a data row.")]),
          Num("Rows 2016", len(p16), mistakes=[(len(p16) + 1, "Off by one: the header row is not a data row.")])])

question("XL-INT-14", "Excel", SRC, F15, "Filter & count", 2,
         "In 2015, how many different pay dates are there, and how many different employees (Emp_No)?",
         [Num("Different pay dates", p15.Pay_Date.nunique()), Num("Different employees", p15.Emp_No.nunique(),
                                                                    mistakes=[(p15.Name.nunique(), "That counts names. Use Emp_No, the unique employee identifier.")] if p15.Name.nunique() != p15.Emp_No.nunique() else [])])

question("XL-INT-15", "Excel", SRC, [F15, F16], "Group & aggregate", 2,
         "What is total overtime pay in 2015 (OT_Pay), and total overtime hours in 2016 (OT_Hours)?",
         [Num("Total OT_Pay 2015", p15.OT_Pay.sum(), 2), Num("Total OT_Hours 2016", p16.OT_Hours.sum(), 2)])

ot16 = p16[p16.OT_Hours > 0]
question("XL-INT-16", "Excel", SRC, F16, "Filter & count", 3,
         "Filter the 2016 file to rows with overtime hours above zero. How many rows remain, and what are their total gross wages?",
         [Num("Rows with overtime", len(ot16)), Num("Gross wages of those rows", ot16.Gross_Wages.sum(), 2)])
