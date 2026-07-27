#!/usr/bin/env bash
set -euo pipefail

if [[ -x ./venv/bin/python ]]; then
  PYTHON_BIN="${PYTHON_BIN:-./venv/bin/python}"
  RUFF_BIN="${RUFF_BIN:-./venv/bin/ruff}"
  MYPY_BIN="${MYPY_BIN:-./venv/bin/mypy}"
  PYTEST_BIN="${PYTEST_BIN:-./venv/bin/pytest}"
  CHECK_WHEEL_BIN="${CHECK_WHEEL_BIN:-./venv/bin/check-wheel-contents}"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
  RUFF_BIN="${RUFF_BIN:-ruff}"
  MYPY_BIN="${MYPY_BIN:-mypy}"
  PYTEST_BIN="${PYTEST_BIN:-pytest}"
  CHECK_WHEEL_BIN="${CHECK_WHEEL_BIN:-check-wheel-contents}"
fi

rm -rf build dist src/cobalt_wren.egg-info

"${RUFF_BIN}" check .
"${MYPY_BIN}" src
"${PYTEST_BIN}" -q

rm -rf build dist src/cobalt_wren.egg-info
"${PYTHON_BIN}" -m build
"${PYTHON_BIN}" -m twine check dist/*
"${CHECK_WHEEL_BIN}" --ignore W004 dist/*.whl

"${PYTHON_BIN}" - <<'PYCODE'
from pathlib import Path
import tarfile
import zipfile

wheel = next(Path("dist").glob("*.whl"))
sdist = next(Path("dist").glob("*.tar.gz"))

with zipfile.ZipFile(wheel) as archive:
    names = set(archive.namelist())
    assert any(name.startswith("cobalt_wren/") for name in names)
    assert not any(name.startswith("langgraph_automation/") for name in names)
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    assert any(name.endswith(".dist-info/licenses/NOTICE") for name in names)
    assert not any(name.endswith(("db.sqlite3", ".env")) for name in names)

with tarfile.open(sdist) as archive:
    names = set(archive.getnames())
    assert any(name.endswith("/CHANGELOG.md") for name in names)
    assert not any(name.endswith(("/db.sqlite3", "/.env")) for name in names)
PYCODE

clean_root="$(mktemp -d)"
trap 'rm -rf "${clean_root}"' EXIT
"${PYTHON_BIN}" -m venv "${clean_root}/venv"
"${clean_root}/venv/bin/pip" install dist/*.whl
"${clean_root}/venv/bin/python" -c 'import cobalt_wren'
"${clean_root}/venv/bin/cobalt-wren" --help >/dev/null

echo "Release validation passed."
