"""Sogdia site robot: checks the published pages once a week.

- Each page (home, Privacy Policy, Terms of Service, translator) must open (HTTP 200).
- Each page must still have its key parts: footer links, "Back to Sogdia",
  and the automatic translator.
- The translation service must answer (tested with Spanish).
If something fails, it is added to report.md so the workflow opens a GitHub Issue.
Nothing is changed automatically.
"""
import json, urllib.request, urllib.parse, os

BASE = "https://truxz78-png.github.io/sogdia-app/"
UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36")
PAGES = {
    "index.html": ['href="privacy.html"', 'href="terms.html"', "autoTranslate", "links.json"],
    "privacy.html": ['src="translate.js"', "Back to", 'href="terms.html"'],
    "terms.html": ['src="translate.js"', "Back to", "Governing Law", 'href="privacy.html"'],
    "translate.js": ["translate.googleapis.com"],
    "links.json": ['"stores"'],
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


problems = []
for page, needed in PAGES.items():
    try:
        status, body = get(BASE + page + "?robot=1")
        missing = [n for n in needed if n not in body]
        if missing:
            problems.append(f"- **{page}**: missing {', '.join('`'+m+'`' for m in missing)}")
    except Exception as e:
        problems.append(f"- **{page}**: does not open ({e})")

try:
    q = urllib.parse.quote("Privacy Policy")
    _, body = get("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=es&dt=t&q=" + q)
    out = "".join(x[0] for x in json.loads(body)[0])
    if not out or out == "Privacy Policy":
        problems.append("- **Translator**: answered, but did not translate (test: Privacy Policy → Spanish)")
except Exception as e:
    problems.append(f"- **Translator**: no answer ({e}). If this repeats every week, the translation may have stopped working.")

if problems:
    text = "\n\n## Site check (pages and translator)\n\n" + "\n".join(problems) + "\n"
    mode = "a" if os.path.exists("report.md") else "w"
    open("report.md", mode, encoding="utf-8").write(text)
print(f"site problems={len(problems)}")
