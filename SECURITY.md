# Безопасность (канон роя T21)

Владелец и единственный Хозяин: @rtynbirf.

## Как сообщить об уязвимости

- Приоритетный канал: Private vulnerability reporting этого репо — https://github.com/rtynbirf/rtynbirf/security/advisories/new
- Контур всего роя и политика координации: https://github.com/rtynbirf
- Реестр уроков и практика disclosures: https://github.com/singulyar/rumu

## Границы и реагирование

- Контур: этот репо, его воркфлоу, секреты и артефакты.
- Реагирование: признание инцидента за **24 часа** (контур Э-2.3 / EU CRA reporting в силе с 2026-09-11).
- Ни один токен/секрет не живёт в репо, логах и артефактах (П-35/П-40); найденный — отзыв немедленно.
- Каждый факт — пломба: append-only SEALS.jsonl, журнал не лжёт.

## Автоматический контур безопасности

- Code scanning: CodeQL (default setup, languages: actions + python) — на каждый push и еженедельно; политика дома: 0 открытых алертов в терминальном состоянии.
- OpenSSF Scorecard: еженедельно; алерты доводятся до нуля фиксом первопричины, не дисмиссом (закон дома).
- Secret scanning + push protection: включены. Dependabot security updates: включены.
