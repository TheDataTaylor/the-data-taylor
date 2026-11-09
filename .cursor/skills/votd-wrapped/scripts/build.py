#!/usr/bin/env python3
"""Usage: python scripts/build.py data.xlsx YEAR out.html [template.html]"""
import sys, json, html
from pathlib import Path
import pandas as pd

xlsx, year, out = sys.argv[1], sys.argv[2], sys.argv[3]
tpl = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).resolve().parent.parent / "template.html"
# Display names of the Tableau Public TUG team (matched case-insensitively; anyone with no VOTDs in the data is left off)
TEAM = ["Rob Taylor", "Chris Westlake", "Lisa Trescott", "Agata Ketterick", "Preethi Lodha", "Eric Howard"]

d = pd.read_excel(xlsx)
flag = f"{year}?"
print("columns:", list(d.columns))
assert flag in d.columns, f"No column named {flag!r}; columns are {list(d.columns)}"

def fix(s):  # repair mojibake (UTF-8 read as Windows-1252/Latin-1) in names and titles; leave good text alone
    try:
        return b"".join(c.encode("cp1252") if c.encode("cp1252", "ignore") else bytes([ord(c)]) for c in s).decode("utf-8")
    except Exception:
        return s

d["name"] = d.authorDisplayName.astype(str).map(fix).map(html.unescape)
d["title"] = d.title.astype(str).map(fix).map(lambda x: html.unescape(html.unescape(x)))
d["pid"] = d.authorProfileName.astype(str)      # a person = a profile name
d["when"] = pd.to_datetime(d.curatedAt, utc=True)   # published date of the VOTD
isy = d[flag].astype(str).str.upper() == "Y"
# Cross-check the flag column against the published date
mism = d[isy != (d.when.dt.year == int(year))]
print(f"flag vs curatedAt year: {len(mism)} mismatched rows" + (" " + str(mism[["title", "curatedAt", flag]].head(10).values.tolist()) if len(mism) else " (all agree)"))
y = d[isy].copy()
cnt = y.groupby("pid").size()
nm = d.groupby("pid").name.agg(lambda s: s.value_counts().index[0])
prior = set(d[~isy].pid)   # anyone with a VOTD outside the year
first_by_date = set(d.groupby("pid").when.min().loc[lambda s: s.dt.year == int(year)].index)   # same idea using dates
print("first-timers by flag vs by date:", len(set(cnt.index) - prior), len(first_by_date & set(cnt.index)))
first_timers = [p for p in cnt.index if p not in prior]       # first ever VOTD is in the year
first_single = [p for p in first_timers if cnt[p] == 1]
top = int(cnt.max())

def tot(c):
    return int(pd.to_numeric(y[c], errors="coerce").fillna(0).sum()) if c in y else 0

res = dict(
    tot=dict(views=tot("viewCount"), favs=tot("numberOfFavorites"), love=tot("reaction_Love"), insightful=tot("reaction_Insightful"), nominate=tot("reaction_Nominate")),
    total=len(y), people=int(cnt.size), top_n=top, top=[nm[p] for p in cnt[cnt == top].index],
    dist={int(k): int(v) for k, v in cnt.value_counts().sort_index().items()},
    first_timers=len(first_timers), first_single=len(first_single), returning=int(cnt.size) - len(first_timers),
)
y = y.sort_values("when")   # oldest to newest by published date
ftset = set(first_timers)
prof = d.dropna(subset=["Profile_URL"]).sort_values("when", ascending=False).groupby("pid").Profile_URL.first()   # newest public profile link per person
rows = [dict(
    n=nm[r["pid"]], t=r["title"], u=r["Thumbnail_URL"], w=r["Workbook_Link"], p=r["pid"], f=int(r["numberOfFavorites"]),
    v=int(r["viewCount"]), ft=r["pid"] in ftset, d=r["when"].strftime("%Y-%m-%d"), pu=prof.get(r["pid"]),
    rx=[int(r.get(c, 0) or 0) for c in ("reaction_Love", "reaction_Insightful", "reaction_Nominate")],
) for _, r in y.iterrows()]
avatar = d.dropna(subset=["avatarUrl"]).sort_values("when", ascending=False).groupby("pid").avatarUrl.first()   # newest photo per person
people = [dict(id=p, n=nm[p], c=int(cnt[p]), ft=p in ftset, av=avatar.get(p), pu=prof.get(p)) for p in cnt.index]
print("people without a profile photo:", sum(1 for p in people if not p["av"]), "of", len(people))
team = []
for n in TEAM:
    m = d[d.name.str.strip().str.lower() == n.lower()]
    if m.empty:
        print(f"WARNING: {n} not found in the data, left off the team slide")
        continue
    av = m.avatarUrl.dropna()
    team.append(dict(n=n, ps=sorted(set(m.pid)), yr=int((m.when.dt.year == int(year)).sum()), all=len(m), av=av.iloc[0] if len(av) else None, pu=prof.get(m.pid.iloc[0])))

def txt(v):
    if pd.isna(v):
        return None
    t = html.unescape(fix(str(v))).strip()
    return "\n".join(l.strip() for l in t.splitlines() if l.strip()) or None

need = set(cnt.index) | {p for m in team for p in m["ps"]}
latest = d.sort_values("when", ascending=False).groupby("pid").first()
allc = d.groupby("pid").size()
prof_data = {}
for p in need:
    r = latest.loc[p]
    prof_data[p] = dict(
        n=nm[p], bio=txt(r.get("bio")), org=txt(r.get("organization")), job=txt(r.get("Job_Title")),
        fol=int(r.get("totalNumberOfFollowers") or 0), fng=int(r.get("totalNumberOfFollowing") or 0), wb=int(r.get("visibleWorkbookCount") or 0),
        av=avatar.get(p), pu=prof.get(p), yr=int(cnt.get(p, 0)), all=int(allc[p]), ft=p in ftset,
    )
for m in team:
    m["pid"] = m["ps"][0]
print(res)
print(cnt.sort_values(ascending=False).head(8).rename(nm).to_string())
print("team:", [(m["n"], m["yr"], m["all"]) for m in team])
data = json.dumps(dict(res=res, rows=rows, people=people, team=team, prof=prof_data), ensure_ascii=False).replace("</", "<\\/")
page = tpl.read_text(encoding="utf-8").replace("__DATA__", data).replace("__YEAR__", str(year))
if "__DATA__" in page or "__YEAR__" in page:
    raise SystemExit("template still has a placeholder after the build")
Path(out).write_text(page, encoding="utf-8", newline="\n")
print("wrote", out)
