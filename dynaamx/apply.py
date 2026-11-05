#!/usr/bin/env python3
"""Apply Dynaamx's changes to a Libredesk source checkout.

    python3 dynaamx/apply.py <libredesk-src> --tzdata <dir> [--zones-out <file>]

1. Removes every "Powered by" credit: the agent sign-in page, the chat widget (and its preview
   in the inbox settings, with the now pointless "Show powered by" switch), the help center
   footers (both themes), the survey page and the footer of every email.
2. Replaces the short time zone list (35 zones in v2.9.2) with every zone the server accepts:
   zone.tab and zone1970.tab from <dir>, the tzdata the image installs, so the list matches
   what the server's time.LoadLocation can load. Labels carry the browser's current offset.

Every edit must match exactly as often as expected, and a final check looks for any credit
left, so a Libredesk release that moves things fails the build instead of shipping a credit.
"""
import argparse
import json
import pathlib
import re
import sys

IMPORT = r"\nimport PoweredBy from '@shared-ui/components/PoweredBy\.vue'"

# (file, pattern, count). Each match is deleted; a leading \s* takes its indentation and line.
REMOVALS = [
    ("frontend/apps/main/src/layouts/auth/AuthLayout.vue",
     r"\s*<footer\b[^>]*>\s*<PoweredBy />\s*</footer>", 1),
    ("frontend/apps/main/src/layouts/auth/AuthLayout.vue", IMPORT, 1),
    ("frontend/apps/widget/src/layouts/MainLayout.vue",
     r"\s*<div\s[^>]*show_powered_by[^>]*>\s*<PoweredBy />\s*</div>", 1),
    ("frontend/apps/widget/src/layouts/MainLayout.vue", IMPORT, 1),
    ("frontend/apps/main/src/features/admin/inbox/LivechatWidgetPreview.vue",
     r"\s*<div\s[^>]*show_powered_by[^>]*>\s*<PoweredBy />\s*</div>", 1),
    ("frontend/apps/main/src/features/admin/inbox/LivechatWidgetPreview.vue", IMPORT, 1),
    ("frontend/apps/main/src/features/admin/inbox/LivechatInboxForm.vue",
     r'\s*<FormField v-slot="[^"]*" name="config\.show_powered_by">.*?</FormField>', 1),
    ("static/email-templates/base.html",
     r"\s*<tr>\s*<td class=\"footer\"[^>]*>\s*<span>Powered by <a [^>]*>libredesk</a></span>\s*</td>\s*</tr>", 1),
    ("static/public/web-templates/index.html",
     r"\s*<footer class=\"container\">\s*Powered by <a [^>]*>libredesk</a>\s*</footer>", 1),
    ("static/public/web-templates/help/classic/layout.html",
     r"\s*<p class=\"hc-footer-powered\">.*?</p>", 1),
    ("static/public/web-templates/help/docs/layout.html",
     r"\s*<p class=\"hcd-footer-powered\">.*?</p>", 1),
]

TIMEZONES = "frontend/apps/main/src/constants/timezones.js"

TIMEZONES_JS = """\
// Dynaamx build (dynaamx/apply.py): every time zone the server accepts, from tzdata {version}
// (zone.tab and zone1970.tab). Labels show each zone's UTC offset today, so they follow
// daylight saving time. Upstream's short list is replaced; every zone it had is kept.
const ZONES = {zones}

const now = new Date()

function offsetMinutes(timeZone) {{
  try {{
    const name = new Intl.DateTimeFormat('en-US', {{ timeZone, timeZoneName: 'longOffset' }})
      .formatToParts(now)
      .find((part) => part.type === 'timeZoneName')?.value
    const match = /^GMT([+-])(\\d{{2}}):(\\d{{2}})$/.exec(name || '')
    if (!match) return 0
    const minutes = Number(match[2]) * 60 + Number(match[3])
    return match[1] === '-' ? -minutes : minutes
  }} catch {{
    return null
  }}
}}

function formatOffset(minutes) {{
  if (minutes === null) return ''
  const sign = minutes < 0 ? '-' : '+'
  const abs = Math.abs(minutes)
  const hh = String(Math.floor(abs / 60)).padStart(2, '0')
  const mm = String(abs % 60).padStart(2, '0')
  return ` (UTC${{sign}}${{hh}}:${{mm}})`
}}

function place(zone) {{
  if (zone === 'UTC') return 'UTC'
  const parts = zone.split('/')
  const city = parts.pop()
  return [city, ...parts.reverse()].join(', ').replaceAll('_', ' ')
}}

function build() {{
  const rows = ZONES.map((zone) => ({{ zone, offset: offsetMinutes(zone), place: place(zone) }}))
  rows.sort((a, b) => {{
    if (a.zone === 'UTC' || b.zone === 'UTC') return a.zone === 'UTC' ? -1 : 1
    if (a.offset !== b.offset) {{
      if (a.offset === null) return 1
      if (b.offset === null) return -1
      return a.offset - b.offset
    }}
    return a.place.localeCompare(b.place)
  }})
  const out = {{}}
  for (const row of rows) {{
    let label = row.place + formatOffset(row.offset)
    if (label in out) label += ` [${{row.zone}}]`
    out[label] = row.zone
  }}
  return out
}}

// {{ "Karachi, Asia (UTC+05:00)": "Asia/Karachi", ... }}, UTC first, then by offset.
export const timeZones = build()
"""


def fail(message: str) -> None:
    print(f"apply.py: {message}", file=sys.stderr)
    sys.exit(1)


def remove(src: pathlib.Path) -> None:
    for rel, pattern, count in REMOVALS:
        path = src / rel
        if not path.is_file():
            fail(f"{rel} not found: Libredesk moved it, update apply.py")
        text = path.read_text()
        updated, n = re.subn(pattern, "", text, flags=re.DOTALL)
        if n != count:
            fail(f"{rel}: expected {count} match(es) of {pattern!r}, found {n}: update apply.py")
        path.write_text(updated)
        print(f"removed credit: {rel}")


def tab_zones(path: pathlib.Path) -> set[str]:
    zones = set()
    for line in path.read_text().splitlines():
        if line and not line.startswith("#"):
            zones.add(line.split("\t")[2])
    return zones


def timezones(src: pathlib.Path, tzdata: pathlib.Path, zones_out: pathlib.Path | None) -> None:
    path = src / TIMEZONES
    old = path.read_text() if path.is_file() else fail(f"{TIMEZONES} not found")
    if "export const timeZones" not in old:
        fail(f"{TIMEZONES} no longer exports timeZones: update apply.py")
    old_values = set(re.findall(r':\s*"([^"]+)"', old))
    if len(old_values) < 10:
        fail(f"{TIMEZONES}: could not read upstream's values")

    zi = (tzdata / "tzdata.zi").read_text()
    version = re.search(r"^# version (\S+)", zi, re.M)
    links = dict(  # link name -> zone it points to
        (parts[2], parts[1]) for parts in (line.split() for line in zi.splitlines())
        if len(parts) == 3 and parts[0] == "L"
    )
    zones = tab_zones(tzdata / "zone.tab") | tab_zones(tzdata / "zone1970.tab") | {"UTC"}
    for value in sorted(old_values - zones):
        # Upstream lists a few old names (America/Buenos_Aires). Keep the name a setting may
        # already hold and drop the zone it points to, so the list has no duplicate place.
        target = links.get(value)
        if target is None:
            fail(f"upstream's {value} is neither a zone nor a link in tzdata")
        zones.discard(target)
        zones.add(value)

    ordered = sorted(zones)
    path.write_text(TIMEZONES_JS.format(
        version=version.group(1) if version else "(unknown)",
        zones=json.dumps(ordered, indent=2).replace('"', "'"),
    ))
    print(f"time zones: {len(ordered)} (upstream had {len(old_values)})")
    if zones_out:
        zones_out.write_text("\n".join(ordered) + "\n")


def check(src: pathlib.Path) -> None:
    """Fail if any credit is left, wherever a new release might have put one."""
    left = []
    for path in (src / "frontend").rglob("*.vue"):
        if "node_modules" in path.parts or path.name == "PoweredBy.vue":
            continue
        text = path.read_text()
        if "<PoweredBy" in text or "helpCenter.poweredBy" in text:
            left.append(path.relative_to(src))
    for path in (src / "static").rglob("*.html"):
        text = path.read_text()
        if re.search(r"powered\s+by", text, re.I) or "helpCenter.poweredBy" in text:
            left.append(path.relative_to(src))
    if left:
        fail("credit still shown in: " + ", ".join(map(str, left)))
    print("check: no credit left")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("src", type=pathlib.Path)
    parser.add_argument("--tzdata", type=pathlib.Path, required=True)
    parser.add_argument("--zones-out", type=pathlib.Path)
    args = parser.parse_args()
    remove(args.src)
    timezones(args.src, args.tzdata, args.zones_out)
    check(args.src)


if __name__ == "__main__":
    main()
