"""BEH-08, BEH-09, BEH-10, DEL-15…DEL-18: группы вывода expired."""

from conftest import days_from_today

OVERDUE_TITLE = "Просроченные:"
SOON_TITLE = "Истекающие в ближайшие 7 дней:"


def entry(n: int, delta: int, **over) -> dict:
    base = {
        "agent": f"agent-{n}",
        "resource": f"res-{n}",
        "action": f"act-{n}",
        "granted_by": f"owner-{n}",
        "until": days_from_today(delta),
    }
    return {**base, **over}


def groups(out: str) -> tuple[list[str], list[str]]:
    lines = out.splitlines()
    i, j = lines.index(OVERDUE_TITLE), lines.index(SOON_TITLE)
    assert i < j
    return (
        [x for x in lines[i + 1 : j] if x.strip()],
        [x for x in lines[j + 1 :] if x.strip()],
    )


def test_group_boundaries(run_cli, make_registry):
    deltas = [-10, -1, 0, 7, 8]
    path = make_registry([entry(n, d) for n, d in enumerate(deltas)])
    out, code = run_cli("expired", "--file", str(path))
    assert code == 0
    overdue, soon = groups(out)
    assert [("agent-0" in r, "agent-1" in r) for r in overdue] == [
        (True, False),
        (False, True),
    ]
    assert len(overdue) == 2
    assert len(soon) == 2
    assert "agent-2" in soon[0] and "agent-3" in soon[1]
    assert "agent-4" not in out


def test_row_has_five_fields_duplicates_and_file_order(run_cli, make_registry):
    a = entry(1, -3)
    b = {**a, "granted_by": "owner-other", "until": days_from_today(-2)}
    c = entry(2, -5)
    s1, s2 = entry(3, 5), entry(4, 1)
    path = make_registry([a, c, b, s1, s2])
    out, _ = run_cli("expired", "--file", str(path))
    overdue, soon = groups(out)
    assert len(overdue) == 3
    for row, e in zip(overdue, [a, c, b], strict=True):
        for key in ("agent", "resource", "action", "granted_by"):
            assert e[key] in row
        assert e["until"].isoformat() in row
    assert "owner-other" in overdue[2] and "owner-1" in overdue[0]
    assert "agent-3" in soon[0] and "agent-4" in soon[1]
    assert "" in out.splitlines()


def test_twenty_entries_counts(run_cli, make_registry):
    deltas = [-30, -20, -9, -8, -7, -6, -5, -4, -3, -1, 0, 1, 2, 3, 4, 7, 8, 9, 30, 100]
    assert len(deltas) == 20
    path = make_registry([entry(n, d) for n, d in enumerate(deltas)])
    out, code = run_cli("expired", "--file", str(path))
    assert code == 0
    overdue, soon = groups(out)
    exp_over = [n for n, d in enumerate(deltas) if d < 0]
    exp_soon = [n for n, d in enumerate(deltas) if 0 <= d <= 7]
    assert len(overdue) == len(exp_over)
    assert len(soon) == len(exp_soon)
    for row, n in zip(overdue, exp_over, strict=True):
        assert f"агент: agent-{n};" in row and f"ресурс: res-{n};" in row
    for row, n in zip(soon, exp_soon, strict=True):
        assert f"агент: agent-{n};" in row


def test_both_groups_always_printed(run_cli, make_registry):
    cases = {
        "empty": [],
        "only_overdue": [entry(1, -1)],
        "only_soon": [entry(1, 3)],
        "far": [entry(1, 50)],
    }
    for name, entries in cases.items():
        path = make_registry(entries, name=f"{name}.yaml")
        out, code = run_cli("expired", "--file", str(path))
        assert code == 0
        overdue, soon = groups(out)
        want_over = sum(e["until"] < days_from_today(0) for e in entries)
        want_soon = sum(
            0 <= (e["until"] - days_from_today(0)).days <= 7 for e in entries
        )
        assert (overdue == ["  (нет)"]) == (want_over == 0)
        assert (soon == ["  (нет)"]) == (want_soon == 0)
