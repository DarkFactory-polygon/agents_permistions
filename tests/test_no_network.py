"""BEH-24: работа без сети (DEL-30, DEL-31)."""

import ast
import os
import subprocess
import sys

from conftest import CLI, days_from_today

ALLOWED_IMPORTS = {"sys", "datetime", "dataclasses", "enum", "pathlib", "yaml"}


def _calls(make_registry, bad_path):
    ok = make_registry(
        [
            {
                "agent": "bot",
                "resource": "db",
                "action": "read",
                "granted_by": "admin",
                "until": days_from_today(3).isoformat(),
            }
        ]
    )
    return [
        ["check", "bot", "read", "db", "--file", str(ok)],
        ["check", "bot", "write", "db", "--file", str(ok)],
        ["expired", "--file", str(ok)],
        ["check", "bot", "read", "db", "--file", str(bad_path)],
        ["check"],
        ["--help"],
    ]


# Блокировка сети на уровне процесса: любая попытка соединения или открытия порта — исключение.
BLOCKER = """
import runpy, socket, sys
def _deny(*a, **k):
    sys.stderr.write("NETWORK-ATTEMPT\\n")
    raise SystemExit(99)
socket.socket.connect = _deny
socket.socket.connect_ex = _deny
socket.socket.bind = _deny
socket.socket.listen = _deny
socket.getaddrinfo = _deny
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def _run(args, tmp_path, blocked):
    cmd = [sys.executable, str(CLI), *args]
    if blocked:
        cmd = [sys.executable, "-c", BLOCKER, str(CLI), *args]
    env = {**os.environ, "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9"}
    if not blocked:
        env = dict(os.environ)
    proc = subprocess.run(
        cmd, check=False, cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", env=env
    )
    return proc.stdout + proc.stderr, proc.returncode


def test_same_output_and_code_with_and_without_network(make_registry, tmp_path):
    calls = _calls(make_registry, tmp_path / "missing.yaml")
    for args in calls:
        normal = _run(args, tmp_path, blocked=False)
        offline = _run(args, tmp_path, blocked=True)
        assert normal == offline, args
        assert "NETWORK-ATTEMPT" not in offline[0]


def test_no_network_primitives_used(make_registry, tmp_path):
    """Ни одного сетевого вызова за все сценарии (код выхода 99 — попытка соединения)."""
    for args in _calls(make_registry, tmp_path / "missing.yaml"):
        out, code = _run(args, tmp_path, blocked=True)
        assert code != 99, (args, out)


def test_blocker_actually_blocks(tmp_path):
    """Страховка: блокировщик действительно срабатывает на сокете."""
    script = tmp_path / "probe.py"
    script.write_text("import socket\nsocket.socket().connect(('127.0.0.1', 9))\n")
    proc = subprocess.run(
        [sys.executable, "-c", BLOCKER, str(script)], check=False, capture_output=True, text=True
    )
    assert proc.returncode == 99
    assert "NETWORK-ATTEMPT" in proc.stderr


def test_working_module_imports_only_allowed():
    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            names.add((node.module or "").split(".")[0])
    assert names <= ALLOWED_IMPORTS, names - ALLOWED_IMPORTS
    forbidden = {"socket", "urllib", "http", "subprocess", "tempfile", "requests", "ssl"}
    assert not names & forbidden

