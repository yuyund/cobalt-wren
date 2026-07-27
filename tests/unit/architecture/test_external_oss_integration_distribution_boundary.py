"""Architecture guards for the separately installed OSS integration plugin."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


ROOT = Path("tests/external_distributions/oss_integration_workflows")
ALLOWED_FOUNDATION_IMPORTS = (
    "cobalt_wren.api.plugins",
    "cobalt_wren.api.workflow",
    "cobalt_wren.integrations.langgraph",
    "cobalt_wren.integrations.llamaindex_workflows",
)


def test_external_oss_distribution_has_independent_metadata_and_entry_point() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert 'name = "oss-integration-workflows"' in text
    assert '[project.entry-points."cobalt_wren.plugins"]' in text
    assert (
        'oss-integrations = "oss_integration_workflows:create_plugin"'
        in text
    )
    assert '"langgraph>=1.0,<2"' in text
    assert '"llama-index-workflows>=2.22,<3"' in text


def test_external_oss_distribution_uses_public_foundation_spi_only() -> None:
    offenders: list[str] = []
    for path in (ROOT / "src").rglob("*.py"):
        for module in collect_import_targets(path):
            if module.startswith("cobalt_wren") and not module.startswith(
                ALLOWED_FOUNDATION_IMPORTS
            ):
                offenders.append(f"{path}:{module}")
    assert offenders == []
