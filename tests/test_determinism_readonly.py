"""BEH-22, BEH-23, BEH-25, DEL-32…DEL-35: повторяемость, только чтение, смена даты."""

import datetime
import os
import stat

import pytest
from conftest import days_from_today

import permissions_cli


def entry(until, **over) -> dict:
    base = {
        "agent": "bot-1",
        "resource": "repo-x",
        "action": "read",
        "granted_by": "alice",
        "until": until,
    }
    return {**base, **over}


def file_state(path):
    st = path.stat()
    return path.read_bytes(), st.st_mtime_ns


def series(run_cli, path):
    f = str(path)
    return [
        ("check", "bot-1", "read", "repo-x", "--file", f),
        ("check", "bot-2", "read", "repo-x", "--file", f),
        ("expired", "--file", f),
        ("check", "bot-1", "--file", f),  # ошибка вызова
        ("expired", "--file", f + ".missing"),  # ошибка файла
    ]


def test_beh22_repeat_calls_identical_and_registry_untouched(run_cli, make_registry):
    path = make_registry(
        [
            entry(days_from_today(3)),
            entry(days_from_today(-2), agent="bot-3"),
            entry(days_from_today(20), agent="bot-4"),
        ]
    )
    before = file_state(path)
    for args in (
        ("check", "bot-1", "read", "repo-x", "--file", str(path)),
        ("expired", "--file", str(path)),
    ):
        first = run_cli(*args)
        second = run_cli(*args)
        assert first == second
    assert file_state(path) == before


def test_beh23_no_new_files_after_calls(run_cli, make_registry, snapshot_places):
    path = make_registry([entry(days_from_today(3))])
    before = snapshot_places()
    for args in series(run_cli, path):
        run_cli(*args, cwd=snapshot_places.work)
    assert snapshot_places() == before


def test_beh23_in_process_calls_leave_no_files(
    make_registry, snapshot_places, call_main
):
    path = make_registry([entry(days_from_today(3))])
    before = snapshot_places()
    call_main("check", "bot-1", "read", "repo-x", "--file", str(path))
    call_main("expired", "--file", str(path))
    call_main("expired", "--file", str(path) + ".missing")
    assert snapshot_places() == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root игнорирует права доступа")
def test_beh23_read_only_registry_and_dir(run_cli, make_registry, tmp_path):
    path = make_registry([entry(days_from_today(3))])
    calls = [
        ("check", "bot-1", "read", "repo-x", "--file", str(path)),
        ("expired", "--file", str(path)),
    ]
    normal = [run_cli(*c) for c in calls]
    path.chmod(0o444)
    tmp_path.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        locked = [run_cli(*c) for c in calls]
        names = sorted(p.name for p in tmp_path.iterdir())
    finally:
        tmp_path.chmod(0o700)
        path.chmod(0o644)
    assert locked == normal
    assert names == ["permissions.yaml"]


def test_beh25_date_change_flips_verdict(make_registry, fake_today, call_main):
    day = datetime.date(2030, 6, 15)
    path = make_registry([entry(day.isoformat())])
    before = file_state(path)
    args = ("check", "bot-1", "read", "repo-x", "--file", str(path))

    fake_today(day)
    out, code = call_main(*args)
    assert code == 0 and out.startswith("разрешено")
    listing, code = call_main("expired", "--file", str(path))
    head, _, soon = listing.partition("Истекающие")
    assert "bot-1" in soon and "bot-1" not in head

    fake_today(day + datetime.timedelta(days=1))
    out, code = call_main(*args)
    assert code == 1 and out.strip() == "запрещено: срок истёк"
    listing, code = call_main("expired", "--file", str(path))
    head, _, soon = listing.partition("Истекающие")
    assert "bot-1" in head and "bot-1" not in soon
    assert file_state(path) == before


def test_del35_harness_provides_snapshot_and_seam(snapshot_places, fake_today):
    (snapshot_places.work / "x.txt").write_text("a")
    snap = snapshot_places()
    assert set(snap) == {"cwd", "home", "install"}
    assert snap["cwd"]["x.txt"][0] == 1
    fake_today(datetime.date(2031, 1, 2))
    assert permissions_cli.today() == datetime.date(2031, 1, 2)
    assert "--today" not in permissions_cli.HELP
