"""Реестр прав агентов: проверка права и список истекающих прав."""

import sys
from dataclasses import dataclass

DEFAULT_FILE = "permissions.yaml"

USAGE = (
    "использование: python permissions_cli.py check <агент> <действие> <ресурс> [--file ПУТЬ] | "
    "python permissions_cli.py expired [--file ПУТЬ]"
)

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
                raise UsageError(f"ошибка вызова: у --file нет значения. {USAGE}")
            file = value
        elif token.startswith("--file="):
            file = token.split("=", 1)[1]
        elif token.startswith("-") and token != "-":
            raise UsageError(f"ошибка вызова: неизвестный параметр {token}. {USAGE}")
        else:
            positional.append(token)
    if not positional:
        raise UsageError(f"ошибка вызова: не указана команда. {USAGE}")
    command, args = positional[0], tuple(positional[1:])
    if command == "check":
        if len(args) != 3:
            raise UsageError(
                f"ошибка вызова: check принимает три аргумента (агент, действие, ресурс), "
                f"получено {len(args)}. {USAGE}"
            )
    elif command == "expired":
        if args:
            raise UsageError(f"ошибка вызова: expired не принимает аргументов. {USAGE}")
    else:
        raise UsageError(f"ошибка вызова: неизвестная команда {command!r}. {USAGE}")
    return Invocation(command=command, args=args, file=file)


def main(argv: list[str]) -> int:
    try:
        invocation = parse_invocation(argv)
        if invocation.help:
            print(HELP, end="")
            return 0
        raise UsageError("команда ещё не реализована")
    except UsageError as failure:
        print(str(failure).replace("\n", " "), file=sys.stderr)
        return 2
    except Exception as failure:  # noqa: BLE001 — fail-closed: без трассировки, одна строка
        print(f"внутренняя ошибка: {type(failure).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
