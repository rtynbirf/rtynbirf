#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""СТРАЖ СПЯЩИХ · правило 26 дома Полимат-Универсум (заходы 3–6, 2026-11-20/21).

Различает ПРИКАЗ и БОЛЕЗНЬ (живой урок инвентаризации: 216 disabled_manually —
намеренные приказы; disabled_inactivity — болезнь 60-дневной заморозки).

1. Флот: состояния воркфлоу. disabled_inactivity → enable (БОЛЕЗНЬ лечится).
   disabled_manually → только пересчёт (ПРИКАЗ не трогается).
1a. Слепое пятно (заход 6, урок markitdown): Actions выключены на уровне репо —
   воркфлоу для рана не существуют, болезни не видны. enabled=False → enable.
2. Критические кроны: активный воркфлоу, молчащий сверх порога, — тихая смерть
   → компенсация ручным диспатчем (kick). Включая СТРАЖА самого (self-watch).
3. Один клейм в append-only ledger: СТРАЖ-СПЯЩИХ.jsonl (правило 25: каждая
   запись несёт источник и метку свежести).
4. Красное — честно красное: exit 2 при найденной болезни/тихой смерти.
5. П4 «СТРАЖ смотрит сердце»: внешний свидетель — сердце factum (pulse.json,
   публичный raw, БЕЗ токена). LIVE — ещё один живой сигнал; STALE/недоступен —
   честная строка в ledger с пометкой factum. Правило 27: ЭКГ остаётся в самом
   factum — СТРАЖ здесь только аудитор (чтение и клейм, никакого enable/kick
   чужого сердца, дубликата стража нет).
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

TOK = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "СТРАЖ-СПЯЩИХ.jsonl")
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "strazh-spyashchih"}
OWNER = "rtynbirf"

# П4: внешний свидетель — сердце factum. Публичный raw, без токена, без ключей.
FACTUM_PULSE_URL = "https://raw.githubusercontent.com/rtynbirf/factum/main/pulse.json"

# критические кроны (правило 26): (repo, workflow_name, порог тишины в секундах)
CRITICAL = [
    (OWNER + "/rtynbirf", "РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ", 2 * 3600),
    (OWNER + "/rtynbirf", "пульс-правды", 4 * 3600),
    (OWNER + "/rtynbirf", "SWARM-SYNC (сверка со средой)", 26 * 3600),
    (OWNER + "/khozyain", "Пульс дома (self-check слоя)", 26 * 3600),
    (OWNER + "/cell-swarm", "wave3-genome-pulse", 26 * 3600),
    # self-watch (заход 4): страж сторожит сам себя — за ночь */23 тикнул ~3 раза вместо ~38
    (OWNER + "/rtynbirf", "СЕРДЦЕ ТАКТА · СТРАЖ СПЯЩИХ (правило 26)", 26 * 3600),
]

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("https://api.github.com" + path, data=data,
                                 headers=HDRS, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}  # 204 No Content → {}

def dispatch_workflow(repo, wf_id):
    """Ручной kick через actions:write."""
    api(f"/repos/{repo}/actions/workflows/{wf_id}/dispatches",
        method="POST", body={"ref": "main"})


def factum_svidetel(now):
    """П4: аудит сердца factum — pulse.json как ещё одного свидетеля дома.
    Правило 25: число несёт источник и метку свежести — возраст пересчитывается
    здесь по часам СТРАЖА от last_beat_utc, self-статус pulse.json сохраняется
    рядом (расхождение источников публикуется, не прячется). Правило 23: STALE /
    недоступен — это клейм «зелёное сердце не клеймится». URL молчит или отвечает
    мусором — честный SOURCE_UNAVAILABLE, не креш."""
    src = "factum pulse.json (raw.githubusercontent.com/rtynbirf/factum/main/pulse.json)"
    svidetel = {"источник": src,
                "свежесть": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "роль": "аудитор (правило 27: ЭКГ остаётся в factum, СТРАЖ не дублирует)"}
    try:
        req = urllib.request.Request(FACTUM_PULSE_URL, headers={"User-Agent": "strazh-spyashchih"})
        with urllib.request.urlopen(req, timeout=30) as r:
            pulse = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        svidetel.update({"статус": "SOURCE_UNAVAILABLE", "сам_о_себе": "",
                         "возраст_удара_ч": None, "последний_удар_utc": "",
                         "ошибка": str(e)[:120]})
        return svidetel
    if not isinstance(pulse, dict) or "status" not in pulse:
        svidetel.update({"статус": "SOURCE_UNAVAILABLE", "сам_о_себе": "",
                         "возраст_удара_ч": None, "последний_удар_utc": "",
                         "ошибка": "ответ не похож на pulse.json"})
        return svidetel
    thr = float(pulse.get("stale_threshold_hours") or 12)
    beat = pulse.get("last_beat_utc") or ""
    try:
        b0 = datetime.fromisoformat(beat.replace("Z", "+00:00"))
        age = round((now - b0).total_seconds() / 3600, 1)
    except Exception:
        age = None
    self_status = pulse.get("status") or "UNKNOWN"
    status = "LIVE" if (age is not None and age <= thr) else "STALE"
    svidetel.update({"статус": status, "сам_о_себе": self_status,
                     "возраст_удара_ч": age, "последний_удар_utc": beat,
                     "порог_stale_ч": thr})
    if status != self_status:
        svidetel["расхождение"] = f"pulse.json говорит {self_status}, аудит по часам СТРАЖА — {status}"
    return svidetel

repo_list = api(f"/users/{OWNER}/repos?per_page=100&type=owner")
disease, orders, kicks, errors, blind = [], [], [], [], []
now = datetime.now(timezone.utc)

for r in repo_list:
    full = r["full_name"]
    try:
        # 1a: Actions выключены на уровне репо (урок markitdown, форк) —
        # воркфлоу не существуют для рана; включаем и идём дальше честно.
        perm = api(f"/repos/{full}/actions/permissions")
        if perm.get("enabled") is False:
            api(f"/repos/{full}/actions/permissions", method="PUT", body={"enabled": True})
            blind.append({"repo": full, "cured": "actions-permissions: enabled"})
            continue
    except Exception as e:
        errors.append({"repo": full, "error": str(e)[:80]})
    try:
        wfs = api(f"/repos/{full}/actions/workflows").get("workflows", [])
    except Exception as e:
        errors.append({"repo": full, "error": str(e)[:80]})
        continue
    for w in wfs:
        st = w.get("state")
        if st == "disabled_inactivity":
            # БОЛЕЗНЬ: лечим — enable + kick
            try:
                req_id = w["id"]
                api(f"/repos/{full}/actions/workflows/{req_id}/enable", method="PUT")
                time.sleep(0.3)
                dispatch_workflow(full, req_id)
                disease.append({"repo": full, "wf": w.get("name"), "cured": "enable+dispatch"})
                time.sleep(0.3)
            except Exception as e:
                errors.append({"repo": full, "wf": w.get("name"), "error": str(e)[:80]})
        elif st == "disabled_manually":
            orders.append(full)  # ПРИКАЗ: пересчитали, не тронули

# тихая смерть критических кронов: активен, но молчит сверх порога
for repo, wname, thr in CRITICAL:
    try:
        wfs = api(f"/repos/{repo}/actions/workflows").get("workflows", [])
        wf = next((w for w in wfs if w.get("name") == wname), None)
        if not wf:
            errors.append({"repo": repo, "wf": wname, "error": "не найден"})
            continue
        if wf.get("state") != "active":
            continue  # неактивный — уже учтён выше
        runs = api(f"/repos/{repo}/actions/runs?event=schedule&per_page=1")
        items = runs.get("workflow_runs", [])
        if items:
            last = datetime.fromisoformat(items[0]["created_at"].replace("Z", "+00:00"))
            age = (now - last).total_seconds()
        else:
            age = None
        if age is None or age > thr:
            # тихая смерть: активен и молчит — компенсируем ручным диспатчем
            try:
                dispatch_workflow(repo, wf["id"])
                kicks.append({"repo": repo, "wf": wname,
                              "silence_h": round((age or 0) / 3600, 1),
                              "action": "dispatch-компенсация"})
                time.sleep(0.3)
            except Exception as e:
                errors.append({"repo": repo, "wf": wname, "error": str(e)[:80]})
    except Exception as e:
        errors.append({"repo": repo, "wf": wname, "error": str(e)[:80]})

# П4: сердце factum — ещё один живой сигнал (LIVE) или честное клеймо с пометкой
# factum (STALE/недоступен). СТРАЖ не лечит чужое сердце (правило 27) — только
# пишет свидетеля в ledger и краснит клейм.
factum = factum_svidetel(now)
if factum["статус"] != "LIVE":
    print(f"СВИДЕТЕЛЬ FACTUM: {factum['статус']} — "
          f"{factum.get('ошибка') or factum.get('расхождение') or 'сердце молчит сверх порога'}")

record = {
    "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "mode": "actions" if os.environ.get("GITHUB_ACTIONS") else "local-run",
    "fleet": len(repo_list),
    "болезнь": disease,
    "выключено_целиком": blind,
    "приказы_не_тронуты": len(set(orders)),
    "kick_тихой_смерти": kicks,
    "свидетель_factum": factum,
    "ошибки": errors,
    "источник": "api.github.com, живой опрос",
}
os.makedirs(os.path.dirname(os.path.abspath(LEDGER)), exist_ok=True)
with open(LEDGER, "a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
print(json.dumps(record, ensure_ascii=False, indent=1))
factum_bad = factum["статус"] in ("STALE", "SOURCE_UNAVAILABLE")
sys.exit(2 if (disease or kicks or blind or factum_bad) else 0)
