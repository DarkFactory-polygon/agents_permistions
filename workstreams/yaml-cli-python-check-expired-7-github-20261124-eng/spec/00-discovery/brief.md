---
schema: discovery-brief
schema_version: 1
spec_stage: discovery
status: draft
generated_by: discovery-runtime
generated_at: '2026-11-24T08:34:26Z'
validation: pass
interview:
  frame: engineer
  sessions:
  - participant_role: customer
coverage:
  systems: covered
  interfaces: covered
  constraints: covered
  arch_preferences: covered
  risks: covered
  feasibility_review: covered
  gate_passed: true
open_questions: 1
blocking_open_questions: 0
conflicts: 0
traces_to:
- upstream.md
---

# Discovery Brief — DarkFactory-polygon/agents_permistions (engineer-фрейм)

## Constraints

- **CON-01** Нельзя: сеть, запись файлов, секреты в реестре. Запуск только на ПК пользователя.
- **CON-02** Платного нет. Стек: Python 3.12 или новее и одна библиотека для YAML (PyYAML).
- **CON-03** «Сегодня» — локальная дата компьютера. Код выхода expired без ошибок — 0.

## System Assessment

- **S-01** YAML-файл прав на ПК пользователя: единственное хранилище, владелец — пользователь. Файл пока не существует, меняется вручную, объём неизвестен.
- **S-02** CLI на Python: программа с командами check и expired, владелец — пользователь.
- **S-03** Системы, где права выдаются на самом деле (GitHub, облака): инструмент с ними не связан.
- **S-04** Конфиги и переписка: сегодняшний источник сведений о правах, инструмент с ними не связан.

## Interfaces

- **IF-01** Вход CLI: YAML-файл прав и аргументы командной строки. Путь к файлу — параметр --file, по умолчанию permissions.yaml в текущем каталоге.
  traces: [S-01, S-02]
- **IF-02** Выход CLI: текст в терминал и код выхода.
  traces: [S-02]
- **IF-03** Потребитель интерфейса CLI — только сам пользователь, других потребителей нет.
  traces: [S-02]

## Architecture Preferences

- **AP-01** Простой CLI без фреймворков, без базы данных и сервера.
  traces: [S-02]
- **AP-02** Принятых ADR и стандартов, которым новое обязано следовать, нет.
  traces: [S-02]

## Risks

- **RK-01** Истории поломок нет. Грабли: даты в YAML могут читаться как дата или строка, а yes/no превращаются в логические значения.
- **RK-02** Недооценено определение «сегодня»: считать по локальной дате компьютера.
- **RK-03** Всё знает только один человек — пользователь.

## Open Questions

- **Q-01** Какого объёма будет файл прав.
  owner_role: engineer
  blocking: false

## Stakeholder Conflicts

- **X-01** FR-01: реализуемо как есть
  **Target**: FR-01
  status: resolved
- **X-02** FR-02: реализуемо как есть
  **Target**: FR-02
  status: resolved
- **X-03** FR-03: реализуемо как есть
  **Target**: FR-03
  status: resolved
- **X-04** FR-05: реализуемо как есть
  **Target**: FR-05
  status: resolved