#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
law_pulse.py · пульс закона дома «Полимат» — гипотеза «дом-эйгенформа».

Гипотеза: форма дома (его закон) есть неподвижная точка собственной динамики —
закон 1–28 не меняется через циклы возмущений (шрамы затягиваются — форма
возвращается), либо честно фиксирует «ФОРМА РЕАГИРУЕТ», когда закон учится.
Этот скрипт делает гипотезу измеримой (метрика home.law.form).

ЧТО ТАКОЕ ЯДРО ЗАКОНА (зафиксировано как метод law_pulse/v1.0):
  кусок 1 — блок правил 1–22 из AGENTS.md: от заголовка секции, в которой
            начинается нумерация правил (строка «1. …»; фактически «## КАНОН»),
            до СЛЕДУЮЩЕГО заголовка того же уровня «## …» после секции,
            содержащей правило «22. …» (фактически «## КОСЯКИ АГЕНТОВ …»);
            в блок входят все секции с правилами 1–22 целиком, сырыми байтами;
  кусок 2 — §2 «Что требует дом (закон 1–27)» из ТРЕБОВАНИЯ-ДЛЯ-АГЕНТОВ.md:
            от строки «## 2.» (фактически «## 2. Что требует дом (закон 1–27)»)
            до строки «## 3.» (исключительно; фактически «## 3. Гейты входа»).
  ЯДРО    = конкатенация двух кусков КАК ЕСТЬ (сырые байты UTF-8);
            ПОРЯДОК ФИКСИРОВАН: сначала AGENTS.md, затем §2 ТРЕБОВАНИЙ.
  Честная оговорка: правило 28 в этот блок НЕ входит — в фактическом
  состоянии дома оно живёт отдельной секцией «## Правило 28 · заход 5»
  в AGENTS.md (§2 ТРЕБОВАНИЙ покрывает закон 1–27); смещение правила 28
  ядро не заметит, но заметит agents_hash (hash всего AGENTS.md).

СОТЫ (формат как у factum/PULSE_LOG.md, но в JSONL — LAW-PULSE.jsonl):
  append-only; каждая строка данных несёт prev = sha256 ПРЕДЫДУЩЕЙ СЫРОЙ
  строки (первые 12 hex); «сырая строка» = байты строки без завершающего \n;
  для первой строки prev = sha256('LAWPULSE')[:12] (у factum — 'PULSE').

ВЕРДИКТ ЗАШИТ РОВНО ТАК (правило 33: форма, не список):
  GENESIS         — первая строка сот: сравнивать ядро не с чем;
  FIXED_POINT     — core_hash нового замера == core_hash предыдущей строки
                    (форма вернулась: закон не сдвинулся от возмущений);
  ФОРМА_РЕАГИРУЕТ — core_hash отличается (закон учится); в detail пишем
                    длину текущего ядра и Δ≈ в байтах (длина ядра записана
                    в detail каждой строки, поэтому Δ считается по длинам
                    без раскопок git-истории), плюс смена agents_hash/req_hash.

Режимы (argparse, stdlib only):
  --measure  замер ядра + append-only допись строки в LAW-PULSE.jsonl;
             печатает полный sha256 ядра и его первые 12 hex;
  --json     контракт метрики home.law.form (stdout, JSON);
  --verify   проверка цепочки сот: валидность JSON, порядок n, сходимость
             prev от sha256('LAWPULSE')[:12], пересчёт вердиктов; exit 1 при бите.

Пример: python3 scripts/law_pulse.py --measure
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Константы метода law_pulse/v1.0 -----------------------------------------
AGENTS_FILE = "AGENTS.md"
REQ_FILE = "ТРЕБОВАНИЯ-ДЛЯ-АГЕНТОВ.md"
LEDGER_FILE = "LAW-PULSE.jsonl"

GENESIS_SEED = "LAWPULSE"      # семя первой строки сот (у factum/PULSE_LOG — 'PULSE')
HEX_LEN = 12                   # длина hash-префикса в сотах (первые 12 hex)
VERDICT_GENESIS = "GENESIS"
VERDICT_FIXED = "FIXED_POINT"
VERDICT_REACT = "ФОРМА_РЕАГИРУЕТ"
METRIC_ID = "home.law.form"
SCOPE = "rtynbirf/rtynbirf@main"
METHOD_VERSION = "law_pulse/v1.0"
SOURCE_LABEL = "AGENTS.md + ТРЕБОВАНИЯ-ДЛЯ-АГЕНТОВ.md §2"

# Поля строки сот — ровно этот набор, порядок фиксирован (правило 45: запись знает источник)
ROW_KEYS = ("n", "utc", "core_hash", "agents_hash", "req_hash", "verdict", "detail", "prev")


# --- Мелкая утилитарщина ------------------------------------------------------
def now_utc() -> str:
    """Метка времени UTC, ISO-8601 с суффиксом Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha12(data: bytes) -> str:
    """sha256 сырых байтов, первые 12 hex — формат сот factum/PULSE_LOG.md."""
    return hashlib.sha256(data).hexdigest()[:HEX_LEN]


def split_lines_keepends(data: bytes) -> list:
    """Разбить байты на строки, СОХРАНИВ каждый \\n в конце строки.

    Своё разбиение вместо bytes.splitlines(): последний делит ещё и по
    \\x0b/\\x0c/\\x1c-\\x1e/\\u2028-подобным границам — сырые байты ядра
    могли бы исказиться. Здесь строка — только до \\n включительно.
    """
    lines = []
    start = 0
    while True:
        idx = data.find(b"\n", start)
        if idx == -1:
            if start < len(data):        # хвост без завершающего \n
                lines.append(data[start:])
            break
        lines.append(data[start:idx + 1])
        start = idx + 1
    return lines


def is_h2(line_text: str) -> bool:
    """Заголовок уровня «## » — уровень секций правил в обоих файлах.
    «### …» отсекается самим префиксом: третья литера «###» — не пробел."""
    return line_text.startswith("## ")


def decode_lines(data: bytes, path_label: str) -> list:
    """Сырые байты -> список строк-текстов (для поиска границ).
    Не-UTF8 -> исключение (fail-closed, правило 33: форма, не пожелание)."""
    try:
        return [line.decode("utf-8") for line in split_lines_keepends(data)]
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path_label}: файл не является корректным UTF-8 ({exc})")


# --- Извлечение ядра ----------------------------------------------------------
def extract_agents_block(data: bytes) -> tuple:
    """Кусок 1 ядра: блок правил 1–22 из AGENTS.md.

    Границы (детерминированные, по содержанию):
      НАЧАЛО — первая секция «## …», в которой есть строка, начинающаяся
               с «1. » (правило 1; фактически «## КАНОН»);
      КОНЕЦ  — следующий заголовок «## …» ПОСЛЕ секции, содержащей строку
               «22. » (правило 22; фактически «## КОСЯКИ АГЕНТОВ …»).
    Блок = сырые байты строк [НАЧАЛО, КОНЕЦ): заголовки секций, пустые строки
    и хвостовой перевод строки входят; сам заголовок КОНЦА — нет.
    """
    lines = split_lines_keepends(data)
    text = decode_lines(data, AGENTS_FILE)
    heads = [i for i, t in enumerate(text) if is_h2(t)]
    if not heads:
        raise ValueError(f"{AGENTS_FILE}: не найдено ни одного заголовка «## …»")

    def section_end(pos: int) -> int:
        return heads[pos + 1] if pos + 1 < len(heads) else len(text)

    # НАЧАЛО: первая секция «## …» со строкой правила «1. …»
    start = None
    for pos, h in enumerate(heads):
        if any(text[i].startswith("1. ") for i in range(h, section_end(pos))):
            start = h
            break
    if start is None:
        raise ValueError(f"{AGENTS_FILE}: не найдено правило «1. …» ни в одной секции «## …»")

    # секция с правилом «22. …» (ищем только от начала ядра и дальше)
    rule22_head = None
    for pos, h in enumerate(heads):
        if h < start:
            continue
        if any(text[i].startswith("22. ") for i in range(h, section_end(pos))):
            rule22_head = h
            break
    if rule22_head is None:
        raise ValueError(f"{AGENTS_FILE}: не найдено правило «22. …» после начала ядра")

    # КОНЕЦ: следующий заголовок того же уровня после секции правила 22
    end = len(text)
    for h in heads:
        if h > rule22_head:
            end = h
            break

    label = {
        "start_line": start + 1,
        "end_line": end + 1 if end < len(text) else len(text),
        "start_heading": text[start].strip(),
        "end_heading": text[end].strip() if end < len(text) else "<конец файла>",
        "included": f"строки {start + 1}–{end} (заголовок-граница не входит)",
    }
    return b"".join(lines[start:end]), label


def extract_req_block(data: bytes) -> tuple:
    """Кусок 2 ядра: §2 «Что требует дом (закон 1–27)» из ТРЕБОВАНИЯ-ДЛЯ-АГЕНТОВ.md.

    Границы: строка с заголовком «## 2.» (фактически «## 2. Что требует дом
    (закон 1–27)») до строки «## 3.» ИСКЛЮЧИТЕЛЬНО (фактически «## 3. Гейты
    входа агента (чек-лист)»). Сырые байты как есть, включая хвостовой \\n.
    """
    lines = split_lines_keepends(data)
    text = decode_lines(data, REQ_FILE)
    start = end = None
    for i, t in enumerate(text):
        if start is None and re.match(r"^##\s*2\.", t):
            start = i
        elif start is not None and re.match(r"^##\s*3\.", t):
            end = i
            break
    if start is None:
        raise ValueError(f"{REQ_FILE}: не найден заголовок «## 2. …»")
    if end is None:
        # «## 3.» не нашёлся — честный фоллбек: берём §2 до конца файла
        end = len(text)

    label = {
        "start_line": start + 1,
        "end_line": end + 1 if end < len(text) else len(text),
        "start_heading": text[start].strip(),
        "end_heading": text[end].strip() if end < len(text) else "<конец файла>",
        "included": f"строки {start + 1}–{end} (заголовок-граница не входит)",
    }
    return b"".join(lines[start:end]), label


def measure_core(root: Path) -> tuple:
    """Собрать ЯДРО ЗАКОНА и hash двух файлов-источников целиком.

    ЯДРО = кусок 1 (AGENTS.md, правила 1–22) + кусок 2 (ТРЕБОВАНИЯ §2);
    ПОРЯДОК КОНКАТЕНАЦИИ ФИКСИРОВАН: сначала AGENTS.md, затем §2 —
    перестановка кусков изменила бы hash, поэтому порядок закреплён здесь,
    в коде метода law_pulse/v1.0.
    """
    agents_path = root / AGENTS_FILE
    req_path = root / REQ_FILE
    for p in (agents_path, req_path):
        if not p.is_file():
            raise FileNotFoundError(f"нет файла-источника ядра: {p}")

    agents_bytes = agents_path.read_bytes()
    req_bytes = req_path.read_bytes()
    block_agents, lab_agents = extract_agents_block(agents_bytes)
    block_req, lab_req = extract_req_block(req_bytes)
    core = block_agents + block_req          # порядок фиксируется этой строкой
    return core, agents_bytes, req_bytes, lab_agents, lab_req


# --- Соты-журнал --------------------------------------------------------------
def read_ledger(path: Path) -> list:
    """Прочитать соты: список пар (сырая строка без \\n, dict строки).

    Файл отсутствует/пуст -> [] (сот ещё нет, это легально: генезис впереди).
    Битая строка -> ValueError (fail-closed: дописывать в битую цепь нельзя).
    """
    if not path.is_file():
        return []
    raw = path.read_bytes()
    if not raw:
        return []
    rows = []
    for raw_line in split_lines_keepends(raw):
        stripped = raw_line[:-1] if raw_line.endswith(b"\n") else raw_line
        try:
            row = json.loads(stripped.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"{path.name}: строка {len(rows) + 1} не является валидным JSON: {exc}"
            )
        rows.append((stripped, row))
    return rows


def cmd_measure(root: Path) -> int:
    """Режим --measure: замер ядра + append-only строка в LAW-PULSE.jsonl."""
    core, agents_bytes, req_bytes, lab_agents, lab_req = measure_core(root)
    core_full = hashlib.sha256(core).hexdigest()
    core_hash = core_full[:HEX_LEN]                       # «hash ядра» в сотах
    agents_hash = sha12(agents_bytes)
    req_hash = sha12(req_bytes)
    core_len = len(core)

    ledger = root / LEDGER_FILE
    rows = read_ledger(ledger)
    # fail-closed: допись в битую цепь запрещена — битые prev уже не починить,
    # а новая строка замела бы след поломки (проверка та же, что у --verify).
    if rows:
        chain_problems = check_chain(rows)
        if chain_problems:
            raise ValueError(
                f"{LEDGER_FILE}: цепь сот битая, допись запрещена "
                f"(запустите --verify для диагноза); первая проблема: "
                f"{chain_problems[0]}"
            )

    # prev = sha256 предыдущей СЫРОЙ строки; для первой — sha256('LAWPULSE')[:12]
    prev = sha12(rows[-1][0]) if rows else sha12(GENESIS_SEED.encode("utf-8"))
    prev_row = rows[-1][1] if rows else None

    # Вердикт зашит здесь ровно так (см. докстринг модуля):
    if prev_row is None:
        verdict = VERDICT_GENESIS
        detail = (f"ядро={core_len} байт: генезис сот, сравнение не с чем "
                  f"({SOURCE_LABEL})")
    elif prev_row.get("core_hash") == core_hash:
        verdict = VERDICT_FIXED
        detail = (f"ядро={core_len} байт: форма вернулась, ядро не сдвинулось "
                  f"(= строке {prev_row.get('n')})")
    else:
        verdict = VERDICT_REACT     # ядро сдвинулось — форма реагирует, закон учится
        # Δ в байтах — по длинам ядра: длина пишется в detail каждой строки
        # («ядро=N байт: …»), git-история не нужна — просто фиксируем смену.
        m = re.search(r"ядро=([0-9]+)", str(prev_row.get("detail", "")))
        if m:
            prev_len = int(m.group(1))
            detail = (f"ядро={core_len} байт: ядро изменилось "
                      f"(было ≈{prev_len} байт, Δ≈{core_len - prev_len:+d}); "
                      f"AGENTS {prev_row.get('agents_hash')}->{agents_hash}, "
                      f"REQ {prev_row.get('req_hash')}->{req_hash}")
        else:
            detail = (f"ядро={core_len} байт: ядро изменилось (длина прошлого "
                      f"ядра неизвестна); AGENTS {prev_row.get('agents_hash')}"
                      f"->{agents_hash}, REQ {prev_row.get('req_hash')}->{req_hash}")

    row = {
        "n": len(rows) + 1,
        "utc": now_utc(),
        "core_hash": core_hash,
        "agents_hash": agents_hash,
        "req_hash": req_hash,
        "verdict": verdict,
        "detail": detail,
        "prev": prev,
    }
    # Разделители-по-умолчанию (как в INV_LEDGER.jsonl дома), ensure_ascii=False:
    # кириллица пишется байтами UTF-8, строка остаётся валидным JSON.
    raw_line = json.dumps(row, ensure_ascii=False).encode("utf-8")
    with ledger.open("ab") as fh:                     # append-only, байтом в байт
        fh.write(raw_line + b"\n")

    # Отчёт замера в stdout (правило 19: факт запуска = артефакт)
    print("=== law_pulse · замер ядра закона (метод law_pulse/v1.0) ===")
    print(f"кусок 1: {AGENTS_FILE}, {lab_agents['included']}: "
          f"от «{lab_agents['start_heading']}» до «{lab_agents['end_heading']}»")
    print(f"кусок 2: {REQ_FILE}, {lab_req['included']}: "
          f"от «{lab_req['start_heading']}» до «{lab_req['end_heading']}»")
    print(f"ядро: {core_len} байт (конкатенация: сначала AGENTS.md, затем §2 ТРЕБОВАНИЙ)")
    print(f"sha256 ядра (полный):  {core_full}")
    print(f"sha256 ядра (12 hex):  {core_hash}")
    print(f"agents_hash ({AGENTS_FILE} целиком): {agents_hash}")
    print(f"req_hash ({REQ_FILE} целиком): {req_hash}")
    if prev_row is None:
        print(f"prev: {prev}  (= sha256('LAWPULSE')[:12], генезис сот)")
    else:
        print(f"prev: {prev}  (= sha256 предыдущей сырой строки сот)")
    print(f"вердикт: {verdict}")
    print(f"строка сот №{row['n']} -> {LEDGER_FILE} (append-only):")
    print(raw_line.decode("utf-8"))
    return 0


def cmd_json(root: Path) -> int:
    """Режим --json: контракт метрики home.law.form (stdout)."""
    core, _agents, _req, _lab_a, _lab_r = measure_core(root)
    core_hash = sha12(core)
    rows = read_ledger(root / LEDGER_FILE)
    if rows:
        # статус сверяется с последним ЗАМЕРЕННЫМ состоянием сот
        status = VERDICT_FIXED if rows[-1][1].get("core_hash") == core_hash else VERDICT_REACT
    else:
        status = VERDICT_GENESIS   # сот ещё нет: измерение не состоялось
    contract = {
        "metric_id": METRIC_ID,
        "value": core_hash,
        "unit": "sha256_12",
        "definition": (
            "Гипотеза «дом-эйгенформа»: sha256 (первые 12 hex) ЯДРА ЗАКОНА — сырой "
            "UTF-8 конкатенации блока правил 1–22 из AGENTS.md (от «## КАНОН» до "
            "«## КОСЯКИ АГЕНТОВ» исключительно) и §2 из ТРЕБОВАНИЯ-ДЛЯ-АГЕНТОВ.md "
            "(от «## 2.» до «## 3.» исключительно); порядок: сначала AGENTS.md, "
            "затем §2. Тот же value при новом замере = неподвижная точка формы "
            "(FIXED_POINT: шрамы затягиваются, закон не сдвинулся); сместился = "
            "закон учится (ФОРМА_РЕАГИРУЕТ). Цепь замеров — LAW-PULSE.jsonl "
            "(append-only, prev = sha256 предыдущей сырой строки)."
        ),
        "source": SOURCE_LABEL,
        "generated_at": now_utc(),
        "scope": SCOPE,
        "method_version": METHOD_VERSION,
        "status": status,
    }
    print(json.dumps(contract, ensure_ascii=False, indent=2))
    return 0


def check_chain(rows: list) -> list:
    """Проверить целостность цепи сот: набор полей, порядок n, сходимость prev
    от sha256('LAWPULSE')[:12], пересчёт вердиктов. Возвращает список проблем
    (пустой список = цепь цела). Одна функция для --verify и --measure:
    допись в битую цепь запрещена (fail-closed, правило 33)."""
    problems = []
    expected_prev = sha12(GENESIS_SEED.encode("utf-8"))
    prev_row = None
    for i, (raw_line, row) in enumerate(rows, start=1):
        for key in ROW_KEYS:
            if key not in row:
                problems.append(f"строка {i}: нет поля «{key}»")
        if row.get("prev") != expected_prev:
            problems.append(f"строка {i}: prev={row.get('prev')} ≠ ожидаемому "
                            f"sha256 предыдущей сырой строки {expected_prev}")
        if row.get("n") != i:
            problems.append(f"строка {i}: n={row.get('n')} ≠ позиции в цепочке ({i})")
        if prev_row is None:
            if row.get("verdict") != VERDICT_GENESIS:
                problems.append(f"строка {i}: первая строка должна быть {VERDICT_GENESIS}, "
                                f"а не {row.get('verdict')}")
        else:
            want = VERDICT_FIXED if prev_row.get("core_hash") == row.get("core_hash") \
                else VERDICT_REACT
            if row.get("verdict") != want:
                problems.append(f"строка {i}: verdict={row.get('verdict')} ≠ "
                                f"пересчитанному {want}")
        prev_row = row
        expected_prev = sha12(raw_line)   # сырая строка БЕЗ завершающего \n
    return problems


def cmd_verify(root: Path) -> int:
    """Режим --verify: проверка цепочки сот (exit 1 при бите, fail-closed)."""
    ledger = root / LEDGER_FILE
    if not ledger.is_file():
        print(f"ЦЕПОЧКА НЕ НАЙДЕНА: {ledger} — сот ещё нет, проверять нечего")
        return 1
    rows = read_ledger(ledger)          # битый JSON здесь уже поднял бы ValueError
    if not rows:
        print(f"ЦЕПОЧКА ПУСТА: {ledger}")
        return 1

    problems = check_chain(rows)
    if problems:
        print("ЦЕПОЧКА БИТА:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"ЦЕПОЧКА ЦЕЛА: {len(rows)} строк; prev сходится от "
          f"sha256('LAWPULSE')[:12] = {sha12(GENESIS_SEED.encode('utf-8'))}; "
          f"вердикты пересчитаны по правилу core_hash")
    for _raw, row in rows:
        print(f"  #{row.get('n')} {row.get('utc')} ядро={row.get('core_hash')} "
              f"AGENTS={row.get('agents_hash')} REQ={row.get('req_hash')} "
              f"→ {row.get('verdict')}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="law_pulse.py",
        description=("Пульс закона дома «Полимат»: sha256 ядра (правила 1–22 из "
                     "AGENTS.md + §2 ТРЕБОВАНИЙ) в соты LAW-PULSE.jsonl "
                     "(метрика home.law.form, гипотеза «дом-эйгенформа»)."),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--measure", action="store_true",
                      help="замер ядра + append-only допись строки в LAW-PULSE.jsonl")
    mode.add_argument("--json", action="store_true",
                      help="контракт метрики home.law.form в stdout")
    mode.add_argument("--verify", action="store_true",
                      help="проверить цепочку сот LAW-PULSE.jsonl (exit 1 при бите)")
    parser.add_argument("--root", default=None,
                        help="корень репо (по умолчанию: папка над scripts/)")
    args = parser.parse_args(argv)

    # По умолчанию корень репо = папка над scripts/ — скрипт самодостаточен
    # и в клоне, и в Actions (checkout кладёт его в <repo>/scripts/).
    root = Path(args.root).resolve() if args.root \
        else Path(__file__).resolve().parent.parent

    try:
        if args.measure:
            return cmd_measure(root)
        if args.json:
            return cmd_json(root)
        return cmd_verify(root)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"ОШИБКА (fail-closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
