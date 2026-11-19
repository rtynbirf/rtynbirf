#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ · revomat-central.py · конечный автомат НАД ФЛОТОМ.
Пролёт всех 75 реп через API: каждая получает состояние конечного автомата:
  МУЗЕЙ (архив: только СВЕРКА, чтение) · ЗДРАВИЕ (гейты чисты) · ДРЕЙФ→КУЗНЯ
  (дефекты канона: паспорт/движок без маркера — перековка на месте, без self-healing
  выдумок: одно лекарство — движок канона).
Пишет доказательство работы: automaton-state.json (флот) + блок ФОРЖ:АВТОМАТ в README
профиля. Лекарство требует токен с write (env GH_TOKEN); без него — только СВЕРКА.
Только stdlib."""
import base64, json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/z/my-project/scripts")

CANON = "ORNAMENTAL MYTHO-REALISM"
TOK = os.environ.get("GH_TOKEN", "")
A = "https://api.github.com"
PROFILE = "rtynbirf/rtynbirf"
INV = json.load(open("/home/z/my-project/scripts/r19_inventory.json"))
MAN = {it["n"]: it for it in json.load(open("/home/z/my-project/scripts/r15_manifest.json"))}
NAMES = sorted(set(INV["live"] + INV["archived"]))
NUM_OF = {n: (MAN.get(n, {}).get("num") or 100 + NAMES.index(n)) for n in NAMES}


def api(method, url, payload=None, timeout=180):
    cmd = ["curl", "-sS", "--max-time", "60", "-X", method, url, "-H", "Accept: application/vnd.github+json"]
    if TOK:
        cmd += ["-H", f"Authorization: Bearer {TOK}"]
    data = None
    if payload is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        data = json.dumps(payload, ensure_ascii=False)
    r = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_raw": r.stdout[:150]}


def raw_text(name, path, br):
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "45",
                        f"https://raw.githubusercontent.com/rtynbirf/{name}/{br}/{path}"],
                       capture_output=True, text=True, timeout=60)
    return r.stdout if r.stdout.startswith("<?xml") or len(r.stdout) > 0 else ""


def raw_ok(name, path, br):
    r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-L", "--max-time", "45",
                        f"https://raw.githubusercontent.com/rtynbirf/{name}/{br}/{path}"],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip() == "200"


def check_repo(name):
    """СВЕРКА одного тела флота → dict состояния. Только чтение."""
    g = api("GET", f"{A}/repos/rtynbirf/{name}")
    if "default_branch" not in g:
        return {"репа": name, "состояние": "ПЕПЕЛ", "дефекты": ["репа недоступна"], "номер": NUM_OF[name]}
    br = g["default_branch"]
    archived = g.get("archived", False)
    rd = api("GET", f"{A}/repos/rtynbirf/{name}/readme?ref={br}")
    md = base64.b64decode(rd["content"]).decode("utf-8", "ignore") if rd.get("content") else ""
    links = sorted({p.split("#")[0].split("?")[0] for p in re.findall(r'(?:src|href)="([^"]+)"', md)
                    if not p.startswith(("http", "data:", "#", "mailto:")) and p.split("#")[0].strip()})
    passport = raw_text(name, "revo-page.svg", br)
    engine = raw_text(name, "revo_autopilot.py", br)
    with ThreadPoolExecutor(6) as ex:
        link_ok = list(ex.map(lambda p: raw_ok(name, p, br), links[:14]))
    g1 = CANON in passport
    g2 = raw_ok(name, "banner.png", br)
    g3 = all(link_ok)
    g4 = bool(engine) and CANON in engine
    defects = []
    if not g1: defects.append("G1_паспорт_без_канона")
    if not g2: defects.append("G2_баннер_недоступен")
    if not g3: defects.append("G3_ссылки:" + ",".join(p for p, ok in zip(links[:14], link_ok) if not ok)[:120])
    if not g4: defects.append("G4_движок_без_канона")
    state = "МУЗЕЙ" if archived else ("ЗДРАВИЕ" if not defects else "ДРЕЙФ")
    return {"репа": name, "номер": NUM_OF[name], "ветка": br, "состояние": state,
            "дефекты": defects, "ссылок_проверено": len(links[:14]),
            "архив": archived}


def heal_repo(name, defect_report):
    """КУЗНЯ: одно предопределённое лекарство — перековка паспорта движком канона.
    Только живые репы и только дефекты G1/G4 (контент паспорта)."""
    if not TOK:
        return "нет токена — лекарство не применено"
    if not any(d.startswith(("G1", "G4")) for d in defect_report["дефекты"]):
        return "лекарство не показано (дефекты не паспортные)"
    eng_src = raw_text(name, "revo_autopilot.py", defect_report["ветка"])
    m = re.search(r"json\.loads\(r'''(.*?)'''\)", eng_src, re.S)
    if not m:
        return "CFG движка не извлечён"
    try:
        cfg = json.loads(m.group(1))
    except Exception as ex:
        return f"CFG бит: {ex}"
    import r19_engine as E
    E.CFG = cfg
    g = api("GET", f"{A}/repos/rtynbirf/{name}")
    br = g["default_branch"]
    tree = api("GET", f"{A}/repos/rtynbirf/{name}/git/trees/{br}?recursive=1")
    paths = [e["path"] for e in tree.get("tree", []) if e.get("type") == "blob"]
    rr = subprocess.run(["curl", "-sS", "-H", f"Authorization: Bearer {TOK}",
                         f"{A}/repos/rtynbirf/{name}/commits?per_page=1"], capture_output=True, text=True)
    mm = re.search(r'[?&]page=(\d+)>; rel="last"', rr.stdout or "")
    n_commits = int(mm.group(1)) if mm else 1
    rd = api("GET", f"{A}/repos/rtynbirf/{name}/readme?ref={br}")
    readme = base64.b64decode(rd["content"]).decode("utf-8", "ignore") if rd.get("content") else ""
    facts = E.facts_from_paths(paths, n_commits, (g.get("pushed_at") or "")[:10],
                               int(g.get("size") or 0), readme, cfg.get("topics") or [],
                               cfg.get("desc") or "", cfg.get("releases") or 0)
    page_svg = E.build_svg(facts)
    was_arch = g.get("archived", False)
    if was_arch:
        api("PATCH", f"{A}/repos/rtynbirf/{name}", {"archived": False}); time.sleep(1.2)
    try:
        ref = api("GET", f"{A}/repos/rtynbirf/{name}/git/ref/heads/{br}")
        head = ref["object"]["sha"]
        cm = api("GET", f"{A}/repos/rtynbirf/{name}/git/commits/{head}")
        items = [{"path": "revo-page.svg", "mode": "100644", "type": "blob", "content": page_svg}]
        tr = api("POST", f"{A}/repos/rtynbirf/{name}/git/trees", {"base_tree": cm["tree"]["sha"], "tree": items})
        if "sha" not in tr or tr["sha"] == cm["tree"]["sha"]:
            return "дерево без изменений"
        nc = api("POST", f"{A}/repos/rtynbirf/{name}/git/commits",
                 {"message": f"РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ: ДРЕЙФ→КУЗНЯ→ЗДРАВИЕ — паспорт перекован движком канона · ИЗДАНИЕ r19 · {CANON}",
                  "tree": tr["sha"], "parents": [head]})
        pr = api("PATCH", f"{A}/repos/rtynbirf/{name}/git/refs/heads/{br}", {"sha": nc["sha"], "force": False})
        return "вылечено ✓" if "object" in pr else "пуш не прошёл"
    finally:
        if was_arch:
            time.sleep(1.2)
            api("PATCH", f"{A}/repos/rtynbirf/{name}", {"archived": True})


print("== ЦЕНТРАЛЬНЫЙ ПРОЛЁТ ФЛОТА:", len(NAMES), "реп ==")
with ThreadPoolExecutor(6) as ex:
    reports = list(ex.map(check_repo, NAMES))
for r in reports:
    if r["состояние"] == "ДРЕЙФ":
        res = heal_repo(r["репа"], r)
        r["кузня"] = res
        print(f"  ДРЕЙФ {r['репа']} → {res} · {r['дефекты']}")
counts = {}
for r in reports:
    counts[r["состояние"]] = counts.get(r["состояние"], 0) + 1
healed = sum(1 for r in reports if r.get("кузня") == "вылечено ✓")
doc = {"автомат": "РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ", "канон": CANON, "издание": "ИЗДАНИЕ r19",
       "флот": len(NAMES), "состояния": counts, "вылечено": healed,
       "тела": reports, "переход_цикла": f"ПЕПЕЛ→ПРОБУЖДЕНИЕ→СВЕРКА→(лечение {healed})→ЗДРАВИЕ",
       "обновлено": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
json.dump(doc, open("/home/z/my-project/scripts/r19_fleet_state.json", "w"), ensure_ascii=False, indent=1)
print("состояния флота:", counts, "· вылечено:", healed)

# запись в профиль: state-файл + README-блок + движок центрального автомата + workflow
fleet_json = json.dumps(doc, ensure_ascii=False, indent=1)
d = api("GET", f"{A}/repos/{PROFILE}/readme")
md = base64.b64decode(d["content"]).decode()
lenta = " · ".join(f"{k}:{v}" for k, v in counts.items())
block = (
    "<!--ФОРЖ:АВТОМАТ:НАЧАЛО-->\n"
    "<div align=\"center\">\n\n"
    f"**РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ** · конечный автомат над флотом · {CANON} · ИЗДАНИЕ r19\n\n"
    f"> ФЛОТ {len(NAMES)} → {lenta} · вылечено {healed} · цикл: {doc['переход_цикла']}\n"
    f"> Доказательство работы: `automaton-state.json` (флот) и `automaton-state.json` в каждом живом теле — "
    f"лента переходов коммитится каждым циклом. Обход ежедневный (`revomat-central.yml`), "
    f"локальные автоматы — суточно в каждом теле (`revomat.yml`).\n\n"
    "</div>\n"
    "<!--ФОРЖ:АВТОМАТ:КОНЕЦ-->"
)
if "<!--ФОРЖ:АВТОМАТ:НАЧАЛО-->" in md:
    md = re.sub(r"<!--ФОРЖ:АВТОМАТ:НАЧАЛО-->.*?<!--ФОРЖ:АВТОМАТ:КОНЕЦ-->", block.replace("\\", "\\\\"), md, flags=re.S)
else:
    md = md.rstrip() + "\n\n" + block + "\n"

items = [{"path": "automaton-state.json", "mode": "100644", "type": "blob", "content": fleet_json},
         {"path": "README.md", "mode": "100644", "type": "blob", "content": md},
         {"path": "revomat-central.py", "mode": "100644", "type": "blob",
          "content": open(os.path.realpath(__file__), encoding="utf-8").read()}]
CENTRAL_YML = """name: РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ
# Конечный автомат над всем флотом (75 тел): ежедневный пролёт СВЕРКА,
# ДРЕЙФ→КУЗНЯ (лечение паспорта движком канона), доказательство в automaton-state.json.
# Лекарство требует PAT с write на свои репы в секретах REVO_PAT; без него — только СВЕРКА.
on:
  schedule:
    - cron: "9 4 * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  central:
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ secrets.REVO_PAT || github.token }}
    steps:
      - uses: actions/checkout@v4
      - name: ПРОЛЁТ ФЛОТА → СВЕРКА/КУЗНЯ
        run: python3 revomat-central.py
"""
items.append({"path": ".github/workflows/revomat-central.yml", "mode": "100644", "type": "blob", "content": CENTRAL_YML})
ref = api("GET", f"{A}/repos/{PROFILE}/git/ref/heads/main")
head = ref["object"]["sha"]
cm = api("GET", f"{A}/repos/{PROFILE}/git/commits/{head}")
tr = api("POST", f"{A}/repos/{PROFILE}/git/trees", {"base_tree": cm["tree"]["sha"], "tree": items})
if "sha" in tr and tr["sha"] != cm["tree"]["sha"]:
    nc = api("POST", f"{A}/repos/{PROFILE}/git/commits",
             {"message": f"РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ: флот {len(NAMES)} — {lenta}; вылечено {healed} · ИЗДАНИЕ r19 · {CANON}",
              "tree": tr["sha"], "parents": [head]})
    pr = api("PATCH", f"{A}/repos/{PROFILE}/git/refs/heads/main", {"sha": nc["sha"], "force": False})
    print("коммит в профиль:", "✓ " + nc["sha"][:8] if "object" in pr else str(pr)[:120])
else:
    print("дерево без изменений или ошибка:", str(tr)[:120])
