"""Sogdia - full link check (run by hand from the Actions tab).

Tests EVERY link in links.json (primary and backup), follows all redirects
(HTTP, meta refresh and simple JavaScript redirects) and looks at the final
page to detect country blocks such as TARGETING_FAILED, "you have been
blocked" or "Access Denied". Writes report.md (in Spanish) with one line
per store. Nothing is changed in links.json.
"""
import json, re, socket, sys, html, urllib.request, urllib.error
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36")
GEO_MARKERS = ["targeting_failed", "you have been blocked", "access denied",
               "not available in your country", "not available in your region",
               "request blocked", "the request could not be satisfied"]
META = re.compile(r'http-equiv=["\']?refresh["\']?[^>]*content=["\']?\d+\s*;\s*url=([^"\'>]+)', re.I)
JSLOC = re.compile(r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.geturl(), r.read(60000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        try:
            body = e.read(60000).decode("utf-8", "ignore")
        except Exception:
            body = ""
        return e.code, e.geturl() or url, body


def check(url):
    """Return (state, detail, final_url). state: OK / ROTO / BLOQUEO / DUDA."""
    if not url:
        return "ROTO", "sin enlace", ""
    cur = url
    try:
        for _ in range(4):
            code, final, body = fetch(cur)
            low = body.lower()
            if any(m in low for m in GEO_MARKERS) or (code == 403 and "cloudfront" in low):
                return "BLOQUEO", f"HTTP {code}, bloqueo por país o antibots", final
            if code in (404, 410):
                return "ROTO", f"HTTP {code}", final
            if code >= 400:
                return "DUDA", f"HTTP {code}", final
            m = META.search(body[:20000]) or (JSLOC.search(body[:20000]) if len(body) < 8000 else None)
            if m:
                nxt = urljoin(final, html.unescape(m.group(1).strip()))
                if nxt != cur and nxt.startswith("http"):
                    cur = nxt
                    continue
            return "OK", f"HTTP {code}", final
        return "OK", "muchas redirecciones", cur
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return "ROTO", f"error: {getattr(e, 'reason', e)}", cur


def host(u):
    try:
        return urlparse(u).netloc.replace("www.", "")[:40]
    except Exception:
        return ""


ICON = {"OK": "✅", "ROTO": "❌", "BLOQUEO": "🚫", "DUDA": "⚠️"}
REG = {"worldwide": "Mundial", "usa-europe": "EE. UU. y Europa", "china": "China",
       "india": "India", "india-only": "Sólo India"}


def main(path="links.json"):
    stores = json.load(open(path, encoding="utf-8"))["stores"]
    jobs = []
    for s in stores:
        jobs.append((s, "primary", s.get("primary")))
        if s.get("backup"):
            jobs.append((s, "backup", s["backup"]))
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda j: check(j[2]), jobs))

    res = {}
    for (s, kind, _), r in zip(jobs, results):
        res.setdefault(s["id"], {})[kind] = r

    count = {"OK": 0, "ROTO": 0, "BLOQUEO": 0, "DUDA": 0}
    lines = ["# Verificación completa de enlaces de Sogdia", "",
             "Probado desde un servidor de GitHub en EE. UU. (fuera de la India).", "",
             "✅ abre · ❌ roto · 🚫 bloqueo por país · ⚠️ dudoso (revisar a mano)", ""]
    current = None
    order = list(REG)
    for s in sorted(stores, key=lambda x: order.index(x["region"]) if x["region"] in order else 99):
        if s["region"] != current:
            current = s["region"]
            lines += ["", f"## {REG.get(current, current)}", ""]
        st, det, fin = res[s["id"]]["primary"]
        count[st] += 1
        line = f"- {ICON[st]} **{s['name']}** — {det} → {host(fin)}"
        if "backup" in res[s["id"]]:
            bst, bdet, bfin = res[s["id"]]["backup"]
            line += f" · respaldo: {ICON[bst]} {bdet} → {host(bfin)}"
        lines.append(line)
    lines = lines[:5] + [f"**Resumen (enlace principal):** ✅ {count['OK']} · ❌ {count['ROTO']} · "
                         f"🚫 {count['BLOQUEO']} · ⚠️ {count['DUDA']}", ""] + lines[5:]
    open("report.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:])
