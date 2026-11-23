# -*- coding: utf-8 -*-
"""SWARM-SYNC — клетка роя: сверка со средой и регенерация секции README.
Данные — только из живого GitHub API (антигаллюцинация). Запись — в рабочую копию,
коммит делает workflow-шаг (идентичность bot, только при изменениях, [skip ci]).

Приказ ХОЗЯИНА 2026-11-24 (сверка 11/11, fallout): sentinel-маркеры и ЗАМЕНА между
ними, не append. append умер вместе с блоком 12:41 (коммит bacc6bc): маркер в README
не совпал с маркером скрипта — замена молча превратилась в приписку. Теперь:
  1) канонические сентинели BEGIN_SWARM_SYNC / END_SWARM_SYNC;
  2) легаси-маркеры SWARM:BEGIN/SWARM:END мигрируются на месте;
  3) нет ни тех ни других = честный exit 1 (fail-closed), а не тихий append.
README — витрина: replace. Ledger — append-only. Это разные носители."""
import base64, json, os, re, sys, time, urllib.error, urllib.request

API = "https://api.github.com"
OWNER, REPO = "rtynbirf", "rtynbirf"
BEGIN, END = "<!--BEGIN_SWARM_SYNC-->", "<!--END_SWARM_SYNC-->"
# легаси-маркеры эпохи 12:41 — распознаём и мигрируем (замена, не дубликат)
LEGACY = re.compile(r"<!--\s*SWARM:BEGIN[^>]*-->.*?<!--\s*SWARM:END[^>]*-->", re.S)
CANON = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)

def hdr(tok):
    return {"Authorization": f"token {tok}", "Accept": "application/vnd.github+json", "User-Agent": "swarm-sync"}

def req(tok, url, method="GET", payload=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(payload).encode() if payload is not None else None,
                               headers=hdr(tok))
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return (json.loads(raw) if raw.strip() else {}), resp.headers

# --- выбор токенов: чтение публичной витрины (закон дома: приватные клетки
# в витрину не попадают — GITHUB_TOKEN видит public-флот; заход 6) ---
READ_TOK = os.environ.get("GITHUB_TOKEN") or os.environ.get("SWARM_TOKEN")
if not READ_TOK:
    sys.exit("нет токенов: GITHUB_TOKEN/SWARM_TOKEN")

# --- сверка со средой: живые данные (публичная опись владельца) ---
repos, page = [], 1
while True:
    data, h = req(READ_TOK, f"{API}/users/{OWNER}/repos?type=owner&per_page=100&sort=updated&page={page}")
    if not data: break
    repos += data
    if 'rel="next"' not in (h.get("Link") or ""): break
    page += 1

total_commits, per_repo = 0, []
lang = {}
for r in repos:
    try:
        _, h = req(READ_TOK, f"{API}/repos/{r['full_name']}/commits?per_page=1")
        m = re.search(r'[?&]page=(\d+)>; rel="last"', h.get("Link") or "")
        c = int(m.group(1)) if m else 1
    except Exception:
        c = 0
    total_commits += c
    per_repo.append((r["name"], r["private"], r.get("language") or "—", c, r["pushed_at"]))
    time.sleep(0.1)
    try:
        ls, _ = req(READ_TOK, f"{API}/repos/{r['full_name']}/languages")
        for k, v in ls.items(): lang[k] = lang.get(k, 0) + v
    except Exception:
        pass

priv = sum(1 for r in repos if r["private"])
top_langs = sorted(lang.items(), key=lambda x: -x[1])[:5]
tmax = max((v for _, v in top_langs), default=1)
bars = [(n, v, "█" * max(1, round(v / tmax * 10))) for n, v in top_langs]
top_commits = sorted(per_repo, key=lambda x: -x[3])[:5]
last_push = max((r[4] or "") for r in per_repo) if per_repo else "—"

# --- генерация секции (все числа — из живого API, антигаллюцинация) ---
now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
lines = [
    BEGIN,
    "## 🛰 SWARM-SYNC · сверка со средой",
    f"> Автогенерация {now} · источник: живой GitHub API (public-флот: /users/rtynbirf/repos; языки — сумма байтов /repos/<repo>/languages, без истории git) · ни одного выдуманного числа · живой счёт роя для био — здесь, не в био",
    "",
    "| Метрика | Значение |",
    "|---|---|",
    f"| Репозиториев | **{len(repos)}** ({len(repos)-priv} публичных · {priv} приватных) |",
    f"| Коммитов всего | **{total_commits}** |",
    f"| Последний push | {last_push[:10] or '—'} |",
    "",
    "**Языки по объёму кода:**",
]
for n, v, b in bars:
    lines.append(f"- `{n}` {b} {v/1e6:.1f} МБ")
lines += ["", "**Топ-5 репо по коммитам (видимая работа):**"]
for n, p, l, c, pu in top_commits:
    vis = "" if not p else " 🔒"
    lines.append(f"- **{n}**{vis} — {c} коммитов · {l}")
lines.append(END)

# --- запись в рабочую копию: ЗАМЕНА между сентинелями, не append ---
section = "\n".join(lines)
ws = os.environ.get("GITHUB_WORKSPACE") or "."
path = os.path.join(ws, "README.md")
if not os.path.exists(path):
    sys.exit(f"README не найден: {path}")
cur = open(path, encoding="utf-8").read()
if CANON.search(cur):
    new = CANON.sub(lambda _: section, cur, count=1)
    how = "замена между каноническими сентинелями"
elif LEGACY.search(cur):
    new = LEGACY.sub(lambda _: section, cur, count=1)
    how = "миграция легаси-блока SWARM:BEGIN/SWARM:END на канонические сентинели (замена, не append)"
else:
    # fail-closed: витрина без маркеров — не тихая приписка, а честный красный
    sys.exit("SWARM-SYNC: в README нет ни сентинелей BEGIN/END_SWARM_SYNC, ни легаси-блока — "
             "отказ вместо append (приказ 2026-11-24: замена, не приписка)")
if new == cur:
    print("изменений нет — коммит не создаём (анти-шум)")
else:
    open(path, "w", encoding="utf-8").write(new)
    print(f"README перегенерирован в рабочей копии ({how}) — коммит выполнит workflow-шаг")
print(f"сверка: {len(repos)} репо, {total_commits} коммитов, {priv} приватных")
