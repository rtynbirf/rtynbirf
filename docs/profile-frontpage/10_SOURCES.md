# Источники и ограничения аудита

Дата просмотра: 2026-11-25.

- https://github.com/rtynbirf
- https://github.com/rtynbirf/rtynbirf
- https://github.com/rtynbirf/polymath-os
- https://github.com/rtynbirf/polymath-os/blob/main/README.md
- https://github.com/rtynbirf/singulyar
- https://github.com/rtynbirf/singulyar/blob/rumu/README.md

Ограничения:
- полный clone не выполнялся;
- `make verify` не запускался;
- тесты СИНГУЛЯРА не запускались;
- все внешние ссылки не проверялись;
- все Actions не проверялись;
- все репозитории аккаунта не анализировались;
- числа — временный публичный срез и могут измениться.

Аудит описывает отображаемое состояние, а не подтверждает корректность исходного кода или CI.

## Мировые источники (сверка захода 7, 2026-11-25)

Проверены поиском и открыты в ходе интеграции:

- GitHub Community Discussion «Best Practices for Optimizing a GitHub Profile» (#154875, 2025-03) —
  https://github.com/orgs/community/discussions/154875 — контекст у пинов, разнообразие подсветки.
- GitHub Docs «Managing your profile README» — https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/customizing-your-profile/managing-your-profile-readme
- Make a README — https://www.makeareadme.com — назначение README, краткость, ссылки вглубь.
- Awesome README (curated list) — https://github.com/matiassingers/awesome-readme — бейджи, структура, визуальная идентичность.
- Utrecht University, Best Practices for Writing Reproducible Code · readme-files —
  https://utrechtuniversity.github.io/workshop-computational-reproducibility/chapters/readme-files.html —
  короткие секции, обновление при изменении проекта, воспроизводимость.

Синтез против мира: ни один из источников не описывает само-свидетельствующуюся витрину
(боты перезаписывают README-блоки из живого API; бейдж читает committed JSON; append-only
ledgers). Это уникальный слой дома; мировая практика потребляет его как «обычные картинки»,
внутри дома каждый блок — клейм со свидетельством (правила 23–28).
