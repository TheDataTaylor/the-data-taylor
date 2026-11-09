---
name: votd-wrapped
description: >-
  Rebuild the VOTD Wrapped slideshow page from the Tableau Public Viz of the
  Day spreadsheet. Use when the user supplies updated VOTD data, an .xlsx of
  VOTD rows, or asks to re-run or refresh VOTD Wrapped.
---

# VOTD Wrapped

Rebuild `votd-wrapped-2026.html` from the VOTD spreadsheet. Do not edit the embedded `DATA` object by hand, and do not rewrite `template.html` unless the user asked for a design change.

## Run

From the site root:

```bash
python .cursor/skills/votd-wrapped/scripts/build.py "<path-to.xlsx>" 2026 votd-wrapped-2026.html
```

Needs `pandas` and `openpyxl`. The default spreadsheet is:

`C:\Users\rober\OneDrive\Documents\Tableau Portfolio\Data\VOTD Data Output (Python).xlsx`

If the user attaches a different file, use that file. The year argument must match the `<YEAR>?` column (for 2026, the column is `2026?`).

## After the script

Read the printed output and tell the user:

- Flag vs `curatedAt` mismatches
- First-timers by flag vs by date (these should match)
- People without a profile photo
- Total VOTDs, unique people, top count, and the team line
- Any `WARNING` (a team member missing from the data is left off the slide)

Then open the page and confirm slide 2's count matches `total`, the logo link is still at the top right, and Back / Next still work.

## What the script already decides

- A row counts only when `<YEAR>?` is `Y`. `curatedAt` orders VOTDs and assigns the month.
- A person is one `authorProfileName`. Display names are repaired for mojibake and the most common spelling is used everywhere.
- A first-timer has no VOTD outside the year. Slide 5 lists everyone with 3 or more VOTDs in the year.
- Top 10s are `numberOfFavorites` and `viewCount`. Overall reactions are favourites + love + insightful + nominations.
- The team list is `TEAM` in `scripts/build.py`: Rob Taylor, Chris Westlake, Lisa Trescott, Agata Ketterick, Preethi Lodha, Eric Howard. Edit that list only when the user changes the team.

## Site template

`template.html` is the slideshow plus the site chrome: favicon, analytics, the square-logo link to `index.html` under the progress bar, extra top padding on full slides so that logo does not cover the grids, and the hosted-page thumbnail warning. Keep those when changing the template. `__DATA__` and `__YEAR__` must stay exactly as written; the script replaces them.

Thumbnails and profile photos load from public.tableau.com in the browser. A local file preview that blocks other sites will not show them. Do not HEAD-check thumbnail URLs; those requests 404 while GET works.
