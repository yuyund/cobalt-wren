"""Documentation contracts for package-wide design principles."""

from pathlib import Path


def test_design_principles_define_internal_and_external_boundaries() -> None:
    root = Path("docs")
    design = root / "architecture" / "design" / "DESIGN_PRINCIPLES.md"
    text = design.read_text()

    assert design.exists()
    for heading in (
        "Change Containment First",
        "Package Surface And Internal Structure",
        "External Libraries Are Implementations, Not Architecture",
        "Workflow Flexibility",
        "Dynamic UI",
        "Safety",
        "Persistence",
        "Configuration",
        "Evidence Of Loose Coupling",
        "Review Rules",
    ):
        assert f"## {heading}" in text

    assert "Loose coupling applies inside the package" in text
    assert "BaseCheckpointSaver" in text
    assert "true resume" in text
    assert "replacement and extension tests" in text


def test_design_principles_are_consistent_with_cross_cutting_docs() -> None:
    root = Path("docs")
    documents = {
        "README": Path("README.md").read_text(),
        "architecture": (root / "architecture" / "layers" / "ARCHITECTURE.md").read_text(),
        "contracts": (root / "contracts" / "core" / "CONTRACTS.md").read_text(),
        "workflow guide": (root / "workflows" / "authoring" / "WORKFLOW_AUTHOR_GUIDE.md").read_text(),
        "invariants": (root / "package" / "completion" / "PACKAGE_INVARIANTS.md").read_text(),
        "api surface": (root / "api" / "surface" / "API_SURFACE.md").read_text(),
    }

    assert "DESIGN_PRINCIPLES.md" in documents["README"]
    assert "Internal Loose Coupling" in documents["architecture"]
    assert "Persistence Convergence" in documents["architecture"]
    assert "Internal Loose Coupling Contract" in documents["contracts"]
    assert "Workflow Flexibility Contract" in documents["contracts"]
    assert "Dynamic UI Projection Contract" in documents["contracts"]
    assert "Workflow Freedom And Foundation Changes" in documents["workflow guide"]
    assert "tests/external_distributions/acme_workflows" in documents["invariants"]
    assert "TEST_CONFIRMED" in documents["invariants"]
    assert "BaseCheckpointSaver" in documents["api surface"]
    assert "Persistence durability is still EPHEMERAL today" not in documents["architecture"]
    assert documents["api surface"].count("FilesystemCheckpointStore is implemented") == 1
