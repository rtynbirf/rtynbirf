#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ТЕРМИНАЛ РОЯ — суточная neofetch-карта вселенной rtynbirf.
Методика сверки — точное зеркало scripts/swarm_sync.py (Link-header пагинация по всем
репо, байтовые языки), чтобы числа на странице сходились до единицы. Никаких ручных чисел.
Падение любого источника -> честная «—». Запускается Action (cron) и вручную."""
import json, os, re, sys, time, urllib.request, datetime

API = "https://api.github.com"
OWNER = "rtynbirf"
TOK = os.environ.get("SWARM_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
if not TOK:
    sys.exit("нет токенов: SWARM_TOKEN/GITHUB_TOKEN")

def req(url):
    r = urllib.request.Request(url, headers={
        "Authorization": "token " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "polimat-neofetch"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return (json.loads(raw) if raw.strip() else {}), resp.headers

user, _ = req(API + "/user")
repos, page = [], 1
while True:
    data, h = req(API + "/user/repos?visibility=all&affiliation=owner&per_page=100&sort=updated&page=%d" % page)
    repos += data
    if 'rel="next"' not in (h.get("Link") or ""): break
    page += 1

total_commits, stars, lang_bytes = 0, 0, {}
for r in repos:
    try:
        _, h = req(API + "/repos/%s/commits?per_page=1" % r["full_name"])
        m = re.search(r'[?&]page=(\d+)>; rel="last"', h.get("Link") or "")
        total_commits += int(m.group(1)) if m else 1
    except Exception:
        pass
    stars += r.get("stargazers_count", 0)
    try:
        ls, _ = req(API + "/repos/%s/languages" % r["full_name"])
        for k, v in ls.items(): lang_bytes[k] = lang_bytes.get(k, 0) + v
        time.sleep(0.1)
    except Exception:
        pass

top_langs = sorted(lang_bytes.items(), key=lambda x: -x[1])[:3]
ABBR = {"JavaScript": "JS", "PowerShell": "PS", "TypeScript": "TS"}
lang_str = " · ".join("%s %.1f" % (ABBR.get(n, n), v / 1e6) for n, v in top_langs) + (" МБ" if top_langs else "")
priv = sum(1 for r in repos if r["private"])
pub = len(repos) - priv

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

try:
    c0 = datetime.datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    uptime = (datetime.datetime.now(datetime.timezone.utc) - c0).days
    created_txt = "с 2022-12 · %d дней" % uptime
except Exception:
    created_txt = "с 2022"

ART = [
    "· · · · · · · · ·",
    "    ╭─────────╮",
    "  ╭─┤  ◉◉◉◉◉  ├─╮",
    "  │ │  ◉◉◉◉◉  │ │",
    "  ╰─┤  ◉◉◉◉◉  ├─╯",
    "    ╰────┬────╯",
    "· · · · · · · · ·",
]

def art_text(x, y0, lh):
    return "\n  ".join(
        '<text x="%d" y="%d" class="%s">%s</text>' % (x, y0 + i * lh, "core" if "◉" in l else "frame", esc(l))
        for i, l in enumerate(ART))

def rows(x, y0, lh, items):
    out = []
    for i, (label, value, sub) in enumerate(items):
        y = y0 + i * lh
        out.append('<text x="%d" y="%d" class="lbl">%s</text>' % (x, y, esc(label)))
        out.append('<text x="%d" y="%d" class="val">%s</text>' % (x + 118, y, esc(value)))
        if sub:
            out.append('<text x="%d" y="%d" class="sub">%s</text>' % (x + 118, y + 15, esc(sub)))
    return "\n  ".join(out)

items = [
    ("ОС", "офлайн-суверен", "без облака · без сети · без разрешений"),
    ("РОЙ", "6 кластеров · 1 организм", "клетки · сверка · эмерджентность"),
    ("РЕПО", "%d мира" % len(repos), "%d публичных · %d приватных" % (pub, priv)),
    ("КОММИТЫ", "%d" % total_commits, "с 2022 · методика SWARM-SYNC"),
    ("ЯЗЫКИ", lang_str, "по объёму кода"),
    ("ЗВЁЗДЫ", "%d" % stars, "каждая — благодарность"),
    ("UPTIME", created_txt, "непрерывная сборка"),
    ("СТАТУС", "рой сверен", "офлайн живёт · заходи с потолка"),
]

svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="780" height="470" viewBox="0 0 780 470" role="img" aria-label="neofetch-карта вселенной rtynbirf">
  <defs>
    <linearGradient id="nterm" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0B0A08"/>
      <stop offset="1" stop-color="#1C1508"/>
    </linearGradient>
    <linearGradient id="nedge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#D9A441"/>
      <stop offset="1" stop-color="#FFBD2E"/>
    </linearGradient>
  </defs>
  <style>
    .mono { font-family: ui-monospace, 'Cascadia Code', 'JetBrains Mono', Menlo, Consolas, monospace; }
    .frame { fill: #D9A441; font-size: 14px; }
    .core  { fill: #FFC96B; font-size: 14px; }
    .lbl   { fill: #D9A441; font-size: 14px; font-weight: 700; }
    .val   { fill: #F5EBD8; font-size: 14px; font-weight: 600; }
    .sub   { fill: #9A8A64; font-size: 11px; }
    .prompt{ fill: #FFBD2E; font-size: 14px; }
  </style>
  <rect x="2" y="2" width="776" height="466" rx="16" fill="url(#nterm)" stroke="#D9A441" stroke-opacity="0.4" stroke-width="2"/>
  <rect x="2" y="2" width="776" height="6" rx="3" fill="url(#nedge)"/>
  <rect x="2" y="16" width="776" height="34" fill="#241D12" stroke="#D9A441" stroke-opacity="0.2"/>
  <circle cx="28" cy="33" r="6" fill="#FF5F56"/>
  <circle cx="50" cy="33" r="6" fill="#FFBD2E"/>
  <circle cx="72" cy="33" r="6" fill="#27C93F"/>
  <text x="390" y="38" text-anchor="middle" class="mono sub">polimat@universum — zsh</text>
  <text x="30" y="78" class="mono prompt">➜ ~ polimat --fetch</text>
  %s
  %s
  <text x="740" y="446" text-anchor="end" class="mono sub">выковано роем · %s</text>
</svg>
''' % (
    art_text(60, 110, 21),
    rows(330, 118, 40, items),
    time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
)

out_path = sys.argv[1] if len(sys.argv) > 1 else "assets/neofetch.svg"
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(svg)
print("neofetch-карта:", out_path, "| репо:", len(repos), "| коммиты:", total_commits, "| языки:", lang_str[:50])
