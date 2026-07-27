#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
VENV_BIN="${VENV_BIN:-./venv/bin}"

rm -rf build dist src/cobalt_wren.egg-info

"${VENV_BIN}/ruff" check .
"${VENV_BIN}/mypy" src
"${VENV_BIN}/pytest" -q

rm -rf build dist src/cobalt_wren.egg-info
"${VENV_BIN}/python" -m build
"${VENV_BIN}/python" -m twine check dist/*
"${VENV_BIN}/check-wheel-contents" --ignore W004 dist/*.whl

"${VENV_BIN}/python" - <<'PY'
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
PY

clean_root="$(mktemp -d)"
trap 'rm -rf "${clean_root}"' EXIT
"${PYTHON_BIN}" -m venv "${clean_root}/venv"
"${clean_root}/venv/bin/pip" install dist/*.whl
"${clean_root}/venv/bin/python" -c 'import cobalt_wren'
"${clean_root}/venv/bin/cobalt-wren" --help >/dev/null

echo "Release validation passed."
