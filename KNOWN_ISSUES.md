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
| kick-прогон РЁВО-АВТОМАТ ЦЕНТРАЛЬНЫЙ 23:55 (диспатч СТРАЖА, заход 3) | 🟢 вылечено | kickнул молчащий крон: fast-obhod зелёный, ПОЛНЫЙ ПРОЛЁТ упал на СВЕРКА/КУЗНЯ/ЗАЧИСЛЕНИЕ — гонка с волной зачисления закона (79 AGENTS.md) / давление API; последующие прогоны зелёные | [44840253496](https://github.com/rtynbirf/rtynbirf/actions/runs/44840253496) |
| ЗАВОДНОЙ КЛЮЧ 23:56 (push 071a0b0) | 🟢 вылечено | лог: HTTP 401 на GET workflows — рука роя SWARM_TOKEN протухла; патч: GITHUB_TOKEN + permissions actions:write (прецедент СЕРДЦЕ ТАКТА) | [44840365171](https://github.com/rtynbirf/rtynbirf/actions/runs/44840365171) |
| generate snake 23:56 (push 071a0b0) | 🟢 вылечено | лог: Authentication failed при пуше в output — тот же протухший SWARM_TOKEN; патч: GITHUB_TOKEN + contents:write | [44840365195](https://github.com/rtynbirf/rtynbirf/actions/runs/44840365195) |
| ТЕРМИНАЛ РОЯ 13:02 (schedule) | 🟢 вылечено | лог: HTTP 401 в «Генерация карты» — тот же корень; патч: GITHUB_TOKEN + contents:write, пуш через x-access-token | [44906888136](https://github.com/rtynbirf/rtynbirf/actions/runs/44906888136) |
| Корень трёх красных: секрет SWARM_TOKEN протух | 🔴 открыт | ротация секрета — только хозяином (Settings → Secrets and variables → Actions). Пьют его ещё 5 воркфлоу: 3d-contrib, numbers-canon, pulse, swarm-health, swarm-sync — все молча немеют с 401 | .github/workflows/*.yml |
| Доктор был нем + чурился | 🟢 вылечено | заход 5: реран отклонялся молча (SWARM_TOKEN 401, exit 0) и серия completion-событий давала 13 прогонов за 3 минуты; патч: GITHUB_TOKEN + actions:write, debounce — фиксированная concurrency «doctor» с cancel-in-progress | .github/workflows/self-heal.yml |
| патч: СТРАЖ сторожит себя + крон → раз в час | ✅ в main | заход 4: self-watch — за ночь */23 тикнул ~3 раза вместо ~38 (schedule GitHub best-effort под нагрузкой); крон 23 * * * *, СЕРДЦЕ ТАКТА в CRITICAL | scripts/strazh_spyashchih.py |
