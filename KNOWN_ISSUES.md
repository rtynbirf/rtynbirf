# KNOWN ISSUES · rtynbirf (профиль-репо) — известные красные и шрамы
> Снимок Волны ×5 (2026-11-09). Живые красные прогоны + известные квирки.

| Что | Статус | Детали | Run/ссылка |
|---|---|---|---|
| swarm-health 20:16 (push ca540b0) | 🟢 вылечено | бот-пуш rejected «fetch first»: параллельные пушы в main + серия диспатчей в одном окне | [42519287437](https://github.com/rtynbirf/rtynbirf/actions/runs/42519287437) |
| swarm-health 20:20 (dispatch 35e1379) | 🟢 вылечено | та же гонка | [42519621376](https://github.com/rtynbirf/rtynbirf/actions/runs/42519621376) |
| swarm-health 20:22 (dispatch 8bc2bb6) | 🟢 вылечено | та же гонка | [42519758019](https://github.com/rtynbirf/rtynbirf/actions/runs/42519758019) |
| swarm-health 20:22 (dispatch 2a6705d) | 🟢 вылечено | та же гонка | [42519802534](https://github.com/rtynbirf/rtynbirf/actions/runs/42519802534) |
| swarm-health 20:24 (dispatch 8d4da5f) | 🟢 вылечено | та же гонка | [42519969481](https://github.com/rtynbirf/rtynbirf/actions/runs/42519969481) |
| зелёный предок серии | ✅ живой прогон | диспатч на 06d71d0 прошёл после снятия гонки | [42519995571](https://github.com/rtynbirf/rtynbirf/actions/runs/42519995571) |
| патч: pull --rebase перед бот-пушем | ✅ в main | Волна ×5, commit 46c4fe2 — бот-коммит больше не падает от «fetch first» | .github/workflows/swarm-health.yml |
| Квирк: GITHUB_TOKEN квоты API | ℹ️ внешний сервис | при исчерпании API-квоты ран краснеет честно — это не баг скрипта | scripts/health_badges.py |
