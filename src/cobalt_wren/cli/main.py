from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from cobalt_wren.scaffold.workflow_package import (
    WorkflowScaffoldOptions,
    create_workflow_scaffold,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cobalt-wren")
    parser.add_argument(
        "--config", type=Path, help="Path to deployment JSON configuration"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser(
        "init-workflow", help="Create an external workflow package"
    )
    init.add_argument("--name", required=True)
    init.add_argument("--kind", required=True)
    init.add_argument(
        "--framework", choices=("plain-python", "native", "langgraph"), default="plain-python"
    )
    init.add_argument("--capability", choices=("execute", "resume"), default="execute")
    init.add_argument("--artifact-store", action="store_true")
    init.add_argument("--checkpoint-store", action="store_true")
    init.add_argument("--provider-profile", action="append", default=[])
    init.add_argument("--tool", action="append", default=[])
    init.add_argument("--event-sink", action="append", default=[])
    init.add_argument("--output", type=Path, default=Path.cwd())
    init.add_argument("--force", action="store_true")

    native_run = subcommands.add_parser("native-run", help="Run a Native workflow locally")
    native_run.add_argument("target", help="Native workflow target using module:object syntax")
    native_run.add_argument("--input", dest="input_json", default="{}", help="Inline JSON object")
    native_run.add_argument("--input-file", type=Path)
    native_run.add_argument("--kind", default="local.native.workflow")
    native_run.add_argument("--run-id", type=int, default=1)

    native_validate = subcommands.add_parser("native-validate", help="Validate a Native workflow and local configuration")
    native_validate.add_argument("target", help="Native workflow target using module:object syntax")
    native_validate.add_argument("--input", dest="input_json")
    native_validate.add_argument("--input-file", type=Path)
    native_validate.add_argument("--kind", default="local.native.workflow")
    native_validate.add_argument("--strict-requirements", action="store_true", help="Treat undeclared requirement warnings as validation failures")

    native_inspect = subcommands.add_parser("native-inspect", help="Inspect Native schemas and requirements without executing")
    native_inspect.add_argument("target", help="Native workflow target using module:object syntax")
    native_inspect.add_argument("--kind", default="local.native.workflow")

    subcommands.add_parser("migrate", help="Apply control-plane migrations")
    server = subcommands.add_parser(
        "runserver", help="Run the local control-plane server"
    )
    server.add_argument("address", nargs="?", default="127.0.0.1:8000")
    server.add_argument("--noreload", action="store_true")

    plugins = subcommands.add_parser("plugins", help="Inspect installed plugins")
    plugins.add_argument("action", choices=("list",))
    workflows = subcommands.add_parser(
        "workflows", help="Inspect workflow contributions"
    )
    workflows.add_argument("action", choices=("list", "validate"))
    workflows.add_argument("kind", nargs="?")

    runs = subcommands.add_parser("runs", help="Operate control-plane runs")
    runs.add_argument("action", choices=("start", "resume", "cancel", "retry"))
    runs.add_argument("run_id", type=int)
    runs.add_argument("--input", type=Path)
    runs.add_argument("--payload", type=Path)
    runs.add_argument("--checkpoint-id")

    artifacts = subcommands.add_parser("artifacts", help="Access artifacts")
    artifacts.add_argument("action", choices=("download",))
    artifacts.add_argument("artifact_id", type=int)
    artifacts.add_argument("--output", type=Path)

    worker = subcommands.add_parser(
        "worker", help="Run the database-backed execution worker"
    )
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--poll-seconds", type=float, default=1.0)
    worker.add_argument("--worker-id")

    subcommands.add_parser(
        "doctor", help="Diagnose configuration and deployment dependencies"
    )
    return parser


def _configure_environment(config: Path | None) -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "cobalt_wren.config.settings"
    )
    if config is not None:
        os.environ["COBALT_WREN_CONFIG_FILE"] = str(config.resolve())


def _django_setup() -> None:
    import django

    django.setup()


def _json_file(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object")
    return value


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str))


def _run_init(args: argparse.Namespace) -> int:
    target = create_workflow_scaffold(
        WorkflowScaffoldOptions(
            distribution_name=args.name,
            workflow_kind=args.kind,
            framework=args.framework,
            resumable=args.capability == "resume",
            artifact_store=args.artifact_store,
            checkpoint_store=args.checkpoint_store,
            provider_profiles=tuple(args.provider_profile),
            tools=tuple(args.tool),
            event_sinks=tuple(args.event_sink),
            output_directory=args.output,
            force=args.force,
        )
    )
    print(target)
    return 0


def _run_native_local(args: argparse.Namespace) -> int:
    from cobalt_wren.native.local import load_native_workflow, run_native_workflow

    payload = _json_file(args.input_file) if args.input_file is not None else json.loads(args.input_json)
    if not isinstance(payload, dict):
        raise ValueError("Native input must be a JSON object")
    config = {"version": 1}
    if args.config is not None:
        loaded = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("deployment config must be a JSON object")
        config = loaded
    workflow = load_native_workflow(args.target)
    try:
        result = run_native_workflow(
            workflow, payload, workflow_kind=args.kind, config=config, run_id=args.run_id
        )
    except Exception as exc:
        cause: BaseException = exc
        while cause.__cause__ is not None:
            cause = cause.__cause__
        notes = [str(note) for note in getattr(cause, "__notes__", ())]
        print(
            json.dumps(
                {
                    "status": "failed",
                    "workflow": workflow.name,
                    "workflow_kind": args.kind,
                    "cause_type": type(cause).__name__,
                    "cause": str(cause),
                    "context": notes,
                    "next_action": "Fix the reported input or step implementation and run the command again.",
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    _print_json({
        "workflow_kind": result.workflow_kind,
        "status": result.status,
        "output": result.output,
        "metadata": result.metadata,
        "input_schema": workflow.input_schema,
        "output_schema": workflow.output_schema,
    })
    return 0


def _run_native_validate(args: argparse.Namespace) -> int:
    from cobalt_wren.native.local import load_native_workflow, validate_native_workflow

    config = {"version": 1}
    if args.config is not None:
        loaded = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("deployment config must be a JSON object")
        config = loaded
    sample = None
    if args.input_file is not None:
        sample = _json_file(args.input_file)
    elif args.input_json is not None:
        loaded_input = json.loads(args.input_json)
        if not isinstance(loaded_input, dict):
            raise ValueError("Native input must be a JSON object")
        sample = loaded_input
    workflow = load_native_workflow(args.target)
    try:
        report = validate_native_workflow(
            workflow, workflow_kind=args.kind, config=config, sample_input=sample
        )
    except Exception as exc:
        diagnostic: BaseException = exc
        cause: BaseException = exc
        while cause.__cause__ is not None:
            cause = cause.__cause__
        _print_json({
            "status": "invalid",
            "workflow": workflow.name,
            "cause_type": type(cause).__name__,
            "cause": str(cause),
            "issues": list(getattr(diagnostic, "issues", ())),
            "suggestions": list(getattr(diagnostic, "suggestions", ())),
        })
        return 1
    requirements = report.requirements
    if args.strict_requirements and report.warnings:
        _print_json({
            "status": "invalid",
            "workflow": report.workflow_name,
            "cause_type": "NativeRequirementLintError",
            "cause": "Native requirement declarations are incomplete.",
            "issues": [str(item["message"]) for item in report.warnings],
            "suggestions": [],
            "warnings": list(report.warnings),
        })
        return 1
    _print_json({
        "status": "valid",
        "workflow": report.workflow_name,
        "workflow_kind": report.workflow_kind,
        "input_schema": report.input_schema,
        "output_schema": report.output_schema,
        "requirements": {
            "provider_profiles": list(requirements.provider_profiles),
            "tools": list(requirements.tools),
            "artifact_store": requirements.artifact_store,
            "checkpoint_store": requirements.checkpoint_store,
            "event_sinks": list(requirements.event_sinks),
        },
        "warnings": list(report.warnings),
    })
    return 0


def _run_native_inspect(args: argparse.Namespace) -> int:
    from cobalt_wren.native.local import lint_native_requirements, load_native_workflow

    workflow = load_native_workflow(args.target)
    requirements = workflow.requirements
    _print_json({
        "workflow": workflow.name,
        "workflow_kind": args.kind,
        "input_schema": workflow.input_schema,
        "output_schema": workflow.output_schema,
        "requirements": {
            "provider_profiles": list(requirements.provider_profiles),
            "tools": list(requirements.tools),
            "artifact_store": requirements.artifact_store,
            "checkpoint_store": requirements.checkpoint_store,
            "event_sinks": list(requirements.event_sinks),
        },
        "limitations": [
            "No durable resume or arbitrary Python state restoration",
            "Synchronous step timeouts cannot forcibly terminate worker threads",
        ],
        "warnings": list(lint_native_requirements(workflow)),
    })
    return 0


def _run_django_command(command: str, *args: str) -> int:
    _django_setup()
    from django.core.management import call_command

    call_command(command, *args)
    return 0


def _run_plugins() -> int:
    from cobalt_wren.api.plugins import discover_plugins

    rows = [
        {
            "name": plugin.metadata.name,
            "version": plugin.metadata.version,
            "types": list(plugin.metadata.plugin_types),
            "provides": {
                key: list(value) for key, value in plugin.metadata.provides.items()
            },
        }
        for plugin in discover_plugins()
    ]
    _print_json(rows)
    return 0


def _run_workflows(action: str, kind: str | None) -> int:
    from cobalt_wren.api.engine import create_engine
    from cobalt_wren.api.plugins import discover_plugins
    from cobalt_wren.apps.automation.services.runtime import (
        load_deployment_package_config_from_settings,
    )

    if action == "list":
        plugins = discover_plugins()
        _print_json(
            [
                {
                    "kind": item.kind,
                    "name": item.definition.metadata.name,
                    "version": item.definition.metadata.version,
                }
                for plugin in plugins
                for item in plugin.contributions.workflows
            ]
        )
        return 0
    engine = create_engine(
        load_deployment_package_config_from_settings(), discover_plugins=True
    )
    if not kind:
        raise ValueError("workflow kind is required for validate")
    prepared = engine.prepare_workflow(kind)
    _print_json(
        {
            "kind": prepared.kind,
            "engine_generation": prepared.engine_generation,
            "metadata": prepared.metadata.metadata if prepared.metadata else {},
        }
    )
    return 0


def _run_run_action(args: argparse.Namespace) -> int:
    from cobalt_wren.apps.automation.models import Run
    from cobalt_wren.apps.automation.services.dispatch import (
        dispatch_cancel,
        dispatch_resume,
        dispatch_retry,
        dispatch_start,
    )

    run = Run.objects.select_related("workflow").get(pk=args.run_id)
    if args.action == "start":
        if args.input is not None:
            run.input_payload = _json_file(args.input)
            run.save(update_fields=["input_payload", "updated_at"])
        dispatched = dispatch_start(run=run)
    elif args.action == "resume":
        dispatched = dispatch_resume(
            run=run,
            payload=_json_file(args.payload),
            checkpoint_id=args.checkpoint_id,
        )
    elif args.action == "cancel":
        dispatched = dispatch_cancel(run=run)
    else:
        dispatched = dispatch_retry(run=run)

    if dispatched.job is not None:
        _print_json(
            {
                "run_id": dispatched.run.pk,
                "status": dispatched.run.status,
                "job_id": dispatched.job.pk,
                "job_status": dispatched.job.status,
            }
        )
    else:
        result = dispatched.result
        assert result is not None
        _print_json(
            {
                "run_id": result.run.pk,
                "status": result.run.status,
                "message": result.message,
                "output": result.output_payload,
            }
        )
    return 0


def _run_artifact(args: argparse.Namespace) -> int:
    from cobalt_wren.apps.automation.services.artifact_access import (
        load_artifact_body,
    )

    loaded = load_artifact_body(args.artifact_id)
    output = args.output or Path(loaded.artifact.storage_key).name
    output = Path(output)
    output.write_bytes(loaded.body)
    print(output.resolve())
    return 0


def _run_doctor() -> int:
    checks: list[dict[str, object]] = []
    ok = True
    try:
        from django.db import connection

        connection.ensure_connection()
        checks.append({"name": "database", "status": "ok", "vendor": connection.vendor})
    except Exception as exc:
        checks.append({"name": "database", "status": "error", "message": str(exc)})
        ok = False
    try:
        from django.core.management import call_command
        from io import StringIO

        output = StringIO()
        call_command("showmigrations", "automation", plan=True, stdout=output)
        pending = [line for line in output.getvalue().splitlines() if "[ ]" in line]
        checks.append(
            {
                "name": "migrations",
                "status": "ok" if not pending else "error",
                "pending": pending,
            }
        )
        ok = ok and not pending
    except Exception as exc:
        checks.append({"name": "migrations", "status": "error", "message": str(exc)})
        ok = False
    try:
        from cobalt_wren.api.plugins import discover_plugins

        plugins = discover_plugins()
        checks.append(
            {
                "name": "plugins",
                "status": "ok",
                "count": len(plugins),
                "plugins": [plugin.metadata.name for plugin in plugins],
            }
        )
    except Exception as exc:
        checks.append({"name": "plugins", "status": "error", "message": str(exc)})
        ok = False
    try:
        from cobalt_wren.apps.automation.services.runtime import (
            get_run_execution_services,
        )

        services = get_run_execution_services()
        services.engine_owner.get_engine()
        checks.append(
            {
                "name": "runtime",
                "status": "ok",
                "signature": services.engine_owner.generation.signature,
            }
        )
    except Exception as exc:
        checks.append({"name": "runtime", "status": "error", "message": str(exc)})
        ok = False
    _print_json({"status": "ok" if ok else "error", "checks": checks})
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init-workflow":
        return _run_init(args)
    if args.command == "native-run":
        return _run_native_local(args)
    if args.command == "native-validate":
        return _run_native_validate(args)
    if args.command == "native-inspect":
        return _run_native_inspect(args)
    _configure_environment(args.config)
    _django_setup()
    if args.command == "migrate":
        from django.core.management import call_command

        call_command("migrate", interactive=False)
        return 0
    if args.command == "runserver":
        from django.core.management import call_command

        call_command("runserver", args.address, use_reloader=not args.noreload)
        return 0
    if args.command == "plugins":
        return _run_plugins()
    if args.command == "workflows":
        return _run_workflows(args.action, args.kind)
    if args.command == "runs":
        return _run_run_action(args)
    if args.command == "artifacts":
        return _run_artifact(args)
    if args.command == "worker":
        import time
        from cobalt_wren.apps.automation.services.jobs import (
            claim_next_job,
            execute_job,
            recover_stale_jobs,
        )

        while True:
            recover_stale_jobs()
            job = claim_next_job(worker_id=args.worker_id)
            if job is not None:
                execute_job(job)
            if args.once:
                return 0
            if job is None:
                time.sleep(max(0.1, args.poll_seconds))
    if args.command == "doctor":
        return _run_doctor()
    return 2


if __name__ == "__main__":
    sys.exit(main())
