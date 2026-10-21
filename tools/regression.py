"""Build site/data/regression.json: data interpretation exams for the restaurant case.

ETL: daily sales (sum of netTotal over the 15 menu items) merged with the weather
and game sheets, as the case asks. Each exam shows Excel-style regression output
(Data Analysis > Regression) and four interpretation questions with model answers.
Every number in the answers is taken from the fitted model.

Run:  python3 tools/regression.py
"""
import json
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
FILE = "restaurant_data.xlsm"

x = pd.read_excel(ROOT / "site" / "files" / FILE, sheet_name=None)
s, w, g = x["salesData"], x["weatherData"], x["gameData"]
d = (s.groupby("date").agg(sales=("netTotal", "sum"), sales_7=("netTotal_7", "sum"),
                           sales_28=("netTotal_28", "sum"), sales_364=("netTotal_364", "sum")).reset_index()
       .merge(w, on="date", how="left").merge(g[["date", "homeGame", "gameDay"]], on="date", how="left"))
d[["homeGame", "gameDay"]] = d[["homeGame", "gameDay"]].fillna(0).astype(int)
d["weekend"] = d.date.dt.dayofweek.isin([5, 6]).astype(int)
N_GAME, N_HOME = int(d.gameDay.sum()), int(d.homeGame.sum())
LAST = d.iloc[-1]
N_SAT = int((g.date.dt.dayofweek == 5).sum())
S364_GAME = d.loc[d.gameDay == 1, "sales_364"].mean()
S364_OTHER = d.loc[d.gameDay == 0, "sales_364"].mean()

LABEL = {"sales": "Sales", "tmax": "tmax", "tmin": "tmin", "prcp": "prcp", "snow": "snow", "gameDay": "gameDay",
         "homeGame": "homeGame", "weekend": "weekend", "sales_7": "sales_7", "sales_28": "sales_28",
         "sales_364": "sales_364", "sales_364:gameDay": "sales_364 × gameDay", "Intercept": "Intercept"}


def money(v, dec=0):
    return f"${v:,.{dec}f}" if v >= 0 else f"-${-v:,.{dec}f}"


def pfmt(p):
    return "below 0.001" if p < 0.001 else f"{p:.3f}"


def fit(formula):
    m = smf.ols(formula, d).fit()
    ci = m.conf_int()
    k = len(m.params) - 1
    out = {
        "formula": formula,
        "stats": [["Multiple R", m.rsquared ** 0.5], ["R Square", m.rsquared], ["Adjusted R Square", m.rsquared_adj],
                  ["Standard Error", m.mse_resid ** 0.5], ["Observations", int(m.nobs)]],
        "anova": {"df_reg": k, "df_res": int(m.df_resid), "ss_reg": m.ess, "ss_res": m.ssr,
                  "F": m.fvalue, "sigF": m.f_pvalue},
        "coefs": [[LABEL[n], m.params[n], m.bse[n], m.tvalues[n], m.pvalues[n], ci.loc[n, 0], ci.loc[n, 1]] for n in m.params.index],
    }
    return m, out


exams = []


def exam(title, scenario, formula, qa):
    m, out = fit(formula)
    exams.append({"id": f"REG{len(exams) + 1:02d}", "title": title, "scenario": scenario, "file": FILE, "minutes": 5,
                  "output": out, "questions": [{"q": q, "a": a} for q, a in qa(m)]})


BASE = ("Bob owns Larry's Commissary. Daily sales are the sum of netTotal over all menu items. "
        "The sales data has been merged with the weather and game data.")

exam("Temperature and sales", BASE + " Bob asks whether warmer days bring more sales. Regression of daily sales on tmax (°F).",
     "sales ~ tmax", lambda m: [
         ("Interpret the coefficient on tmax.",
          f"For each extra degree Fahrenheit of maximum temperature, daily sales are on average {money(m.params.tmax, 2)} higher. "
          f"A 10-degree warmer day is associated with about {money(10 * m.params.tmax)} more in sales."),
         ("Is the effect of temperature statistically significant at the 5% level?",
          f"Yes. The p-value is {pfmt(m.pvalues.tmax)}, below 0.05, and the 95% confidence interval "
          f"({money(m.conf_int().loc['tmax', 0], 2)} to {money(m.conf_int().loc['tmax', 1], 2)}) does not contain 0."),
         ("How much of the variation in daily sales does temperature explain? What does that mean for Bob?",
          f"R Square is {m.rsquared:.3f}: temperature explains only about {m.rsquared * 100:.1f}% of the day-to-day variation in sales. "
          "The effect is real but small. Temperature alone is a poor tool for planning ingredients and shifts."),
         ("Does the intercept have a meaningful interpretation here?",
          f"Not really. The intercept ({money(m.params.Intercept)}) is predicted sales at 0°F. The coldest day in the data is "
          f"{d.tmax.min():.0f}°F, so 0°F is outside the data and the intercept is just the line's starting point."),
     ])

exam("Game days", BASE + f" gameDay = 1 on the {N_GAME} days with a university football game (home or away), otherwise 0.",
     "sales ~ gameDay", lambda m: [
         ("Interpret the intercept and the coefficient on gameDay.",
          f"The intercept ({money(m.params.Intercept)}) is average daily sales on days without a game. "
          f"On game days sales are on average {money(m.params.gameDay)} higher, i.e. about {money(m.params.Intercept + m.params.gameDay)} per day."),
         ("Is the game-day effect significant? How sure can Bob be about its size?",
          f"It is significant (p {pfmt(m.pvalues.gameDay)}). But the 95% confidence interval is wide, "
          f"from {money(m.conf_int().loc['gameDay', 0])} to {money(m.conf_int().loc['gameDay', 1])}, because there are only {N_GAME} game days in the data."),
         ("Can Bob conclude that football games cause the higher sales?",
          f"Not from this regression alone. {N_SAT} of the {N_GAME} games are on Saturdays, so gameDay may partly pick up a normal weekend effect. "
          "That is omitted-variable bias. Adding a weekend variable would show how much of the effect is really the game."),
         ("What does R Square tell you here?",
          f"R Square = {m.rsquared:.3f}. Game days explain about {m.rsquared * 100:.1f}% of the variation in daily sales. "
          "The effect is large on the few game days, but there are so few of them that they explain little of the variation across the whole year."),
     ])

exam("Home games", BASE + f" homeGame = 1 on the {N_HOME} days with a home game, otherwise 0.",
     "sales ~ homeGame", lambda m: [
         ("Interpret the coefficient on homeGame.",
          f"On home-game days sales are on average {money(m.params.homeGame)} higher than on other days "
          f"({money(m.params.Intercept + m.params.homeGame)} vs {money(m.params.Intercept)})."),
         ("Why should Bob be careful with this estimate even though p is very small?",
          f"It rests on only {N_HOME} home-game days. One unusual day can move the coefficient a lot, and the 95% interval runs from "
          f"{money(m.conf_int().loc['homeGame', 0])} to {money(m.conf_int().loc['homeGame', 1])}."),
         ("Compare with the gameDay regression (all games). What does the difference suggest?",
          "The home-game effect is larger than the effect of games in general. That suggests the crowds in town on home-game days drive sales more than the game itself, "
          "but with so few observations this is a hypothesis to watch, not a firm conclusion."),
         ("Would you use homeGame to plan staffing? What would you add first?",
          "Yes, as an input for the few home-game days, which Bob knows in advance from the schedule. "
          "I would first add a weekend control so the home-game effect is not just a Saturday effect."),
     ])

exam("Rain and snow", BASE + " Regression of daily sales on precipitation (prcp, inches) and snow (inches).",
     "sales ~ prcp + snow", lambda m: [
         ("Are rain or snow significant drivers of sales?",
          f"No. The p-values are {pfmt(m.pvalues.prcp)} (prcp) and {pfmt(m.pvalues.snow)} (snow), far above 0.05. "
          "Both confidence intervals include 0."),
         ("Adjusted R Square is negative. What does that mean?",
          f"Adjusted R Square ({m.rsquared_adj:.3f}) corrects R Square ({m.rsquared:.4f}) for the number of variables. "
          "A negative value means the model explains less than its two variables should explain by chance alone: the model has no explanatory power."),
         ("Why are there fewer observations than days with sales data?",
          f"There are {int(m.nobs)} observations but {len(d)} days of sales. Some days have no precipitation or snow reading, "
          "and Excel's regression drops rows with missing values. These are gaps from the ETL merge."),
         ("What should Bob conclude?",
          "Weather in the form of rain or snow does not measurably change his sales. He does not need to adjust purchasing or shifts for forecast rain."),
     ])

pred7 = smf.ols("sales ~ sales_7", d).fit()
target = LAST.date + pd.Timedelta(days=7)
exam("Forecasting one week ahead", BASE + f" sales_7 is sales on the same weekday one week earlier. The last day in the data is "
     f"{LAST.date:%d %B %Y}, with sales of {money(LAST.sales)}. Bob wants a forecast for {target:%d %B %Y}.",
     "sales ~ sales_7", lambda m: [
         ("Write the regression equation and interpret the coefficient on sales_7.",
          f"Sales = {m.params.Intercept:,.2f} + {m.params.sales_7:.4f} × sales_7. Each extra dollar of sales on the same weekday last week is "
          f"associated with about {m.params.sales_7 * 100:.0f} cents more sales today."),
         (f"Forecast sales for {target:%d %B %Y}.",
          f"Use the last observed day as sales_7: {m.params.Intercept:,.2f} + {m.params.sales_7:.4f} × {LAST.sales:,.0f} = "
          f"{money(m.params.Intercept + m.params.sales_7 * LAST.sales)}."),
         ("How confident can Bob be in that forecast?",
          f"Moderately. R Square = {m.rsquared:.3f}, so last week's sales explain {m.rsquared * 100:.0f}% of the variation. "
          f"The standard error of {money(m.mse_resid ** 0.5)} means a typical day misses the forecast by roughly that much, "
          f"so a rough 95% range is ±{money(2 * m.mse_resid ** 0.5)}."),
         ("The coefficient is below 1. What does that mean?",
          "Sales revert towards the average: a very strong week is usually followed by a somewhat less extreme one, and vice versa."),
     ])

exam("Same day last year", BASE + " sales_364 is sales 364 days earlier: the same weekday, 52 weeks ago.",
     "sales ~ sales_364", lambda m: [
         ("Interpret the coefficient on sales_364.",
          f"Each extra dollar of sales on the same day last year is associated with {money(m.params.sales_364, 2)} more sales today."),
         ("Why use 364 days and not 365?",
          "364 days is exactly 52 weeks, so the comparison day is the same weekday. Weekday patterns are strong in restaurant sales "
          "(e.g. Sundays are almost always closed), so 365 days would compare different weekdays."),
         ("Compare R Square with the sales_7 model. Which predictor is better?",
          f"R Square is {m.rsquared:.3f} here vs {pred7.rsquared:.3f} with sales_7. Last year's same day explains more of the variation, "
          "because it captures seasonality (time of year, holidays, the football season)."),
         ("Is the relationship significant?",
          f"Yes. t = {m.tvalues.sales_364:.1f} and p {pfmt(m.pvalues.sales_364)}."),
     ])

exam("Last year's sales and game days", BASE + " The model includes sales_364, gameDay and their interaction (sales_364 × gameDay), "
     "as the case asks: how do sales one year ago interact with a game day?",
     "sales ~ sales_364 * gameDay", lambda m: [
         ("What does the interaction term sales_364 × gameDay measure?",
          "Whether the link between last year's sales and today's sales is different on game days. Its coefficient is the extra slope on sales_364 for game days."),
         ("Interpret the interaction coefficient and its p-value.",
          f"The coefficient is {m.params['sales_364:gameDay']:.4f} with p = {pfmt(m.pvalues['sales_364:gameDay'])}. "
          "The relationship between last year's and today's sales is no different on game days: there is no evidence of an interaction."),
         ("gameDay is not significant here, though it was on its own. Why?",
          f"Once sales_364 is in the model, much of the game-day effect is already captured: on game days, sales on the same day last year averaged {money(S364_GAME)} vs {money(S364_OTHER)} on other days. "
          f"Also, with the interaction included, gameDay ({money(m.params.gameDay)}, p = {pfmt(m.pvalues.gameDay)}) means the game effect when sales_364 = 0, "
          "which is not a realistic situation."),
         ("What would you tell Bob?",
          f"Use last year's sales (slope {m.params.sales_364:.3f}, p {pfmt(m.pvalues.sales_364)}) as the main predictor. "
          f"Adding game days and their interaction raises R Square only from about {smf.ols('sales ~ sales_364', d).fit().rsquared:.3f} to {m.rsquared:.3f}."),
     ])

exam("Maximum and minimum temperature", BASE + " Regression of daily sales on both tmax and tmin.",
     "sales ~ tmax + tmin", lambda m: [
         ("tmin has a negative coefficient. Does that mean colder nights increase sales?",
          f"No. tmax and tmin are highly correlated (correlation {d.tmax.corr(d.tmin):.2f}). With both in the model, each coefficient is the effect "
          "holding the other fixed, which hardly happens in practice. The negative sign is not significant "
          f"(p = {pfmt(m.pvalues.tmin)}) and is a symptom of multicollinearity."),
         ("Compare the tmax coefficient with the model that only has tmax.",
          f"It changes from {money(smf.ols('sales ~ tmax', d).fit().params.tmax, 2)} to {money(m.params.tmax, 2)} per degree, and its standard error "
          f"grows to {m.bse.tmax:.2f}. Correlated predictors make individual coefficients unstable."),
         ("Did adding tmin improve the model?",
          f"Barely. R Square rises to {m.rsquared:.3f}, Adjusted R Square is {m.rsquared_adj:.3f}, and tmin is not significant. Keep one temperature variable."),
         ("What is the F-test telling you here?",
          f"F = {m.fvalue:.2f} with Significance F = {pfmt(m.f_pvalue)}: the two variables together explain more than nothing, "
          "even though tmin on its own is not significant."),
     ])

exam("Weekends", BASE + " weekend = 1 on Saturdays and Sundays. Note: the restaurant is almost always closed on Sundays, "
     "so nearly all weekend observations are Saturdays.",
     "sales ~ weekend", lambda m: [
         ("Interpret the intercept and the weekend coefficient.",
          f"Average weekday sales are {money(m.params.Intercept)}. Weekend days sell on average {money(m.params.weekend)} more, "
          f"about {money(m.params.Intercept + m.params.weekend)} per day."),
         ("How many weekend observations are there, and why does that matter?",
          f"{int(d.weekend.sum())} of {len(d)} days, almost all Saturdays. The result describes Saturdays; it says nothing about Sunday trading."),
         ("Is the effect significant, and how much variation does it explain?",
          f"Yes (t = {m.tvalues.weekend:.1f}, p {pfmt(m.pvalues.weekend)}). R Square = {m.rsquared:.3f}, so the weekend effect alone explains {m.rsquared * 100:.0f}% of the variation."),
         ("How should Bob use this result?",
          "Schedule more staff and buy more ingredients for Saturdays. It is a predictable, recurring effect he can plan around every week."),
     ])

exam("Three lagged sales variables", BASE + " The model uses sales 7, 28 and 364 days earlier.",
     "sales ~ sales_7 + sales_28 + sales_364", lambda m: [
         ("Interpret the coefficient on sales_364 in this model.",
          f"Holding sales 7 and 28 days ago constant, each extra dollar of sales on the same day last year is associated with "
          f"{money(m.params.sales_364, 2)} more sales today."),
         ("Why is the sales_364 coefficient smaller here than in the single-variable model?",
          f"It falls from {smf.ols('sales ~ sales_364', d).fit().params.sales_364:.3f} to {m.params.sales_364:.3f}. The lags are correlated, "
          "so part of what sales_364 picked up alone is now credited to the recent lags."),
         ("Compare R Square and Adjusted R Square with the sales_364-only model.",
          f"R Square rises from {smf.ols('sales ~ sales_364', d).fit().rsquared:.3f} to {m.rsquared:.3f}, and Adjusted R Square to {m.rsquared_adj:.3f}. "
          "The extra variables add real explanatory power, not just noise."),
         ("Which variables are significant at 5%?",
          "All three: " + ", ".join(f"{v} (p {pfmt(m.pvalues[v])})" for v in ["sales_7", "sales_28", "sales_364"]) + "."),
     ])

exam("Temperature, game days and weekends", BASE + " Regression of daily sales on tmax, gameDay and weekend together.",
     "sales ~ tmax + gameDay + weekend", lambda m: [
         ("Interpret the coefficient on gameDay.",
          f"Holding temperature and weekend constant, game days have on average {money(m.params.gameDay)} more sales than other days (p = {pfmt(m.pvalues.gameDay)})."),
         ("In the gameDay-only model the effect was larger. Why did it shrink?",
          f"It drops from {money(smf.ols('sales ~ gameDay', d).fit().params.gameDay)} to {money(m.params.gameDay)}. {N_SAT} of the {N_GAME} games are on Saturdays, "
          "which are busy anyway. Without the weekend control, gameDay took credit for part of the Saturday effect: omitted-variable bias."),
         ("Which of the three variables matters most for Bob's planning?",
          f"Weekend has the largest and most precise effect ({money(m.params.weekend)}, t = {m.tvalues.weekend:.1f}). "
          f"Game days add {money(m.params.gameDay)} on top. Temperature is significant but small ({money(m.params.tmax, 2)} per degree)."),
         ("How good is the model overall?",
          f"R Square = {m.rsquared:.3f}, Adjusted R Square = {m.rsquared_adj:.3f}. It explains {m.rsquared * 100:.0f}% of the variation: "
          "better than any of the three alone, but much less than models with lagged sales."),
     ])

out = ROOT / "site" / "data" / "regression.json"
out.write_text(json.dumps({"exams": exams}, indent=1, default=float))
print(f"{len(exams)} regression exams -> {out.relative_to(ROOT)}")
for e in exams:
    print(e["id"], e["title"], "| R2 =", round(e["output"]["stats"][1][1], 3))
