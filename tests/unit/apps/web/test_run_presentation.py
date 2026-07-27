from pathlib import Path
from cobalt_wren.apps.web.presentation.run_components import (
    get_run_live_components,
)
from cobalt_wren.apps.web.templatetags.ui_presentation import (
    status_badge_class,
)


def test_run_component_registry_has_stable_semantic_order() -> None:
    components = get_run_live_components()
    assert [component.key for component in components] == [
        "run.current_state",
        "run.native_telemetry",
        "run.failure_diagnostic",
        "run.llm_conversation",
        "run.node_output",
        "run.timeline",
    ]
    assert [component.order for component in components] == sorted(
        component.order for component in components
    )
    assert all(
        component.template_name.startswith("dynamic/components/")
        for component in components
    )


def test_run_live_parent_template_is_registry_driven() -> None:
    source = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/run_live.html"
    ).read_text()
    assert "for component in components" in source
    assert "component.template_name" in source
    assert "llm_conversation.html" not in source
    assert "execution_timeline.html" not in source


def test_status_mapping_is_renderer_only_and_semantic() -> None:
    assert status_badge_class("Succeeded") == "bg-green-lt text-green"
    assert status_badge_class("Failed") == "bg-red-lt text-red"
    assert status_badge_class("Running") == "bg-blue-lt text-blue"
    assert status_badge_class("unknown") == "bg-secondary-lt text-secondary"


def test_theme_tokens_are_separate_from_component_rules() -> None:
    tokens = Path(
        "src/cobalt_wren/apps/web/static/cobalt_wren/theme-tokens.css"
    ).read_text()
    components = Path(
        "src/cobalt_wren/apps/web/static/cobalt_wren/components.css"
    ).read_text()
    assert "--cp-component-gap" in tokens
    assert ".llm-conversation-list" not in tokens
    assert "var(--cp-component-gap)" in components


def test_generic_templates_delegate_field_rendering() -> None:
    for filename in ("detail.html", "list.html", "fragment.html"):
        source = Path(
            f"src/cobalt_wren/apps/web/templates/dynamic/{filename}"
        ).read_text()
        assert "dynamic/components/field_value.html" in source
        assert "{{ field.display_value }}" not in source


def test_field_renderer_is_the_only_generic_display_value_boundary() -> None:
    source = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/components/field_value.html"
    ).read_text()
    assert "dynamic/components/value.html" in source
    assert "status_badge_class" in source


def test_structured_json_control_exists_only_at_field_boundary() -> None:
    value_source = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/components/value.html"
    ).read_text()
    field_source = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/components/field_value.html"
    ).read_text()
    assert "Technical JSON" not in value_source
    assert field_source.count("Technical JSON") == 1


def test_semantic_detail_projection_is_renderer_neutral() -> None:
    source = Path(
        "src/cobalt_wren/apps/automation/ui/detail_presentations.py"
    ).read_text()
    assert "template_name" not in source
    assert "dynamic/components" not in source
    assert "tabler" not in source.lower()
    assert "bootstrap" not in source.lower()
    assert "bg-" not in source


def test_selected_detail_pages_share_one_semantic_renderer() -> None:
    source = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/detail.html"
    ).read_text()
    semantic = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/components/semantic_detail.html"
    ).read_text()
    assert "detail_presentation" in source
    assert "semantic_detail.html" in source
    assert "spans" not in semantic
    assert "events" not in semantic
    assert "artifacts" not in semantic
    assert "checkpoints" not in semantic


def test_failure_diagnostic_component_is_registered_after_current_state() -> None:
    source = Path(
        "src/cobalt_wren/apps/web/presentation/run_components.py"
    ).read_text()
    assert 'RunComponentSpec("run.failure_diagnostic"' in source
    assert source.index('RunComponentSpec("run.current_state"') < source.index(
        'RunComponentSpec("run.failure_diagnostic"'
    )


def test_failure_diagnostic_template_uses_shared_value_renderer() -> None:
    source = Path(
        "src/cobalt_wren/apps/web/templates/dynamic/components/run_failure_diagnostic.html"
    ).read_text()
    assert "dynamic/components/value.html" in source
    assert "Technical JSON" not in source
    assert "live.failure.input_value" in source
    assert "live.failure.event_value" in source
