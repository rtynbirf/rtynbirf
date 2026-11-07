#!/usr/bin/env python3
"""SWARM-SYNC — клетка роя: сверка со средой и автогенерация секции README.
Запускается в GitHub Actions и локально. Только stdlib. Токен не печатает."""
import base64, json, os, re, sys, time, urllib.request

API = "https://api.github.com"
OWNER, REPO = "rtynbirf", "rtynbirf"
BEGIN, END = "<!-- SWARM:BEGIN автогенерация -->", "<!-- SWARM:END -->"

def hdr(tok):
    return {"Authorization": f"token {tok}", "Accept": "application/vnd.github+json", "User-Agent": "swarm-sync"}

def req(tok, url, method="GET", payload=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(payload).encode() if payload is not None else None,
                               headers=hdr(tok))
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return (json.loads(raw) if raw.strip() else {}), resp.headers

# --- выбор токенов: чтение данных (нужны приватные) и запись (лучше от bot) ---
READ_TOK = os.environ.get("SWARM_TOKEN") or os.environ.get("GITHUB_TOKEN")
WRITE_TOK = os.environ.get("GITHUB_TOKEN") or os.environ.get("SWARM_TOKEN")
if not READ_TOK or not WRITE_TOK:
    sys.exit("нет токенов: SWARM_TOKEN/GITHUB_TOKEN")

# --- сверка со средой: живые данные ---
user, _ = req(READ_TOK, f"{API}/user")
repos, page = [], 1
while True:
    data, h = req(READ_TOK, f"{API}/user/repos?visibility=all&affiliation=owner&per_page=100&sort=updated&page={page}")
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
    per_repo.append((r["name"], r["private"], r.get("language") or "—", c, r["size_kb"] if "size_kb" in r else r.get("size", 0), r["pushed_at"]))
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
last_push = max((r[5] or "") for r in per_repo) if per_repo else "—"

# --- генерация секции (все числа — из живого API, антигаллюцинация) ---
now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
lines = [
    BEGIN,
    "## 🛰 SWARM-SYNC · сверка со средой",
    f"> Автогенерация {now} · источник: живой GitHub API · ни одного выдуманного числа",
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
lines += ["", "**Топ-5 репо по коммитам (визимая работа):**"]
for n, p, l, c, s, pu in top_commits:
    vis = "" if not p else " 🔒"
    lines.append(f"- **{n}**{vis} — {c} коммитов · {l}")
lines.append(END)

# --- запись только при реальном изменении (анти-пустые-коммиты, best practice) ---
st, readme = req(WRITE_TOK, f"{API}/repos/{OWNER}/{REPO}/contents/README.md")
cur = base64.b64decode(readme["content"]).decode()
section = "\n".join(lines)
new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), section.replace("\\", "\\\\"), cur, flags=re.S)
if BEGIN not in cur:
    new = cur.rstrip() + "\n\n" + section + "\n"
if new == cur:
    print("изменений нет — коммит не создаём (анти-шум)")
    return_ok = True
else:
    body = {"message": f"swarm-sync: сверка со средой {now} [skip ci]", "content": base64.b64encode(new.encode()).decode(), "sha": readme["sha"]}
    st2, resp = req(WRITE_TOK, f"{API}/repos/{OWNER}/{REPO}/contents/README.md", "PUT", body)
    print("README обновлён:", st2)
print(f"сверка: {len(repos)} репо, {total_commits} коммитов, {priv} приватных")
