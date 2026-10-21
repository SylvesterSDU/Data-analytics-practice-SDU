"""Excel part 1: PwC assignment, NYC film permits (cross-checked against solutions.xlsx)."""
import pandas as pd

from .common import FILES, Date, Num, Text, question

F = "NYC_Film_Permits.xlsx"
SRC = "NYC film permits"
d = pd.read_excel(FILES / F)
s = d[d.EventType == "Shooting Permit"].copy()
ALL_TYPES = "That figure includes all event types. Filter EventType to Shooting Permit first."


def q(n, topic, minutes, prompt, checks, note=None):
    question(f"XL-NYC-{n:02d}", "Excel", SRC, F, topic, minutes, prompt, checks, note)


q(1, "Data profiling & cleaning", 2,
  "How many records (data rows) and how many columns does the permits table have?",
  [Num("Number of records", len(d), mistakes=[(len(d) + 1, "Off by one: the header row is not a record.")]),
   Num("Number of columns", d.shape[1])])

zip_ok = d.ZipCode.dropna()
invalid = int(((zip_ok < 10000) | (zip_ok > 99999)).sum())
q(2, "Data profiling & cleaning", 3,
  "Profile the ZipCode column. How many records have a missing zip code, and how many have a value that is not a valid 5-digit zip code?",
  [Num("Records with missing zip code", d.ZipCode.isna().sum()),
   Num("Records with an invalid zip code", invalid,
       mistakes=[(invalid + d.ZipCode.isna().sum(), "That count includes the blanks. Count missing and invalid values separately.")])])

const = [c for c in d if d[c].nunique(dropna=False) == 1][0]
q(3, "Data profiling & cleaning", 2,
  "Which column has the same value in every record? Give the exact column name.",
  [Text("Column name", const)])

q(4, "Dates & durations", 3,
  "What are the oldest and the newest EnteredOn values? Give the full date and time.",
  [Date("Oldest EnteredOn", d.EnteredOn.min(), with_time=True),
   Date("Newest EnteredOn", d.EnteredOn.max(), with_time=True)],
  note="Dates can be typed as 2011-12-07 16:38 or 12/7/2011 16:38.")

et = d.EventType.value_counts()
q(5, "Group & aggregate", 3,
  "How many different event types are there? Which is the most common, and how many records does it have?",
  [Num("Number of event types", d.EventType.nunique()),
   Text("Most common event type", et.index[0]),
   Num("Records of that type", et.iloc[0])])

cat = s.Category.value_counts()
q(6, "Group & aggregate", 3,
  "Considering shooting permits only: what is the most common category, and how many shooting permits does it have?",
  [Text("Most common category", cat.index[0]),
   Num("Shooting permits in that category", cat.iloc[0],
       mistakes=[((d.Category == cat.index[0]).sum(), ALL_TYPES)])])

student = s[s.SubCategoryName == "Student Film"]
q(7, "Filter & count", 3,
  "Filter the permits to shooting permits for student films. How many are there, and how many of them are in Brooklyn?",
  [Num("Student-film shooting permits", len(student),
       mistakes=[((d.Category == "Student").sum(),
                  "That is Category = Student across all event types. Restrict EventType to Shooting Permit, or use SubCategoryName = Student Film."),
                 (len(student) + 1, "Off by one: did you include the header row in your count?")]),
   Num("Of these, in Brooklyn", (student.Borough == "Brooklyn").sum(),
       mistakes=[((d[d.Category == "Student"].Borough == "Brooklyn").sum(), ALL_TYPES)])])

multi = s["CommunityBoard(s)"].astype(str).str.contains(",")
multi_all = d["CommunityBoard(s)"].astype(str).str.contains(",")
q(8, "Text functions & extraction", 4,
  "What percentage of shooting permits required approval by more than one Community Board? (Several boards are listed in one cell, separated by commas.) Give the percentage with two decimals.",
  [Num("Percentage of shooting permits", multi.mean() * 100, 2, percent=True,
       mistakes=[(multi_all.mean() * 100, ALL_TYPES), (multi.sum(), "That is the count. The question asks for a percentage of all shooting permits.")])])

yr = pd.crosstab(s.StartDateTime.dt.year, s.Borough)
first = int(yr.index[(yr.Brooklyn > yr.Manhattan)][0])
yr_e = pd.crosstab(s.EnteredOn.dt.year, s.Borough)
q(9, "Group & aggregate", 4,
  "In what year (based on StartDateTime) did the number of shooting permits in Brooklyn first exceed the number in Manhattan? How many Brooklyn shoots were there that year?",
  [Num("Year", first),
   Num("Brooklyn shooting permits that year", yr.loc[first, "Brooklyn"],
       mistakes=[(yr_e.loc[first, "Brooklyn"] if first in yr_e.index else -1,
                  "That count is based on EnteredOn. Use the year of StartDateTime.")])])

man = s[s.Borough == "Manhattan"]
bway = man.ParkingHeld.str.contains("BROADWAY", case=False)
q(10, "Text functions & extraction", 4,
  "What percentage of Manhattan shooting permits take place on or near Broadway (the ParkingHeld text mentions BROADWAY)? Round to the nearest percent.",
  [Num("Percentage", bway.mean() * 100, 0, percent=True,
       mistakes=[(bway.sum() / len(s) * 100, "You divided by all shooting permits. The base is Manhattan shooting permits only.")]),
   Num("Number of Manhattan permits mentioning Broadway", bway.sum())])

foreign = s[(s.Country != "United States of America") & (s.EnteredOn.dt.year >= 2013)]
q(11, "Filter & count", 3,
  "How many shooting permit applications entered in 2013 or later came from a country other than the United States?",
  [Num("Foreign applications since 2013", len(foreign),
       mistakes=[((s.Country != "United States of America").sum(), "That count covers all years. Add the EnteredOn filter (2013 or later).")])])

dur_h = (s.EndDateTime - s.StartDateTime).dt.total_seconds() / 3600
dur_all = (d.EndDateTime - d.StartDateTime).dt.total_seconds() / 3600
q(12, "Dates & durations", 4,
  "What is the average duration of a shooting permit in hours (EndDateTime minus StartDateTime)? Give one decimal.",
  [Num("Average duration (hours)", dur_h.mean(), 1,
       mistakes=[(dur_all.mean(), ALL_TYPES), (dur_h.mean() / 24, "That is in days. Multiply the date difference by 24 to get hours.")])],
  note="In Excel, subtracting two date-times gives days. Multiply by 24 for hours.")

q(13, "Dates & durations", 4,
  "What were the durations of the shortest and the longest shooting permit? Give the shortest in minutes and the longest in hours (one decimal).",
  [Num("Shortest (minutes)", dur_h.min() * 60),
   Num("Longest (hours)", dur_h.max(), 1, mistakes=[(dur_h.max() / 24, "That is in days. Multiply by 24.")])])

lead = (s.StartDateTime - s.EnteredOn).dt.total_seconds() / 86400
lead_all = (d.StartDateTime - d.EnteredOn).dt.total_seconds() / 86400
q(14, "Dates & durations", 3,
  "What is the average lead time in days between entering a shooting permit (EnteredOn) and its start (StartDateTime)? Round to the nearest day.",
  [Num("Average lead time (days)", lead.mean(), 0, mistakes=[(lead_all.mean(), ALL_TYPES)])])

wd = s.StartDateTime.dt.day_name().value_counts()
q(15, "Dates & durations", 3,
  "On which day of the week do most shooting permits start, and how many start on that day?",
  [Text("Day of the week (full name)", wd.index[0]),
   Num("Shooting permits starting that day", wd.iloc[0])],
  note="Excel: =TEXT(date,\"dddd\") or WEEKDAY().")


def touches_friday(r):
    days = pd.date_range(r.StartDateTime.normalize(), r.EndDateTime.normalize())
    return any(x.dayofweek == 4 for x in days)


fri = s.apply(touches_friday, axis=1)
fri_start = (s.StartDateTime.dt.dayofweek == 4)
q(16, "Dates & durations", 6,
  "What percentage of shooting permits include shooting on at least part of a Friday (the permit starts on, ends on, or spans a Friday)? Give two decimals.",
  [Num("Percentage", fri.mean() * 100, 2, percent=True,
       mistakes=[(fri_start.mean() * 100, "That only counts permits that start on a Friday. Permits that end on or run through a Friday also count.")])])

zips = s.ZipCode.value_counts()
q(17, "Sort & top-N", 3,
  "Which zip code has the most shooting permits, and how many? What is the second-most common zip code?",
  [Text("Top zip code", int(zips.index[0])), Num("Shooting permits in that zip code", zips.iloc[0],
                                                   mistakes=[(d.ZipCode.value_counts().iloc[0], ALL_TYPES)]),
   Text("Second zip code", int(zips.index[1]))])

tv_q = s[(s.Borough == "Queens") & (s.Category == "Television") & (s.StartDateTime.dt.year == 2016)]
q(18, "Filter & count", 3,
  "How many shooting permits for Television started in Queens in 2016?",
  [Num("Permits", len(tv_q),
       mistakes=[(((d.Borough == "Queens") & (d.Category == "Television") & (d.StartDateTime.dt.year == 2016)).sum(), ALL_TYPES),
                 (((s.Borough == "Queens") & (s.Category == "Television") & (s.EnteredOn.dt.year == 2016)).sum(),
                  "That uses EnteredOn. The question asks when the shoot started (StartDateTime).")])])
