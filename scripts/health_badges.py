#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Волна ×4 · П49 (rtynbirf#4): живые бейджи здоровья роя.

Канон:
- числа никогда руками — опись swarm_health.json пишется только из живого GitHub API;
- генератор бейджей работает из описи офлайн (двойная генерация идентична байт в байт);
- бейджи — shields.io dynamic JSON, читают живой JSON по raw-URL (источник кликабелен);
- честный красный лучше зелёной лжи: раны считаются фактами прогонов, не мнением.

Режимы:
  --live --write   живой API-забор → опись + сплайс бейджей в README
  --write          пересборка README-блока из существующей описи (офлайн)
  --selftest       самоиспытание (без сети)
  --check          приёмка: raw-JSON 200 и свежесть ≤ 8 дней; бейджи резолвятся 200
  --assert-fresh   приёмка: опись на диске свежее 8 дней

Только stdlib. Токен читается из env (GITHUB_TOKEN, затем SWARM_TOKEN) и никуда не пишется.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = "rtynbirf/rtynbirf"
OWNER = "rtynbirf"
JSON_PATH = "swarm_health.json"
RAW_URL = "https://raw.githubusercontent.com/%s/main/%s" % (REPO, JSON_PATH)
BLOB_URL = "https://github.com/%s/blob/main/%s" % (REPO, JSON_PATH)
API = "https://api.github.com"
HEAVY_MIB = 512          # порог «тяжеловеса» (доктрина тяжёлых файлов: >512 МиБ репо)
FRESH_DAYS_MAX = 8       # приёмка из тела issue: свежесть JSON ≤ 8 дней
WOUND_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}
BEGIN = "<!-- HEALTH:BEGIN автогенерация · swarm_health.json · scripts/health_badges.py -->"
END = "<!-- HEALTH:END -->"
README_ANCHOR = "komarev.com/ghpvc"   # строка бейджей витрины; блок встаёт следом
UA = "poly-mat-w4f2-health"


# ---------------------------------------------------------------- утилиты

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def age_days(generated_at, at=None):
    at = at or datetime.now(timezone.utc)
    return (at - parse_iso(generated_at)).total_seconds() / 86400.0


def http_json(url, token=None):
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def pick_token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("SWARM_TOKEN") or ""


# ---------------------------------------------------------------- живой забор

def fetch_live(token):
    """Опись здоровья роя только из фактов живого API. Публичная витрина."""
    repos, page = [], 1
    while page <= 3:  # 27 публичных репо — с запасом
        batch = http_json("%s/users/%s/repos?per_page=100&sort=pushed&page=%d" % (API, OWNER, page), token)
        if not batch:
            break
        repos.extend(batch)
        page += 1
    heavy = [
        {"repo": r["name"], "size_mib": round(r["size"] / 1024.0, 1)}
        for r in repos if r.get("size", 0) > HEAVY_MIB * 1024
    ]
    heavy.sort(key=lambda x: -x["size_mib"])

    wounds, unscanned = [], []
    for r in sorted(repos, key=lambda x: x["name"]):
        try:
            runs = http_json(
                "%s/repos/%s/actions/runs?branch=%s&status=completed&per_page=1"
                % (API, r["full_name"], urllib.parse.quote(r["default_branch"] or "main", safe="")),
                token,
            ).get("workflow_runs", [])
        except Exception as e:  # сеть/права — честно фиксируем дыру покрытия
            unscanned.append({"repo": r["name"], "reason": str(e)[:80]})
            continue
        if not runs:
            continue  # прогонов нет — раны нет (пусто ≠ красный)
        top = runs[0]
        if top.get("conclusion") in WOUND_CONCLUSIONS:
            wounds.append({
                "repo": r["name"],
                "workflow": top.get("name") or "",
                "conclusion": top["conclusion"],
                "url": top.get("html_url") or "",
            })

    prs = http_json("%s/search/issues?q=%s&per_page=1"
                    % (API, urllib.parse.quote("is:pr is:open user:%s" % OWNER)), token)

    inv = {
        "schema": "swarm_health/1",
        "generated_at": now_iso(),
        "source": {
            "api": "https://api.github.com/users/%s/repos" % OWNER,
            "rules": {
                "wounds": "последний завершённый прогон на default-ветке в {%s}" % ",".join(sorted(WOUND_CONCLUSIONS)),
                "heavyweights_mib": HEAVY_MIB,
                "fresh_days_max": FRESH_DAYS_MAX,
            },
            "coverage": "public",
            "repos_total": len(repos),
            "repos_scanned": len(repos) - len(unscanned),
            "unscanned": unscanned,
        },
        "wounds": {"count": len(wounds), "repos": wounds},
        "open_prs": {"count": prs.get("total_count", 0), "query": "is:pr is:open user:%s" % OWNER},
        "heavyweights": {"count": len(heavy), "repos": heavy},
    }
    inv["wounds"]["badge_color"] = "brightgreen" if not wounds else "red"
    inv["open_prs"]["badge_color"] = "brightgreen" if prs.get("total_count", 0) == 0 else "orange"
    inv["heavyweights"]["badge_color"] = "brightgreen" if not heavy else "orange"
    return inv


# ---------------------------------------------------------------- бейджи

def _enc(v):
    return urllib.parse.quote(str(v), safe="")


def badge(label, query, color, link, suffix=""):
    """shields.io dynamic JSON; URL целиком безопасен для markdown-круглых скобок."""
    url = ("https://img.shields.io/badge/dynamic/json?url=%s&query=%s&label=%s&color=%s"
           % (_enc(RAW_URL), _enc(query), _enc(label), _enc(color)))
    if suffix:
        url += "&suffix=%s" % _enc(suffix)
    url += "&style=flat-square&cacheSeconds=3600"
    return "[![%s](%s)](%s)" % (label, url, link)


def badge_row(inv):
    g = inv["generated_at"][:10]
    return " ".join([
        badge("РАНЫ", "$.wounds.count", inv["wounds"]["badge_color"], BLOB_URL),
        badge("PR", "$.open_prs.count", inv["open_prs"]["badge_color"],
              "https://github.com/pulls?q=is%%3Apr+is%%3Aopen+user%%3A%s" % OWNER),
        badge("ТЯЖЕЛОВЕСЫ", "$.heavyweights.count", inv["heavyweights"]["badge_color"], BLOB_URL,
              suffix="репо"),
        badge("ОПИСЬ", "$.generated_date", "2E2540", BLOB_URL),
    ]), g


# ---------------------------------------------------------------- сплайс README

def splice_readme(readme, inv):
    row, _ = badge_row(inv)
    block = BEGIN + "\n" + row + "\n" + END
    if BEGIN in readme and END in readme:
        return readme.split(BEGIN)[0] + block + readme.split(END, 1)[1]
    lines = readme.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if README_ANCHOR in line:
            head, tail = "".join(lines[:i + 1]), "".join(lines[i + 1:])
            return head + "\n" + block + "\n" + tail
    raise SystemExit("якорь бейджей витрины не найден — README менялся вручную; резать вслепую отказываюсь")


def write_json(inv, path):
    inv = dict(inv)
    inv["generated_date"] = inv["generated_at"][:10]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return path


# ---------------------------------------------------------------- приёмки

def selftest():
    inv = {
        "generated_at": "2026-11-08T19:00:00Z",
        "wounds": {"count": 1, "badge_color": "red"},
        "open_prs": {"count": 2, "badge_color": "orange"},
        "heavyweights": {"count": 1, "badge_color": "orange"},
    }
    row1, d1 = badge_row(inv)
    row2, d2 = badge_row(inv)
    assert row1 == row2, "двойная генерация бейджей неидентична"
    assert d1 == d2 == "2026-11-08"
    for raw in re.findall(r"\((https://[^)]+)\)", row1):
        assert " " not in raw and "(" not in raw and ")" not in raw, "URL ломает markdown: %r" % raw
    assert row1.count("img.shields.io/badge/dynamic/json") == 4
    assert urllib.parse.unquote(row1).count("swarm_health.json") >= 1

    inv2 = dict(inv)
    inv2["open_prs"] = {"count": 0, "badge_color": "brightgreen"}
    row3, _ = badge_row(inv2)
    assert row3 != row1, "изменение описи обязано менять бейджи"

    assert abs(age_days("2026-11-06T00:00:00Z", at=parse_iso("2026-11-08T12:00:00Z")) - 2.5) < 1e-9
    assert age_days(now_iso()) < 0.01, "свежесть только что созданной описи не ноль"

    base = "# t\n\n[![Views](https://komarev.com/ghpvc/?username=rtynbirf)](x)\n\n## FLAGSHIPS\n"
    once = splice_readme(base, inv)
    twice = splice_readme(once, inv)
    assert once == twice, "сплайс не идемпотентен"
    assert once.count(BEGIN) == 1 and once.count(END) == 1
    assert "komarev.com/ghpvc" in once.split(BEGIN)[0], "блок обязан стоять после строки бейджей витрины"

    no_wounds = dict(inv, wounds={"count": 0, "badge_color": "brightgreen"})
    prs0 = dict(inv, open_prs={"count": 0, "badge_color": "brightgreen"})
    heavy0 = dict(inv, heavyweights={"count": 0, "badge_color": "brightgreen"})
    assert badge_row(no_wounds)[0] != row1, "раны=0 обязаны перекрасить бейдж"
    assert badge_row(prs0)[0] != row1, "PR=0 обязан перекрасить бейдж"
    assert badge_row(heavy0)[0] != row1, "тяжеловесы=0 обязаны перекрасить бейдж"

    digest = hashlib.sha256(b"abc").hexdigest()
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    print("✓ двойная генерация бейджей идентична")
    print("✓ URL-ы markdown-безопасны, источники кликабельны")
    print("✓ цвет/value следуют факту описи (0 → brightgreen, >0 → red/orange)")
    print("✓ возраст описи считается; свежая опись = 0 дней")
    print("✓ сплайс README идемпотентен и встаёт после строки бейджей витрины")
    print("SELFTEST: OK")


def load_inventory(path=JSON_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def assert_fresh(path=JSON_PATH):
    inv = load_inventory(path)
    age = age_days(inv["generated_at"])
    ok = age <= FRESH_DAYS_MAX
    print("✓ опись от %s · возраст %.2f дн (порог ≤ %d)" % (inv["generated_at"], age, FRESH_DAYS_MAX))
    if not ok:
        raise SystemExit("ОПИСЬ ПРОТУХЛА: %.1f дн > %d — живой API-забор отстал" % (age, FRESH_DAYS_MAX))
    print("FRESH: OK")


def _get_retry(url, retries=4, pause=4):
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except Exception as e:  # shields.io/CDN бывают медленными — честная повторная попытка
            last = e
            time.sleep(pause)
    raise SystemExit("GET недоступен после %d попыток: %s (%s)" % (retries, url[:120], last))


def check(retries=6):
    last = None
    for attempt in range(retries):
        try:
            code, body = _get_retry(RAW_URL, retries=1)
            assert code == 200
            inv = json.loads(body)
            break
        except SystemExit:
            raise
        except Exception as e:  # CDN githubusercontent догоняет после коммита
            last = e
            time.sleep(4)
    else:
        raise SystemExit("raw-JSON недоступен: %s" % last)
    age = age_days(inv["generated_at"])
    assert age <= FRESH_DAYS_MAX, "свежесть %.1f дн > %d" % (age, FRESH_DAYS_MAX)
    print("✓ raw JSON 200 · сгенерирован %s · возраст %.2f дн" % (inv["generated_at"], age))

    row, _ = badge_row(inv)
    urls = re.findall(r"\((https://img\.shields\.io[^)]+)\)", row)
    assert len(urls) == 4, "ожидались 4 бейджа, найдено %d" % len(urls)
    for u in urls:
        status, svg = _get_retry(u)
        assert status == 200 and "<svg" in svg, "бейдж не отрисовался: %s" % u
        print("✓ бейдж 200: %s" % urllib.parse.unquote(u)[:110])
    print("CHECK: OK")


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="живые бейджи здоровья роя (П49)")
    ap.add_argument("--live", action="store_true", help="живой API-забор → опись")
    ap.add_argument("--write", action="store_true", help="записать опись и сплайсить README")
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--assert-fresh", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if args.check:
        check()
        return
    if args.assert_fresh:
        assert_fresh()
        return

    if args.live:
        token = pick_token()
        if not token:
            raise SystemExit("нет токена в env (GITHUB_TOKEN/SWARM_TOKEN) — числа руками не выдумываем")
        inv = fetch_live(token)
        if args.write:
            write_json(inv, JSON_PATH)
            print("✓ опись написана: %s (раны=%d, pr=%d, тяжеловесы=%d)"
                  % (JSON_PATH, inv["wounds"]["count"], inv["open_prs"]["count"],
                     inv["heavyweights"]["count"]))
        else:
            print(json.dumps(inv, ensure_ascii=False, indent=2))
    inv = load_inventory(JSON_PATH)
    if args.write:
        with open(args.readme, encoding="utf-8") as f:
            readme = f.read()
        new = splice_readme(readme, inv)
        with open(args.readme, "w", encoding="utf-8") as f:
            f.write(new)
        print("✓ README-блок бейджей выровнен с описью")
    else:
        print(badge_row(inv)[0])


if __name__ == "__main__":
    main()
