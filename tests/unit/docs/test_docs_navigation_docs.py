"""Docs coverage for the docs navigation structure."""

from __future__ import annotations

from pathlib import Path


def test_docs_navigation_entries_exist_and_point_to_subsections() -> None:
    root = Path('docs')
    docs_index = root / 'index.md'
    docs_agents = root / 'AGENTS.md'
    agent_index = root / 'agent' / 'index.md'
    codex_workflow = root / 'agent' / 'CODEX_WORKFLOW.md'
    navigation = root / 'agent' / 'navigation.md'
    protocol = root / 'agent' / 'operating-protocol.md'
    hygiene = root / 'agent' / 'hygiene-and-reporting.md'
    package_index = root / 'package' / 'index.md'
    package_completion_index = root / 'package' / 'completion' / 'index.md'
    package_verification_index = root / 'package' / 'verification' / 'index.md'
    package_gaps_index = root / 'package' / 'gaps' / 'index.md'
    architecture_index = root / 'architecture' / 'index.md'
    architecture_layers_index = root / 'architecture' / 'layers' / 'index.md'
    architecture_dataflow = root / 'architecture' / 'dataflow' / 'DATAFLOW.md'
    architecture_audit_index = root / 'architecture' / 'audit' / 'index.md'
    architecture_persistence_audit = root / 'architecture' / 'audit' / 'PERSISTENCE_FAILURE_MODE_AUDIT.md'
    architecture_artifact_protocol_audit = root / 'architecture' / 'audit' / 'ARTIFACT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    architecture_checkpoint_protocol_audit = root / 'architecture' / 'audit' / 'CHECKPOINT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    architecture_persistence_orchestration_audit = root / 'architecture' / 'audit' / 'PERSISTENCE_ORCHESTRATION_SUFFICIENCY_AUDIT.md'
    architecture_design_index = root / 'architecture' / 'design' / 'index.md'
    architecture_design_artifact = root / 'architecture' / 'design' / 'DURABLE_ARTIFACT_BACKEND_DESIGN.md'
    architecture_design_checkpoint = root / 'architecture' / 'design' / 'DURABLE_CHECKPOINT_BACKEND_DESIGN.md'
    api_index = root / 'api' / 'index.md'
    api_surface_index = root / 'api' / 'surface' / 'index.md'
    api_errors_index = root / 'api' / 'errors' / 'index.md'
    configuration_index = root / 'configuration' / 'index.md'
    configuration_model_index = root / 'configuration' / 'model' / 'index.md'
    configuration_schema_index = root / 'configuration' / 'schema' / 'index.md'
    contracts_index = root / 'contracts' / 'index.md'
    contracts_core_index = root / 'contracts' / 'core' / 'index.md'
    contracts_errors_index = root / 'contracts' / 'errors' / 'index.md'
    contracts_integrations_index = root / 'contracts' / 'integrations' / 'index.md'
    contracts_filesystem_artifact = root / 'contracts' / 'integrations' / 'FILESYSTEM_ARTIFACT_STORE.md'
    contracts_checkpoint = root / 'contracts' / 'integrations' / 'CHECKPOINT_STORE.md'
    workflows_index = root / 'workflows' / 'index.md'
    workflows_authoring_index = root / 'workflows' / 'authoring' / 'index.md'
    workflows_readiness_index = root / 'workflows' / 'readiness' / 'index.md'
    roadmap_index = root / 'roadmap' / 'index.md'
    roadmap_milestones_index = root / 'roadmap' / 'milestones' / 'index.md'
    roadmap_gates_index = root / 'roadmap' / 'gates' / 'index.md'
    assurance_index = root / 'assurance' / 'index.md'
    assurance_scope_index = root / 'assurance' / 'scope' / 'index.md'
    assurance_contracts_index = root / 'assurance' / 'contracts' / 'index.md'
    assurance_gaps_index = root / 'assurance' / 'gaps' / 'index.md'
    assurance_testing_index = root / 'assurance' / 'testing' / 'index.md'
    assurance_persistence_harness = root / 'assurance' / 'testing' / 'PERSISTENCE_CONTRACT_TEST_HARNESS.md'
    assurance_artifact_test_plan = root / 'assurance' / 'testing' / 'DURABLE_ARTIFACT_TEST_PLAN.md'
    assurance_checkpoint_test_plan = root / 'assurance' / 'testing' / 'DURABLE_CHECKPOINT_TEST_PLAN.md'

    for path in (
        docs_index,
        docs_agents,
        agent_index,
        codex_workflow,
        navigation,
        protocol,
        hygiene,
        package_index,
        package_completion_index,
        package_verification_index,
        package_gaps_index,
        architecture_index,
        architecture_layers_index,
        architecture_dataflow,
        architecture_audit_index,
        architecture_persistence_audit,
        architecture_artifact_protocol_audit,
        architecture_checkpoint_protocol_audit,
        architecture_persistence_orchestration_audit,
        architecture_design_index,
        architecture_design_artifact,
        architecture_design_checkpoint,
        api_index,
        api_surface_index,
        api_errors_index,
        configuration_index,
        configuration_model_index,
        configuration_schema_index,
        contracts_index,
        contracts_core_index,
        contracts_errors_index,
        contracts_integrations_index,
        contracts_filesystem_artifact,
        contracts_checkpoint,
        workflows_index,
        workflows_authoring_index,
        workflows_readiness_index,
        roadmap_index,
        roadmap_milestones_index,
        roadmap_gates_index,
        assurance_index,
        assurance_scope_index,
        assurance_contracts_index,
        assurance_gaps_index,
        assurance_testing_index,
        assurance_persistence_harness,
        assurance_artifact_test_plan,
        assurance_checkpoint_test_plan,
    ):
        assert path.exists()

    index_text = docs_index.read_text()
    docs_agents_text = docs_agents.read_text()
    agent_index_text = agent_index.read_text()
    codex_workflow_text = codex_workflow.read_text()
    navigation_text = navigation.read_text()
    protocol_text = protocol.read_text()
    hygiene_text = hygiene.read_text()
    package_index_text = package_index.read_text()
    architecture_index_text = architecture_index.read_text()
    architecture_audit_index_text = architecture_audit_index.read_text()
    architecture_design_index_text = architecture_design_index.read_text()
    api_index_text = api_index.read_text()
    configuration_index_text = configuration_index.read_text()
    contracts_index_text = contracts_index.read_text()
    contracts_integrations_text = contracts_integrations_index.read_text()
    workflows_index_text = workflows_index.read_text()
    roadmap_index_text = roadmap_index.read_text()
    assurance_index_text = assurance_index.read_text()
    assurance_testing_text = assurance_testing_index.read_text()

    for token in ('./AGENTS.md', './agent/index.md', './architecture/index.md'):
        assert token in index_text

    assert 'Keep links inside `docs/` relative.' in docs_agents_text
    assert 'Start at `index.md`' in docs_agents_text
    assert 'navigation.md' in agent_index_text
    assert 'operating-protocol.md' in agent_index_text
    assert 'hygiene-and-reporting.md' in agent_index_text
    assert 'Read Next' in codex_workflow_text
    assert '../index.md' in navigation_text
    assert '../AGENTS.md' in navigation_text
    assert 'git status --short --untracked-files=all' in protocol_text
    assert './venv/bin/python -m pytest -q' in protocol_text
    assert 'Reporting Template' in hygiene_text
    assert 'Do not hide untracked files.' in hygiene_text
    assert 'completion/index.md' in package_index_text
    assert 'verification/index.md' in package_index_text
    assert 'gaps/index.md' in package_index_text
    assert 'layers/index.md' in architecture_index_text
    assert 'dataflow/DATAFLOW.md' in architecture_index_text
    assert 'audit/index.md' in architecture_index_text
    assert 'PERSISTENCE_FAILURE_MODE_AUDIT.md' in architecture_index_text
    assert 'PERSISTENCE_ORCHESTRATION_SUFFICIENCY_AUDIT.md' in architecture_index_text
    assert 'design/index.md' in architecture_index_text
    assert 'ARTIFACT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md' in architecture_audit_index_text
    assert 'CHECKPOINT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md' in architecture_audit_index_text
    assert 'PERSISTENCE_ORCHESTRATION_SUFFICIENCY_AUDIT.md' in architecture_audit_index_text
    assert 'DURABLE_ARTIFACT_BACKEND_DESIGN.md' in architecture_design_index_text
    assert 'DURABLE_CHECKPOINT_BACKEND_DESIGN.md' in architecture_design_index_text
    assert 'surface/index.md' in api_index_text
    assert 'errors/index.md' in api_index_text
    assert 'model/index.md' in configuration_index_text
    assert 'schema/index.md' in configuration_index_text
    assert 'core/index.md' in contracts_index_text
    assert 'errors/index.md' in contracts_index_text
    assert 'integrations/index.md' in contracts_index_text
    assert 'CHECKPOINT_STORE.md' in contracts_integrations_text
    assert 'authoring/index.md' in workflows_index_text
    assert 'readiness/index.md' in workflows_index_text
    assert 'milestones/index.md' in roadmap_index_text
    assert 'gates/index.md' in roadmap_index_text
    assert 'scope/index.md' in assurance_index_text
    assert 'contracts/index.md' in assurance_index_text
    assert 'gaps/index.md' in assurance_index_text
    assert 'testing/index.md' in assurance_index_text
    assert 'PERSISTENCE_CONTRACT_TEST_HARNESS.md' in assurance_testing_text
    assert 'DURABLE_ARTIFACT_TEST_PLAN.md' in assurance_testing_text
    assert 'DURABLE_CHECKPOINT_TEST_PLAN.md' in assurance_testing_text
