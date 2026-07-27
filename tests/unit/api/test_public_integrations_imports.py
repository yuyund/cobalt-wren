"""Public workflow integration facade coverage."""

from __future__ import annotations


def test_public_integration_api_exports() -> None:
    import cobalt_wren.api.integrations as integration_api

    expected = {
        "IntegrationSupport",
        "IntegrationMaturity",
        "IntegrationAvailabilityStatus",
        "ActionSafety",
        "ProjectionOwnerKind",
        "IntegrationCapability",
        "IntegrationDefinition",
        "IntegrationAvailability",
        "IntegrationContext",
        "ExecutionUnitProjection",
        "LifecycleProjection",
        "IntegrationProjection",
        "IntegrationActionDescriptor",
        "IntegrationActionRequest",
        "IntegrationProjectionBatch",
        "WorkflowIntegrationProvider",
    }
    assert set(integration_api.__all__) == expected
    for name in expected:
        assert getattr(integration_api, name) is not None


def test_definition_rejects_duplicate_capabilities() -> None:
    from cobalt_wren.api.integrations import IntegrationCapability, IntegrationDefinition

    try:
        IntegrationDefinition(
            integration_id="demo",
            distribution="demo",
            import_name="demo",
            provider_path="demo:provider",
            capabilities=(IntegrationCapability("execute"), IntegrationCapability("execute")),
        )
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate capabilities must be rejected")
