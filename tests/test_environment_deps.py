"""DEL-04: одна внешняя зависимость проекта; средства разработки — отдельно."""

import sys
import tomllib
from pathlib import Path

from conftest import days_from_today

ROOT = Path(__file__).resolve().parent.parent


def _names(items):
    return [i.split(">")[0].split("=")[0].strip().lower() for i in items if i.strip()]


def test_requirements_single_pyyaml():
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    assert _names(lines) == ["pyyaml"]


def test_pyproject_dependencies():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert _names(data["project"]["dependencies"]) == ["pyyaml"]
    assert "pytest" not in _names(data["project"]["dependencies"])
    assert "pytest" in _names(data["dependency-groups"]["dev"])


def test_requires_python_312_or_newer():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["project"]["requires-python"].replace(" ", "") == ">=3.12"
    assert sys.version_info >= (3, 12)


def test_both_commands_run_as_plain_user(run_cli, make_registry):
    """BEH-27: обе команды работают из терминала без прав администратора и серверов."""
    make_registry(
        [
            {
                "agent": "agent-a",
                "resource": "repo-x",
                "action": "read",
                "granted_by": "boss",
                "until": days_from_today(5).isoformat(),
            }
        ]
    )
    out, code = run_cli("check", "agent-a", "read", "repo-x")
    assert code == 0 and "Traceback" not in out and out.strip()
    out, code = run_cli("expired")
    assert code == 0 and "Traceback" not in out


def test_only_stdlib_and_yaml_imported():
    import ast

    tree = ast.parse((ROOT / "permissions_cli.py").read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert mods - set(sys.stdlib_module_names) <= {"yaml"}
