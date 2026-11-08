"""Sogdia site robot: checks the published pages once a week (inside check-links.yml).

It only checks and reports. It NEVER changes the pages or the legal text.

1. Each page (home, Privacy Policy, Terms of Service, translator, links) must open (HTTP 200)
   and still have its key parts: footer links, "Back to Sogdia", the automatic translator
   and the <meta name="google" content="notranslate"> tag.
2. The translation service must answer. It asks as little as possible:
   up to 3 languages (es, ar, zh-CN), 5 seconds apart, and stops as soon as one answers.
   - HTTP 429 (Google busy: GitHub servers are shared by thousands of users) = only a WARNING
     in the log. No alert. It is tried again next week.
   - A real error (empty answer, another HTTP code, an answer that is not JSON) = alert.
Problems are added to report.md, and the workflow opens a GitHub Issue with them.
The full language test of the legal text is NOT run here (it always gets 429 from GitHub);
run it from Termux only when the legal text changes.
"""
import json, os, time, urllib.request, urllib.parse, urllib.error

BASE = "https://truxz78-png.github.io/sogdia-app/"
UA = "Mozilla/5.0"
META = '<meta name="google" content="notranslate">'
PAGES = {
    "index.html": ['href="privacy.html"', 'href="terms.html"', "autoTranslate",
                   "translate_a/single", "links.json", META],
    "privacy.html": ['src="translate.js"', "Back to", 'href="terms.html"', META],
    "terms.html": ['src="translate.js"', "Back to", "Governing Law", 'href="privacy.html"', META],
    "translate.js": ["translate_a/single"],
    "links.json": ['"stores"'],
}
TEST_LANGS = ["es", "ar", "zh-CN"]
TEST_TEXT = "Privacy Policy"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


problems = []

# 1) Pages
for page, needed in PAGES.items():
    try:
        _, body = get(BASE + page + "?robot=1")
        missing = [n for n in needed if n not in body]
        if missing:
            problems.append(f"- **{page}**: missing {', '.join('`'+m+'`' for m in missing)}")
    except Exception as e:
        problems.append(f"- **{page}**: does not open ({e})")
if not problems:
    print("OK: all pages open and have their key parts (home, privacy.html, terms.html, translate.js, links.json).")

# 2) Translator
busy, errors, ok_lang = [], [], None
for i, lang in enumerate(TEST_LANGS):
    if i:
        time.sleep(5)
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=" + lang +
           "&dt=t&q=" + urllib.parse.quote(TEST_TEXT))
    try:
        _, body = get(url)
        try:
            out = "".join(x[0] for x in json.loads(body)[0] if x and x[0])
        except Exception:
            errors.append(f"{lang}: the answer is not valid JSON")
            continue
        if not out.strip() or out.strip() == TEST_TEXT:
            errors.append(f"{lang}: empty or untranslated answer")
            continue
        ok_lang = lang
        break
    except urllib.error.HTTPError as e:
        if e.code == 429:
            busy.append(lang)
        else:
            errors.append(f"{lang}: HTTP {e.code}")
    except Exception as e:
        errors.append(f"{lang}: no answer ({e})")

if ok_lang:
    print(f"OK: el traductor responde ({ok_lang}).")
elif errors:
    print("ERROR: el traductor falló: " + "; ".join(errors))
    problems.append("- **Translator**: real error, not just 'Google busy': " + "; ".join(errors))
else:
    print(f"AVISO: Google estaba ocupado (HTTP 429 en {', '.join(busy)}). No es un fallo de la página; "
          "se vuelve a probar la próxima semana.")

if problems:
    text = "\n\n## Site check (pages and translator)\n\n" + "\n".join(problems) + "\n"
    mode = "a" if os.path.exists("report.md") else "w"
    open("report.md", mode, encoding="utf-8").write(text)
print(f"site problems={len(problems)}")
