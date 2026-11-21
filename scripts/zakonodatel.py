#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЗАКОНОДАТЕЛЬ · правило 28 дома Полимат-Универсум (заход 5, 2026-11-21).

Единый источник закона — rtynbirf/rtynbirf (AGENTS.md 1–28 + ТРЕБОВАНИЯ-ДЛЯ-АГЕНТОВ).
Распространение изменений закона по флоту — ТОЛЬКО через этот скрипт:

  python scripts/zakonodatel.py --file закон-дельта.md --message "..." --limit 20

Дисциплина волны (шрамы 2026-11-21: 79-коммитная волна чурила Доктора гейтов
и рвала ЗАВОДНОЙ КЛЮЧ):
  * батч ≤ --limit тел за прогон (по умолчанию 20), пауза между телами;
  * идемпотентность: маркер блока не дублируется, уже накрытые тела пропускаются;
  * архивы пропускаются, отказы — честно в протокол (zakonodatel-protokol.jsonl);
  * продолжение волны — следующим прогоном (очередь = тела без маркера).
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HDRS_TPL = {"Accept": "application/vnd.github+json", "User-Agent": "zakonodatel"}


def hdr(tok):
    return dict(HDRS_TPL, Authorization=f"Bearer {tok}")


def api(tok, path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("https://api.github.com" + path, data=data,
                                 headers=hdr(tok), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:150]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="файл с дельтой закона (markdown)")
    ap.add_argument("--message", required=True, help="commit message (правило 12: что сделано + REVE=РЕВО)")
    ap.add_argument("--limit", type=int, default=20, help="батч тел за прогон")
    ap.add_argument("--pause", type=float, default=2.0, help="пауза между телами, сек")
    ap.add_argument("--marker", default="ПРАВИЛА 23–27", help="маркер уже накрытого тела")
    ap.add_argument("--owner", default="rtynbirf")
    args = ap.parse_args()

    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not tok:
        sys.exit("нет GITHUB_TOKEN")
    block = open(args.file, encoding="utf-8").read()
    repos = api(tok, f"/users/{args.owner}/repos?per_page=100&type=owner")
    if isinstance(repos, dict) and "__error__" in repos:
        sys.exit(f"флот недоступен: {repos}")

    queue = [r for r in repos if not r["archived"]]
    protokol = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "wave_file": args.file, "limit": args.limit,
                "накрыто_уже": [], "внесено": [], "отказы": []}
    done = 0
    for r in queue:
        if done >= args.limit:
            break
        name = r["name"]
        cur = api(tok, f"/repos/{args.owner}/{name}/contents/AGENTS.md?ref={r['default_branch']}")
        if "__error__" in cur:
            protokol["отказы"].append({"repo": name, "step": "get", "code": cur["__error__"]})
            continue
        content = base64.b64decode(cur["content"]).decode("utf-8", "replace")
        if args.marker in content:
            protokol["накрыто_уже"].append(name)
            continue
        new = content.rstrip() + "\n" + block
        put = api(tok, f"/repos/{args.owner}/{name}/contents/AGENTS.md", method="PUT", body={
            "message": args.message,
            "content": base64.b64encode(new.encode("utf-8")).decode(),
            "sha": cur["sha"], "branch": r["default_branch"],
        })
        if "__error__" in put:
            protokol["отказы"].append({"repo": name, "step": "put", "code": put["__error__"]})
        else:
            protokol["внесено"].append(name)
            done += 1
        time.sleep(args.pause)

    protokol["итог"] = {"внесено": len(protokol["внесено"]), "уже": len(protokol["накрыто_уже"]),
                        "отказов": len(protokol["отказы"]), "осталось_в_очереди": len(queue) - done}
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "zakonodatel-protokol.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(protokol, ensure_ascii=False) + "\n")
    print(json.dumps(protokol, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
