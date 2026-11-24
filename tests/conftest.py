"""Общая оснастка: реестр во временном каталоге, даты от сегодняшней, запуск подпроцессом."""

import datetime
import os
import subprocess
import sys
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parent.parent / "permissions_cli.py"
sys.path.insert(0, str(CLI.parent))


def days_from_today(delta: int) -> datetime.date:
    """Дата относительно текущей локальной даты."""
    return datetime.date.today() + datetime.timedelta(days=delta)


@pytest.fixture
def make_registry(tmp_path):
    """Фабрика реестра: записи — словари с ключами agent, resource, action, granted_by, until."""

    def make(entries: list[dict], name: str = "permissions.yaml") -> Path:
        lines = ["permissions:"] if entries else ["permissions: []"]
        for entry in entries:
            first = True
            for key, value in entry.items():
                lines.append(f"  {'-' if first else ' '} {key}: {value}")
                first = False
        path = tmp_path / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    return make


@pytest.fixture
def run_cli(tmp_path):
    """Запуск команды подпроцессом: (объединённый вывод, код выхода)."""

    def run(*args: str, cwd: Path | None = None) -> tuple[str, int]:
        proc = subprocess.run(
            [sys.executable, str(CLI), *args],
            check=False,
            cwd=cwd or tmp_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return proc.stdout + proc.stderr, proc.returncode

    return run


# Каталоги, которые меняют сторонние процессы (кэши, VCS, окружение, журналы исполнителя).
_INVENTORY_SKIP = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__", "spec"}


def inventory(root: Path) -> dict[str, tuple[int, int]]:
    """Снимок места: относительный путь -> (размер, st_mtime_ns) для файлов и каталогов."""
    snap: dict[str, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _INVENTORY_SKIP]
        for name in [*dirnames, *filenames]:
            full = Path(dirpath) / name
            try:
                st = full.lstat()
            except OSError:
                continue
            snap[str(full.relative_to(root))] = (st.st_size, st.st_mtime_ns)
    return snap


@pytest.fixture
def snapshot_places(tmp_path, monkeypatch):
    """Функция снимка инвентаря трёх мест: рабочий каталог, домашний каталог, каталог установки.

    Рабочий и домашний каталоги — изолированные каталоги во временной области; HOME
    подменяется для запускаемых процессов.
    """
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(work)

    def snap() -> dict[str, dict[str, tuple[int, int]]]:
        return {
            "cwd": inventory(work),
            "home": inventory(home),
            "install": inventory(CLI.parent),
        }

    snap.work = work
    snap.home = home
    return snap


@pytest.fixture
def fake_today(monkeypatch):
    """Подмена шва даты в текущем процессе: fake_today(date) задаёт «сегодня» для main()."""
    import permissions_cli

    def set_date(value: datetime.date) -> None:
        monkeypatch.setattr(permissions_cli, "today", lambda: value)

    return set_date


@pytest.fixture
def call_main(capsys):
    """Вызов main(argv) в текущем процессе: (stdout + stderr, код выхода)."""
    import permissions_cli

    def call(*args: str) -> tuple[str, int]:
        code = permissions_cli.main(list(args))
        captured = capsys.readouterr()
        return captured.out + captured.err, code

    return call
