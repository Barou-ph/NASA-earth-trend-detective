# Who it is for, the problem, and who pays

> The "who pays" parts are **hypotheses to validate** through interviews. Nothing below is a market size or a customer quote.

## Audience
| Group | Role in the product |
|---|---|
| **Urban planning and environment officers, and the consultants who write their reports (EIA, ESG, climate adaptation)** | Primary users and likely buyers |
| Students, journalists, the public | Free tier: the guided "data detective" experience, drives adoption (the NASA challenge's own audience) |
| Environmental scientists worldwide | Not targeted: they already have Giovanni and the KNMI Climate Explorer |

Starting point: Vietnam (Ho Chi Minh City case, bilingual VI/EN, real satellite series for NO₂ and aerosols).

## Problem
Someone who must justify a greening target, a traffic measure or a heat plan has to show with numbers that a problem is getting worse.
The data exists, but getting from a NASA portal to a defensible statement takes several manual steps: find the variable, download a CSV,
clean error values, pick a test, correct for autocorrelation and for testing many indicators, and write a conclusion that does not overclaim.
Each step can silently go wrong (for example a raw file with `-9999` fill values turned a significant decrease into a slope of 13.4).

## What the product gives them
1. A **one-page brief per city**: which indicators are changing, by how much, and how far to trust each (evidence trust score).
2. **Directions to consider**, from a public rule table, shown only when the evidence is moderate or better.
3. **Honest caveats**: data gaps, model-based data, correlation is not causation.
4. The numbers behind it in an analysis lab, with a data-quality report for every series.

## Who might pay (to validate)
- Consultancies writing environmental, ESG or adaptation reports: per report.
- Environment and planning departments: yearly licence, several cities and users.
- Donor-funded projects that need baseline data.

## How to validate (before the pitch)
Interview 3 to 5 real people (a planning officer, an environmental consultant). Record: where they get stuck today, how long it takes,
what they would pay for, and one verbatim quote. Put the counts and the quote on the pitch slides in place of the bracketed placeholders.

## Deliberately not claimed
- No tree counts or cooling targets: that needs district-level surface temperature and vegetation data and an explicit, user-editable scenario with stated assumptions.
- No policy recommendations: the suggestions are directions to consider.
