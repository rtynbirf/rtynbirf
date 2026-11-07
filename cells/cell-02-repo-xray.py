#!/usr/bin/env python3
"""Полный анализ аккаунта GitHub по токену. ТОКЕН НИГДЕ НЕ ПЕЧАТАЕТСЯ И НЕ СОХРАНЯЕТСЯ."""
import json, re, time, urllib.request

TOK = [l.strip() for l in open("/tmp/gh_tokens.txt") if l.strip()]
# classic-токен (строка с ghp_) — у него есть скоуп repo для приватных
TOKEN = [t for t in TOK if t.startswith("ghp_")][0]
OUT = "/home/z/my-project/download/github-visualization"
import os
os.makedirs(OUT, exist_ok=True)

API = "https://api.github.com"

def req(url):
    r = urllib.request.Request(url, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "account-analysis",
    })
    with urllib.request.urlopen(r, timeout=30) as resp:
        return resp.read().decode(), resp.headers

def get_json(url):
    data, hdrs = req(url)
    return json.loads(data), hdrs

# --- профиль ---
user, _ = get_json(f"{API}/user")
profile = {k: user.get(k) for k in ("login", "name", "created_at", "followers", "following",
                                     "public_repos", "total_private_repos", "bio", "company", "location")}
print("ПРОФИЛЬ:", json.dumps(profile, ensure_ascii=False))

# --- все свои репозитории (публичные + приватные), с пагинацией ---
repos, page = [], 1
while True:
    data, hdrs = get_json(f"{API}/user/repos?visibility=all&affiliation=owner&per_page=100&sort=updated&page={page}")
    if not data:
        break
    repos += data
    link = hdrs.get("Link") or ""
    if 'rel="next"' not in link:
        break
    page += 1
print("РЕПО ВСЕГО:", len(repos))

# --- обогащение: языки и число коммитов на каждое репо ---
for i, r in enumerate(repos):
    full = r["full_name"]
    try:
        langs, _ = get_json(f"{API}/repos/{full}/languages")
        r["_languages"] = langs
    except Exception as e:
        r["_languages"] = {}
    try:
        _, hdrs = req(f"{API}/repos/{full}/commits?per_page=1")
        link = hdrs.get("Link") or ""
        m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
        r["_commits"] = int(m.group(1)) if m else (1 if link == "" else 0)
    except urllib.error.HTTPError as e:
        r["_commits"] = 0  # пустое репо (409) или иное
    except Exception:
        r["_commits"] = 0
    if (i + 1) % 10 == 0:
        print(f"  обогащено {i+1}/{len(repos)}")
    time.sleep(0.15)

# --- компактная выдача без мусора ---
clean = []
for r in repos:
    clean.append({
        "name": r["name"], "full_name": r["full_name"], "private": r["private"],
        "fork": r["fork"], "archived": r["archived"], "description": r.get("description"),
        "language": r.get("language"), "languages_bytes": r["_languages"],
        "stars": r["stargazers_count"], "forks_count": r["forks_count"],
        "size_kb": r["size"], "topics": r.get("topics", []),
        "created_at": r["created_at"], "updated_at": r["updated_at"], "pushed_at": r["pushed_at"],
        "commits_total": r["_commits"],
    })

result = {
    "profile": profile,
    "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "repos_count": len(clean),
    "private_count": sum(1 for c in clean if c["private"]),
    "public_count": sum(1 for c in clean if not c["private"]),
    "fork_count": sum(1 for c in clean if c["fork"]),
    "repos": clean,
}
json.dump(result, open(f"{OUT}/repo_analysis.json", "w"), ensure_ascii=False, indent=2)
print("СОХРАНЕНО:", f"{OUT}/repo_analysis.json")

# --- сводка для промпта ---
lang_total = {}
for c in clean:
    for l, b in (c["languages_bytes"] or {}).items():
        lang_total[l] = lang_total.get(l, 0) + b
top_langs = sorted(lang_total.items(), key=lambda x: -x[1])[:8]
total_commits = sum(c["commits_total"] for c in clean)
print("ТОП ЯЗЫКОВ:", top_langs)
print("КОММИТОВ ВСЕГО:", total_commits)
