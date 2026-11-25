#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПРИЁМКА ФРОНТ-СТРАНИЦЫ rtynbirf (заход 7): базовые проверки пакета v1.0 +
инварианты живого слоя дома: якорная целостность ФОРЖ-блоков и alt-тексты.

Требования: FR-01…12 (03_SPEC.md). Запуск: python scripts/check_readme.py [repo-root]
Exit 0 = PASS, exit 1 = FAIL."""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
readme = root / "README.md"
required = [
    "# rtynbirf · POLYMATH-UNIVERSUM",
    "## С чего начать",
    "## Основные направления",
    "## Принципы",
    "## Проверка и достоверность",
    "## Карта и текущее состояние",
    "## Участие и обратная связь",
]
expected_anchors = [
    "ФОРЖ:АККАУНТ", "НОО:ПУЛЬТ", "АТЛАС:КАРТА", "КАРТЫ", "INV:АВТОМАТ",
    "ФОРЖ:МУЗА", "ФОРЖ:ПАСПОРТ", "ФОРЖ:КАНОН-СИНТЕЗ", "ФОРЖ:АВТОМАТ", "ФОРЖ:КАРТА",
]

if not readme.exists():
    print("FAIL: README.md отсутствует")
    sys.exit(1)
text = readme.read_text(encoding="utf-8")
errors = []

h1 = re.findall(r"(?m)^# .+$", text)
if len(h1) != 1:
    errors.append(f"ожидали ровно один H1, найдено {len(h1)}")
for h in required:
    if h not in text:
        errors.append(f"нет обязательного заголовка: {h}")
if re.search(r"\b(TODO|TBD|LOREM)\b", text):
    errors.append("незакрытые TODO/TBD/LOREM")

# локальные ссылки существуют
local = re.findall(r"\]\((?!https?://|#)([^)]+)\)", text)
for target in local:
    path = (root / target.split("#", 1)[0]).resolve()
    if not path.exists():
        errors.append(f"битая локальная ссылка: {target}")

# FR-12 · якорная целостность живого слоя: пары НАЧАЛО/КОНЕЦ, полный состав
begins = re.findall(r"<!--([А-ЯЁA-Z]+(?:[:][А-ЯЁA-Z0-9_-]+)*):НАЧАЛО(?:[-_][A-Z0-9_-]+)?-->", text)
ends = re.findall(r"<!--([А-ЯЁA-Z]+(?:[:][А-ЯЁA-Z0-9_-]+)*):КОНЕЦ-->", text)
if sorted(begins) != sorted(ends):
    errors.append(f"якоря не сбалансированы: НАЧАЛО={sorted(begins)} vs КОНЕЦ={sorted(ends)}")
missing = [a for a in expected_anchors if a not in begins]
if missing:
    errors.append(f"потеряны живые якоря ФОРЖ: {missing}")

# доступность: каждая <img> имеет alt=
imgs = re.findall(r"<img\b[^>]*>", text)
for tag in imgs:
    if "alt=" not in tag:
        errors.append(f"<img> без alt: {tag[:60]}…")

if errors:
    print("FAIL")
    print("\n".join("- " + e for e in errors))
    sys.exit(1)
print(f"PASS: заголовков {len(required)}; якорей живого слоя {len(set(begins))}/{len(expected_anchors)}; "
      f"локальных ссылок {len(local)}; <img> с alt {len(imgs)}/{len(imgs)}")
