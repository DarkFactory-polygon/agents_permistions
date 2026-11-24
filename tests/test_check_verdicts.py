"""BEH-01…BEH-07, DEL-19…DEL-25: вердикты check и пустой реестр."""

import datetime
import re
from pathlib import Path

from conftest import days_from_today

import permissions_cli

SOURCE = Path(permissions_cli.__file__).read_text(encoding="utf-8")


def entry(until, **over) -> dict:
    base = {
        "agent": "bot-1",
        "resource": "repo-x",
        "action": "read",
        "granted_by": "alice",
        "until": until,
    }
    return {**base, **over}


def check(run_cli, path, agent="bot-1", action="read", resource="repo-x"):
    return run_cli("check", agent, action, resource, "--file", str(path))


def test_beh01_active_permission(run_cli, make_registry):
    until = days_from_today(5)
    out, code = check(run_cli, make_registry([entry(until)]))
    assert code == 0
    assert out.strip() == f"разрешено: выдал alice, до {until.isoformat()}"


def test_beh02_last_day_included(run_cli, make_registry):
    out, code = check(run_cli, make_registry([entry(days_from_today(0))]))
    assert code == 0
    assert out.startswith("разрешено")


def test_beh03_expired(run_cli, make_registry):
    out, code = check(run_cli, make_registry([entry(days_from_today(-1))]))
    assert code == 1
    assert out.strip() == "запрещено: срок истёк"
    assert "разрешено" not in out.replace("запрещено", "")


def test_beh04_no_entry(run_cli, make_registry):
    out, code = check(
        run_cli, make_registry([entry(days_from_today(5))]), agent="bot-2"
    )
    assert code == 1
    assert out.strip() == "запрещено: записи нет"


def test_beh05_star_is_literal(run_cli, make_registry):
    for field, args in (
        ("agent", {"agent": "bot-9"}),
        ("action", {"action": "write"}),
        ("resource", {"resource": "repo-y"}),
    ):
        path = make_registry([entry(days_from_today(5), **{field: "'*'"})])
        out, code = check(run_cli, path, **args)
        assert (out.strip(), code) == ("запрещено: записи нет", 1)
    path = make_registry([entry(days_from_today(5), agent="'*'")])
    out, code = check(run_cli, path, agent="*")
    assert code == 0
    assert out.startswith("разрешено")


def test_beh06_any_active_entry_any_order(run_cli, make_registry):
    old = entry(days_from_today(-3), granted_by="old-owner")
    live = entry(days_from_today(9), granted_by="live-owner")
    outs = []
    for entries in ([old, live], [live, old]):
        out, code = check(run_cli, make_registry(entries))
        assert code == 0
        outs.append(out)
    assert outs[0] == outs[1]
    assert "live-owner" in outs[0] and "old-owner" not in outs[0]
    assert days_from_today(9).isoformat() in outs[0]


def test_beh07_empty_list(run_cli, make_registry):
    path = make_registry([])
    out, code = check(run_cli, path)
    assert (out.strip(), code) == ("запрещено: записи нет", 1)
    out, code = run_cli("expired", "--file", str(path))
    assert code == 0
    assert out.count("(нет)") == 2
    assert "ошибка" not in out.lower()


def test_del25_today_read_once_and_passed_as_parameter():
    assert len(re.findall(r"\.today\(\)|\.now\(", SOURCE)) == 1
    perms = [
        permissions_cli.Permission("a", "r", "x", "o", datetime.date(2026, 1, 10), 1)
    ]
    results = []
    for _ in range(2):
        results.append(
            permissions_cli.run_check(
                perms, ("a", "x", "r"), datetime.date(2026, 1, 10)
            )
        )
    assert results == [0, 0]
    assert (
        permissions_cli.run_check(perms, ("a", "x", "r"), datetime.date(2026, 1, 11))
        == 1
    )
