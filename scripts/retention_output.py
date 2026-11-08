#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Волна ×4 · П49 (rtynbirf#4): retention output-ветки (подрезка змейки-коммитов).

Правило: коммиты ветки `output` (SVG змейки) старше 90 дней подрезаются шагом CI.
Правило дома №1 «Печать до разрушения»: перед подрезкой печатается SHA256-манифест
подрезаемых SHA (в вывод и в $GITHUB_STEP_SUMMARY). Без устаревших коммитов — зелёный
no-op (ритм без шума). Подрезка выполняется только при RETENTION_ALLOW_PRUNE=1.

Режимы:
  --max-age-days N [--apply]   осмотр/подрезка ветки output
  --selftest                   самоиспытание (без сети)

Только stdlib. Токен — env GITHUB_TOKEN, никуда не пишется.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

REPO = "rtynbirf/rtynbirf"
BRANCH = "output"
API = "https://api.github.com"
UA = "poly-mat-w4f2-retention"


def http_json(url, token):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Authorization": "Bearer %s" % token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def list_output_commits(token):
    out, page = [], 1
    while page <= 5:
        batch = http_json("%s/repos/%s/commits?sha=%s&per_page=100&page=%d" % (API, REPO, BRANCH, page), token)
        if not batch:
            break
        out.extend(batch)
        page += 1
    return [
        {"sha": c["sha"], "date": c["commit"]["committer"]["date"], "msg": c["commit"]["message"].splitlines()[0]}
        for c in out
    ]


def select_stale(commits, max_age_days, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    stale = []
    for c in commits:
        d = datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
        if d < cutoff:
            stale.append(c)
    return sorted(stale, key=lambda x: x["date"])


def manifest(shas):
    return hashlib.sha256("\n".join(sorted(shas)).encode()).hexdigest()


def seal(shas, max_age_days):
    m = manifest([c["sha"] for c in shas])
    lines = ["## 🗡 retention output · печать до разрушения",
             "Порог: %d дней. Подрезается %d коммит(ов)." % (max_age_days, len(shas)),
             "", "```", "manifest-sha256: %s" % m, ""]
    lines += ["%s %s %s" % (c["sha"][:12], c["date"], c["msg"][:50]) for c in shas]
    lines.append("```")
    text = "\n".join(lines)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return m


def git(*args):
    subprocess.run(["git"] + list(args), check=True)


def prune(stale, max_age_days, do_apply):
    m = seal(stale, max_age_days)
    if not do_apply:
        print("DRY-RUN: подрезка не выполнялась (для исполнения --apply и RETENTION_ALLOW_PRUNE=1)")
        return
    if os.environ.get("RETENTION_ALLOW_PRUNE") != "1":
        raise SystemExit("подрезка запрещена: нет RETENTION_ALLOW_PRUNE=1")
    subprocess.run(["git", "config", "user.name", "retention[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
    git("checkout", "--orphan", "retention-prune")
    git("add", "-A")
    subprocess.run(["git", "commit", "-m",
                    "retention: подрезка output — %d коммит(ов) старше %d дн (manifest %s) [skip ci]"
                    % (len(stale), max_age_days, m[:12])], check=True)
    git("push", "origin", "HEAD:%s" % BRANCH, "--force")
    print("pruned=%d manifest=%s — output пересобран свежим orphan-коммитом" % (len(stale), m[:12]))


def selftest():
    now = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
    commits = [
        {"sha": "a" * 40, "date": "2026-05-01T00:00:00Z", "msg": "старый"},
        {"sha": "b" * 40, "date": "2026-11-01T00:00:00Z", "msg": "свежий"},
        {"sha": "c" * 40, "date": (now - timedelta(days=90, minutes=1)).isoformat().replace("+00:00", "Z"), "msg": "ровно 90+1мин"},
        {"sha": "d" * 40, "date": (now - timedelta(days=89)).isoformat().replace("+00:00", "Z"), "msg": "89 дней — жив"},
    ]
    stale = select_stale(commits, 90, now=now)
    assert [c["sha"][0] for c in stale] == ["a", "c"], "граница 90 дней сломана"
    m1 = manifest([c["sha"] for c in stale])
    m2 = manifest([c["sha"] for c in reversed(stale)])
    assert m1 == m2, "манифест зависит от порядка"
    assert len(select_stale(commits, 10, now=now + timedelta(days=400))) == 4, "порог растёт — режется всё"
    assert select_stale(commits, 400, now=now) == [], "свежие коммиты не режутся"
    print("✓ граница 90 дней: старше — режем, младше — жив")
    print("✓ SHA256-манифест не зависит от порядка")
    print("SELFTEST: OK")


def main():
    ap = argparse.ArgumentParser(description="retention output-ветки (П49)")
    ap.add_argument("--max-age-days", type=int, default=90)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("нет GITHUB_TOKEN в env")
    commits = list_output_commits(token)
    print("✓ ветка %s: коммитов %d" % (BRANCH, len(commits)))
    stale = select_stale(commits, args.max_age_days)
    if not stale:
        print("pruned=0 — подрезать нечего (свежий orphan, ритм без шума)")
        return
    prune(stale, args.max_age_days, args.apply)


if __name__ == "__main__":
    main()
