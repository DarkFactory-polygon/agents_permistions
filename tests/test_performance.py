"""BEH-26: ответ на реестре из 1000 записей — не дольше 2 секунд (DEL-36, DEL-37)."""

import subprocess
import sys
import time

import pytest
from conftest import CLI, days_from_today

THRESHOLD_SECONDS = 2.0
ENTRIES = 1000
CALLS = 10


@pytest.fixture
def big_registry(make_registry):
    entries = [
        {
            "agent": f"agent-{i}",
            "resource": f"res-{i % 50}",
            "action": ("read", "write", "delete")[i % 3],
            "granted_by": f"admin-{i % 7}",
            "until": days_from_today((i % 40) - 15).isoformat(),
        }
        for i in range(ENTRIES)
    ]
    return make_registry(entries)


def _timed(tmp_path, *args):
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return time.perf_counter() - start, proc


def _leftovers(marker: str) -> list[str]:
    out = subprocess.run(
        ["ps", "-axo", "command"], capture_output=True, text=True, check=False
    ).stdout
    return [line for line in out.splitlines() if marker in line and "ps -axo" not in line]


def test_check_within_threshold(big_registry, tmp_path):
    for i in range(CALLS):
        elapsed, proc = _timed(
            tmp_path,
            "check",
            f"agent-{i * 99}",
            ("read", "write", "delete")[(i * 99) % 3],
            f"res-{(i * 99) % 50}",
            "--file",
            str(big_registry),
        )
        assert proc.returncode in (0, 1), proc.stderr
        assert proc.stdout.strip(), "ответ должен появиться в том же вызове"
        assert elapsed <= THRESHOLD_SECONDS, f"вызов {i}: {elapsed:.2f} с"


def test_expired_within_threshold(big_registry, tmp_path):
    for i in range(CALLS):
        elapsed, proc = _timed(tmp_path, "expired", "--file", str(big_registry))
        assert proc.returncode == 0, proc.stderr
        assert "Просроченные:" in proc.stdout
        assert "агент: agent-" in proc.stdout
        assert elapsed <= THRESHOLD_SECONDS, f"вызов {i}: {elapsed:.2f} с"


def test_no_process_left_after_exit(big_registry, tmp_path):
    marker = str(big_registry)
    for args in (
        ("check", "agent-1", "write", "res-1", "--file", marker),
        ("expired", "--file", marker),
    ):
        _, proc = _timed(tmp_path, *args)
        assert proc.returncode in (0, 1)
        assert _leftovers(marker) == []
