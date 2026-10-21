"""SQL part 1: PwC assignment on the Chinook database (cross-checked against PWC answers.docx)."""
from datetime import datetime

from .common import Date, Num, Text, question, sql, val

C = "Chinook_Sqlite.sqlite"


def q(n, topic, minutes, prompt, checks, note=None):
    question(f"SQL-CHN-{n:02d}", "SQL", "Chinook", C, topic, minutes, prompt, checks, note)


q(1, "Data profiling & cleaning", 2,
  "How many columns does the Customer table have, and how many rows are in the Invoice table? How many customers list a company?",
  [Num("Columns in Customer", len(sql(C, "PRAGMA table_info(Customer)"))),
   Num("Rows in Invoice", val(C, "SELECT COUNT(*) FROM Invoice")),
   Num("Customers with a company", val(C, "SELECT COUNT(Company) FROM Customer"),
       mistakes=[(val(C, "SELECT COUNT(*) FROM Customer"), "COUNT(*) counts every row. COUNT(Company) skips NULLs, or add WHERE Company IS NOT NULL.")])])

first5 = sql(C, "SELECT Country FROM Customer LIMIT 5")
by_last = sql(C, "SELECT LastName FROM Customer ORDER BY LastName LIMIT 3")
q(2, "Sort & top-N", 2,
  "Select only the first 5 rows of the Customer table: what is the country in the last row? Then sort customers by last name: what is the last name in the third row?",
  [Text("Country in row 5", first5[-1][0]), Text("Last name in row 3", by_last[2][0])])

q(3, "Filter & count", 2,
  "How many invoices have a total greater than $10 and less than $20? How many have a billing country in Brazil, Argentina or Chile?",
  [Num("Invoices between $10 and $20", val(C, "SELECT COUNT(*) FROM Invoice WHERE Total > 10 AND Total < 20")),
   Num("Invoices from Brazil, Argentina or Chile", val(C, "SELECT COUNT(*) FROM Invoice WHERE BillingCountry IN ('Brazil','Argentina','Chile')"))])

q(4, "Text functions & extraction", 2,
  "How many invoices have a billing country that starts with the letter C? What is the length of the longest employee last name?",
  [Num("Invoices with country starting with C", val(C, "SELECT COUNT(*) FROM Invoice WHERE BillingCountry LIKE 'C%'"),
       mistakes=[(val(C, "SELECT COUNT(*) FROM Invoice WHERE BillingCountry LIKE '%C%'"), "LIKE '%C%' matches C anywhere. Starts with C is LIKE 'C%'.")]),
   Num("Longest employee last name (characters)", val(C, "SELECT MAX(LENGTH(LastName)) FROM Employee"),
       mistakes=[(val(C, "SELECT MAX(LENGTH(LastName)) FROM Customer"), "That is from the Customer table. The question asks about employees.")])])

emp = sql(C, "SELECT BirthDate, HireDate FROM Employee")
ages = []
for b, h in emp:
    b, h = datetime.fromisoformat(b), datetime.fromisoformat(h)
    ages.append(h.year - b.year - ((h.month, h.day) < (b.month, b.day)))
q(5, "Dates & durations", 4,
  "How many employees were born on a Sunday? How old was the oldest employee when hired, in completed years?",
  [Num("Employees born on a Sunday", val(C, "SELECT COUNT(*) FROM Employee WHERE strftime('%w', BirthDate) = '0'"),
       mistakes=[(val(C, "SELECT COUNT(*) FROM Employee WHERE strftime('%w', BirthDate) = '7'"), "strftime('%w') returns 0 for Sunday, not 7.")]),
   Num("Age at hire, completed years", max(ages), mistakes=[(max(ages) + 1, "You rounded up. Use completed years (the person had not yet had their next birthday).")])],
  note="SQLite: strftime('%w', date) gives the weekday (0 = Sunday); julianday() gives the difference between dates in days.")

dates = sql(C, "SELECT MIN(InvoiceDate), MAX(InvoiceDate) FROM Invoice", one=True)
q(6, "Dates & durations", 2,
  "What is the range of invoice dates covered by the database? Give the first and the last invoice date.",
  [Date("First invoice date", dates[0]), Date("Last invoice date", dates[1])])

rows = sql(C, "SELECT BillingCountry, SUM(Total) t FROM Invoice GROUP BY BillingCountry ORDER BY t DESC")
q(7, "Group & aggregate", 3,
  "Return a list of billing countries by the total value of their invoices, highest first.",
  [Num("Number of rows in your result", len(rows),
       mistakes=[(val(C, "SELECT COUNT(*) FROM Invoice"), "That is one row per invoice. You need GROUP BY BillingCountry.")]),
   Text("Country in the first row", rows[0][0]),
   Num("Invoice total for that country", rows[0][1], 2,
       mistakes=[(val(C, "SELECT COUNT(*) FROM Invoice WHERE BillingCountry = 'USA'"), "That looks like COUNT(*). The question asks for the value, so use SUM(Total).")])])

prices = dict(sql(C, "SELECT UnitPrice, COUNT(*) FROM InvoiceLine GROUP BY UnitPrice"))
q(8, "Group & aggregate", 3,
  "How many invoice line items are there, and how many distinct prices? How many downloads (invoice lines) were there at each price?",
  [Num("Invoice line items", val(C, "SELECT COUNT(*) FROM InvoiceLine")),
   Num("Distinct prices", val(C, "SELECT COUNT(DISTINCT UnitPrice) FROM InvoiceLine"),
       mistakes=[(val(C, "SELECT COUNT(DISTINCT UnitPrice) FROM Track"), "That counts prices in the Track table. Count prices actually used in InvoiceLine.")]),
   Num("Downloads at $0.99", prices[0.99]), Num("Downloads at $1.99", prices[1.99])])

per_track = sql(C, "SELECT c, COUNT(*) FROM (SELECT TrackId, COUNT(*) c FROM InvoiceLine GROUP BY TrackId) GROUP BY c ORDER BY c DESC")
q(9, "Multi-step queries", 4,
  "Which tracks have been downloaded the most? Find the highest number of downloads for a single track and how many tracks share it.",
  [Num("Highest downloads of one track", per_track[0][0]), Num("Tracks with that many downloads", per_track[0][1])],
  note="Count downloads per track in a subquery, then summarise that result.")

q(10, "Joins & lookups", 3,
  "How many distinct tracks and distinct albums have been downloaded at least once?",
  [Num("Distinct tracks downloaded", val(C, "SELECT COUNT(DISTINCT TrackId) FROM InvoiceLine"),
       mistakes=[(val(C, "SELECT COUNT(*) FROM InvoiceLine"), "That counts all invoice lines. Use COUNT(DISTINCT TrackId).")]),
   Num("Distinct albums downloaded", val(C, "SELECT COUNT(DISTINCT t.AlbumId) FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId"))])

genre = sql(C, "SELECT g.Name, COUNT(*) FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.Name ORDER BY 2 DESC")
q(11, "Joins & lookups", 4,
  "What is the most popular genre measured by downloads (invoice lines), and how many downloads does it have? Which genre is second?",
  [Text("Most popular genre", genre[0][0]), Num("Downloads", genre[0][1],
                                                  mistakes=[(val(C, "SELECT COUNT(*) FROM Track t JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = 'Rock'"),
                                                             "That is the number of Rock tracks in the catalogue. Count downloads: join InvoiceLine.")]),
   Text("Second genre", genre[1][0])])

rep = sql(C, "SELECT e.FirstName || ' ' || e.LastName, SUM(i.Total) FROM Invoice i JOIN Customer c ON c.CustomerId = i.CustomerId JOIN Employee e ON e.EmployeeId = c.SupportRepId GROUP BY e.EmployeeId ORDER BY 2 DESC")
q(12, "Joins & lookups", 5,
  "Which support representative (employee) is linked to the highest invoice total through their customers? Give the name and the total.",
  [Text("Employee (first and last name)", rep[0][0]), Num("Invoice total", rep[0][1], 2)],
  note="Invoice → Customer (CustomerId) → Employee (SupportRepId = EmployeeId).")

years = dict(sql(C, "SELECT strftime('%Y', InvoiceDate), SUM(Total) FROM Invoice GROUP BY 1"))
best = max(years, key=years.get)
q(13, "Dates & durations", 3,
  "Total invoice value per year: which year has the highest total, and what is it?",
  [Num("Year", int(best)), Num("Total", years[best], 2)])
