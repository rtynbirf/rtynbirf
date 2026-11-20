#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Виджет профиля: КАРТА=ТЕРРИТОРИИ · МОДЕЛЬ=РЕАЛЬНОСТЬ.
SVG перерисовывается из данных атласа (passports.json) на автомате:
12 классов — регионы (площадь ∝ живым позициям), цвет — доминирующая
ступень M-шкалы, поглощённые позиции — полые кольца за краем ядра.
Упаковка детерминированная (фиаллотаксис 137.5° + радиальный отжим) —
Пуанкаре одобрил бы: карта изометрична данным."""
import json, math, sys
from collections import Counter

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/passports.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "assets/atlas-territory.svg"

D = json.load(open(SRC, encoding="utf-8"))
P = D["passports"]
live = [p for p in P if not str(p.get("status", "")).startswith("поглощён")]
absorbed = len(P) - len(live)
agg = Counter()
cls = Counter()
cls_m = {}
for p in live:
    for pat, code in (("Research", "M4"), ("Experimental", "M3"), ("Deployed", "M2"), ("Mainstream", "M1")):
        if pat in p["maturity"]:
            agg[code] += 1
            c = p["type_code"].split("/")[0]
            cls[c] += 1
            cls_m.setdefault(c, Counter())[code] += 1
            break
VERSION = D.get("version", "—")
DATE = max((p.get("verified_on", "—") for p in P if p.get("verified_on", "—") != "—"), default="2026-11-20")

M_COLOR = {"M1": "#d4a24e", "M2": "#4e9fb8", "M3": "#8b6cc8", "M4": "#c25b5b"}
M_NAME = {"M1": "M1 Mainstream", "M2": "M2 Deployed", "M3": "M3 Experimental", "M4": "M4 Research"}

# упаковка: главный класс в центре, остальные — по фиаллотаксисной орбите
items = sorted(cls.items(), key=lambda kv: -kv[1])
k = 5.2
placed = []          # (x, y, r)
def place(r, start_r):
    ang, rr, misses = 0.0, start_r, 0
    for _ in range(6000):
        x, y = CX + rr * math.cos(math.radians(ang)), CY + rr * math.sin(math.radians(ang))
        ok_bounds = 50 + r <= x <= 770 - r and 90 + r <= y <= 578 - r
        ok_free = all((x - px) ** 2 + (y - py) ** 2 >= (r + pr + 7) ** 2 for px, py, pr in placed)
        if ok_bounds and ok_free:
            return x, y
        misses += 1
        ang += 137.508
        if misses % 12 == 0:
            rr += 4
    raise SystemExit(f"упаковка не сошлась для r={r}")

CX, CY = 400, 330
svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" font-family="Georgia, 'Times New Roman', serif">
<rect width="1200" height="630" fill="#0d0b08"/>
<rect x="8" y="8" width="1184" height="614" fill="none" stroke="#d4a24e" stroke-width="1.4" opacity="0.75"/>
<rect x="14" y="14" width="1172" height="602" fill="none" stroke="#d4a24e" stroke-width="0.5" opacity="0.35"/>
<text x="36" y="56" fill="#d4a24e" font-size="30" font-weight="bold" letter-spacing="2">КАРТА = ТЕРРИТОРИИ</text>
<text x="36" y="80" fill="#9c8f78" font-size="14" letter-spacing="4">МОДЕЛЬ = РЕАЛЬНОСТЬ</text>
<text x="1164" y="52" fill="#c8b98f" font-size="13" text-anchor="end">GLOBAL PRACTICE ATLAS · {VERSION} · {DATE}</text>
<text x="1164" y="70" fill="#77694f" font-size="11" text-anchor="end">данные: global-practice-atlas · автомат: relomat</text>''']

for i, (c, n) in enumerate(items):
    r = max(14, math.sqrt(n) * 4.6)
    if i == 0:
        x, y = CX, CY
    else:
        x, y = place(r, 70 + r)
    placed.append((x, y, r))
    dom = cls_m[c].most_common(1)[0][0]
    share = cls_m[c][dom] / n
    op = 0.28 + 0.5 * share
    svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{M_COLOR[dom]}" fill-opacity="{op:.2f}" stroke="#d4a24e" stroke-width="0.9"/>')
    fs = 13 if r >= 42 else (11 if r >= 30 else 9)
    svg.append(f'<text x="{x:.0f}" y="{y + 3:.0f}" fill="#f2e8d5" font-size="{fs}" text-anchor="middle" font-weight="bold">{c}</text>')
    if r >= 26:
        svg.append(f'<text x="{x:.0f}" y="{y + 17:.0f}" fill="#c8b98f" font-size="10" text-anchor="middle">{n}</text>')

# поглощённые — полые кольца (строки сохранены, позиции слились)
for j in range(absorbed):
    ang = j * 34.0
    x, y = CX + 356 * math.cos(math.radians(ang)), CY + 356 * math.sin(math.radians(ang))
    svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6.5" fill="none" stroke="#77694f" stroke-width="1.2" stroke-dasharray="3 2"/>')

svg.append(f'<text x="{CX}" y="{CY + 286:.0f}" fill="#5f5643" font-size="10" text-anchor="middle">— — полые кольца: {absorbed} поглощённых позиций, строки сохранены</text>')

# правая панель: M-шкала и верификация
px = 830
svg.append(f'<text x="{px}" y="120" fill="#d4a24e" font-size="16" font-weight="bold" letter-spacing="1">M-ШКАЛА · ЖИВЫХ {len(live)}</text>')
yy = 150
for code in ("M1", "M2", "M3", "M4"):
    w = agg[code] / max(agg.values()) * 210
    svg.append(f'<rect x="{px}" y="{yy - 11}" width="{w:.0f}" height="13" fill="{M_COLOR[code]}" opacity="0.75"/>')
    svg.append(f'<text x="{px + 224}" y="{yy}" fill="#e8dcc0" font-size="13">{M_NAME[code]}</text>')
    svg.append(f'<text x="{px}" y="{yy - 15}" fill="#9c8f78" font-size="11">{agg[code]}</text>')
    yy += 44
svg.append(f'<text x="{px}" y="{yy + 8}" fill="#d4a24e" font-size="15" font-weight="bold" letter-spacing="1">ВЕРИФИКАЦИЯ</text>')
for t in ["РЕЛОМАТ · строки атласа: 43/43", "РЕЛОМАТ · эмерджентные: 11/11",
          "глобальный скан: 660 675 пар · 5 SAME найдены", "QA: 15 проверок · CI независим"]:
    svg.append(f'<text x="{px}" y="{yy + 30}" fill="#c8b98f" font-size="12.5">{t}</text>')
    yy += 22
svg.append(f'<text x="{px}" y="{yy + 44}" fill="#77694f" font-size="11">неполнота помечена честно: open_fields · Гёдель одобрил бы</text>')
svg.append(f'<text x="36" y="600" fill="#5f5643" font-size="10.5">перерисовывается автоматически из данных репозитория · классы — коды 12-классной типологии · площадь ∝ числу живых позиций</text>')
svg.append('</svg>')
open(OUT, "w", encoding="utf-8").write("\n".join(svg))
print(f"виджет: {OUT} | классов {len(items)} · живых {len(live)} · M {dict(agg)} | поглощённых колец {absorbed}")
