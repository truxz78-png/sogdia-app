"""Sogdia link robot (option B).

Checks every store link in links.json once a week.
- If the active link is clearly broken, it switches automatically:
  primary -> backup -> official page. Customers never land on a dead link.
- If the primary link works again, it switches back to primary.
- Writes report.md when something changed or failed, so the workflow can
  open a GitHub Issue (the owner gets it by email and can review it later).

Only clear failures count as "broken": DNS/connection errors, 404 and 410.
Answers like 403/429/5xx are often anti-bot protection, so they are only
reported as "uncertain" and never cause a switch.
"""
import json, socket, urllib.request, urllib.error, sys, datetime

UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36")
BROKEN_CODES = {404, 410}


def check(url):
    """Return 'ok', 'broken' or 'uncertain' plus a short detail."""
    if not url:
        return "broken", "no link"
    last = ""
    for _ in range(2):  # retry once
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return "ok", str(r.status)
        except urllib.error.HTTPError as e:
            if e.code in BROKEN_CODES:
                last = f"HTTP {e.code}"
                continue
            return "uncertain", f"HTTP {e.code}"
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            last = f"error: {getattr(e, 'reason', e)}"
            continue
    return "broken", last


def main(path="links.json"):
    data = json.load(open(path, encoding="utf-8"))
    changes, broken, uncertain = [], [], []

    for s in data["stores"]:
        name, active = s["name"], s.get("active", "primary")
        st_primary, det = check(s.get("primary"))

        if st_primary == "uncertain":
            uncertain.append(f"- {name}: primary link answered {det} (not changed)")
        if st_primary == "broken":
            broken.append(f"- {name}: primary link broken ({det})")

        if st_primary == "uncertain":
            continue  # never switch on an unclear answer
        if st_primary == "ok":
            if active != "primary":
                s["active"] = "primary"
                changes.append(f"- {name}: primary link works again -> switched back to PRIMARY")
            continue

        # primary is broken -> try backup, then official
        new = "official"
        if s.get("backup"):
            st_backup, det_b = check(s["backup"])
            if st_backup in ("ok", "uncertain"):
                new = "backup"
            else:
                broken.append(f"- {name}: backup link broken too ({det_b})")
        if active != new:
            s["active"] = new
            changes.append(f"- {name}: switched to {new.upper()} -> find a new affiliate link")

    if changes:
        data["updated"] = datetime.date.today().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    if changes or broken:
        lines = ["Weekly link check for Sogdia.", ""]
        if changes:
            lines += ["## Automatic changes (customers were not affected)", *changes, ""]
        if broken:
            lines += ["## Broken links to replace", *broken, ""]
        if uncertain:
            lines += ["## Uncertain (probably anti-bot, check manually if you want)", *uncertain, ""]
        lines.append("When you add a new link in links.json, close this issue.")
        open("report.md", "w", encoding="utf-8").write("\n".join(lines))

    print(f"changes={len(changes)} broken={len(broken)} uncertain={len(uncertain)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
