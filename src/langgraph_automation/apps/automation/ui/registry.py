"""Registry for allowlisted UI models, fields, actions, and related sections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from langgraph_automation.apps.automation.models.artifact import Artifact
from langgraph_automation.apps.automation.models.checkpoint import CheckpointMetadata
from langgraph_automation.apps.automation.models.event import RunEvent
from langgraph_automation.apps.automation.models.execution import ExecutionSpan
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.policies.runs import (
    PolicyResult,
    can_cancel_run,
    can_retry_run,
    can_start_run,
)
from langgraph_automation.apps.automation.selectors.artifacts import (
    list_artifacts_for_run,
)
from langgraph_automation.apps.automation.selectors.checkpoints import (
    list_checkpoints_for_run,
)
from langgraph_automation.apps.automation.selectors.events import list_events_for_run
from langgraph_automation.apps.automation.selectors.runs import get_run, list_runs
from langgraph_automation.apps.automation.selectors.spans import list_spans_for_run
from langgraph_automation.apps.automation.selectors.workflows import (
    get_workflow,
    list_workflows,
)
from langgraph_automation.apps.automation.services.dispatch import (
    dispatch_cancel,
    dispatch_retry,
    dispatch_start,
)

Selector = Callable[[Any | None, Any | None], Iterable[object]]
DetailSelector = Callable[[int, Any | None], object | None]
ActionHandler = Callable[[Any, int, Any | None, Any | None], object]
PolicyCallable = Callable[[Any | None, Any], PolicyResult]


@dataclass(frozen=True)
class RelatedSectionConfig:
    model_key: str
    name: str
    title: str
    selector: Selector
    columns: list[str]
    empty_message: str = "No records found"


@dataclass(frozen=True)
class ActionConfig:
    name: str
    label: str
    handler: ActionHandler
    method: str = "POST"
    danger: bool = False
    confirm: str | None = None
    policy: PolicyCallable | None = None


@dataclass(frozen=True)
class ModelUIConfig:
    model_key: str
    model: type
    title: str
    list_fields: list[str]
    detail_fields: list[str]
    list_selector: Selector
    detail_selector: DetailSelector
    actions: list[ActionConfig] = field(default_factory=list)
    related_sections: list[RelatedSectionConfig] = field(default_factory=list)
    readonly_fields: list[str] = field(default_factory=list)
    hidden_fields: list[str] = field(default_factory=list)
    default_ordering: list[str] | None = None
    search_fields: list[str] | None = None
    filter_fields: list[str] | None = None
    page_size: int = 50


MODEL_UI_REGISTRY: dict[str, ModelUIConfig] = {}


def register_model_ui(model_key: str, config: ModelUIConfig) -> None:
    MODEL_UI_REGISTRY[model_key] = config


def get_model_ui_config(model_key: str) -> ModelUIConfig | None:
    return MODEL_UI_REGISTRY.get(model_key)


def _wrap_list_selector(
    selector: Callable[[Any | None, Any | None], Iterable[object]],
) -> Selector:
    return selector


def _wrap_detail_selector(
    selector: Callable[[int, Any | None], object | None],
) -> DetailSelector:
    return selector


def _run_related_selector(
    selector: Callable[[Run, Any | None], Iterable[object]],
) -> Selector:
    def wrapped(obj: Any | None, actor: Any | None) -> Iterable[object]:
        if not isinstance(obj, Run):
            return []
        return selector(obj, actor)

    return wrapped


def _run_action_handler(action: Callable[..., object]) -> ActionHandler:
    def wrapped(
        actor: Any, object_id: int, request: Any | None, obj: Any | None
    ) -> object:
        if obj is None:
            obj = get_run(object_id)
        if obj is None:
            raise LookupError(f"Run {object_id} not found")
        return action(run=obj, actor=actor)

    return wrapped


def register_default_model_ui() -> None:
    register_model_ui(
        "workflows",
        ModelUIConfig(
            model_key="workflows",
            model=Workflow,
            title="Workflow",
            list_fields=["name", "description", "created_at", "updated_at"],
            detail_fields=[
                "name",
                "description",
                "definition_payload_summary",
                "created_at",
                "updated_at",
            ],
            list_selector=_wrap_list_selector(lambda _obj, _actor: list_workflows()),
            detail_selector=_wrap_detail_selector(
                lambda object_id, _actor: get_workflow(object_id)
            ),
            search_fields=["name", "description"],
            filter_fields=["created_at"],
        ),
    )
    register_model_ui(
        "runs",
        ModelUIConfig(
            model_key="runs",
            model=Run,
            title="Run",
            list_fields=["name", "workflow", "status", "thread_id", "created_at"],
            detail_fields=[
                "name",
                "workflow",
                "status",
                "thread_id",
                "input_payload_summary",
                "output_payload_summary",
                "error_message",
                "started_at",
                "finished_at",
                "last_event_at",
                "last_span_name",
                "created_at",
                "updated_at",
            ],
            list_selector=_wrap_list_selector(lambda _obj, _actor: list_runs()),
            detail_selector=_wrap_detail_selector(
                lambda object_id, _actor: get_run(object_id)
            ),
            actions=[
                ActionConfig(
                    name="start",
                    label="Start",
                    handler=_run_action_handler(dispatch_start),
                    policy=can_start_run,
                ),
                ActionConfig(
                    name="cancel",
                    label="Cancel",
                    handler=_run_action_handler(dispatch_cancel),
                    danger=True,
                    confirm="Cancel this run?",
                    policy=can_cancel_run,
                ),
                ActionConfig(
                    name="retry",
                    label="Retry",
                    handler=_run_action_handler(dispatch_retry),
                    policy=can_retry_run,
                ),
            ],
            related_sections=[
                RelatedSectionConfig(
                    model_key="spans",
                    name="spans",
                    title="Execution Spans",
                    selector=_run_related_selector(
                        lambda run, _actor: list_spans_for_run(run.pk)
                    ),
                    columns=[
                        "run",
                        "span_type",
                        "name",
                        "status",
                        "node_name",
                        "duration_ms",
                        "created_at",
                    ],
                    empty_message="No spans yet",
                ),
                RelatedSectionConfig(
                    model_key="events",
                    name="events",
                    title="Run Events",
                    selector=_run_related_selector(
                        lambda run, _actor: list_events_for_run(run.pk)
                    ),
                    columns=["run", "event_type", "level", "node_name", "created_at"],
                    empty_message="No events yet",
                ),
                RelatedSectionConfig(
                    model_key="artifacts",
                    name="artifacts",
                    title="Artifacts",
                    selector=_run_related_selector(
                        lambda run, _actor: list_artifacts_for_run(run.pk)
                    ),
                    columns=[
                        "run",
                        "name",
                        "kind",
                        "content_type",
                        "size",
                        "created_at",
                    ],
                    empty_message="No artifacts yet",
                ),
                RelatedSectionConfig(
                    model_key="checkpoints",
                    name="checkpoints",
                    title="Checkpoints",
                    selector=_run_related_selector(
                        lambda run, _actor: list_checkpoints_for_run(run.pk)
                    ),
                    columns=[
                        "run",
                        "thread_id",
                        "checkpoint_id",
                        "backend",
                        "node_name",
                        "created_at",
                    ],
                    empty_message="No checkpoints yet",
                ),
            ],
            default_ordering=["-created_at"],
            search_fields=["name", "thread_id"],
            filter_fields=["status", "workflow"],
        ),
    )
    register_model_ui(
        "spans",
        ModelUIConfig(
            model_key="spans",
            model=ExecutionSpan,
            title="Execution Span",
            list_fields=[
                "run",
                "span_type",
                "name",
                "status",
                "node_name",
                "duration_ms",
                "created_at",
            ],
            detail_fields=[
                "run",
                "parent",
                "span_type",
                "name",
                "status",
                "node_name",
                "attempt",
                "started_at",
                "finished_at",
                "duration_ms",
                "input_summary",
                "output_summary",
                "error_message",
                "metrics_summary",
                "metadata_summary",
                "external_trace_id",
                "external_span_id",
                "created_at",
                "updated_at",
            ],
            list_selector=_wrap_list_selector(
                lambda _obj, _actor: ExecutionSpan.objects.select_related(
                    "run", "parent"
                ).all()
            ),
            detail_selector=_wrap_detail_selector(
                lambda object_id, _actor: (
                    ExecutionSpan.objects.select_related("run", "parent")
                    .filter(pk=object_id)
                    .first()
                )
            ),
            filter_fields=["span_type", "status", "node_name"],
            search_fields=["name", "node_name", "error_message"],
        ),
    )
    register_model_ui(
        "events",
        ModelUIConfig(
            model_key="events",
            model=RunEvent,
            title="Run Event",
            list_fields=["run", "event_type", "level", "node_name", "created_at"],
            detail_fields=[
                "run",
                "span",
                "event_type",
                "level",
                "node_name",
                "message",
                "payload_summary",
                "created_at",
            ],
            list_selector=_wrap_list_selector(
                lambda _obj, _actor: RunEvent.objects.select_related(
                    "run", "span"
                ).all()
            ),
            detail_selector=_wrap_detail_selector(
                lambda object_id, _actor: (
                    RunEvent.objects.select_related("run", "span")
                    .filter(pk=object_id)
                    .first()
                )
            ),
            filter_fields=["event_type", "level", "node_name"],
            search_fields=["message"],
        ),
    )
    register_model_ui(
        "artifacts",
        ModelUIConfig(
            model_key="artifacts",
            model=Artifact,
            title="Artifact",
            list_fields=["run", "name", "kind", "content_type", "size", "created_at"],
            detail_fields=[
                "run",
                "span",
                "name",
                "kind",
                "storage_key",
                "content_type",
                "size",
                "metadata_summary",
                "created_at",
            ],
            list_selector=_wrap_list_selector(
                lambda _obj, _actor: Artifact.objects.select_related(
                    "run", "span"
                ).all()
            ),
            detail_selector=_wrap_detail_selector(
                lambda object_id, _actor: (
                    Artifact.objects.select_related("run", "span")
                    .filter(pk=object_id)
                    .first()
                )
            ),
            filter_fields=["kind", "content_type"],
            search_fields=["name", "storage_key"],
        ),
    )
    register_model_ui(
        "checkpoints",
        ModelUIConfig(
            model_key="checkpoints",
            model=CheckpointMetadata,
            title="Checkpoint Metadata",
            list_fields=[
                "run",
                "thread_id",
                "checkpoint_id",
                "backend",
                "node_name",
                "created_at",
            ],
            detail_fields=[
                "run",
                "span",
                "thread_id",
                "checkpoint_id",
                "checkpoint_namespace",
                "backend",
                "node_name",
                "state_summary",
                "created_at",
            ],
            list_selector=_wrap_list_selector(
                lambda _obj, _actor: CheckpointMetadata.objects.select_related(
                    "run", "span"
                ).all()
            ),
            detail_selector=_wrap_detail_selector(
                lambda object_id, _actor: (
                    CheckpointMetadata.objects.select_related("run", "span")
                    .filter(pk=object_id)
                    .first()
                )
            ),
            filter_fields=["backend", "node_name"],
            search_fields=["thread_id", "checkpoint_id"],
        ),
    )


register_default_model_ui()
