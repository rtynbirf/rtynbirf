#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Лобное место профиля: живой блок INV-AUTOMAT в README.

Читает ТОЛЬКО живые источники (raw.githubusercontent), ни одной цифры руками:
  - rtynbirf/inv-automat docs/inventory.json  (последний прогон FSM)
  - INV_LEDGER.jsonl клеток-свидетелей        (последняя строка)

Идемпотентная вставка между маркерами:
  <!--INV:АВТОМАТ:НАЧАЛО--> ... <!--INV:АВТОМАТ:КОНЕЦ-->
Точка вставки при отсутствии маркеров: сразу после блока АТЛАС:КАРТА
(конвенция профиля: маркер-блоки перед H1).

Запуск: python3 scripts/lobnoe_mesto.py README.md
"""

import json
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com"
USER = "rtynbirf"
PROOFS = ("singulyar", "cell-swarm", "polymath-tools-atlas")
BEGIN = "<!--INV:АВТОМАТ:НАЧАЛО-->"
END = "<!--INV:АВТОМАТ:КОНЕЦ-->"
ANCHOR = "<!--АТЛАС:КАРТА:КОНЕЦ-->"


def fetch(url, timeout=30):
    req = urllib.request.Request(url,
                                 headers={"User-Agent": "inv-lobnoe-mesto"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def last_ledger(repo):
    """Последняя строка INV_LEDGER.jsonl клетки — живое свидетельство."""
    try:
        lines = fetch(f"{RAW}/{USER}/{repo}/HEAD/INV_LEDGER.jsonl")
        rec = json.loads(lines.strip().splitlines()[-1])
        return (f"[{repo}](https://github.com/{USER}/{repo})"
                f" **{rec['commits']}** коммитов / **{rec['files']}** файлов")
    except Exception as e:
        return f"{repo}: свидетельство недоступно ({str(e)[:40]})"


def render():
    d = json.loads(fetch(f"{RAW}/{USER}/inv-automat/HEAD/docs/inventory.json"))
    s = d["fsm"]["summary"]
    meta = d["meta"]
    agg = d["aggregates"]
    ts = (s.get("ts") or meta.get("run_finished") or "")[:16].replace("T", " ")
    proofs = " · ".join(last_ledger(r) for r in PROOFS)

    rows = [
        f"| Прогон FSM | `{s.get('run_id')}` · {ts} UTC · отчёт собран | [ledger переходов](https://github.com/{USER}/inv-automat/blob/main/automat/ledger/runs.jsonl) · append-only |",
        f"| Клеток в рое | {agg.get('repos_count')} | core `/user/repos` — живой API |",
        f"| Коммитов в клетках | {agg.get('commits_sum_clones')} | clone --bare --filter=blob:none + rev-list |",
        f"| Claims сверено | {s.get('claims')} · PASS {s.get('claims_pass')} · FAIL {s.get('claims_fail')} · противоречий {s.get('contradictions')} | механизм inv-automat |",
        f"| Клеток замерено git'ом | {meta.get('git_clones')} | точные счётчики, ноль бинарников |",
    ]
    if s.get("degraded_from"):
        rows.append(f"| Деградация | из состояния `{s['degraded_from']}` — честный частичный прогон | ledger |")

    block = f"""{BEGIN}
## 🧬 INV-AUTOMAT — конечный автомат инвентаризации: живой замер роя

| факт | значение | источник |
|---|---|---|
{chr(10).join(rows)}

**Периферийные свидетели** — в каждой живой клетке, cron-такт разнесён по хэшу имени. Последние живые свидетельства (INV_LEDGER.jsonl): {proofs}

📄 Живой отчёт: [rtynbirf.github.io/inv-automat](https://rtynbirf.github.io/inv-automat/) · 🤖 Клетка-автомат: [rtynbirf/inv-automat](https://github.com/{USER}/inv-automat)

*Ни одна цифра блока не взята из README: core/search/git/raw — и каждый переход автомата дописан в ledger. Блок перерисовывается на автомате из живого инвентаря.*
{END}"""
    return block


def inject(readme, block):
    if BEGIN in readme and END in readme:
        pre = readme[:readme.index(BEGIN)]
        post = readme[readme.index(END) + len(END):]
        return pre + block + post
    if ANCHOR in readme:
        i = readme.index(ANCHOR) + len(ANCHOR)
        return readme[:i] + "\n\n" + block + readme[i:]
    return block + "\n\n" + readme  # крайний случай: наверх, лобное место


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    with open(path, encoding="utf-8") as f:
        readme = f.read()
    updated = inject(readme, render())
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("лобное место перерисовано:", BEGIN, "→", END,
          "| длина README:", len(updated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
