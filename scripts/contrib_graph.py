"""Generate a weekly contribution-activity line chart as an SVG (dark theme)."""
import json, os, subprocess, sys, urllib.request
from datetime import date

USER = os.environ.get("GH_USER", "Mohanraj1232")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist/contribution-graph.svg"

QUERY = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
totalContributions weeks{firstDay contributionDays{contributionCount}}}}}}"""


def token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    return t or subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"u": USER}}).encode(),
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json", "User-Agent": "contrib-graph"},
    )
    with urllib.request.urlopen(req) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [(w["firstDay"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def render(weeks, total):
    W, H = 960, 330
    L, R, T, B = 56, 28, 112, 262          # plot box
    vals = [v for _, v in weeks]
    top = max(max(vals), 4)
    top = top + (top % 2)                   # even max so the mid tick is whole
    n = len(vals)
    x = lambda i: L + (W - L - R) * i / max(n - 1, 1)
    y = lambda v: B - (B - T) * v / top
    pts = [(x(i), y(v)) for i, v in enumerate(vals)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{L},{B} {line} {W-R},{B}"
    grid = "".join(
        f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="rgba(255,255,255,0.07)"/>'
        f'<text x="{L-12}" y="{y(v)+4:.1f}" text-anchor="end" class="ax">{v}</text>'
        for v in (0, top // 2, top)
    )
    ticks, last = "", None
    for i, (d, _) in enumerate(weeks):
        dt = date.fromisoformat(d)
        if dt.month != last and dt.month in (1, 4, 7, 10) or i == 0:
            ticks += f'<text x="{x(i):.1f}" y="{B+22}" text-anchor="middle" class="ax">{dt.strftime("%b")} {dt.strftime("%y")}</text>'
        last = dt.month
    dots = "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="#050607" stroke="#2D8CF0" stroke-width="1.6"/>' for px, py in pts)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none">
  <defs>
    <style>text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
    .ax{{font-size:11px;fill:rgba(255,255,255,0.45)}}</style>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2D8CF0" stop-opacity="0.35"/><stop offset="1" stop-color="#2D8CF0" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="#050607" stroke="rgba(255,255,255,0.1)"/>
  <text x="32" y="50" font-size="24" font-weight="600" fill="#ffffff">Contribution activity</text>
  <text x="32" y="78" font-size="14" fill="rgba(255,255,255,0.55)">{USER} / weekly totals over the last year</text>
  {grid}
  <polygon points="{area}" fill="url(#fill)"/>
  <polyline points="{line}" stroke="#2D8CF0" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
  {dots}
  {ticks}
  <text x="32" y="{H-14}" class="ax">{total} contributions / through {date.today().isoformat()}</text>
</svg>
'''


if __name__ == "__main__":
    weeks, total = fetch()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(render(weeks, total))
    print(f"wrote {OUT}: {len(weeks)} weeks, {total} contributions")
