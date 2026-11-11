#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПУЛЬС ПРАВДЫ: дом перемеряет себя и приводит цифры к реальности.
Измерение → правка цифр в forge-pulse.svg / forge-now.svg / README → коммит, если изменилось.
Никаких деклараций: число в доме = измерение. Ошибка сети = мягкий отступ, файлы не трогаем."""
import json, os, re, sys, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor

TOK = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def api(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "pulse-truth")
    req.add_header("Accept", "application/vnd.github+json")
    if TOK:
        req.add_header("Authorization", "token " + TOK)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def raw_st(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status
    except Exception:
        return 0


def pl(n, one, few, many):
    n = abs(int(n)) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def measure():
    user = api("https://api.github.com/users/rtynbirf")
    repos = api("https://api.github.com/users/rtynbirf/repos?per_page=100&sort=pushed")
    if not isinstance(repos, list):
        raise RuntimeError("список репо не получен")
    s = api("https://api.github.com/search/commits?q=author%3Artynbirf&per_page=1")
    commits = s.get("total_count") if isinstance(s, dict) else None

    def chk(r):
        return raw_st("https://raw.githubusercontent.com/rtynbirf/%s/%s/banner.png" % (r["name"], r["default_branch"]))
    with ThreadPoolExecutor(16) as ex:
        banners = sum(1 for st in ex.map(chk, repos) if st == 200)
    sg = api("https://api.github.com/repos/rtynbirf/singulyar")
    tree = api("https://api.github.com/repos/rtynbirf/singulyar/git/trees/%s?recursive=1" % sg["default_branch"])
    pages = sum(1 for x in tree.get("tree", []) if x.get("path", "").endswith(".html") and x["type"] == "blob") if isinstance(tree, dict) else 0
    msk = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    return dict(repos=len(repos), alive=sum(1 for r in repos if not r.get("archived")),
                stars=sum(r["stargazers_count"] for r in repos), forks=sum(r["forks_count"] for r in repos),
                followers=user.get("followers", 0), commits=commits, banners=banners,
                pages=pages, last_push=max(r["pushed_at"] for r in repos), msk=msk)


def rebuild_pulse(svg, m):
    if m["commits"] is None:
        return svg, 0
    line = "%d %s ОТКРЫТЫ" % (m["repos"], pl(m["repos"], "ФЛОТ", "ФЛОТА", "ФЛОТОВ"))
    return re.subn(r"\d+ ФЛОТ[АОВ]+ ОТКРЫТЫ", line, svg)


def rebuild_now(svg, m):
    svg2, k1 = re.subn(r"срез: \d{4}-\d{2}-\d{2}", "срез: " + m["msk"].strftime("%Y-%m-%d"), svg)
    mm = re.search(r"СЕЙЧАС В КУЗНЕ:[^<]*", svg2)
    if not mm:
        return svg2, 0
    old = mm.group(0)
    tail = old.split("СИНГУЛЯРА")[-1] if "СИНГУЛЯРА" in old else ""
    new = ("СЕЙЧАС В КУЗНЕ:  %d публичных %s  ·  %d %s OBSIDIAN &amp; GOLD  ·  "
           "рука кузни на %d страницах СИНГУЛЯРА%s") % (
        m["repos"], pl(m["repos"], "флот", "флота", "флотов"),
        m["banners"], pl(m["banners"], "штандарт", "штандарта", "штандартов"),
        m["pages"], tail)
    return svg2.replace(old, new), 1


def rebuild_readme(md, m):
    date_b = m["msk"].strftime("%Y-%m-%d").replace("-", "--")
    md, k1 = re.subn(r"\[!\[Commits\]\(https://img\.shields\.io/badge/commits-[^)]*\)\](?:\(https://github\.com/rtynbirf\))*",
                     "[![Commits](https://img.shields.io/badge/commits-%d%%2B%%20since%%202022-2E2540?style=flat-square)](https://github.com/rtynbirf)" % m["commits"], md)
    md, k2 = re.subn(r"\[!\[Audit\]\(https://img\.shields\.io/badge/audited-[^)]*\)\](?:\(https://github\.com/rtynbirf\))*",
                     "[![Audit](https://img.shields.io/badge/audited-%s-2E2540?style=flat-square)](https://github.com/rtynbirf)" % date_b, md)
    return md, (k1 + k2)


def main():
    m = measure()
    changed = 0
    for path, fn in (("assets/forge-pulse.svg", rebuild_pulse), ("assets/forge-now.svg", rebuild_now)):
        svg = open(path, encoding="utf-8").read()
        svg2, k = fn(svg, m)
        if k and svg2 != svg:
            open(path, "w", encoding="utf-8").write(svg2)
            changed += 1
            print("обновлён", path)
    md = open("README.md", encoding="utf-8").read()
    md2, k = rebuild_readme(md, m)
    if k and md2 != md:
        open("README.md", "w", encoding="utf-8").write(md2)
        changed += 1
        print("обновлён README.md")
    print("ПУЛЬС:", json.dumps({k: v for k, v in m.items() if k != "msk"}, ensure_ascii=False),
          "| срез:", m["msk"].strftime("%Y-%m-%d %H:%M МСК"), "| правок:", changed)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("пульс мягко отступил (файлы не тронуты):", str(e)[:200])
        sys.exit(0)
