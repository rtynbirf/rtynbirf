#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЗАВОДНОЙ КЛЮЧ — клетка роя: кроны GitHub душатся под нагрузкой (прогон может
опоздать на часы или не случиться вовсе). Ключ заводит спящих: по каждому пушу
в main проверяет возраст последнего УСПЕШНОГО прогона периодических клеток и
диспатчит просроченных. Красные прогоны не ретраит вслепую (честный красный +
гигиена уведомлений); их чинит волна или Доктор гейтов.

Патч 2026-11-15 (доведение до ума, ПРАВДА-2):
- транзиенты (429, 5xx, вторичный 403 rate-limit) — ретрай с бэкоффом и
  печатью кода; молчаливая смерть крона от одиночного транзиента = ложный красный;
- один неотвечающий вызов больше не убивает весь завод: клетка уходит в "раны",
  ключ продолжает заводить остальных (пуш 01:10 11-15: один 403 обнулил весь прогон);
- каждый отказ печатается со своим HTTP-кодом и телом (честный красный)."""
import json, os, sys, time, urllib.request, urllib.error, datetime

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

def req(url, method="GET", payload=None, retries=3):
    """Живой вызов: транзиенты (429/5xx/вторичный 403) — бэкофф; остальное — сразу.
    Тело ответа печатаем: честный отказ это код + причина, не пустой крэш."""
    last = None
    for attempt in range(retries):
        r = urllib.request.Request(url, method=method,
                                   data=json.dumps(payload).encode() if payload is not None else None,
                                   headers=hdr())
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                raw = resp.read().decode()
                return (json.loads(raw) if raw.strip() else {}), resp.status
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:160]
            except Exception:
                pass
            transient = e.code in (429, 500, 502, 503, 504) or (
                e.code == 403 and "rate limit" in body.lower())
            print(f"API {method} {url.split(API)[-1]} -> HTTP {e.code} "
                  f"(попытка {attempt + 1}/{retries}) {body}", file=sys.stderr)
            last = (None, e.code)
            if not transient:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            print(f"API {method} {url.split(API)[-1]} -> сеть: {e} "
                  f"(попытка {attempt + 1}/{retries})", file=sys.stderr)
            last = (None, 0)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"транзиент не отступил после {retries} попыток (последний код {last[1]})")

def wind_cell(fname, max_age_h, now):
    """Завод одной клетки. Возвращает (статус, слово). Исключения — наверх."""
    w = by_path.get(fname)
    if not w:
        return None, f"{fname}: клетки нет — пропуск"
    runs = req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{w['id']}/runs?per_page=5")[0].get("workflow_runs", [])
    if not runs:
        req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{w['id']}/dispatches",
            method="POST", payload={"ref": "main"})
        return "fired", f"{fname}: прогонов нет — диспатч (первый завод)"
    last = runs[0]
    if last["status"] in ("in_progress", "queued", "waiting"):
        return None, f"{fname}: уже в работе ({last['created_at']}) — не трогаем"
    age_h = (now - datetime.datetime.fromisoformat(last["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600
    if last["conclusion"] == "success" and age_h > max_age_h:
        req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{w['id']}/dispatches",
            method="POST", payload={"ref": "main"})
        return "fired", f"{fname}: спал {age_h:.1f} ч (норма {max_age_h}) — ЗАВЕДЁН"
    if last["conclusion"] != "success":
        return "wound", f"{fname}: честный красный ({last['conclusion']}, {age_h:.1f} ч) — не ретраим вслепую"
    return None, f"{fname}: свежий ({age_h:.1f} ч) — ключ не нужен"

def main():
    global by_path
    wfs = req(f"{API}/repos/{OWNER}/{REPO}/actions/workflows?per_page=100")[0].get("workflows", [])
    by_path = {w["path"].split("/")[-1]: w for w in wfs}
    now = datetime.datetime.now(datetime.timezone.utc)
    wound, fired, lines = [], [], []
    for fname, max_age_h in WATCHLIST.items():
        try:
            kind, line = wind_cell(fname, max_age_h, now)
        except Exception as e:
            kind, line = "wound", f"{fname}: завод не прошёл ({e}) — рана Доктору, завод продолжается"
        lines.append(line)
        print(line, flush=True)
        if kind == "fired":
            fired.append(fname); time.sleep(1)
        elif kind == "wound":
            wound.append(line)
    print("ИТОГ:", f"заведено {len(fired)}: {', '.join(fired)}" if fired else "все на ходу",
          ("| раны: " + "; ".join(wound)) if wound else "| ран нет")
    # ключ отработал целиком: раны перечислены честно, крэш не нужен.
    sys.exit(0)

if __name__ == "__main__":
    main()
