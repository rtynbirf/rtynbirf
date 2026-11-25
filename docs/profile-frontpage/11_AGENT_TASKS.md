# Задание агентам

Цель: безопасно модернизировать `rtynbirf/rtynbirf` по ТЗ.

- A1 Repository Scout: read-only inventory, HEAD/default branch, baseline.
- A2 Claim Auditor: извлечь метрики и утверждения; отметить VERIFIED/UNKNOWN/STALE/INCONSISTENT.
- A3 Information Architect: сопоставить блоки текущего README с новой структурой; не терять уникальные смыслы.
- A4 README Editor: подготовить README без неподтверждённых чисел.
- A5 Validator: ссылки, Markdown, заголовки, alt, сценарии T1–T7.
- A6 Independent Reviewer: независимо проверить diff, доказательства и потерю смыслов.

Протокол: INVENTORY → CLAIMS → INFORMATION_MAP → DRAFT → VALIDATE → INDEPENDENT_REVIEW → HUMAN_APPROVAL → PUBLISH.

До отдельного разрешения все операции read-only. Запрещены push, merge, delete, force-push и изменения исходников других репозиториев. UNKNOWN не превращать в PASS.
