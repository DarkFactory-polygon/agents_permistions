"""BEH-18: неверный вызов — подсказка и код 2."""

import pytest

BAD_CALLS = [
    ["grant", "agent-a", "read", "repo-x"],
    [],
    ["check", "agent-a", "read"],
    ["check", "agent-a", "read", "repo-x", "extra"],
    ["expired", "agent-a"],
]


@pytest.mark.parametrize("args", BAD_CALLS)
def test_bad_invocation(run_cli, make_registry, args):
    make_registry([])
    out, code = run_cli(*args)
    assert code == 2
    assert "check" in out and "expired" in out
    assert out.lower().index("агент") < out.lower().index("действие") < out.lower().index("ресурс")
    assert len(out.strip().splitlines()) == 1
    assert "разрешено" not in out and "запрещено" not in out
    assert "Traceback" not in out


def test_exit_codes_only_from_main(run_cli):
    _, code = run_cli("--help")
    assert code == 0
