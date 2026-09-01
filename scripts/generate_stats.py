#!/usr/bin/env python3
"""Draw the profile README's stat graphics from the GitHub GraphQL API.

No third-party services and no dependencies - standard library only.

Outputs, all sharing one visual language with the portrait:
  hd-*.svg    the section headings, drawn in this page's own typeface
  stats.svg   hero total + weekly sparkline
  streak.svg  current and longest streak
  langs.svg   top languages, by bytes and by repository count
  year.svg    the year as a character map, in the portrait's own ramp

GitHub strips <script> and CSS from READMEs, so the headings have to be images
to carry the page's typeface, and motion has to be SMIL. Every file uses the
portrait's grey ink, a transparent background, and the same left-to-right
clipPath reveal.

Env:
  GITHUB_TOKEN  required
  GH_LOGIN      user to summarise (default: arqam365)
  OUT_DIR       where to write (default: <repo>/assets)
"""
import base64
import functools
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com/graphql"

# Two things are pinned for determinism:
#  * the contribution window, to whole UTC days - otherwise "the past year" is
#    measured from request time, days drift between week buckets, and the
#    sparkline moves a fraction of a pixel every night;
#  * privacy: PUBLIC on repositories - otherwise a personal token sees private
#    repos and a workflow token does not, so language totals disagree.
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 privacy: PUBLIC) {
      nodes {
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

# The portrait's ink is the data ink, so every graphic reads as one material.
LIGHT = dict(data="#6e7681", emph="#424a53", dim="#8c959f", rule="#d8dee4")
DARK = dict(data="#c9d1d9", emph="#f0f6fc", dim="#8b949e", rule="#30363d")
MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "&apos;Liberation Mono&apos;,monospace")
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

WIDTH = 620            # every graphic shares one column width
LEFT = 34              # shared left inset, so stacked blocks line up
REVEAL = 1.30          # seconds; matches the portrait's cadence
RAMP = [" ", ":", "+", "#", "@"]      # steps of the portrait's own ramp
MON = ["jan", "feb", "mar", "apr", "may", "jun",
       "jul", "aug", "sep", "oct", "nov", "dec"]

HEADINGS = ["about", "stack", "work", "stats", "about this page"]


@functools.lru_cache(maxsize=None)
def face(filename, weight):
    """One @font-face rule with the subset inlined as a data URI.

    An external font URL cannot work here: these SVGs are loaded through <img>,
    and browsers refuse to fetch subresources for an image document.
    """
    with open(os.path.join(FONT_DIR, filename), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def fonts(*weights):
    return "".join(face(f"jbmono-{w}.woff2", w) for w in weights)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def shell(height, body, weights=(400,)):
    """Common wrapper: transparent, ink that follows the colour scheme."""
    css = "".join(f".{k}{{fill:{v}}}" for k, v in
                  dict(d=LIGHT["data"], e=LIGHT["emph"],
                       m=LIGHT["dim"], r=LIGHT["rule"]).items())
    dark = "".join(f".{k}{{fill:{v}}}" for k, v in
                   dict(d=DARK["data"], e=DARK["emph"],
                        m=DARK["dim"], r=DARK["rule"]).items())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{height}" viewBox="0 0 {WIDTH} {height}" '
            f'font-family="{MONO}">'
            f"<style>{fonts(*weights)}{css}"
            f"@media(prefers-color-scheme:dark){{{dark}}}</style>"
            f"{body}</svg>")


def wipe(i, w, h, y=0, x=0, dur=REVEAL, delay=0.0):
    """Left-to-right clipPath reveal.

    The rect starts closed. Carrying the finished width as the base attribute
    would leave anything not yet animating fully drawn, so the graphic appears
    complete and then blanks and redraws.
    """
    return (f'<clipPath id="w{i}"><rect x="{x}" y="{y}" height="{h}" '
            f'width="0"><animate attributeName="width" from="0" to="{w}" '
            f'begin="{delay}s" dur="{dur}s" fill="freeze"/></rect></clipPath>')


# ---------------------------------------------------------------- data

def window():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    return (f"{start.isoformat()}T00:00:00Z", f"{today.isoformat()}T23:59:59Z")


def fetch(login, token):
    since, until = window()
    body = json.dumps({"query": QUERY,
                       "variables": {"login": login,
                                     "from": since, "to": until}}).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL: {payload['errors']}")
    return payload["data"]["user"]


def days_of(user):
    weeks = (user["contributionsCollection"]["contributionCalendar"]["weeks"])
    return [d for w in weeks for d in w["contributionDays"]]


def streaks(days):
    """Current and longest run of consecutive days with a contribution.

    Today counts as neutral while it is still in progress: a day with no
    contributions yet should not zero a live streak.
    """
    cur = best = run = 0
    for d in days:
        if d["contributionCount"] > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            cur += 1
        elif cur or d is not days[-1]:
            break
    return cur, best


def language_totals(user):
    by_bytes, by_repo = {}, {}
    for repo in user["repositories"]["nodes"]:
        edges = repo["languages"]["edges"]
        for e in edges:
            by_bytes[e["node"]["name"]] = (by_bytes.get(e["node"]["name"], 0)
                                           + e["size"])
        if edges:
            top = edges[0]["node"]["name"]
            by_repo[top] = by_repo.get(top, 0) + 1
    return by_bytes, by_repo


# ---------------------------------------------------------------- drawing

def draw_heading(text):
    h = 26
    body = (f'{wipe(0, WIDTH, h, dur=0.55)}'
            f'<g clip-path="url(#w0)">'
            f'<text x="0" y="15" class="e" font-size="14" font-weight="600" '
            f'letter-spacing="0.5">{esc(text)}</text>'
            f'<rect x="{len(text) * 8.4 + 16}" y="9" '
            f'width="{WIDTH - len(text) * 8.4 - 16}" height="1" class="r"/>'
            f"</g>")
    return shell(h, body, weights=(600,))


def draw_stats(user, days):
    total = (user["contributionsCollection"]["contributionCalendar"]
             ["totalContributions"])
    active = sum(1 for d in days if d["contributionCount"] > 0)
    weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
    wk = [sum(d["contributionCount"] for d in w) for w in weeks]
    best_week = max(wk) if wk else 0

    h, top, bot = 148, 92, 138
    peak = max(wk) or 1
    step = (WIDTH - LEFT * 2) / max(len(wk) - 1, 1)
    pts = [(LEFT + i * step, bot - (v / peak) * (bot - top))
           for i, v in enumerate(wk)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (f"{LEFT},{bot} " + line + f" {LEFT + (len(wk) - 1) * step:.1f},{bot}")

    body = (
        f'{wipe(0, WIDTH, h)}'
        f'<g clip-path="url(#w0)">'
        f'<text x="{LEFT}" y="46" class="e" font-size="40" '
        f'font-weight="600">{total:,}</text>'
        f'<text x="{LEFT}" y="66" class="m" font-size="11">'
        f'contributions in the last year</text>'
        f'<text x="{WIDTH - LEFT}" y="30" class="e" font-size="17" '
        f'font-weight="600" text-anchor="end">{active}</text>'
        f'<text x="{WIDTH - LEFT}" y="44" class="m" font-size="10" '
        f'text-anchor="end">active days</text>'
        f'<text x="{WIDTH - LEFT}" y="64" class="e" font-size="17" '
        f'font-weight="600" text-anchor="end">{best_week}</text>'
        f'<text x="{WIDTH - LEFT}" y="78" class="m" font-size="10" '
        f'text-anchor="end">best week</text>'
        f'<polygon points="{area}" class="d" opacity="0.18"/>'
        f'<polyline points="{line}" fill="none" stroke="currentColor" '
        f'class="d" stroke-width="1.4" style="stroke:{LIGHT["data"]}"/>'
        f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" '
        f'class="e"/>'
        f"</g>")
    return shell(h, body, weights=(400, 600))


def draw_streak(days):
    cur, best = streaks(days)
    h = 96
    cells = [("current streak", cur), ("longest streak", best),
             ("days tracked", len(days))]
    body = [wipe(0, WIDTH, h), '<g clip-path="url(#w0)">']
    for i, (label, value) in enumerate(cells):
        x = LEFT + i * ((WIDTH - LEFT * 2) / 3)
        body.append(f'<text x="{x:.0f}" y="40" class="e" font-size="26" '
                    f'font-weight="600">{value}</text>')
        body.append(f'<text x="{x:.0f}" y="58" class="m" '
                    f'font-size="10">{label}</text>')
    body.append(f'<rect x="{LEFT}" y="76" width="{WIDTH - LEFT * 2}" '
                f'height="1" class="r"/>')
    body.append("</g>")
    return shell(h, "".join(body), weights=(400, 600))


def draw_langs(by_bytes, by_repo):
    top_b = sorted(by_bytes.items(), key=lambda kv: -kv[1])[:5]
    top_r = sorted(by_repo.items(), key=lambda kv: -kv[1])[:5]
    total_b = sum(by_bytes.values()) or 1
    rows = max(len(top_b), len(top_r))
    h = 34 + rows * 19
    colw = (WIDTH - LEFT * 2 - 30) / 2

    body = [wipe(0, WIDTH, h), '<g clip-path="url(#w0)">',
            f'<text x="{LEFT}" y="12" class="m" font-size="10">BY BYTES</text>',
            f'<text x="{LEFT + colw + 30:.0f}" y="12" class="m" '
            f'font-size="10">BY REPOS</text>']

    for i, (name, size) in enumerate(top_b):
        y = 32 + i * 19
        pct = size / total_b
        body.append(f'<text x="{LEFT}" y="{y}" class="d" '
                    f'font-size="11">{esc(name.lower())}</text>')
        body.append(f'<rect x="{LEFT + 96}" y="{y - 8}" '
                    f'width="{pct * (colw - 140):.1f}" height="8" class="d" '
                    f'opacity="0.55"/>')
        body.append(f'<text x="{LEFT + colw:.0f}" y="{y}" class="m" '
                    f'font-size="10" text-anchor="end">{pct * 100:.0f}%</text>')

    x0 = LEFT + colw + 30
    peak_r = max((n for _, n in top_r), default=1) or 1
    for i, (name, n) in enumerate(top_r):
        y = 32 + i * 19
        body.append(f'<text x="{x0:.0f}" y="{y}" class="d" '
                    f'font-size="11">{esc(name.lower())}</text>')
        body.append(f'<rect x="{x0 + 96:.0f}" y="{y - 8}" '
                    f'width="{n / peak_r * (colw - 140):.1f}" height="8" '
                    f'class="d" opacity="0.55"/>')
        body.append(f'<text x="{x0 + colw:.0f}" y="{y}" class="m" '
                    f'font-size="10" text-anchor="end">{n}</text>')
    body.append("</g>")
    return shell(h, "".join(body), weights=(400,))


def draw_year(days):
    """The year as one character per day, in the portrait's own ramp."""
    weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
    counts = sorted(d["contributionCount"] for d in days
                    if d["contributionCount"] > 0)
    # Scale to a busy-but-typical day, not to the single loudest one. Against
    # the raw maximum a normal day rounds to zero and the map reads empty.
    peak = counts[int(len(counts) * 0.9)] if counts else 1
    cw, rh = 10.4, 13
    h = 34 + 7 * rh + 18
    active = len(counts)

    def glyph(n):
        if n <= 0:
            return " "
        # any activity is visible; the ramp above that is proportional
        return RAMP[min(len(RAMP) - 1, 1 + int(n / max(peak, 1) * (len(RAMP) - 2)))]

    body = [wipe(0, WIDTH, h), '<g clip-path="url(#w0)">',
            f'<text x="0" y="12" class="m" font-size="10">'
            f'{active} of {len(days)} days had a contribution</text>']

    for wd, label in ((0, "mon"), (2, "wed"), (4, "fri")):
        body.append(f'<text x="0" y="{34 + wd * rh + 9}" class="m" '
                    f'font-size="9">{label}</text>')

    for r in range(7):
        line = "".join(glyph(w[r]["contributionCount"]) if r < len(w) else " "
                       for w in weeks)
        body.append(f'<text xml:space="preserve" x="{LEFT}" '
                    f'y="{34 + r * rh + 9}" class="d" font-size="11" '
                    f'letter-spacing="{cw - 6.6:.2f}">{esc(line)}</text>')

    seen = set()
    for i, w in enumerate(weeks):
        m = int(w[0]["date"][5:7]) - 1
        if m not in seen and int(w[0]["date"][8:10]) <= 7:
            seen.add(m)
            body.append(f'<text x="{LEFT + i * cw:.0f}" y="{h - 3}" '
                        f'class="m" font-size="9">{MON[m]}</text>')
    body.append("</g>")
    return shell(h, "".join(body), weights=(400,))


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required")
    login = os.environ.get("GH_LOGIN", "arqam365")
    out = os.environ.get("OUT_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(out, exist_ok=True)

    user = fetch(login, token)
    days = days_of(user)
    by_bytes, by_repo = language_totals(user)

    files = {"stats.svg": draw_stats(user, days),
             "streak.svg": draw_streak(days),
             "langs.svg": draw_langs(by_bytes, by_repo),
             "year.svg": draw_year(days)}
    for text in HEADINGS:
        files[f"hd-{text.replace(' ', '-')}.svg"] = draw_heading(text)

    for name, svg in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{name}: {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
