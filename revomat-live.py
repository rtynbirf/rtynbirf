#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""РЁВО-ЖИВОЙ МОДУЛЬ (revomat-live.py) · ИЗДАНИЕ r20-ЖИВОЕ · stdlib + cairosvg.
Мировая практика (github-readme-stats, lowlighter/metrics): картинка генерируется
в репо из живых данных GitHub API и коммитится обратно. Здесь то же, в каноне
Ornamental Mytho-Realism, для всего флота:
  1) ЖИВОЕ ЛИЦО: у каждого тела полоса реальных данных API (коммиты, звёзды, форки,
     ветви, размер КБ, дата пуша, штамп перерисовки). Автомат сверяет отпечаток
     данных с запечатлённым (live-state.json); ушло — лицо перерисовывается
     (тот же канон, тот же CFG тела, только данные свежие). ПРАВИЛО 22: лицо
     пишется ТОЛЬКО blob-API (encoding base64), верификация байтами ПОСЛЕ записи.
  2) ЖИВАЯ КАРТА РОЯ: live-map.png в профиле переписывается КАЖДЫМ обходом —
     решётка тел: №, имя, звёзды, коммиты, размер, АРХИВ/ЖИВ, штамп времени.
  3) README профиля: блок ЖИВАЯ КАРТА (idempotent по маркеру ФОРЖ:КАРТА).
Actions-безопасен: checkout → self_text, без путей песочницы."""
import base64, hashlib, importlib.util, json, os, re, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

CANON = "ORNAMENTAL MYTHO-REALISM"
EDITION = "ИЗДАНИЕ r20-ЖИВОЕ"
TOK = os.environ.get("GH_TOKEN", "")
A = "https://api.github.com"
OWNER = "rtynbirf"
PROFILE = f"{OWNER}/{OWNER}"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
STATE_FILE = "live-state.json"
DRY = os.environ.get("LIVE_DRY", "") == "1"

SCHEMES = [
    dict(bg="#10243E", bg2="#1B3B5F", ink="#F3ECD9", gold="#D4AF37", gold2="#E8C868", dim="#8FA3BF", accent="#D5281B"),
    dict(bg="#38100A", bg2="#4E1A10", ink="#F4E9D6", gold="#D4AF37", gold2="#E8C868", dim="#C39272", accent="#2C5F9E"),
    dict(bg="#0C2E21", bg2="#14402E", ink="#EFE7D2", gold="#D4AF37", gold2="#E8C868", dim="#8FB09C", accent="#C43B27"),
    dict(bg="#2A1D12", bg2="#3A2A1B", ink="#F1E8D8", gold="#D4AF37", gold2="#E8C868", dim="#B79F7E", accent="#1F5B8B"),
    dict(bg="#171512", bg2="#232017", ink="#F2E9D4", gold="#D4AF37", gold2="#E8C868", dim="#A99E82", accent="#B03A2A"),
    dict(bg="#EFE6CF", bg2="#F6EFDC", ink="#241C10", gold="#9A7B23", gold2="#C9A227", dim="#6E6249", accent="#C43B27"),
]


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


def discover_fleet():
    fleet = {}
    for page in (1, 2, 3, 4):
        batch = api("GET", f"{A}/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed")
        if not isinstance(batch, list) or not batch:
            break
        for r in batch:
            fleet[r["name"]] = {"ветка": r.get("default_branch", "main"),
                                "архив": bool(r.get("archived")),
                                "desc": r.get("description") or "",
                                "topics": r.get("topics") or [],
                                "pushed": (r.get("pushed_at") or "")[:10],
                                "звёзды": int(r.get("stargazers_count") or 0),
                                "форки": int(r.get("forks_count") or 0),
                                "issues": int(r.get("open_issues_count") or 0),
                                "size": int(r.get("size") or 0)}
    return fleet


def page_count(name, what):
    rr = subprocess.run(["curl", "-sS", "-D", "-", "-o", "/dev/null", "-H",
                         f"Authorization: Bearer {TOK}", f"{A}/repos/{OWNER}/{name}/{what}?per_page=1"],
                        capture_output=True, text=True, timeout=60)
    m = re.search(r'[?&]page=(\d+)>; rel="last"', rr.stdout or "")
    return int(m.group(1)) if m else 1


def push_tree(name, br, items, message, attempts=4):
    for attempt in range(attempts):
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
    return "пуш не прошёл"


def engine_module(src):
    tmp = tempfile.mkdtemp(prefix="revo-live-")
    p = os.path.join(tmp, "engine.py")
    open(p, "w", encoding="utf-8").write(src)
    spec = importlib.util.spec_from_file_location("revo_live_" + str(abs(hash(p)) % 9999), p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def own_cfg_of(name, br):
    """Собственный CFG тела — лицо остаётся тем же полотном, меняются только данные."""
    eng = raw_text(name, "revo_autopilot.py", br)
    m = re.search(r"json\.loads\(r'''(.*?)'''\)", eng, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def data_band(pal, d, W, H):
    """Полоса ЖИВОГО ЛИЦА: реальные данные API под нижним меандром (канон не тронут)."""
    gold, gold2, dim, ink = pal["gold"], pal["gold2"], pal["dim"], pal["ink"]
    row1 = (f"ЖИВОЕ ЛИЦО · ДАННЫЕ API: КОММИТЫ {d['коммиты']} · ЗВЁЗДЫ {d['звёзды']} · ФОРКИ {d['форки']} · "
            f"ВЕТВИ {d['ветви']} · РАЗМЕР {d['size']} КБ · ПУШ {d['pushed']}")
    row2 = f"ПЕРЕПИСАНО АВТОМАТОМ {d['штамп']} UTC · ЖИВАЯ КАРТА: live-map.png В ПРОФИЛЕ РОЯ · {EDITION}"
    e = [f'<line x1="26" y1="{H-52}" x2="{W-26}" y2="{H-52}" stroke="{gold}" stroke-width="0.9" opacity="0.85"/>',
         f'<text x="{W/2}" y="{H-36}" text-anchor="middle" font-family="monospace" font-size="12" '
         f'fill="{gold2}" letter-spacing="0.6">{row1}</text>',
         f'<text x="{W/2}" y="{H-22}" text-anchor="middle" font-family="monospace" font-size="9.5" '
         f'fill="{dim}" letter-spacing="1.1">{row2}</text>']
    return "".join(e)


def build_live_svg(mod, cfg, d, W=1280, H=456):
    """Канон 1280×400 (все элементы канона на своих местах) + полоса живых данных
    на расширенной канве 456: нижний меандр и девиз остаются на y≤388, полоса 404–436,
    рамка и углы адаптируются к H. Полоса ВНУТРИ viewBox — видно в рендере."""
    svg = mod_build(mod, cfg, W, H)
    svg = svg[:-6] + data_band(cfg["palette"], d, W, H) + "</svg>"
    return svg


def mod_build(mod, cfg, W=1280, H=400):
    """Точная копия кузни лица r19 (build_banner_svg) — стиль канона единый."""
    E, pal = mod, cfg["palette"]
    num, name, school = cfg["num"], cfg["name"], cfg.get("school") or "ШКОЛА РОЯ"
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


def build_map_svg(items, d, COLS=8, CW=180, CH=100):
    """ЖИВАЯ КАРТА РОЯ: решётка тел с реальными данными; переписывается каждым обходом."""
    rows = (len(items) + COLS - 1) // COLS
    W = 48 + COLS * CW + (COLS - 1) * 6
    H = 96 + rows * CH + (rows - 1) * 6 + 52
    pal0 = SCHEMES[0]
    gold, gold2, ink, dim = pal0["gold"], pal0["gold2"], pal0["ink"], pal0["dim"]
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    e.append(f'<defs><radialGradient id="mp" cx="0.5" cy="0.3" r="1.2">'
             f'<stop offset="0" stop-color="#1B3B5F"/><stop offset="1" stop-color="#10243E"/></radialGradient>'
             f'<pattern id="mplat" width="34" height="34" patternUnits="userSpaceOnUse">'
             f'<path d="M 0 17 H 34 M 17 0 V 34" stroke="{gold2}" stroke-width="0.4" opacity="0.14"/></pattern></defs>')
    e.append(f'<rect width="{W}" height="{H}" fill="#10243E"/>')
    e.append(f'<rect width="{W}" height="{H}" fill="url(#mp)" opacity="0.95"/>')
    e.append(f'<rect width="{W}" height="{H}" fill="url(#mplat)"/>')
    e.append(f'<rect x="10" y="10" width="{W-20}" height="{H-20}" fill="none" stroke="{gold}" stroke-width="1.6"/>')
    e.append(f'<rect x="17" y="17" width="{W-34}" height="{H-34}" fill="none" stroke="{gold2}" stroke-width="0.6" opacity="0.75"/>')
    e.append(f'<text x="{W/2}" y="52" text-anchor="middle" font-family="serif" font-size="26" fill="{ink}" '
             f'letter-spacing="6">ЖИВАЯ КАРТА РОЯ · {CANON}</text>')
    e.append(f'<text x="{W/2}" y="76" text-anchor="middle" font-family="monospace" font-size="12" fill="{gold2}" '
             f'letter-spacing="1.2">ТЕЛ {d["флот"]} · КОММИТОВ {d["коммиты_Σ"]} · ЗВЁЗД {d["звёзды_Σ"]} · '
             f'МУЗЕЙ {d["архивы"]} · ПЕРЕПИСАНО {d["штамп"]} UTC · {EDITION}</text>')
    for i, it in enumerate(items):
        r, c = divmod(i, COLS)
        x0, y0 = 24 + c * (CW + 6), 96 + r * (CH + 6)
        pal = SCHEMES[it["num"] % len(SCHEMES)] if it["num"] else pal0
        arc = it["архив"]
        op = "0.55" if arc else "0.94"
        e.append(f'<g><rect x="{x0}" y="{y0}" width="{CW}" height="{CH}" rx="3" fill="{pal["bg"]}" fill-opacity="{op}" '
                 f'stroke="{pal["gold"] if not arc else pal["dim"]}" stroke-width="0.8"/>')
        e.append(f'<text x="{x0+8}" y="{y0+18}" font-family="monospace" font-size="10.5" fill="{pal["gold2"]}">№{it["num"]}</text>')
        nm = it["имя"].upper()
        e.append(f'<text x="{x0+8}" y="{y0+40}" font-family="monospace" font-size="{11 if len(nm)<=16 else 9}" '
                 f'fill="{pal["ink"]}">{nm[:16]}</text>')
        e.append(f'<text x="{x0+8}" y="{y0+60}" font-family="monospace" font-size="9.5" fill="{pal["dim"]}">'
                 f'★{it["звёзды"]} · C{it["коммиты"]} · {it["size"]}КБ</text>')
        e.append(f'<text x="{x0+8}" y="{y0+80}" font-family="monospace" font-size="9" fill="{pal["dim"]}">ПУШ {it["pushed"]}</text>')
        if arc:
            e.append(f'<g transform="rotate(-14 {x0+CW-30} {y0+CH-16})">'
                     f'<text x="{x0+CW-30}" y="{y0+CH-16}" text-anchor="middle" font-family="monospace" '
                     f'font-size="10" fill="{pal["accent"]}" opacity="0.85">АРХИВ</text></g>')
        e.append("</g>")
    e.append(f'<text x="{W/2}" y="{H-26}" text-anchor="middle" font-family="monospace" font-size="10" fill="{dim}" '
             f'letter-spacing="1.6">РЕВО В ОСНОВЕ ВСЕГО · REVE=РЕВО · ЧЕЛОВЕК=МИФ, МИФ=ЧЕЛОВЕК</text>')
    e.append("</svg>")
    return "".join(e)


def png_of(svg, w, h=None):
    import cairosvg
    kw = {"output_width": w}
    if h:
        kw["output_height"] = h
    return cairosvg.svg2png(bytestring=svg.encode(), **kw)


def push_png_blob(name, br, path, png_bytes, message):
    """ПРАВИЛО 22: лицо — только blob-API (encoding base64); верификация байтами после записи."""
    bl = api("POST", f"{A}/repos/{OWNER}/{name}/git/blobs",
             {"content": base64.b64encode(png_bytes).decode(), "encoding": "base64"})
    if "sha" not in bl:
        return f"blob не создан: {str(bl)[:80]}", None
    res = push_tree(name, br, [{"path": path, "mode": "100644", "type": "blob", "sha": bl["sha"]}], message)
    if res == "записано ✓":
        vf = api("GET", f"{A}/repos/{OWNER}/{name}/contents/{path}?ref={br}")
        vb = base64.b64decode(vf.get("content") or "")
        if not vb.startswith(PNG_MAGIC) or hashlib.sha256(vb).hexdigest() != hashlib.sha256(png_bytes).hexdigest():
            return "ВЕРИФИКАЦИЯ ПАЛА: байты не совпали", None
        return "записано ✓ (верифицировано байтами)", bl["sha"]
    if res == "без изменений":
        return "уже такое лицо в репо (успех)", bl["sha"]
    return res, None


def banner_sha_of(name, br):
    f = api("GET", f"{A}/repos/{OWNER}/{name}/contents/banner.png?ref={br}")
    return f.get("sha") or ""


def repaint(name, info, cfg, mod):
    br = info["ветка"]
    d = {"коммиты": page_count(name, "commits"), "ветви": page_count(name, "branches"),
         "звёзды": info["звёзды"], "форки": info["форки"], "size": info["size"],
         "pushed": info["pushed"],
         "штамп": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}
    cfg2 = dict(cfg)
    cfg2["desc"] = info["desc"] or cfg.get("desc") or name
    cfg2["topics"] = (info["topics"] or cfg.get("topics") or [])[:4]
    svg = build_live_svg(mod, cfg2, d, 1280, 456)
    png = png_of(svg, 1280, 456)
    if png[:8] != PNG_MAGIC:
        return d, "лицо без PNG-магии", None
    if DRY:
        return d, "дри-ран: будет перекрашено", None
    res, bsha = push_png_blob(name, br, "banner.png", png,
                              f"ЖИВОЕ ЛИЦО: полотно переписано реальными данными API (коммиты {d['коммиты']}, звёзды "
                              f"{d['звёзды']}, пуш {d['pushed']}) · {EDITION} · {CANON} · REVE=РЕВО")
    return d, res, bsha


# ================= ПРОЛЁТ ЖИВОГО МОДУЛЯ =================
t0 = time.time()
fleet = discover_fleet()
eng_src = self_text("revo-engine-template.py")
assert "@@CFG@@" in eng_src, "нет слота @@CFG@@ в шаблоне"
desk = json.loads(self_text("fleet-desk.json") or '{"тела": {}}') if self_text("fleet-desk.json").strip() else {"тела": {}}
try:
    state = json.loads(self_text(STATE_FILE) or "{}")
except Exception:
    state = {}
mod = engine_module(eng_src)
print(f"== ЖИВОЙ МОДУЛЬ: флот {len(fleet)} · в desk {len(desk.get('тела', {}))} · в state {len(state)} ==")

def job(item):
    name, info = item
    br = info["ветка"]
    st = state.get(name) or {}
    # КОНТУР ПРИНУЖДЕНИЯ: запечатанный sha лица vs реальный sha в репо.
    # Лицо без записанного sha, перекрытое извне или отставшее по изданию — перекрашивается.
    cur_sha = banner_sha_of(name, br)
    need_by_sha = bool(cur_sha) and st.get("лицо_sha") != cur_sha
    live_fp = {"коммиты": None, "звёзды": info["звёзды"], "форки": info["форки"],
               "size": info["size"], "pushed": info["pushed"], "desc": info["desc"],
               "topics": ",".join(info["topics"][:4])}
    fp_equal = st.get("fp") == json.dumps(live_fp, sort_keys=True)
    if (not need_by_sha) and fp_equal and st.get("канон") == CANON and st.get("издание") == EDITION \
            and st.get("лицо_sha"):
        return name, None, st.get("данные", {}), "данные не ушли — не тронуто"
    cfg = own_cfg_of(name, br)
    if not cfg:
        cfg = {"name": name, "num": len(state) + 1, "school": "ШКОЛА РОЯ",
               "palette": SCHEMES[0]}
    cfg.setdefault("palette", SCHEMES[(cfg.get("num") or 1) % len(SCHEMES)])
    d, res, bsha = repaint(name, info, cfg, mod)
    return name, (json.dumps(live_fp, sort_keys=True), d, res, bsha), d, res

with ThreadPoolExecutor(6) as ex:
    out = list(ex.map(job, sorted(fleet.items())))
repainted, skipped, failed = [], [], []
new_state = dict(state)
for name, fpd, d, res in out:
    if fpd is None:
        skipped.append(name)
        continue
    fp, _, res2, bsha = fpd
    ok = res2.startswith("записано") or res2 == "уже такое лицо в репо (успех)"
    if ok:
        repainted.append((name, res2))
        new_state[name] = {"fp": fp, "канон": CANON, "издание": EDITION,
                           "данные": {k: d.get(k) for k in ("коммиты", "звёзды", "форки", "ветви", "size", "pushed")},
                           "штамп": d.get("штамп"), "лицо_sha": bsha}
    else:
        failed.append((name, res2))
        new_state.pop(name, None)  # не отмечать свежим — следующий обход перекрасит
print(f"перекрашено: {len(repainted)} · не изменились: {len(skipped)} · неудач: {len(failed)}")
for n, r in repainted[:10]:
    print(f"  {n} → {r}")
if len(repainted) > 10:
    print(f"  … ещё {len(repainted)-10}")
for n, r in failed[:8]:
    print(f"  НЕУДАЧА {n} → {r}")

# ЖИВАЯ КАРТА — переписывается КАЖДЫМ обходом
items = []
for i, (name, info) in enumerate(sorted(fleet.items())):
    dd = new_state.get(name, {}).get("данные") or {}
    items.append({"num": (desk.get("тела", {}).get(name, {}) or {}).get("num") or i + 1,
                  "имя": name, "архив": info["архив"], "звёзды": info["звёзды"],
                  "коммиты": dd.get("коммиты") or page_count(name, "commits"),
                  "size": info["size"], "pushed": info["pushed"]})
map_d = {"флот": len(fleet), "коммиты_Σ": sum(i["коммиты"] for i in items),
         "звёзды_Σ": sum(i["звёзды"] for i in items),
         "архивы": sum(1 for i in items if i["архив"]),
         "штамп": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}
map_svg = build_map_svg(items, map_d)
map_png = png_of(map_svg, 1530)
assert map_png[:8] == PNG_MAGIC, "карта без PNG-магии"
print(f"ЖИВАЯ КАРТА: {len(items)} тел · Σ коммитов {map_d['коммиты_Σ']} · {len(map_png)} Б")
if DRY:
    open("/tmp/live-map-preview.png", "wb").write(map_png)
    print("дри-ран: карта не запушена; превью /tmp/live-map-preview.png")
    raise SystemExit(0)

# README профиля: блок ЖИВОЙ КАРТЫ (idempotent)
rd = api("GET", f"{A}/repos/{PROFILE}/readme")
md = base64.b64decode(rd["content"]).decode("utf-8", "ignore")
map_block = (
    "<!--ФОРЖ:КАРТА:НАЧАЛО-->\n"
    "<div align=\"center\">\n\n"
    f"### 🗺 ЖИВАЯ КАРТА РОЯ · переписывается автоматом при каждом обходе (данные API)\n\n"
    f'<img src="live-map.png" width="100%" alt="Живая карта роя — реальные данные API, канон {CANON}">\n\n'
    "> Полотна лиц всех тел несут полосу ДАННЫХ API и перерисовываются, когда реальность "
    "ушла от запечатлённого (правило 25). Доказательства: `live-state.json`, `live-map.png`.\n\n"
    "</div>\n"
    "<!--ФОРЖ:КАРТА:КОНЕЦ-->"
)
if "<!--ФОРЖ:КАРТА:НАЧАЛО-->" in md:
    md = re.sub(r"<!--ФОРЖ:КАРТА:НАЧАЛО-->.*?<!--ФОРЖ:КАРТА:КОНЕЦ-->", map_block.replace("\\", "\\\\"), md, flags=re.S)
    md_res = "блок заменён"
else:
    md = md.rstrip() + "\n\n" + map_block + "\n"
    md_res = "блок добавлен"

bl = api("POST", f"{A}/repos/{PROFILE}/git/blobs",
         {"content": base64.b64encode(map_png).decode(), "encoding": "base64"})
own = open(os.path.realpath(__file__), encoding="utf-8").read()
items_push = [
    {"path": "live-map.png", "mode": "100644", "type": "blob", "sha": bl["sha"]},
    {"path": STATE_FILE, "mode": "100644", "type": "blob",
     "content": json.dumps(new_state, ensure_ascii=False, indent=1)},
    {"path": "README.md", "mode": "100644", "type": "blob", "content": md},
    {"path": "revomat-live.py", "mode": "100644", "type": "blob", "content": own},
]
res = push_tree(OWNER, "main", items_push,
                f"ЖИВОЙ МОДУЛЬ: лица переписаны данными API ({len(repainted)} перекрашено, {len(skipped)} не ушли), "
                f"ЖИВАЯ КАРТА переписана ({map_d['флот']} тел, Σ {map_d['коммиты_Σ']} коммитов) · {EDITION} · {CANON} · REVE=РЕВО")
print(f"README: {md_res} · самозапись карты+state: {res}")
json.dump({"перекрашено": len(repainted), "не_ушли": len(skipped), "карта": map_d},
          open("live-last.json", "w"), ensure_ascii=False, indent=1)
print(f"пролёт живого модуля завершён за {time.time()-t0:.0f} с")
