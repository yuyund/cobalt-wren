"""Architecture guards for the separately installable external distribution fixture."""
from __future__ import annotations
from pathlib import Path
from tests.support.import_scan import collect_import_targets

ROOT = Path("tests/external_distributions/acme_workflows")
ALLOWED = ("cobalt_wren.api.plugins", "cobalt_wren.api.workflow")

def test_external_distribution_has_independent_project_metadata_and_entry_point() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert 'name = "acme-workflows"' in text
    assert '[project.entry-points."cobalt_wren.plugins"]' in text
    assert 'acme = "acme_workflows:create_plugin"' in text

def test_external_distribution_imports_only_public_spi() -> None:
    offenders: list[str] = []
    for path in (ROOT / "src").rglob("*.py"):
        for module in collect_import_targets(path):
            if module.startswith("cobalt_wren") and not module.startswith(ALLOWED):
                offenders.append(f"{path}:{module}")
    assert offenders == []
