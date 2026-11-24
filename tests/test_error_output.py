"""BEH-15, BEH-16, BEH-17, DEL-29: отказы по файлу и форма сообщения об ошибке."""

import os
import stat

import pytest
from conftest import days_from_today

ENTRY = {
    "agent": "bot",
    "resource": "db",
    "action": "read",
    "granted_by": "alice",
}


def valid_entry(**over):
    return {**ENTRY, "until": days_from_today(10).isoformat(), **over}


def assert_clean_failure(output: str, code: int):
    assert code == 2
    assert len(output.strip().splitlines()) == 1
    assert "Traceback" not in output
    assert "permissions_cli" not in output
    assert ".py" not in output
    assert "разрешено" not in output
    assert "запрещено" not in output


COMMANDS = [("check", "bot", "read", "db"), ("expired",)]


@pytest.mark.parametrize("cmd", COMMANDS)
def test_beh15_missing_default_file(run_cli, tmp_path, cmd):
    out, code = run_cli(*cmd)
    assert_clean_failure(out, code)
    assert str(tmp_path / "permissions.yaml") in out


@pytest.mark.parametrize("cmd", COMMANDS)
def test_beh15_missing_explicit_file(run_cli, tmp_path, cmd):
    missing = str(tmp_path / "nope" / "reg.yaml")
    out, code = run_cli(*cmd, "--file", missing)
    assert_clean_failure(out, code)
    assert missing in out


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="нужны права POSIX")
@pytest.mark.parametrize("cmd", COMMANDS)
def test_beh16_unreadable_file(run_cli, make_registry, cmd):
    path = make_registry([valid_entry()])
    path.chmod(0)
    try:
        out, code = run_cli(*cmd, "--file", str(path))
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert_clean_failure(out, code)
    assert str(path) in out
    assert "не читается" in out


@pytest.mark.parametrize("cmd", COMMANDS)
def test_beh16_directory_instead_of_file(run_cli, tmp_path, cmd):
    out, code = run_cli(*cmd, "--file", str(tmp_path))
    assert_clean_failure(out, code)
    assert str(tmp_path) in out


def test_beh16_not_utf8(run_cli, tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"permissions: \xff\xfe\x00\n")
    out, code = run_cli("check", "bot", "read", "db", "--file", str(path))
    assert_clean_failure(out, code)
    assert str(path) in out


def test_beh17_broken_yaml(run_cli, tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("permissions: [\n  - a: {\n", encoding="utf-8")
    out, code = run_cli("check", "bot", "read", "db", "--file", str(path))
    assert_clean_failure(out, code)
    assert str(path) in out


def test_beh17_invalid_entry(run_cli, make_registry):
    path = make_registry([valid_entry(until="31.12.2026")])
    out, code = run_cli("expired", "--file", str(path))
    assert_clean_failure(out, code)
    assert str(path) in out


@pytest.mark.parametrize(
    "argv",
    [
        (),
        ("check", "a", "b"),
        ("expired", "x"),
        ("bogus",),
        ("expired", "--nope"),
        ("expired", "--file"),
    ],
)
def test_beh17_bad_invocation(run_cli, argv):
    out, code = run_cli(*argv)
    assert_clean_failure(out, code)
    assert "ошибка вызова" in out


def test_del29_check_never_allows_on_failures(run_cli, make_registry, tmp_path):
    cases = {
        "no_entry": make_registry([valid_entry(agent="other")], name="a.yaml"),
        "expired": make_registry(
            [valid_entry(until=days_from_today(-1).isoformat())], name="b.yaml"
        ),
        "typed": make_registry([valid_entry(agent="123")], name="c.yaml"),
        "missing": tmp_path / "missing.yaml",
    }
    broken = tmp_path / "d.yaml"
    broken.write_text("permissions: [\n", encoding="utf-8")
    cases["broken"] = broken
    for path in cases.values():
        out, code = run_cli("check", "bot", "read", "db", "--file", str(path))
        assert code != 0
        assert "разрешено" not in out.replace("запрещено", "")
