"""DEL-04: одна внешняя зависимость проекта; средства разработки — отдельно."""

import tomllib
from pathlib import Path

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
