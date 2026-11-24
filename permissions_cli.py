"""Реестр прав агентов: проверка права и список истекающих прав."""

import datetime
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_FILE = "permissions.yaml"

USAGE = (
    "использование: python permissions_cli.py check <агент> <действие> <ресурс> [--file ПУТЬ] | "
    "python permissions_cli.py expired [--file ПУТЬ]"
)

# Подсказка для сообщений об ошибке: без имён файлов инструмента.
USAGE_HINT = "ожидается: check <агент> <действие> <ресурс> [--file ПУТЬ] или expired [--file ПУТЬ]"

HELP = f"""\
{USAGE}

Команды:
  check <агент> <действие> <ресурс>  проверить, действует ли право (порядок аргументов:
                                     агент, действие, ресурс); код 0 — разрешено, 1 — запрещено
  expired                            показать просроченные права и истекающие в ближайшие 7 дней

Параметры:
  --file ПУТЬ   файл реестра; по умолчанию {DEFAULT_FILE} в текущем каталоге
  --help        показать эту справку

Формат реестра: YAML-маппинг с ключом permissions, значение — список записей.
Каждая запись содержит пять ключей:
  agent       агент
  resource    ресурс
  action      действие
  granted_by  кто выдал
  until       до какого числа, формат даты YYYY-MM-DD (последний день срока включительно)

Коды выхода: 0, 1, 2 (2 — ошибка вызова или реестра).
"""


class UsageError(Exception):
    """Неверный вызов; несёт готовое сообщение."""


class RegistryError(Exception):
    """Отказ по файлу или записи реестра; несёт готовое сообщение с местом ошибки."""


TEXT_FIELDS = ("agent", "resource", "action", "granted_by")
REQUIRED_FIELDS = ("agent", "resource", "action", "granted_by", "until")


def _is_iso_date_shape(value: str) -> bool:
    """Строго YYYY-MM-DD: четыре цифры, дефис, две цифры, дефис, две цифры (только ASCII)."""
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        return False
    digits = value[:4] + value[5:7] + value[8:]
    return all(ch in "0123456789" for ch in digits)


@dataclass(frozen=True)
class Permission:
    agent: str
    resource: str
    action: str
    granted_by: str
    until: datetime.date
    index: int


class _RegistryLoader(yaml.SafeLoader):
    """SafeLoader, не падающий на невозможной дате: оставляет сырую строку для проверки записи."""


def _construct_timestamp(loader: yaml.SafeLoader, node: yaml.Node):
    try:
        return yaml.SafeLoader.construct_yaml_timestamp(loader, node)
    except ValueError:
        return loader.construct_scalar(node)


_RegistryLoader.add_constructor("tag:yaml.org,2002:timestamp", _construct_timestamp)


def _shape(value: object) -> str:
    if value is None:
        return "пусто"
    if isinstance(value, dict):
        return "маппинг"
    if isinstance(value, list):
        return "список"
    return f"{type(value).__name__}"


def _kind(value: object) -> str:
    if isinstance(value, bool):
        return "логическое значение"
    if value is None:
        return "пустое значение (null)"
    if isinstance(value, int | float):
        return "число"
    if isinstance(value, datetime.datetime | datetime.date):
        return "дата"
    return type(value).__name__


def _parse_until(value: object, where: str) -> datetime.date:
    if isinstance(value, datetime.datetime):
        raise RegistryError(
            f"{where}: поле until содержит дату со временем, нужна дата YYYY-MM-DD"
        )
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and _is_iso_date_shape(value):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            pass
    shown = "пусто" if value is None else repr(value)
    raise RegistryError(
        f"{where}: поле until не календарная дата YYYY-MM-DD (значение: {shown})"
    )


def _validate_entry(raw: object, index: int, path: str) -> Permission:
    where = f"{path}: запись {index}"
    if not isinstance(raw, dict):
        raise RegistryError(f"{where} не маппинг (найдено: {_shape(raw)})")
    for field in REQUIRED_FIELDS:
        if field not in raw:
            raise RegistryError(f"{where}: нет обязательного поля {field}")
    for field in TEXT_FIELDS:
        if not isinstance(raw[field], str):
            raise RegistryError(
                f"{where}: поле {field} прочитано не как строка ({_kind(raw[field])}); "
                f"возьмите значение в кавычки"
            )
    return Permission(
        agent=raw["agent"],
        resource=raw["resource"],
        action=raw["action"],
        granted_by=raw["granted_by"],
        until=_parse_until(raw["until"], where),
        index=index,
    )


def load_registry(path: str) -> list[Permission]:
    """Читает и полностью проверяет реестр: весь список либо отказ на первой неверной записи."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        shown = str(Path.cwd() / path) if path == DEFAULT_FILE else path
        raise RegistryError(f"файл реестра не найден: {shown}") from None
    except UnicodeDecodeError:
        raise RegistryError(
            f"{path}: файл не читается (содержимое не в кодировке UTF-8)"
        ) from None
    except OSError as failure:
        reason = failure.strerror or "ошибка чтения"
        raise RegistryError(f"{path}: файл не читается ({reason})") from None
    try:
        data = yaml.load(text, Loader=_RegistryLoader)
    except yaml.YAMLError as failure:
        mark = getattr(failure, "problem_mark", None)
        place = (
            f"строка {mark.line + 1}, столбец {mark.column + 1}"
            if mark
            else "место не названо"
        )
        problem = getattr(failure, "problem", None) or "ошибка разбора YAML"
        raise RegistryError(
            f"{path}: YAML не разбирается ({place}): {problem}"
        ) from None
    if data is None:
        return []
    if not isinstance(data, dict):
        raise RegistryError(
            f"{path}: верхний уровень должен быть маппингом с ключом permissions "
            f"(найдено: {_shape(data)})"
        )
    if not data:
        return []
    if "permissions" not in data:
        raise RegistryError(
            f"{path}: нет ключа permissions (найдены ключи: "
            f"{', '.join(map(str, data))})"
        )
    entries = data["permissions"]
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise RegistryError(
            f"{path}: permissions должен быть списком записей (найдено: {_shape(entries)})"
        )
    return [_validate_entry(raw, i, path) for i, raw in enumerate(entries, start=1)]


@dataclass(frozen=True)
class Invocation:
    command: str
    args: tuple[str, ...]
    file: str = DEFAULT_FILE
    help: bool = False


def parse_invocation(argv: list[str]) -> Invocation:
    if "--help" in argv:
        return Invocation(command="", args=(), help=True)
    positional: list[str] = []
    file = DEFAULT_FILE
    it = iter(argv)
    for token in it:
        if token == "--file":
            value = next(it, None)
            if value is None:
                raise UsageError(f"ошибка вызова: у --file нет значения. {USAGE_HINT}")
            file = value
        elif token.startswith("--file="):
            file = token.split("=", 1)[1]
        elif token.startswith("-") and token != "-":
            raise UsageError(
                f"ошибка вызова: неизвестный параметр {token}. {USAGE_HINT}"
            )
        else:
            positional.append(token)
    if not positional:
        raise UsageError(f"ошибка вызова: не указана команда. {USAGE_HINT}")
    command, args = positional[0], tuple(positional[1:])
    if command == "check":
        if len(args) != 3:
            raise UsageError(
                f"ошибка вызова: check принимает три аргумента (агент, действие, ресурс), "
                f"получено {len(args)}. {USAGE_HINT}"
            )
    elif command == "expired":
        if args:
            raise UsageError(
                f"ошибка вызова: expired не принимает аргументов. {USAGE_HINT}"
            )
    else:
        raise UsageError(
            f"ошибка вызова: неизвестная команда {command!r}. {USAGE_HINT}"
        )
    return Invocation(command=command, args=args, file=file)


EXPIRY_WINDOW_DAYS = 7


def run_check(
    permissions: list[Permission], args: tuple[str, ...], today: datetime.date
) -> int:
    agent, action, resource = args
    matching = [
        p
        for p in permissions
        if (p.agent, p.action, p.resource) == (agent, action, resource)
    ]
    for p in matching:
        if p.until >= today:
            print(f"разрешено: выдал {p.granted_by}, до {p.until.isoformat()}")
            return 0
    reason = "срок истёк" if matching else "записи нет"
    print(f"запрещено: {reason}")
    return 1


def _format_row(p: Permission) -> str:
    return (
        f"  агент: {p.agent}; ресурс: {p.resource}; действие: {p.action}; "
        f"выдал: {p.granted_by}; до: {p.until.isoformat()}"
    )


def run_expired(permissions: list[Permission], today: datetime.date) -> int:
    limit = today + datetime.timedelta(days=EXPIRY_WINDOW_DAYS)
    overdue = [p for p in permissions if p.until < today]
    soon = [p for p in permissions if today <= p.until <= limit]
    lines = ["Просроченные:"]
    lines += [_format_row(p) for p in overdue] or ["  (нет)"]
    lines += ["", f"Истекающие в ближайшие {EXPIRY_WINDOW_DAYS} дней:"]
    lines += [_format_row(p) for p in soon] or ["  (нет)"]
    print("\n".join(lines))
    return 0


def main(argv: list[str]) -> int:
    try:
        invocation = parse_invocation(argv)
        if invocation.help:
            print(HELP, end="")
            return 0
        permissions = load_registry(invocation.file)
        today = datetime.date.today()
        if invocation.command == "check":
            return run_check(permissions, invocation.args, today)
        return run_expired(permissions, today)
    except (UsageError, RegistryError) as failure:
        print(str(failure).replace("\n", " "), file=sys.stderr)
        return 2
    except Exception as failure:  # noqa: BLE001 — fail-closed: без трассировки, одна строка
        print(f"внутренняя ошибка: {type(failure).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
