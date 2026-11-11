#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЗАВОДНОЙ КЛЮЧ — клетка роя: кроны GitHub душатся под нагрузкой (прогон может
опоздать на часы или не случиться вовсе). Ключ заводит спящих: по каждому пушу
в main проверяет возраст последнего УСПЕШНОГО прогона периодических клеток и
диспатчит просроченных. Красные прогоны не ретраит вслепую (честный красный +
гигиена уведомлений); их чинит волна или Доктор гейтов."""
import json, os, sys, time, urllib.request, datetime

API = "https://api.github.com"
OWNER, REPO = "rtynbirf", "rtynbirf"
TOK = os.environ.get("GITHUB_TOKEN")
if not TOK:
    sys.exit("нет GITHUB_TOKEN")

# клетка: файл воркфлоу → максимальный возраст последнего успешного прогона (часов)
WATCHLIST = {
    "pulse.yml": 2,            # пульс-правды: расчётка 30 мин, терпит до 2 ч
    "3d-contrib.yml": 26,      # свет вселенной: расчётка сутки
    "numbers-canon.yml": 26,   # канон пяти: расчётка сутки (после 3d-contrib)
    "swarm-sync.yml": 26,      # сверка со средой: расчётка сутки
    "swarm-health.yml": 24 * 8,  # расчётка понедельник 04:41, терпит до 8 суток
    "neofetch-card.yml": 26,   # терминал роя: расчётка сутки
}

def hdr():
    return {"User-Agent": "zavodnoy-klyuch", "Accept": "application/vnd.github+json",
            "Authorization": f"token {TOK}"}

def req(url, method="GET", payload=None):
    r = urllib.request.Request(url, method=method,
                               data=json.dumps(payload).encode() if payload is not None else None,
                               headers=hdr())
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return (json.loads(raw) if raw.strip() else {}), resp.status

def main():
    wfs = req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows?per_page=100")[0].get("workflows", [])
    by_path = {w["path"].split("/")[-1]: w for w in wfs}
    now = datetime.datetime.now(datetime.timezone.utc)
    wound, fired = [], []
    for fname, max_age_h in WATCHLIST.items():
        w = by_path.get(fname)
        if not w:
            print(f"{fname}: клетки нет — пропуск"); continue
        runs = req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{w['id']}/runs?per_page=5")[0].get("workflow_runs", [])
        if not runs:
            print(f"{fname}: прогонов нет — диспатч (первый завод)")
            req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{w['id']}/dispatches",
                method="POST", payload={"ref": "main"})
            fired.append(fname); time.sleep(1); continue
        last = runs[0]
        if last["status"] in ("in_progress", "queued", "waiting"):
            print(f"{fname}: уже в работе ({last['created_at']}) — не трогаем"); continue
        age_h = (now - datetime.datetime.fromisoformat(last["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600
        if last["conclusion"] == "success" and age_h > max_age_h:
            req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{w['id']}/dispatches",
                method="POST", payload={"ref": "main"})
            fired.append(fname)
            print(f"{fname}: спал {age_h:.1f} ч (норма {max_age_h}) — ЗАВЕДЁН")
        elif last["conclusion"] != "success":
            wound.append(f"{fname}:{last['conclusion']}@{last['created_at']}")
            print(f"{fname}: честный красный ({last['conclusion']}, {age_h:.1f} ч) — не ретраим вслепую")
        else:
            print(f"{fname}: свежий ({age_h:.1f} ч) — ключ не нужен")
    print("ИТОГ:", f"заведено {len(fired)}: {', '.join(fired)}" if fired else "все на ходу",
          ("| раны: " + ", ".join(wound)) if wound else "| ран нет")

if __name__ == "__main__":
    main()
