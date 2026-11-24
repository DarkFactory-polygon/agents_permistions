"""BEH-20: справка описывает команды, --file, пять полей и формат даты."""

import pytest

ARGS = [["--help"], ["check", "--help"], ["expired", "--help"], ["check", "a", "b", "c", "--help"]]


@pytest.mark.parametrize("args", ARGS)
def test_help_content(run_cli, args):
    out, code = run_cli(*args)
    assert code == 0
    for word in ["check", "expired", "--file", "permissions.yaml", "YYYY-MM-DD"]:
        assert word in out
    for key in ["agent", "resource", "action", "granted_by", "until"]:
        assert key in out
    low = out.lower()
    assert low.index("агент") < low.index("действие") < low.index("ресурс")


def test_help_has_no_machine_output_or_secrets(run_cli):
    out, _ = run_cli("--help")
    low = out.lower()
    for word in ["--json", "--format", "password", "token", "пароль", "токен"]:
        assert word not in low
