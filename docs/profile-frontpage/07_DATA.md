# Модель динамических данных

Одна метрика — один канонический источник. Все виджеты и текстовые представления читают один и тот же generated output.

## Контракт
`metric_id`, `value`, `unit`, `definition`, `source`, `generated_at`, `scope`, `method_version`, `status`.

## Свежесть
FRESH, STALE, SOURCE_UNAVAILABLE, UNKNOWN, INVALID. Просроченное значение нельзя показывать как текущее.

## СИНГУЛЯР
Разделять основной каталог, фонд, опубликованные материалы и экспериментальные материалы. Для языков — `ready_languages`, `pipeline_languages`, `target_languages`.

## Polymath OS
Разделять runtime tests, unit tests, integration tests, claim verification checks, agent self-tests и external audits.

## Fallback
Если источник недоступен: показать последнее значение с датой и STALE либо UNKNOWN. Не подставлять ручное число.
