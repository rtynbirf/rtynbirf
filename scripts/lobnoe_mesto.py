#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Лобное место профиля: лицо блока INV-AUTOMAT (баннер + обёртка README).

Стиль-канон дома: ORNAMENTAL MYTHO-REALISM (Правило 24 AGENTS.md) —
палитра NEUTRAL (лапис-обсидиан + золото + слоновая кость) + вермильон REVO,
MONO/SERIF, двойная золотая рамка, кронштейны, меандр, гравюрный штрих.
БАННЕР = ЛИЦО БЛОКА; числа — ТОЛЬКО из живых источников (Правило 3):
  - rtynbirf/inv-automat docs/inventory.json (последний прогон FSM)
  - INV_LEDGER.jsonl клеток-свидетелей (последняя строка)

Запуск: python3 scripts/lobnoe_mesto.py README.md
Пишет: assets/inv-forehead.svg + README между маркерами
  <!--INV:АВТОМАТ:НАЧАЛО--> ... <!--INV:АВТОМАТ:КОНЕЦ-->
"""

import json
import os
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com"
USER = "rtynbirf"
PROOFS = ("singulyar", "cell-swarm", "polymath-tools-atlas")
BEGIN = "<!--INV:АВТОМАТ:НАЧАЛО-->"
END = "<!--INV:АВТОМАТ:КОНЕЦ-->"
ANCHOR = "<!--АТЛАС:КАРТА:КОНЕЦ-->"
BANNER = "assets/inv-forehead.svg"
CANON = "ORNAMENTAL MYTHO-REALISM"

# палитра дома — из revo_account.py / revomat-central.py (Правило 24)
MONO = "'Cascadia Mono', ui-monospace, Consolas, monospace"
SERIF = "Georgia, 'Times New Roman', serif"
REVO = "#D5281B"
NEUTRAL = dict(bg="#10243E", bg2="#1B3B5F", ink="#F3ECD9",
               gold="#D4AF37", gold2="#E8C868", dim="#8FA3BF")


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;") \
                 .replace(">", "&gt;").replace('"', "&quot;")


def fetch(url, timeout=30):
    req = urllib.request.Request(url,
                                 headers={"User-Agent": "inv-lobnoe-mesto"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def last_ledger(repo):
    try:
        lines = fetch(f"{RAW}/{USER}/{repo}/HEAD/INV_LEDGER.jsonl")
        rec = json.loads(lines.strip().splitlines()[-1])
        return repo, rec["commits"], rec["files"]
    except Exception:
        return repo, None, None


def load_data():
    d = json.loads(fetch(f"{RAW}/{USER}/inv-automat/HEAD/docs/inventory.json"))
    witnesses = [last_ledger(r) for r in PROOFS]
    return d, witnesses


def render_banner(d, witnesses):
    """Лицевая плита блока: Ornamental Mytho-Realism, живые числа."""
    p = NEUTRAL
    bg, bg2, ink = p["bg"], p["bg2"], p["ink"]
    gold, gold2, dim = p["gold"], p["gold2"], p["dim"]
    s = d["fsm"]["summary"]
    meta = d["meta"]
    agg = d["aggregates"]
    run_id = esc(s.get("run_id") or meta.get("run_started") or "")
    ts = esc((s.get("ts") or meta.get("run_finished") or "")[:16]
             .replace("T", " "))
    n_cells = esc(agg.get("repos_count", "—"))
    n_commits = esc(agg.get("commits_sum_clones", "—"))
    n_claims = esc(s.get("claims", "—"))
    n_pass = esc(s.get("claims_pass", "—"))
    n_fail = esc(s.get("claims_fail", "—"))
    n_git = esc(meta.get("git_clones", "—"))
    witnesses_line = " · ".join(
        f"{esc(name)} {esc(commits)}" if commits is not None
        else f"{esc(name)} —" for name, commits, _ in witnesses)

    e = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 400" '
         'width="1280" height="400">']
    # маркер канона обязателен в баннере (КАНОН 1 AGENTS.md)
    e.append(f'<!-- {CANON} · INV-AUTOMAT · конечный автомат инвентаризации · '
             f'лицо блока · прогон {run_id} · числа только из живого '
             f'инвентаря (core/search/git/raw) -->')
    e.append('<defs>'
             '<radialGradient id="ra1" cx="0.5" cy="0.46" r="1.05">'
             f'<stop offset="0" stop-color="{bg2}"/>'
             f'<stop offset="1" stop-color="{bg}"/></radialGradient>'
             '<pattern id="meander" width="26" height="14" '
             'patternUnits="userSpaceOnUse">'
             f'<path d="M0 12 V3 H18 V12 H9 V8 H26" fill="none" '
             f'stroke="{gold2}" stroke-width="1.1" opacity="0.55"/></pattern>'
             '<pattern id="hatchg" width="6" height="6" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             f'<line x1="0" y1="0" x2="0" y2="6" stroke="{gold2}" '
             f'stroke-width="0.6" opacity="0.3"/></pattern>'
             '</defs>')
    e.append(f'<rect width="1280" height="400" fill="{bg}"/>')
    e.append(f'<rect width="1280" height="400" fill="url(#ra1)" '
             f'opacity="0.92"/>')
    # меандр-лента и двойная рамка с кронштейнами
    e.append(f'<rect x="22" y="34" width="1236" height="12" '
             f'fill="url(#meander)"/>')
    e.append(f'<rect x="14" y="14" width="1252" height="372" fill="none" '
             f'stroke="{gold}" stroke-width="1.3"/>')
    e.append(f'<rect x="22" y="22" width="1236" height="356" fill="none" '
             f'stroke="{gold}" stroke-width="0.55" opacity="0.55"/>')
    for (x, y, dx, dy) in ((22, 22, 1, 1), (1258, 22, -1, 1),
                           (22, 378, 1, -1), (1258, 378, -1, -1)):
        e.append(f'<path d="M {x} {y+dy*13} L {x} {y} L {x+dx*13} {y}" '
                 f'fill="none" stroke="{gold2}" stroke-width="1.4"/>')
    e.append(f'<path d="M 22 54 L 22 22 L 54 22 Z" fill="{REVO}"/>')
    # шапка и титул
    e.append(f'<text x="64" y="66" font-family="{MONO}" font-size="11" '
             f'fill="{gold}" letter-spacing="4">INV-AUTOMAT · КОНЕЧНЫЙ АВТОМАТ '
             f'ИНВЕНТАРИЗАЦИИ · LEDGER APPEND-ONLY · REVE=РЕВО</text>')
    e.append(f'<text x="64" y="146" font-family="{SERIF}" font-size="46" '
             f'fill="{ink}" letter-spacing="5">ИНВЕНТАРИЗАЦИЯ РОЯ</text>')
    e.append(f'<text x="64" y="186" font-family="{SERIF}" font-size="21" '
             f'fill="{gold2}" letter-spacing="2">живой замер, не декларация'
             f'</text>')
    e.append(f'<line x1="64" y1="206" x2="700" y2="206" stroke="{gold}" '
             f'stroke-width="1" opacity="0.85"/>')
    e.append(f'<text x="64" y="230" font-family="{MONO}" font-size="12.5" '
             f'fill="{dim}">ни одной цифры из README: core / search / git '
             f'blob:none / raw — и каждый переход автомата в ledger</text>')
    # пять медальонов фактов (золото — живое, вермильон — FAIL)
    medals = [("КЛЕТОК В РОЕ", n_cells, gold),
              ("КОММИТОВ В КЛЕТКАХ", n_commits, gold),
              ("CLAIMS СВЕРЕНО", n_claims, gold),
              ("PASS", n_pass, gold2),
              ("FAIL", n_fail, REVO)]
    for i, (lab, v, col) in enumerate(medals):
        cx = 109 + i * 150
        e.append(f'<g transform="translate({cx},292)">'
                 f'<circle r="27" fill="none" stroke="{col}" '
                 f'stroke-width="1.3"/>'
                 f'<circle r="31" fill="none" stroke="{col}" '
                 f'stroke-width="0.5" opacity="0.5"/>'
                 f'<text y="6" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="14.5" fill="{ink}">{v}</text>'
                 f'<text y="50" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="9.5" fill="{dim}" letter-spacing="2">{lab}'
                 f'</text></g>')
    # FSM-цепь: 9 состояний, DONE залит золотом
    states = ["IDLE", "BOOT", "INVENTORY", "CLAIMS", "VERIFY", "LEDGER",
              "REPORT", "PUBLISH", "DONE"]
    x0, y0 = 64, 342
    bx = x0
    for i, st in enumerate(states):
        w = 14 + 6.6 * len(st)
        fillc = gold2 if st == "DONE" else "none"
        tcol = bg2 if st == "DONE" else gold2
        e.append(f'<rect x="{bx:.0f}" y="{y0}" width="{w:.0f}" height="20" '
                 f'fill="{fillc}" stroke="{gold}" stroke-width="0.9"/>'
                 f'<text x="{bx + w/2:.0f}" y="{y0+13.5}" text-anchor="middle" '
                 f'font-family="{MONO}" font-size="9" fill="{tcol}" '
                 f'letter-spacing="1">{st}</text>')
        if i < len(states) - 1:
            e.append(f'<path d="M {bx+w:.0f} {y0+10} L {bx+w+12:.0f} '
                     f'{y0+10} M {bx+w+7:.0f} {y0+6.5} L {bx+w+12:.0f} '
                     f'{y0+10} L {bx+w+7:.0f} {y0+13.5}" fill="none" '
                     f'stroke="{dim}" stroke-width="0.9"/>')
        bx += w + 14
    # гравюрный штрих-подложка под свидетелями
    e.append(f'<rect x="{bx+8:.0f}" y="{y0}" width="{1216-bx-8:.0f}" '
             f'height="20" fill="url(#hatchg)" stroke="{gold2}" '
             f'stroke-width="0.5"/>')
    e.append(f'<text x="{bx+16:.0f}" y="{y0+13.5}" font-family="{MONO}" '
             f'font-size="9" fill="{ink}">СВИДЕТЕЛИ: {witnesses_line}'
             f'</text>')
    # правая колонка: git-замер и прогон
    e.append(f'<text x="1216" y="146" text-anchor="end" font-family="{MONO}" '
             f'font-size="12" fill="{dim}">клеток замерено git\'ом</text>')
    e.append(f'<text x="1216" y="172" text-anchor="end" font-family="{SERIF}" '
             f'font-size="26" fill="{ink}">{n_git}</text>')
    e.append(f'<text x="1216" y="230" text-anchor="end" font-family="{MONO}" '
             f'font-size="10.5" fill="{dim}" letter-spacing="1">ПРОГОН '
             f'{run_id}</text>')
    e.append(f'<text x="1216" y="248" text-anchor="end" font-family="{MONO}" '
             f'font-size="10.5" fill="{dim}" letter-spacing="1">{ts} UTC'
             f'</text>')
    # подвал
    e.append(f'<line x1="64" y1="372" x2="1216" y2="372" stroke="{gold}" '
             f'stroke-width="0.6" opacity="0.5"/>')
    e.append(f'<text x="640" y="392" text-anchor="middle" '
             f'font-family="{MONO}" font-size="10" fill="{dim}" '
             f'letter-spacing="2">SVG ПЕРЕРИСОВЫВАЕТСЯ АВТОМАТОМ ИЗ ЖИВОГО '
             f'ИНВЕНТАРЯ · РЕВО В ОСНОВЕ ВСЕГО · REVE=РЕВО · '
             f'ЧЕЛОВЕК=АККАУНТ=PID1</text>')
    e.append("</svg>")
    return "".join(e)


def render_block():
    d, witnesses = load_data()
    svg = render_banner(d, witnesses)
    alt = ("INV-AUTOMAT — конечный автомат инвентаризации: живой замер роя "
           "(Ornamental Mytho-Realism): прогон FSM, клеток, коммитов, claims "
           "PASS/FAIL, FSM-цепь IDLE→DONE, свидетели; числа — только живой "
           "инвентарь")
    block = f"""{BEGIN}
<div align="center">
  <a href="https://github.com/{USER}/inv-automat"><img src="{BANNER}" width="100%" alt="{alt}" /></a>
  <p><sub>🧬 КОНЕЧНЫЙ АВТОМАТ: <a href="https://github.com/{USER}/inv-automat">{USER}/inv-automat</a> — таблица переходов <code>IDLE→BOOT→INVENTORY→CLAIMS→VERIFY→LEDGER→REPORT→PUBLISH→DONE</code> · 📄 живой отчёт: <a href="https://rtynbirf.github.io/inv-automat/">Pages</a> · 📜 <a href="https://github.com/{USER}/inv-automat/blob/main/automat/ledger/runs.jsonl">ledger переходов</a> (append-only) · свидетель в каждой живой клетке — SVG перерисовывается автоматом из живого инвентаря, ни одной цифры из README</sub></p>
</div>
{END}"""
    return svg, block


def inject(readme, block):
    if BEGIN in readme and END in readme:
        pre = readme[:readme.index(BEGIN)]
        post = readme[readme.index(END) + len(END):]
        return pre + block + post
    if ANCHOR in readme:
        i = readme.index(ANCHOR) + len(ANCHOR)
        return readme[:i] + "\n\n" + block + readme[i:]
    return block + "\n\n" + readme


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    svg, block = render_block()
    os.makedirs(os.path.dirname(BANNER) or ".", exist_ok=True)
    with open(BANNER, "w", encoding="utf-8") as f:
        f.write(svg)
    with open(path, encoding="utf-8") as f:
        readme = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(inject(readme, block))
    print("лицо блока перековано:", BANNER, len(svg), "байт, канон:",
          CANON in svg, "| README:", BEGIN, "→", END)
    return 0


if __name__ == "__main__":
    sys.exit(main())
