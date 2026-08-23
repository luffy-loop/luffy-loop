import json
import os
import subprocess
from datetime import date, timedelta
from pathlib import Path

USERNAME = "luffy-loop"
OUTPUT = Path("assets/contribution-calendar.svg")

QUERY = """
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

payload = {
    "query": QUERY,
    "variables": {
        "login": USERNAME
    }
}

result = subprocess.run(
    [
        "curl",
        "-s",
        "-X",
        "POST",
        "-H",
        f"Authorization: bearer {os.environ['GITHUB_TOKEN']}",
        "-H",
        "Content-Type: application/json",
        "https://api.github.com/graphql",
        "-d",
        json.dumps(payload)
    ],
    capture_output=True,
    text=True,
    check=True
)

data = json.loads(result.stdout)

if "errors" in data:
    raise RuntimeError(json.dumps(data["errors"], indent=2))

calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

total = calendar["totalContributions"]

days = []

for week in calendar["weeks"]:
    for contribution_day in week["contributionDays"]:
        days.append(contribution_day)

days.sort(key=lambda item: item["date"])

# Keep approximately the last year
end_date = date.today()
start_date = end_date - timedelta(days=364)

days = [
    day for day in days
    if start_date.isoformat() <= day["date"] <= end_date.isoformat()
]

if not days:
    raise RuntimeError("No contribution data was returned.")

# Start the calendar on Sunday
first_date = date.fromisoformat(days[0]["date"])
padding = (first_date.weekday() + 1) % 7

columns = []

current_column = [None] * padding

for day in days:
    current_column.append(day)

    if len(current_column) == 7:
        columns.append(current_column)
        current_column = []

while current_column:
    current_column.append(None)

    if len(current_column) == 7:
        columns.append(current_column)
        current_column = []

# Visual settings
CELL_SIZE = 15
GAP = 4
LEFT = 48
TOP = 58

column_width = CELL_SIZE + GAP

SVG_WIDTH = LEFT + len(columns) * column_width + 30
SVG_HEIGHT = 190

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

COLORS = {
    "NONE": "#161B22",
    "FIRST_QUARTILE": "#3B0764",
    "SECOND_QUARTILE": "#6D28D9",
    "THIRD_QUARTILE": "#8B5CF6",
    "FOURTH_QUARTILE": "#C4B5FD"
}

svg = []

svg.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
    f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
)

svg.append(
    '<rect width="100%" height="100%" rx="12" fill="#0D1117"/>'
)

# Contribution count
svg.append(
    f'<text x="18" y="27" '
    f'fill="#E6EDF3" '
    f'font-family="Arial, Helvetica, sans-serif" '
    f'font-size="17" '
    f'font-weight="600">'
    f'{total} contributions in the last year'
    f'</text>'
)

# Month labels
previous_month = None

for x, column in enumerate(columns):

    valid_days = [day for day in column if day is not None]

    if not valid_days:
        continue

    first_day = date.fromisoformat(valid_days[0]["date"])

    # Only show a label when the month changes
    if first_day.month == previous_month:
        continue

    previous_month = first_day.month

    xpos = LEFT + x * column_width

    svg.append(
        f'<text x="{xpos}" y="47" '
        f'fill="#8B949E" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="12">'
        f'{MONTHS[first_day.month - 1]}'
        f'</text>'
    )

# Contribution cells
for x, column in enumerate(columns):

    for y, day in enumerate(column):

        if day is None:
            continue

        count = day["contributionCount"]
        level = day["contributionLevel"]

        color = COLORS.get(
            level,
            COLORS["NONE"]
        )

        xpos = LEFT + x * column_width
        ypos = TOP + y * column_width

        plural = "contributions" if count != 1 else "contribution"

        tooltip = (
            f'{count} {plural} on {day["date"]}'
        )

        svg.append(
            f'<rect '
            f'x="{xpos}" '
            f'y="{ypos}" '
            f'width="{CELL_SIZE}" '
            f'height="{CELL_SIZE}" '
            f'rx="3" '
            f'fill="{color}">'
            f'<title>{tooltip}</title>'
            f'</rect>'
        )

# Legend
legend_y = TOP + 7 * column_width + 18

svg.append(
    f'<text x="18" y="{legend_y}" '
    f'fill="#8B949E" '
    f'font-family="Arial, Helvetica, sans-serif" '
    f'font-size="11">'
    f'Less'
    f'</text>'
)

legend_colors = [
    "#161B22",
    "#3B0764",
    "#6D28D9",
    "#8B5CF6",
    "#C4B5FD"
]

for index, color in enumerate(legend_colors):

    xpos = 48 + index * 19

    svg.append(
        f'<rect '
        f'x="{xpos}" '
        f'y="{legend_y - 11}" '
        f'width="14" '
        f'height="14" '
        f'rx="3" '
        f'fill="{color}"/>'
    )

svg.append(
    f'<text '
    f'x="{48 + len(legend_colors) * 19 + 5}" '
    f'y="{legend_y}" '
    f'fill="#8B949E" '
    f'font-family="Arial, Helvetica, sans-serif" '
    f'font-size="11">'
    f'More'
    f'</text>'
)

svg.append("</svg>")

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT.write_text(
    "\n".join(svg),
    encoding="utf-8"
)

print(f"Contribution calendar generated: {OUTPUT}")
