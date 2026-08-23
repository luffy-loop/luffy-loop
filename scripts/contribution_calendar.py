import json
import os
import subprocess
from datetime import date, timedelta
from pathlib import Path

USERNAME = "luffy-loop"
OUTPUT = Path("assets/contribution-calendar.svg")

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            contributionLevel
            date
          }
        }
      }
    }
  }
}
"""

variables = json.dumps({"login": USERNAME})

result = subprocess.run(
    [
        "curl",
        "-s",
        "-X",
        "POST",
        "-H",
        "Authorization: bearer " + os.environ["GITHUB_TOKEN"],
        "-H",
        "Content-Type: application/json",
        "https://api.github.com/graphql",
        "-d",
        json.dumps({
            "query": query,
            "variables": json.loads(variables)
        })
    ],
    capture_output=True,
    text=True,
    check=True
)

data = json.loads(result.stdout)

calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

total = calendar["totalContributions"]

days = []

for week in calendar["weeks"]:
    for d in week["contributionDays"]:
        days.append(d)

days.sort(key=lambda x: x["date"])

# Last 365 days
end_date = date.today()
start_date = end_date - timedelta(days=364)

days = [
    d for d in days
    if start_date.isoformat() <= d["date"] <= end_date.isoformat()
]

# Align the first day to Sunday
first = date.fromisoformat(days[0]["date"])
padding = (first.weekday() + 1) % 7

columns = []

current_column = []

for _ in range(padding):
    current_column.append(None)

for d in days:
    current_column.append(d)

    if len(current_column) == 7:
        columns.append(current_column)
        current_column = []

while current_column:
    current_column.append(None)

    if len(current_column) == 7:
        columns.append(current_column)
        current_column = []

cell = 16
gap = 4
left = 52
top = 55
width = left + len(columns) * (cell + gap) + 20
height = 180

month_names = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

levels = {
    "NONE": "#161B22",
    "FIRST_QUARTILE": "#3B0764",
    "SECOND_QUARTILE": "#6D28D9",
    "THIRD_QUARTILE": "#8B5CF6",
    "FOURTH_QUARTILE": "#C4B5FD",
}

svg = []

svg.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
)

svg.append("""
<rect width="100%" height="100%" rx="10" fill="#0D1117"/>
""")

svg.append(
    f'<text x="18" y="25" fill="#E6EDF3" '
    f'font-family="Arial, sans-serif" font-size="16" font-weight="600">'
    f'{total} contributions in the last year</text>'
)

# Month labels
seen_months = set()

for x, column in enumerate(columns):
    valid = [d for d in column if d]

    if not valid:
        continue

    first_day = date.fromisoformat(valid[0]["date"])

    if first_day.month in seen_months:
        continue

    seen_months.add(first_day.month)

    xpos = left + x * (cell + gap)

    svg.append(
        f'<text x="{xpos}" y="43" fill="#8B949E" '
        f'font-family="Arial, sans-serif" font-size="12">'
        f'{month_names[first_day.month - 1]}</text>'
    )

# Contribution cells
for x, column in enumerate(columns):

    for y, d in enumerate(column):

        if d is None:
            continue

        count = d["contributionCount"]
        level = d["contributionLevel"]

        fill = levels.get(level, levels["NONE"])

        xpos = left + x * (cell + gap)
        ypos = top + y * (cell + gap)

        tooltip = (
            f'{count} contribution'
            f'{"s" if count != 1 else ""} on {d["date"]}'
        )

        svg.append(
            f'<rect x="{xpos}" y="{ypos}" '
            f'width="{cell}" height="{cell}" rx="3" '
            f'fill="{fill}">'
            f'<title>{tooltip}</title>'
            f'</rect>'
        )

# Legend
legend_y = top + 7 * (cell + gap) + 12

svg.append(
    f'<text x="18" y="{legend_y + 3}" fill="#8B949E" '
    f'font-family="Arial, sans-serif" font-size="11">Less</text>'
)

legend_colors = [
    "#161B22",
    "#3B0764",
    "#6D28D9",
    "#8B5CF6",
    "#C4B5FD",
]

for i, color in enumerate(legend_colors):

    x = 50 + i * 18

    svg.append(
        f'<rect x="{x}" y="{legend_y - 8}" '
        f'width="13" height="13" rx="3" fill="{color}"/>'
    )

svg.append(
    f'<text x="{50 + len(legend_colors) * 18 + 5}" '
    f'y="{legend_y + 3}" fill="#8B949E" '
    f'font-family="Arial, sans-serif" font-size="11">More</text>'
)

svg.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(svg), encoding="utf-8")

print(f"Generated {OUTPUT}")
