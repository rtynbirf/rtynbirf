#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ v2 · revomat-central.py · конечный автомат НАД ФЛОТОМ.
ИЗДАНИЕ r19c · Actions-безопасен (никаких путей песочницы), stdlib + cairosvg для ковки лиц.

Закон v2 (урок сиротства 2026-11-19: assembly-protocol и dogovor выпали из статической описи):
  1. ОПИСЬ ДИНАМИЧЕСКАЯ: флот каждый пролёт открывается через API (все тела аккаунта,
     пагинация). Статические списки запрещены — тело вне списка = сирота без лица.
  2. ЗАЧИСЛЕНИЕ: тело, не найденное в fleet-desk.json, зачисляется полным каноном:
     banner.png (лицо, PNG-магия), revo-page.svg (паспорт), README-лицо (баннер +
     ФОРЖ:ПАСПОРТ), revo_autopilot.py (движок канона), revomat.py, revomat.yml,
     revo-obhod.yml, AGENTS.md (закон). БАННЕР = ЛИЦО АККАУНТА.
  3. Гейты СВЕРКИ: G1 паспорт с каноном · G2 banner.png с PNG-магией (размер и 200-код
     не достаточно — base64-текст проходил старый гейт) · G3 ссылки README · G4 движок
     с каноном · G5 state-файл непрерывности.
  4. МУЗЕЙ (архив): только СВЕРКА; лечение G1/G4 через unarchive→запись→archive.
  5. Самозапись (зуб A-HUSH): 3 попытки fetch+rebase+push; доказательство работы —
     automaton-state.json + fleet-desk.json + блок ФОРЖ:АВТОМАТ в README профиля.
"""
import base64, json, os, re, subprocess, tempfile, time, importlib.util
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

try:
    import cairosvg
except Exception:
    cairosvg = None

CANON = "ORNAMENTAL MYTHO-REALISM"
EDITION = "ИЗДАНИЕ r19c"
TOK = os.environ.get("GH_TOKEN", "")
A = "https://api.github.com"
OWNER = "rtynbirf"
PROFILE = f"{OWNER}/{OWNER}"
DESK_FILE = "fleet-desk.json"
FAST = os.environ.get("REVOMAT_FAST", "") == "1"  # быстрый обход: только опись+зачисление (без СВЕРКИ/лечения)
SCHEMES = [
    dict(bg="#10243E", bg2="#1B3B5F", ink="#F3ECD9", gold="#D4AF37", gold2="#E8C868", dim="#8FA3BF", accent="#D5281B"),
    dict(bg="#38100A", bg2="#4E1A10", ink="#F4E9D6", gold="#D4AF37", gold2="#E8C868", dim="#C39272", accent="#2C5F9E"),
    dict(bg="#0C2E21", bg2="#14402E", ink="#EFE7D2", gold="#D4AF37", gold2="#E8C868", dim="#8FB09C", accent="#C43B27"),
    dict(bg="#2A1D12", bg2="#3A2A1B", ink="#F1E8D8", gold="#D4AF37", gold2="#E8C868", dim="#B79F7E", accent="#1F5B8B"),
    dict(bg="#171512", bg2="#232017", ink="#F2E9D4", gold="#D4AF37", gold2="#E8C868", dim="#A99E82", accent="#B03A2A"),
    dict(bg="#EFE6CF", bg2="#F6EFDC", ink="#241C10", gold="#9A7B23", gold2="#C9A227", dim="#6E6249", accent="#C43B27"),
]
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

CENTRAL_YML = """name: РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ
# Конечный автомат над всем флотом. Два режима одного исходника:
#  БЫСТРЫЙ ОБХОД (каждые 15 минут): динамическая опись через API + мгновенное зачисление
#   сирот полным каноном (лицо-баннер blob-API, паспорт, README-лицо, движок, автоматы,
#   закон) — новое тело ждёт лица максимум 15 минут, не сутки.
#  ПОЛНЫЙ ПРОЛЁТ (ежедневно 04:09 + вручную): СВЕРКА гейтов (G2 = PNG-магия по blob-API),
#   ДРЕЙФ→КУЗНЯ (паспорт движком канона), доказательство в automaton-state.json.
on:
  schedule:
    - cron: "*/15 * * * *"
    - cron: "9 4 * * *"
  workflow_dispatch:
concurrency:
  group: revomat-central
  cancel-in-progress: false
permissions:
  contents: write
jobs:
  fast-obhod:
    if: github.event_name == 'workflow_dispatch' || (github.event_name == 'schedule' && github.event.schedule == '*/15 * * * *')
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ secrets.REVO_PAT || github.token }}
      REVOMAT_FAST: "1"
    steps:
      - uses: actions/checkout@v4
      - name: инструменты ковки лиц
        run: pip install cairosvg --quiet
      - name: ОПИСЬ + ЗАЧИСЛЕНИЕ СИРОТ
        run: python3 revomat-central.py
      - name: ЖИВОЕ ЛИЦО + ЖИВАЯ КАРТА (данные API → полотна, правило 25)
        run: python3 revomat-live.py
  full-prolet:
    if: github.event_name == 'workflow_dispatch' || (github.event_name == 'schedule' && github.event.schedule == '9 4 * * *')
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ secrets.REVO_PAT || github.token }}
    steps:
      - uses: actions/checkout@v4
      - name: инструменты ковки лиц
        run: pip install cairosvg --quiet
      - name: ПОЛНЫЙ ПРОЛЁТ → СВЕРКА/КУЗНЯ/ЗАЧИСЛЕНИЕ
        run: python3 revomat-central.py
      - name: ЖИВОЕ ЛИЦО + ЖИВАЯ КАРТА (данные API → полотна, правило 25)
        run: python3 revomat-live.py
"""


def api(method, url, payload=None):
    cmd = ["curl", "-sS", "--max-time", "60", "-X", method, url, "-H", "Accept: application/vnd.github+json"]
    if TOK:
        cmd += ["-H", f"Authorization: Bearer {TOK}"]
    data = None
    if payload is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        data = json.dumps(payload, ensure_ascii=False)
    r = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=180)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_raw": r.stdout[:150]}


def raw_bytes(name, path, br):
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "45",
                        f"https://raw.githubusercontent.com/{OWNER}/{name}/{br}/{path}"],
                       capture_output=True, timeout=60)
    return r.stdout or b""


def raw_text(name, path, br):
    return raw_bytes(name, path, br).decode("utf-8", "ignore")


def self_text(path):
    """Чтение файла собственного тела: checkout (Actions) → API contents (свежесть) → raw (CDN)."""
    if os.path.exists(path):
        try:
            src = open(path, encoding="utf-8").read()
            if src.strip():
                return src
        except Exception:
            pass
    c = api("GET", f"{A}/repos/{PROFILE}/contents/{path}?ref=main")
    if c.get("content"):
        return base64.b64decode(c["content"]).decode("utf-8", "ignore")
    t = raw_text(OWNER, path, "main")
    return "" if t.lstrip().startswith(("404", "403", "400")) else t


def raw_head(name, path, br, n=8):
    return raw_bytes(name, path, br)[:n]


def discover_fleet():
    """ОПИСЬ ДИНАМИЧЕСКАЯ: все тела аккаунта через API, пагинация. Никаких списков из файла."""
    fleet = {}
    for page in (1, 2, 3, 4):
        batch = api("GET", f"{A}/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed")
        if not isinstance(batch, list) or not batch:
            print(f"ДИАГНОЗ флота: страница {page} ответила не списком → {str(batch)[:160]} (шрам 45680030815)")
            break
        for r in batch:
            fleet[r["name"]] = {"ветка": r.get("default_branch", "main"),
                                "архив": bool(r.get("archived")),
                                "desc": r.get("description") or "",
                                "topics": r.get("topics") or [],
                                "pushed": (r.get("pushed_at") or "")[:10],
                                "size": int(r.get("size") or 0)}
    return fleet


def n_commits_of(name):
    rr = subprocess.run(["curl", "-sS", "-D", "-", "-o", "/dev/null", "-H",
                         f"Authorization: Bearer {TOK}", f"{A}/repos/{OWNER}/{name}/commits?per_page=1"],
                        capture_output=True, text=True, timeout=60)
    m = re.search(r'[?&]page=(\d+)>; rel="last"', rr.stdout or "")
    return int(m.group(1)) if m else 1


def load_engine():
    """Движок канона: шаблон из собственного тела (revo-engine-template.py, слот @@CFG@@)."""
    src = self_text("revo-engine-template.py")
    assert "@@CFG@@" in src, "шаблон движка без слота @@CFG@@"
    return src


def engine_module(src):
    tmp = tempfile.mkdtemp(prefix="revo-eng-")
    p = os.path.join(tmp, "engine.py")
    open(p, "w", encoding="utf-8").write(src)
    spec = importlib.util.spec_from_file_location("revo_engine_" + str(abs(hash(p)) % 9999), p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_banner_svg(mod, cfg):
    """Лицо тела: 1280×400 канон (решётка Сецессиона, меандр, медальон-архетип, печать РЕВО)."""
    E, pal = mod, cfg["palette"]
    num, name, school = cfg["num"], cfg["name"], cfg["school"]
    W, H = 1280, 400
    bg, bg2, ink, gold, gold2, dim, acc = (pal["bg"], pal.get("bg2", pal["bg"]), pal["ink"],
                                           pal["gold"], pal["gold2"], pal["dim"], pal.get("accent", "#D5281B"))
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    e.append(f'<defs><radialGradient id="bn{num}" cx="0.42" cy="0.4" r="1.15">'
             f'<stop offset="0" stop-color="{bg2}"/><stop offset="1" stop-color="{bg}"/></radialGradient>'
             + E.hatch("hatchm", gold2, 0.5, 4.2, 45) + E.hatch("hatchv", ink, 0.5, 5.5, -45) + "</defs>")
    e.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
    e.append(f'<rect width="{W}" height="{H}" fill="url(#bn{num})" opacity="0.94"/>')
    e.append(f'<path d="M 60 {H-52} Q 240 {110} 470 {H-52} Z" fill="{gold}" opacity="0.12"/>')
    e.append(f'<path d="M 150 {H-52} Q 320 {170} 560 {H-52} Z" fill="{ink}" opacity="0.15"/>')
    e.append(f'<circle cx="180" cy="112" r="30" fill="{acc}" opacity="0.28"/>')
    e.append(f'<circle cx="180" cy="112" r="42" fill="none" stroke="{gold2}" stroke-width="0.7" opacity="0.7"/>')
    e.append(E.lattice(pal, W, H, step=68))
    e.append(f'<rect x="10" y="10" width="{W-20}" height="{H-20}" fill="none" stroke="{gold}" stroke-width="1.6"/>')
    e.append(f'<rect x="17" y="17" width="{W-34}" height="{H-34}" fill="none" stroke="{gold2}" stroke-width="0.6" opacity="0.75"/>')
    e.append(E.meander(pal, 26, 388, W - 26))
    e.append(E.meander(pal, 26, 12, W - 26, cell=12, sw=1.1))
    for (x, y, sgn) in ((17, 17, 1), (W - 17, 17, -1), (17, H - 17, 1), (W - 17, H - 17, -1)):
        e.append(f'<g transform="translate({x},{y}) scale({sgn},1)"><path d="M 0 0 L 26 0 L 26 5 L 5 26 L 0 26 Z" '
                 f'fill="{acc}" opacity="0.9"/><circle cx="13" cy="13" r="3.2" fill="{gold2}"/></g>')
    e.append(f'<text x="34" y="62" font-family="{E.SERIF}" font-size="11" fill="{gold}" letter-spacing="3.4">'
             f'{CANON} · ШТАНДАРТ МАСТЕРСКОЙ · {E.esc(school.upper())}</text>')
    ticks = "".join(f'<line x1="0" y1="-17" x2="0" y2="-14" transform="rotate({a})"/>' for a in range(0, 360, 30))
    e.append(f'<g transform="translate({W-58},58)"><circle r="15" fill="none" stroke="{acc}" stroke-width="1.3"/>'
             f'<circle r="11" fill="none" stroke="{acc}" stroke-width="0.55" opacity="0.6"/>'
             f'<text y="4" text-anchor="middle" font-family="{E.MONO}" font-size="10.5" fill="{gold2}">{num}</text>'
             f'<g stroke="{acc}" stroke-width="0.7">{ticks}</g></g>')
    nm = name.upper()
    fs = min(54, max(26, 620 / (len(nm) * 0.78)))
    e.append(f'<text x="34" y="164" font-family="{E.SERIF}" font-size="{fs:.1f}" fill="{ink}" letter-spacing="4">{E.esc(nm)}</text>')
    e.append(f'<line x1="34" y1="190" x2="640" y2="190" stroke="{gold}" stroke-width="1" opacity="0.85"/>')
    for i, ln in enumerate([l for l in E.wrap2(cfg.get("desc") or name, 88) if l][:2]):
        e.append(f'<text x="34" y="{218 + i*21}" font-family="{E.MONO}" font-size="12.5" fill="{dim}" letter-spacing="0.3">{E.esc(ln)}</text>')
    cx = 34
    for t in (cfg.get("topics") or [])[:4]:
        tw = int(len(t) * 8.4 + 26)
        e.append(f'<path d="M {cx} 258 L {cx+10} 252 L {cx+tw-10} 252 L {cx+tw} 258 L {cx+tw} 282 L {cx+tw-10} 288 L {cx+10} 288 L {cx} 282 Z" '
                 f'fill="none" stroke="{gold2}" stroke-width="0.9"/>'
                 f'<text x="{cx + tw/2:.0f}" y="274" text-anchor="middle" font-family="{E.MONO}" font-size="10.5" fill="{ink}" letter-spacing="1">{E.esc(t.upper())}</text>')
        cx += tw + 10
    e.append(f'<g transform="translate(96,336) rotate(-8)"><rect x="-26" y="-26" width="52" height="52" fill="{acc}"/>'
             f'<rect x="-21" y="-21" width="42" height="42" fill="none" stroke="{gold2}" stroke-width="0.8"/>'
             f'<text y="5.5" text-anchor="middle" font-family="{E.MONO}" font-size="13" fill="#F5EFE2" letter-spacing="2">РЕВО</text></g>')
    e.append(f'<text x="150" y="342" font-family="{E.SERIF}" font-size="14" fill="{acc}" letter-spacing="2">ЧЕЛОВЕК=МИФ · МИФ=ЧЕЛОВЕК</text>')
    e.append(E.myth_figure(pal, 980, 216, 152))
    for a in range(15, 360, 45):
        e.append(f'<line x1="0" y1="-166" x2="0" y2="-178" transform="rotate({a}) translate(980,216)" '
                 f'stroke="{gold2}" stroke-width="1.0" opacity="0.85"/>')
    e.append(f'<text x="980" y="382" text-anchor="middle" font-family="{E.MONO}" font-size="9.5" fill="{dim}" '
             f'letter-spacing="1.6">РЕВО В ОСНОВЕ ВСЕГО · REVE=РЕВО · {E.esc(school.upper())}</text>')
    e.append("</svg>")
    return "".join(e)


def push_tree(name, br, items, message, attempts=3):
    """Зуб A-HUSH: коммит и пуш со свежим base_tree, попытки с rebase через перечитывание head."""
    for attempt in range(1, attempts + 1):
        ref = api("GET", f"{A}/repos/{OWNER}/{name}/git/ref/heads/{br}")
        if "object" not in ref:
            time.sleep(4); continue
        head = ref["object"]["sha"]
        cm = api("GET", f"{A}/repos/{OWNER}/{name}/git/commits/{head}")
        if "tree" not in cm:
            time.sleep(4); continue
        tr = api("POST", f"{A}/repos/{OWNER}/{name}/git/trees", {"base_tree": cm["tree"]["sha"], "tree": items})
        if "sha" not in tr:
            time.sleep(4); continue
        if tr["sha"] == cm["tree"]["sha"]:
            return "без изменений"
        nc = api("POST", f"{A}/repos/{OWNER}/{name}/git/commits", {"message": message, "tree": tr["sha"], "parents": [head]})
        if "sha" not in nc:
            time.sleep(4); continue
        pr = api("PATCH", f"{A}/repos/{OWNER}/{name}/git/refs/heads/{br}", {"sha": nc["sha"], "force": False})
        if "object" in pr:
            return "записано ✓"
        time.sleep(6)
    return "пуш не прошёл за попытки"


def enroll(name, info, eng_src, num):
    """ЗАЧИСЛЕНИЕ СИРОТЫ: полный канон — лицо, паспорт, README, движок, автоматы, закон.
    ГВАРДИЯ (урок ложного зачисления 2026-11-19): тело, где канон уже стоит
    (баннер с PNG-магией + движок с каноном + паспорт с каноном), ЗАПИСЬЮ НЕ ТРОГАЕТСЯ —
    только регистрируется в desk с его собственным CFG-номером."""
    br = info["ветка"]
    if raw_head(name, "banner.png", br) == PNG_MAGIC:
        eng0 = raw_text(name, "revo_autopilot.py", br)
        pg0 = raw_text(name, "revo-page.svg", br)
        if CANON in eng0 and CANON in pg0:
            m = re.search(r"json\.loads\(r'''(.*?)'''\)", eng0, re.S)
            own_cfg = json.loads(m.group(1)) if m else {}
            return None, {"res": "уже с каноном — запись не тронута",
                          "num": own_cfg.get("num"), "school": own_cfg.get("school")}
    cfg = {"name": name, "num": num, "school": "НОВОСТРОЙ РОЯ", "desc": info["desc"],
           "topics": (info["topics"] or [])[:4], "releases": 0,
           "palette": SCHEMES[num % len(SCHEMES)]}
    mod = engine_module(eng_src.replace("@@CFG@@", json.dumps(cfg, ensure_ascii=False)))
    tree = api("GET", f"{A}/repos/{OWNER}/{name}/git/trees/{br}?recursive=1")
    paths = [e["path"] for e in tree.get("tree", []) if e.get("type") == "blob"]
    readme = raw_text(name, "README.md", br)
    facts = mod.facts_from_paths(paths, n_commits_of(name), info["pushed"], info["size"],
                                 readme, cfg["topics"], cfg["desc"], 0)
    page_svg = mod.build_svg(facts)
    md = readme
    if not md.strip():
        md = f"# {name}\n\n{cfg['desc'] or 'тело флота'}\n"
    banner_div = ('<div align="center">\n\n'
                  f'<a href="https://github.com/{OWNER}/{name}">'
                  f'<img src="banner.png" width="100%" alt="{name} — штандарт мастерской в каноне {CANON}"></a>\n\n'
                  "</div>\n")
    if '<img src="banner.png"' not in md:
        md = banner_div + "\n" + md
    md = mod.patch_readme(md, facts)
    face_svg = build_banner_svg(mod, cfg)
    png_bytes = b""
    if cairosvg is not None:
        png_bytes = cairosvg.svg2png(bytestring=face_svg.encode(), output_width=1280, output_height=400)
        assert png_bytes[:8] == PNG_MAGIC, "лицо без PNG-магии — ковка бракована"
    items = [{"path": "revo-page.svg", "mode": "100644", "type": "blob", "content": page_svg},
             {"path": "README.md", "mode": "100644", "type": "blob", "content": md},
             {"path": "revo_autopilot.py", "mode": "100644", "type": "blob",
              "content": eng_src.replace("@@CFG@@", json.dumps(cfg, ensure_ascii=False))},
             {"path": "revomat.py", "mode": "100644", "type": "blob", "content": self_text("revomat.py")},
             {"path": "revomat.yml", "mode": "100644", "type": "blob",
              "content": self_text(".github/workflows/revomat.yml").replace("{num}", str(num))},
             {"path": ".github/workflows/revomat.yml", "mode": "100644", "type": "blob",
              "content": self_text(".github/workflows/revomat.yml").replace("{num}", str(num))},
             {"path": ".github/workflows/revo-obhod.yml", "mode": "100644", "type": "blob",
              "content": self_text(".github/workflows/revo-obhod.yml")},
             {"path": "AGENTS.md", "mode": "100644", "type": "blob", "content": self_text("AGENTS.md")}]
    if png_bytes:
        # ПРАВИЛО 22: лицо пишется ТОЛЬКО blob-API (encoding:base64) — tree-API content
        # кладёт base64-текст вместо байтов (дважды доказанный класс косяков).
        bl = api("POST", f"{A}/repos/{OWNER}/{name}/git/blobs",
                 {"content": base64.b64encode(png_bytes).decode(), "encoding": "base64"})
        if "sha" in bl:
            items.append({"path": "banner.png", "mode": "100644", "type": "blob", "sha": bl["sha"]})
    res = push_tree(name, br, items,
                    f"РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ: ЗАЧИСЛЕНИЕ СИРОТЫ {name} — полный канон: лицо-баннер, "
                    f"паспорт, README-лицо, движок, автоматы, закон · {EDITION} · {CANON} · REVE=РЕВО")
    # сразу запускаем автоматы тела: паспорт куется движком, state появляется — G5 закрыт
    for wf in ("revomat.yml", "revo-obhod.yml"):
        api("POST", f"{A}/repos/{OWNER}/{name}/actions/workflows/{wf}/dispatches", {"ref": br})
    return cfg, {"res": res}


def check_repo(name, info, num):
    """СВЕРКА тела. G2 теперь проверяет PNG-магию, не только 200-код."""
    br = info["ветка"]
    rd = api("GET", f"{A}/repos/{OWNER}/{name}/readme?ref={br}")
    md = base64.b64decode(rd["content"]).decode("utf-8", "ignore") if rd.get("content") else ""
    links = sorted({p.split("#")[0].split("?")[0] for p in re.findall(r'(?:src|href)="([^"]+)"', md)
                    if not p.startswith(("http", "data:", "#", "mailto:", "camo")) and p.split("#")[0].strip()})
    passport = raw_text(name, "revo-page.svg", br)
    engine = raw_text(name, "revo_autopilot.py", br)
    with ThreadPoolExecutor(6) as ex:
        link_ok = list(ex.map(lambda p: raw_ok(name, p, br), links[:14]))
    g1 = CANON in passport
    g2 = raw_head(name, "banner.png", br) == PNG_MAGIC
    g3 = all(link_ok)
    g4 = bool(engine) and CANON in engine
    # грейс G5: тело, зачисленное менее 2 суток назад, ещё кует state — дефектом не считать
    za = (desk.get("тела", {}).get(name, {}) or {}).get("зачислено", "")
    fresh = bool(re.match(r"\d{4}-\d{2}-\d{2}", str(za))) and \
        (datetime.now() - datetime.strptime(str(za)[:10], "%Y-%m-%d")).days < 2
    g5 = bool(raw_text(name, "automaton-state.json", br).strip()) or fresh
    defects = []
    if not g1: defects.append("G1_паспорт_без_канона")
    if not g2: defects.append("G2_баннер_без_магии_png")
    if not g3: defects.append("G3_ссылки:" + ",".join(p for p, ok in zip(links[:14], link_ok) if not ok)[:120])
    if not g4: defects.append("G4_движок_без_канона")
    if not g5: defects.append("G5_state_нет")
    state = "МУЗЕЙ" if info["архив"] else ("ЗДРАВИЕ" if not defects else "ДРЕЙФ")
    return {"репа": name, "номер": num, "ветка": br, "состояние": state, "дефекты": defects,
            "ссылок_проверено": min(len(links), 14), "архив": info["архив"]}


def raw_ok(name, path, br):
    r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-L", "--max-time", "45",
                        f"https://raw.githubusercontent.com/{OWNER}/{name}/{br}/{path}"],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip() == "200"


def heal(name, report, eng_src):
    """КУЗНЯ: одно лекарство — перековка паспорта движком канона (G1/G4). Музей: unarchive→запись→archive."""
    if not TOK or not any(d.startswith(("G1", "G4")) for d in report["дефекты"]):
        return "лекарство не показано"
    br = report["ветка"]
    m = re.search(r"json\.loads\(r'''(.*?)'''\)", raw_text(name, "revo_autopilot.py", br), re.S)
    if not m:
        return "CFG движка не извлечён"
    try:
        cfg = json.loads(m.group(1))
    except Exception as ex:
        return f"CFG бит: {ex}"
    mod = engine_module(eng_src.replace("@@CFG@@", json.dumps(cfg, ensure_ascii=False)))
    tree = api("GET", f"{A}/repos/{OWNER}/{name}/git/trees/{br}?recursive=1")
    paths = [e["path"] for e in tree.get("tree", []) if e.get("type") == "blob"]
    rd = api("GET", f"{A}/repos/{OWNER}/{name}/readme?ref={br}")
    readme = base64.b64decode(rd["content"]).decode("utf-8", "ignore") if rd.get("content") else ""
    facts = mod.facts_from_paths(paths, n_commits_of(name), fleet[name]["pushed"], fleet[name]["size"],
                                 readme, cfg.get("topics") or [], cfg.get("desc") or "", cfg.get("releases") or 0)
    page_svg = mod.build_svg(facts)
    if report["архив"]:
        api("PATCH", f"{A}/repos/{OWNER}/{name}", {"archived": False}); time.sleep(1.5)
    try:
        res = push_tree(name, br, [{"path": "revo-page.svg", "mode": "100644", "type": "blob", "content": page_svg}],
                        f"РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ: ДРЕЙФ→КУЗНЯ→ЗДРАВИЕ — паспорт перекован движком канона · {EDITION} · {CANON}")
        return res
    finally:
        if report["архив"]:
            time.sleep(1.5)
            api("PATCH", f"{A}/repos/{OWNER}/{name}", {"archived": True})


# ================== ПРОЛЁТ ==================
fleet = discover_fleet()
if not fleet:
    print("ДЕГРАДАЦИЯ: API вернул пустой флот — пустоту не публикуем (правило 25), честный выход (шрам 45680030815)")
    raise SystemExit(3)
eng_src = load_engine()
try:
    desk = json.loads(self_text(DESK_FILE) or '{"тела": {}}')
except Exception:
    desk = {"тела": {}}
if "тела" not in desk:
    desk = {"тела": {}}
nums = [v.get("num", 0) for v in desk["тела"].values()] or [0]
next_num = max(nums) + 1
new_names = sorted(n for n in fleet if n not in desk["тела"])
enrolled = []
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
print(f"== ОПИСЬ ДИНАМИЧЕСКАЯ: тел {len(fleet)} · в описи {len(desk['тела'])} · вне описи {len(new_names)} ==")
for n in new_names:
    # нумерация — продолжение СЕРИИ МАНИФЕСТА (№1-68); фолбэки 100+ не считаются
    series = [v.get("num", 0) for v in desk["тела"].values() if 0 < v.get("num", 0) < 100]
    num = max(series or [66]) + 1
    cfg, res = enroll(n, fleet[n], eng_src, num)
    if cfg is None:  # гвардия: канон уже стоит — регистрируем с его собственным номером
        num2 = res.get("num") or num
        desk["тела"][n] = {"num": num2, "ветка": fleet[n]["ветка"], "архив": fleet[n]["архив"],
                           "зачислено": "подтверждено", "канон": True, "школа": res.get("school")}
        enrolled.append({"репа": n, "номер": num2, "зачисление": res["res"]})
        print(f"  ПОДТВЕРЖДЕНО {n} · полотно №{num2} · {res['res']}")
    else:
        desk["тела"][n] = {"num": num, "ветка": fleet[n]["ветка"], "архив": fleet[n]["архив"],
                           "зачислено": today, "канон": True}
        enrolled.append({"репа": n, "номер": num, "зачисление": res["res"]})
        print(f"  ЗАЧИСЛЕНО {n} · полотно №{num} · {res['res']}")

if FAST:
    # БЫСТРЫЙ ОБХОД: опись + зачисление сирот, без СВЕРКИ/КУЗНИ (полный пролёт — раз в сутки)
    own = open(os.path.realpath(__file__), encoding="utf-8").read()
    doc = {"автомат": "РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ v2 · БЫСТРЫЙ ОБХОД", "канон": CANON, "издание": EDITION,
           "опись": "динамическая (API, пагинация) — правило 21 закона AGENTS.md",
           "флот": len(fleet), "зачислено_сирот": len(enrolled), "зачислены": [e["репа"] for e in enrolled],
           "обновлено": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    fleet_json = json.dumps(doc, ensure_ascii=False, indent=1)
    desk_json = json.dumps(desk, ensure_ascii=False, indent=1)
    items = [{"path": "automaton-state.json", "mode": "100644", "type": "blob", "content": fleet_json},
             {"path": DESK_FILE, "mode": "100644", "type": "blob", "content": desk_json},
             {"path": "revomat-central.py", "mode": "100644", "type": "blob", "content": own},
             {"path": ".github/workflows/revomat-central.yml", "mode": "100644", "type": "blob", "content": CENTRAL_YML}]
    mes = (f"РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ v2 · БЫСТРЫЙ ОБХОД: опись {len(fleet)}"
           + (f", зачислено сирот {len(enrolled)}: " + ", ".join(e["репа"] for e in enrolled) if enrolled else ", сирот нет")
           + " · правило 21-22 · REVE=РЕВО")
    print("самозапись (быстрый обход):", push_tree(OWNER, "main", items, mes))
    raise SystemExit(0)

NUM_OF = {n: (desk["тела"].get(n, {}).get("num") or 0) for n in fleet}
with ThreadPoolExecutor(6) as ex:
    reports = list(ex.map(lambda t: check_repo(t[0], t[1], NUM_OF[t[0]]), sorted(fleet.items())))
healed = 0
for r in reports:
    if r["состояние"] == "ДРЕЙФ":
        res = heal(r["репа"], r, eng_src)
        r["кузня"] = res
        healed += 1 if res == "записано ✓" else 0
        print(f"  ДРЕЙФ {r['репа']} → {res} · {r['дефекты'][:1]}")
counts = {}
for r in reports:
    counts[r["состояние"]] = counts.get(r["состояние"], 0) + 1
doc = {"автомат": "РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ v2", "канон": CANON, "издание": EDITION,
       "опись": "динамическая (API, пагинация) — правило 21 закона AGENTS.md",
       "флот": len(fleet), "состояния": counts, "зачислено_сирот": len(enrolled),
       "зачислены": [e["репа"] for e in enrolled], "вылечено": healed,
       "тела": reports, "обновлено": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
print("состояния флота:", counts, "· зачислено:", len(enrolled), "· вылечено:", healed)

# самозапись в профиль (зуб A-HUSH)
fleet_json = json.dumps(json.loads(json.dumps(doc)), ensure_ascii=False, indent=1)
desk_json = json.dumps(desk, ensure_ascii=False, indent=1)
d = api("GET", f"{A}/repos/{PROFILE}/readme")
if d.get("content"):
    md = base64.b64decode(d["content"]).decode("utf-8", "ignore")
else:
    print(f"README профиля недоступен ({str(d.get('message', d.get('_raw', 'пустой ответ'))[:80])}) — блок автомата не тронут, самозапись без README (шрам 45680030815)")
    md = None
lenta = " · ".join(f"{k}:{v}" for k, v in counts.items())
block = (
    "<!--ФОРЖ:АВТОМАТ:НАЧАЛО-->\n"
    "<div align=\"center\">\n\n"
    f"**РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ v2** · конечный автомат над флотом · {CANON} · {EDITION}\n\n"
    f"> ОПИСЬ ДИНАМИЧЕСКАЯ: ФЛОТ {len(fleet)} → {lenta} · зачислено сирот {len(enrolled)}"
    + (f" ({', '.join(e['репа'] for e in enrolled)})" if enrolled else "")
    + f" · вылечено {healed} · цикл: ПЕПЕЛ→ПРОБУЖДЕНИЕ→СВЕРКА→(зачисление/лечение)→ЗДРАВИЕ\n"
    "> БАННЕР = ЛИЦО АККАУНТА: любое тело без лица зачисляется полным каноном автоматически. "
    "Доказательство работы: `automaton-state.json` и `fleet-desk.json`.\n\n"
    "</div>\n"
    "<!--ФОРЖ:АВТОМАТ:КОНЕЦ-->"
)
readme_ok = md is not None
if readme_ok and "<!--ФОРЖ:АВТОМАТ:НАЧАЛО-->" in md:
    md = re.sub(r"<!--ФОРЖ:АВТОМАТ:НАЧАЛО-->.*?<!--ФОРЖ:АВТОМАТ:КОНЕЦ-->", block.replace("\\", "\\\\"), md, flags=re.S)
elif readme_ok:
    md = md.rstrip() + "\n\n" + block + "\n"
own = open(os.path.realpath(__file__), encoding="utf-8").read()
items = [{"path": "automaton-state.json", "mode": "100644", "type": "blob", "content": fleet_json},
         {"path": DESK_FILE, "mode": "100644", "type": "blob", "content": desk_json},
         {"path": "revomat-central.py", "mode": "100644", "type": "blob", "content": own},
         {"path": ".github/workflows/revomat-central.yml", "mode": "100644", "type": "blob", "content": CENTRAL_YML},
         {"path": "revo-engine-template.py", "mode": "100644", "type": "blob", "content": eng_src}]
if readme_ok:
    items.insert(2, {"path": "README.md", "mode": "100644", "type": "blob", "content": md})
mes = (f"РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ v2: опись динамическая — флот {len(fleet)}"
       + (f", зачислено сирот {len(enrolled)}: " + ", ".join(e["репа"] for e in enrolled) if enrolled else ", сирот нет")
       + f" · {lenta} · баннер=лицо аккаунта · {EDITION} · {CANON} · REVE=РЕВО")
res = push_tree(OWNER, "main", items, mes)
print("самозапись в профиль:", res)
json.dump(doc, open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "r19_fleet_state_v2.json"),
                    "w"), ensure_ascii=False, indent=1)
