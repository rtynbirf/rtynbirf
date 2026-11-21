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

record = {
    "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "mode": "actions" if os.environ.get("GITHUB_ACTIONS") else "local-run",
    "fleet": len(repo_list),
    "болезнь": disease,
    "выключено_целиком": blind,
    "приказы_не_тронуты": len(set(orders)),
    "kick_тихой_смерти": kicks,
    "ошибки": errors,
    "источник": "api.github.com, живой опрос",
}
os.makedirs(os.path.dirname(os.path.abspath(LEDGER)), exist_ok=True)
with open(LEDGER, "a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
print(json.dumps(record, ensure_ascii=False, indent=1))
sys.exit(2 if (disease or kicks or blind) else 0)
