"""Docs coverage for artifact store runtime configuration."""

from __future__ import annotations

from pathlib import Path


def test_artifact_store_runtime_configuration_docs_exist_and_cover_core_terms() -> None:
    root = Path("docs")
    configuration_model = root / "configuration" / "model" / "CONFIGURATION.md"
    configuration_schema = root / "configuration" / "schema" / "CONFIG_SCHEMA.md"
    api_surface = root / "api" / "surface" / "API_SURFACE.md"
    contracts_core = root / "contracts" / "core" / "CONTRACTS.md"
    roadmap = root / "roadmap" / "milestones" / "ROADMAP.md"
    assurance_contracts = root / "assurance" / "contracts" / "PERSISTENCE_DURABILITY_CONTRACT.md"
    assurance_traceability = root / "assurance" / "testing" / "PERSISTENCE_TEST_TRACEABILITY.md"

    for path in (
        configuration_model,
        configuration_schema,
        api_surface,
        contracts_core,
        roadmap,
        assurance_contracts,
        assurance_traceability,
    ):
        assert path.exists()

    model_text = configuration_model.read_text().lower()
    schema_text = configuration_schema.read_text().lower()
    api_text = api_surface.read_text().lower()
    contracts_text = contracts_core.read_text().lower()
    roadmap_text = roadmap.read_text().lower()
    assurance_contracts_text = assurance_contracts.read_text().lower()
    traceability_text = assurance_traceability.read_text().lower()

    for token in (
        "stores.artifact",
        "artifact store runtime selection",
        "memory",
        "filesystem",
        "startup-only",
        "explicit filesystem selection is opt-in",
        "one filesystem root is one artifact identity domain",
        "`filesystemartifactstore` root is constructor-injected",
    ):
        assert token in model_text

    for token in (
        "the built-in artifact store is selected through `stores.artifact`",
        "canonical variants",
        "section absence normalizes to `memory`",
        "section presence requires `backend`",
        "accepted backends are exactly `memory` and `filesystem`",
        "`filesystem` requires an absolute `root`",
        "backend selection is startup-only",
        "runtime selection does not fall back from filesystem to memory",
    ):
        assert token in schema_text

    for token in (
        "artifact runtime selection is controlled by typed config under `stores.artifact`",
        "`memoryartifactstore` remains the default when the section is absent",
        "`filesystemartifactstore` is explicit opt-in and must fail startup on initialization errors",
        "the filesystem root is trusted configuration and must not be echoed in runtime diagnostics",
    ):
        assert token in api_text

    for token in (
        "artifact backend selection is represented by `stores.artifact`",
        "missing `stores.artifact` normalizes to `memoryartifactstore`",
        "explicit filesystem selection requires an absolute root and startup-only construction",
        "`filesystemartifactstore` is explicit opt-in and is constructed from typed config exactly once per runtime assembly",
    ):
        assert token in contracts_text

    for token in (
        "artifact backend runtime selection and configuration block v4",
        "typed artifact store settings: complete",
        "canonical runtime builder: complete",
        "no fallback semantics: complete",
    ):
        assert token in roadmap_text

    for token in (
        "`stores.artifact` is the runtime selection boundary for built-in artifact backends",
        "section absence normalizes to `memoryartifactstore`",
        "runtime selection is startup-only",
        "filesystem initialization errors fail runtime initialization instead of falling back to memory",
    ):
        assert token in assurance_contracts_text

    for token in (
        "artifact backend runtime selection is typed and startup-only",
        "filesystem selection remains explicit opt-in",
        "durable default is not enabled",
    ):
        assert token in traceability_text
