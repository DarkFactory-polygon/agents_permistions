"""Общая оснастка: реестр во временном каталоге, даты от сегодняшней, запуск подпроцессом."""

import datetime
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
