"""BEH-11…BEH-14, DEL-10, DEL-11: загрузка и полная проверка реестра."""

import pytest

GOOD = {
    "agent": "agent-a",
    "resource": "repo-x",
    "action": "read",
    "granted_by": "boss",
    "until": "2099-01-01",
}


def commands():
    return [("check", "agent-a", "read", "repo-x"), ("expired",)]


def assert_refusal(run_cli, path, *needles):
    for cmd in commands():
        out, code = run_cli(*cmd, "--file", str(path))
        assert code == 2, out
        assert len(out.strip().splitlines()) == 1
        assert str(path) in out
        for needle in needles:
            assert needle in out
        assert "разрешено" not in out and "запрещено" not in out
        assert "Traceback" not in out


def test_broken_yaml(run_cli, tmp_path):
    path = tmp_path / "permissions.yaml"
    path.write_text("permissions:\n  - agent: 'oops\n    x: [\n", encoding="utf-8")
    assert_refusal(run_cli, path, "строка")


@pytest.mark.parametrize("missing", list(GOOD))
def test_missing_field(run_cli, make_registry, missing):
    bad = {k: v for k, v in GOOD.items() if k != missing}
    path = make_registry([GOOD, bad, GOOD])
    assert_refusal(run_cli, path, "запись 2", missing)


@pytest.mark.parametrize("value", ["2026-02-31", "скоро", "", "2026-13-01", "2026-1-5"])
def test_bad_until(run_cli, make_registry, value):
    path = make_registry([GOOD, {**GOOD, "until": value}])
    assert_refusal(run_cli, path, "запись 2", "until")


@pytest.mark.parametrize("field", ["agent", "resource", "action", "granted_by"])
@pytest.mark.parametrize(
    "value", ["yes", "no", "on", "off", "null", "2026", "2026-01-02"]
)
def test_typed_value(run_cli, make_registry, field, value):
    path = make_registry([GOOD, {**GOOD, field: value}])
    assert_refusal(run_cli, path, "запись 2", field)


def test_datetime_until_rejected(run_cli, make_registry):
    path = make_registry([{**GOOD, "until": "2099-01-01 10:00:00"}])
    assert_refusal(run_cli, path, "запись 1", "until")


@pytest.mark.parametrize(
    "body", ["permission: []\n", "- a\n- b\n", "just text\n", "permissions: 5\n"]
)
def test_bad_shape(run_cli, tmp_path, body):
    path = tmp_path / "permissions.yaml"
    path.write_text(body, encoding="utf-8")
    assert_refusal(run_cli, path)


def test_entry_not_mapping(run_cli, tmp_path):
    path = tmp_path / "permissions.yaml"
    path.write_text("permissions:\n  - just-a-string\n", encoding="utf-8")
    assert_refusal(run_cli, path, "запись 1")


@pytest.mark.parametrize("body", ["", "permissions: []\n", "permissions:\n", "{}\n"])
def test_empty_is_not_refusal(tmp_path, body):
    import permissions_cli

    path = tmp_path / "permissions.yaml"
    path.write_text(body, encoding="utf-8")
    assert permissions_cli.load_registry(str(path)) == []


def test_valid_loads(make_registry):
    import permissions_cli

    path = make_registry([GOOD, {**GOOD, "until": "2099-02-02", "extra": "x"}])
    perms = permissions_cli.load_registry(str(path))
    assert [p.index for p in perms] == [1, 2]
    assert str(perms[1].until) == "2099-02-02"


def test_native_date_until(tmp_path):
    import permissions_cli

    path = tmp_path / "p.yaml"
    path.write_text(
        "permissions:\n  - {agent: a, resource: r, action: x, granted_by: g, until: 2099-01-01}\n",
        encoding="utf-8",
    )
    assert str(permissions_cli.load_registry(str(path))[0].until) == "2099-01-01"


def test_unreadable_file(run_cli, tmp_path):
    out, code = run_cli("expired", "--file", str(tmp_path / "nope.yaml"))
    assert code == 2 and len(out.strip().splitlines()) == 1
