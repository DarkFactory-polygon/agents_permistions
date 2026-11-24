"""BEH-19, BEH-21, DEL-12…DEL-14: источник данных и равнозначные формы даты."""

import shutil

from conftest import days_from_today

A = {
    "agent": "agent-a",
    "resource": "repo-x",
    "action": "read",
    "granted_by": "owner",
    "until": days_from_today(30),
}
B = {**A, "agent": "agent-b", "resource": "repo-y", "action": "write"}


def snapshot(run_cli, cwd, *file_args):
    return [
        run_cli("check", "agent-a", "read", "repo-x", *file_args, cwd=cwd),
        run_cli("check", "agent-b", "write", "repo-y", *file_args, cwd=cwd),
        run_cli("expired", *file_args, cwd=cwd),
    ]


def test_default_file_is_cwd_permissions(run_cli, make_registry, tmp_path):
    make_registry([A])
    out, code = run_cli("check", "agent-a", "read", "repo-x", cwd=tmp_path)
    assert code == 0 and "разрешено" in out
    out, code = run_cli("check", "agent-b", "write", "repo-y", cwd=tmp_path)
    assert code == 1 and "запрещено: записи нет" in out
    _, code = run_cli("expired", cwd=tmp_path)
    assert code == 0


def test_explicit_file(run_cli, make_registry, tmp_path):
    make_registry([A])
    other = tmp_path / "sub"
    other.mkdir()
    path = make_registry([B], name="sub/other.yaml")
    out, code = run_cli("check", "agent-b", "write", "repo-y", "--file", str(path))
    assert code == 0 and "разрешено" in out
    out, code = run_cli("check", "agent-a", "read", "repo-x", "--file", str(path))
    assert code == 1 and "запрещено: записи нет" in out
    out, code = run_cli("expired", "--file", str(path))
    assert code == 0


def test_other_files_irrelevant(run_cli, make_registry, tmp_path):
    reg = make_registry([A])
    decoys = [
        "config.yaml",
        "permissions.yml",
        ".permissions-cli.toml",
        "permissions_cli.yaml",
    ]
    for name in decoys:
        (tmp_path / name).write_text("permissions: [garbage\n", encoding="utf-8")
    before = snapshot(run_cli, tmp_path)
    before_file = snapshot(run_cli, tmp_path, "--file", str(reg))
    for name in decoys:
        (tmp_path / name).unlink()
    assert snapshot(run_cli, tmp_path) == before
    assert snapshot(run_cli, tmp_path, "--file", str(reg)) == before_file


def test_install_dir_files_irrelevant(make_registry, tmp_path, tmp_path_factory):
    import subprocess
    import sys

    from conftest import CLI

    make_registry([A])
    install = tmp_path_factory.mktemp("install")
    copy = install / "permissions_cli.py"
    shutil.copy(CLI, copy)

    def run():
        proc = subprocess.run(
            [sys.executable, str(copy), "check", "agent-a", "read", "repo-x"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.stdout + proc.stderr, proc.returncode

    before = run()
    for name in ("permissions.yaml", "config.yaml", "permissions-cli.toml"):
        (install / name).write_text("permissions: [broken\n", encoding="utf-8")
    assert run() == before
    assert before[1] == 0


def test_date_forms_equivalent(run_cli, tmp_path):
    def reg(name, until_line, extra=""):
        p = tmp_path / name
        p.write_text(
            "permissions:\n  - agent: agent-a\n    resource: repo-x\n"
            "    action: read\n    granted_by: owner\n"
            f"    until: {until_line}\n{extra}",
            encoding="utf-8",
        )
        return p

    day = days_from_today(3).isoformat()
    s = reg("s.yaml", f'"{day}"')
    n = reg("n.yaml", day)
    e = reg("e.yaml", f'"{day}"', "    comment: заметка\n")
    results = [
        [
            run_cli("check", "agent-a", "read", "repo-x", "--file", str(p)),
            run_cli("expired", "--file", str(p)),
        ]
        for p in (s, n, e)
    ]
    assert results[0] == results[1] == results[2]
    assert results[0][0][1] == 0
    assert "agent-a" in results[0][1][0]
