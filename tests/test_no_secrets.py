"""BEH-28: инструмент не требует и не выводит секретов (DEL-40, DEL-41)."""

import ast
import os
import re
import subprocess
import sys

import pytest
from conftest import CLI, days_from_today

FIELDS = {"agent", "resource", "action", "granted_by", "until"}
SECRET_RE = re.compile(
    r"passw|passwd|token|secret|credential|api[_ -]?key|private[_ -]?key|auth|"
    r"парол|токен|секрет|учётн|учетн|ключ доступа|api-ключ",
    re.IGNORECASE,
)


def _registry(make_registry):
    entry = {
        "agent": "bot",
        "resource": "db",
        "action": "read",
        "granted_by": "admin",
        "until": days_from_today(3).isoformat(),
    }
    expired = {**entry, "agent": "old", "until": days_from_today(-2).isoformat()}
    return make_registry([entry, expired])


def _calls(path):
    return [
        ["--help"],
        ["check", "bot", "read", "db", "--file", str(path)],
        ["check", "bot", "write", "db", "--file", str(path)],
        ["check", "old", "read", "db", "--file", str(path)],
        ["expired", "--file", str(path)],
    ]


def _run(args, tmp_path, env=None, stdin=subprocess.DEVNULL):
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        stdin=stdin,
        timeout=30,
    )
    return proc.stdout + proc.stderr, proc.returncode


def test_help_and_outputs_have_no_secret_words(make_registry, tmp_path):
    for args in _calls(_registry(make_registry)):
        out, _ = _run(args, tmp_path)
        assert not SECRET_RE.search(out), (args, SECRET_RE.search(out).group(0))


def test_help_describes_only_five_record_fields(run_cli):
    out, code = run_cli("--help")
    assert code == 0
    block = out.split("пять ключей:")[1].split("Коды выхода")[0]
    listed = set(re.findall(r"^  (\w+)\s", block, re.MULTILINE))
    assert listed == FIELDS


@pytest.mark.parametrize("flag", ["--password", "--token", "--key", "--secret", "--api-key"])
def test_secret_arguments_are_not_accepted(flag, make_registry, tmp_path):
    path = _registry(make_registry)
    out, code = _run(["check", "bot", "read", "db", "--file", str(path), flag, "x"], tmp_path)
    assert code == 2
    assert "неизвестный параметр" in out


def test_secret_environment_variables_do_not_change_behavior(make_registry, tmp_path):
    path = _registry(make_registry)
    secret_env = {
        **os.environ,
        "PASSWORD": "hunter2",
        "TOKEN": "tok-123",
        "API_KEY": "key-456",
        "SECRET": "s3cr3t",
    }
    for args in _calls(path):
        plain = _run(args, tmp_path, env=dict(os.environ))
        with_env = _run(args, tmp_path, env=secret_env)
        assert plain == with_env, args
        for value in ("hunter2", "tok-123", "key-456", "s3cr3t"):
            assert value not in with_env[0]


def test_commands_never_read_stdin(make_registry, tmp_path):
    """Закрытый stdin и stdin с «паролем» дают один и тот же результат: ввода не ждут."""
    path = _registry(make_registry)
    for args in _calls(path):
        closed = _run(args, tmp_path)
        proc = subprocess.run(
            [sys.executable, str(CLI), *args],
            check=False,
            cwd=tmp_path,
            input="hunter2\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert closed == (proc.stdout + proc.stderr, proc.returncode), args
        assert "hunter2" not in proc.stdout + proc.stderr


def test_source_has_no_credential_prompts_or_env_reads():
    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    imported = set()
    calls = set()
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node, ast.Attribute):
            attrs.add(node.attr)
    assert not imported & {"getpass", "os", "keyring", "socket", "urllib", "http", "requests"}
    assert "input" not in calls
    assert not attrs & {"environ", "getenv", "stdin"}
