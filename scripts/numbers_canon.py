#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""КАНОН ПЯТИ ЧИСЕЛ — клетка роя: сверка панели 3D-SVG с живым GraphQL.
Число в доме = измерение. Срез зависит от замков: репо под замком на момент
прогона даёт заниженные числа, поэтому канон меряет под SWARM_TOKEN (полный обзор).
Артефакт: swarm_numbers.json. Честный красный: сумма пяти ≠ календарю GraphQL.
Запись — в рабочую копию, коммит делает workflow-шаг."""
import json, os, re, sys, time, urllib.request, datetime

API = "https://api.github.com"
OWNER, REPO = "rtynbirf", "rtynbirf"
SVG = "profile-3d-contrib/profile-night-rainbow.svg"

READ_TOK = os.environ.get("SWARM_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not READ_TOK:
    sys.exit("нет токенов: SWARM_TOKEN/GITHUB_TOKEN")

def hdr(auth=True):
    h = {"User-Agent": "numbers-canon", "Accept": "application/vnd.github+json"}
    if auth:
        h["Authorization"] = f"token {READ_TOK}"
    return h

def req(url, method="GET", payload=None, auth=True):
    r = urllib.request.Request(url, method=method,
                               data=json.dumps(payload).encode() if payload is not None else None,
                               headers=hdr(auth))
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return (json.loads(raw) if raw.strip() else {})

def graphql_five():
    """Пять сумм + календарь за скользящий год под полным токеном (замки не режут)."""
    to = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    frm = to - datetime.timedelta(days=364)
    q = """query($l:String!,$f:DateTime!,$t:DateTime!){
      user(login:$l){ contributionsCollection(from:$f,to:$t){
        totalCommitContributions totalIssueContributions totalPullRequestContributions
        totalPullRequestReviewContributions totalRepositoryContributions
        restrictedContributionsCount contributionCalendar{ totalContributions } } } }"""
    r = req("https://api.github.com/graphql", method="POST",
            payload={"query": q, "variables": {"l": OWNER, "f": frm.isoformat(), "t": to.isoformat()}})
    if "errors" in r:
        raise RuntimeError("graphql: " + json.dumps(r["errors"])[:200])
    cc = r["data"]["user"]["contributionsCollection"]
    five = {
        "Commit": cc["totalCommitContributions"],
        "Issue": cc["totalIssueContributions"],
        "PullReq": cc["totalPullRequestContributions"],
        "Review": cc["totalPullRequestReviewContributions"],
        "Repo": cc["totalRepositoryContributions"],
    }
    return five, cc["contributionCalendar"]["totalContributions"], cc["restrictedContributionsCount"], frm, to

def public_search(frm, to):
    """Публичная перекрёстная сверка (search API) — то, что видит гость."""
    w = f"{frm.date().isoformat()}..{to.date().isoformat()}"

    def total(q, commits=False):
        try:
            return req(f"{API}/search/{'commits' if commits else 'issues'}?q={q}&per_page=1",
                       auth=commits).get("total_count")
        except Exception:
            return None

    prs = total(f"author:{OWNER}+type:pr+created:{w}")
    time.sleep(2)
    iss = total(f"author:{OWNER}+type:issue+created:{w}")
    time.sleep(2)
    com = total(f"author:{OWNER}+author-date:{w}", commits=True)
    time.sleep(2)
    rep = req(f"{API}/search/repositories?q=user:{OWNER}+fork:false+created:{w}&per_page=1").get("total_count")
    return {"Commit": com, "Issue": iss, "PullReq": prs, "Repo": rep, "window": w}

def svg_panel(path):
    """Панель SVG: пять чисел, сумма, период. Если файла нет — мягкий пропуск."""
    if not os.path.exists(path):
        return None
    s = open(path, encoding="utf-8").read()
    texts = [t.strip() for t in re.findall(r">([^<>]+)<", s) if t.strip()]
    out, keys = {}, ["Commit", "Issue", "PullReq", "Review", "Repo"]
    try:
        for k in keys:
            j = texts.index(k)
            out[k] = int(texts[j + 1])
        out["total"] = int(texts[texts.index("contributions") - 1])
        out["period"] = texts[texts.index("contributions") + 1]
    except (ValueError, IndexError):
        return None
    return out

def main():
    five, cal_total, restricted, frm, to = graphql_five()
    sum5 = sum(five.values())
    pub = public_search(frm, to)
    panel = svg_panel(os.environ.get("GITHUB_WORKSPACE", ".") + "/" + SVG)

    inv_ok = (sum5 == cal_total)
    if not inv_ok:
        print(f"КОНТРРАЗУМ: сумма пяти {sum5} ≠ календарь {cal_total} — источник врёт себе")
    print(f"КАНОН (скользящий год {frm.date()}..{to.date()}): "
          + " ".join(f"{k}={v}" for k, v in five.items())
          + f" | сумма={sum5} | календарь={cal_total} | приватные={restricted}")
    print("ПУБЛИЧНАЯ СВЕРКА:", json.dumps({k: v for k, v in pub.items() if k != "window"}, ensure_ascii=False))

    svg_verdict = None
    if panel:
        age = (to.date() - datetime.date.fromisoformat(panel["period"].split("/")[-1].strip())).days
        deltas = {k: five[k] - panel[k] for k in five}
        svg_verdict = {
            "period": panel["period"], "age_days": age, "panel": {k: panel[k] for k in five},
            "panel_total": panel["total"], "panel_sum_check": sum(panel[k] for k in five) == panel["total"],
            "delta_vs_canon": deltas,
            "verdict": ("свежий" if age <= 1 else
                        "свежий, срез под замками" if age <= 2 and any(v > 0 for v in deltas.values()) else
                        f"устарел на {age} дн — заводится ЗАВОДНЫМ КЛЮЧОМ / кроном 3d-contrib"),
        }
        print("SVG-ПАНЕЛЬ:", json.dumps(svg_verdict, ensure_ascii=False))

    ws = os.environ.get("GITHUB_WORKSPACE") or "."
    art = {
        "schema": "swarm_numbers/1",
        "generated_at": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"from": frm.date().isoformat(), "to": to.date().isoformat()},
        "graphql": {"five": five, "sum_of_five": sum5, "calendar_total": cal_total,
                    "restricted": restricted, "invariant_sum5_eq_calendar": inv_ok},
        "public_search": pub,
        "svg_panel": svg_verdict,
    }
    out = os.path.join(ws, "swarm_numbers.json")
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    new = json.dumps(art, ensure_ascii=False, indent=2)
    if old == new:
        print("канон не изменился — запись не нужна (анти-шум)")
    else:
        open(out, "w", encoding="utf-8").write(new + "\n")
        print("swarm_numbers.json обновлён")
    if not inv_ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
