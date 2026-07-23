#!/usr/bin/env python3
"""Generate an all-time GitHub contributions histogram SVG (one bar per year).

Usage: gen_all_time_contributions.py <login> <output.svg>
Requires env GITHUB_TOKEN with read access (public data is enough).
"""
import os
import sys
import json
import datetime
import urllib.request

API = "https://api.github.com/graphql"


def gql(token, query, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": "bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "profile-card-generator",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if data.get("errors"):
        raise SystemExit("GraphQL errors: " + json.dumps(data["errors"]))
    return data["data"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render(login, years, total, start_year, out):
    # GitHub light ("github") theme palette to match the other cards
    bg, border = "#fffefe", "#e4e2e2"
    title_color, text_color, sub_color = "#2f80ed", "#434d58", "#8b949e"
    bar_color = "#40c463"
    font = "'Segoe UI', Ubuntu, Sans-Serif"

    n = len(years)
    left, right, top, bottom = 45, 20, 58, 36
    plot_h, slot, bar_w = 150, 46, 26
    width = left + n * slot + right
    height = top + plot_h + bottom
    baseline = top + plot_h
    max_c = max((c for _, c in years), default=1) or 1

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" role="img" '
        f'aria-label="All-time contributions histogram">'
    )
    p.append(
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="6" '
        f'fill="{bg}" stroke="{border}"/>'
    )
    p.append(
        f'<text x="{left-20}" y="26" font-family="{font}" font-size="15" '
        f'font-weight="600" fill="{title_color}">GitHub contributions</text>'
    )
    p.append(
        f'<text x="{width-right}" y="26" text-anchor="end" font-family="{font}" '
        f'font-size="12" fill="{sub_color}">{total:,} since {start_year}</text>'
    )
    p.append(
        f'<line x1="{left-8}" y1="{baseline}.5" x2="{width-right}" y2="{baseline}.5" '
        f'stroke="{border}"/>'
    )

    for i, (y, c) in enumerate(years):
        bh = 0 if max_c == 0 else plot_h * c / max_c
        if c > 0 and bh < 2:
            bh = 2
        x = left + i * slot + (slot - bar_w) / 2
        by = baseline - bh
        p.append(
            f'<rect x="{x:.1f}" y="{by:.1f}" width="{bar_w}" height="{bh:.1f}" '
            f'rx="3" fill="{bar_color}"/>'
        )
        p.append(
            f'<text x="{x + bar_w/2:.1f}" y="{by-5:.1f}" text-anchor="middle" '
            f'font-family="{font}" font-size="10" fill="{text_color}">{c}</text>'
        )
        p.append(
            f'<text x="{x + bar_w/2:.1f}" y="{baseline+16:.1f}" text-anchor="middle" '
            f'font-family="{font}" font-size="10" fill="{sub_color}">{y}</text>'
        )

    p.append("</svg>")
    svg = "".join(p)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)
    print(f"Wrote {out}: {n} years, {total} total contributions")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: gen_all_time_contributions.py <login> <output.svg>")
    login, out = sys.argv[1], sys.argv[2]
    token = os.environ["GITHUB_TOKEN"]

    created = gql(token, "query($l:String!){user(login:$l){createdAt}}", {"l": login})
    start_year = int(created["user"]["createdAt"][:4])
    now = datetime.datetime.now(datetime.timezone.utc)
    end_year = now.year

    q = ("query($l:String!,$from:DateTime!,$to:DateTime!){"
         "user(login:$l){contributionsCollection(from:$from,to:$to){"
         "contributionCalendar{totalContributions}}}}")
    years = []
    for yr in range(start_year, end_year + 1):
        frm = f"{yr}-01-01T00:00:00Z"
        to = now.strftime("%Y-%m-%dT%H:%M:%SZ") if yr == end_year else f"{yr}-12-31T23:59:59Z"
        d = gql(token, q, {"l": login, "from": frm, "to": to})
        c = d["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        years.append((yr, c))

    total = sum(c for _, c in years)
    render(login, years, total, start_year, out)


if __name__ == "__main__":
    main()
