from __future__ import annotations

import json
from pathlib import Path
import sys

from cobalt_wren.cli.main import main


def _module(tmp_path: Path) -> str:
    path = tmp_path / "native_cli_example.py"
    path.write_text(
        """from typing import TypedDict
from cobalt_wren.native import NativeWorkflowContext, workflow
class Request(TypedDict):
    name: str
@workflow('CLI example')
async def example(ctx: NativeWorkflowContext, request: Request) -> dict[str, str]:
    del ctx
    return {'message': request['name']}
"""
    )
    sys.path.insert(0, str(tmp_path))
    return "native_cli_example:example"


def test_native_validate_reports_schema_and_valid_sample(tmp_path: Path, capsys) -> None:
    target = _module(tmp_path)
    try:
        assert main(["native-validate", target, "--input", '{"name":"Yudai"}']) == 0
    finally:
        sys.path.remove(str(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "valid"
    assert payload["input_schema"]["required"] == ["name"]
    assert payload["requirements"]["artifact_store"] is False


def test_native_validate_reports_actionable_input_issues(tmp_path: Path, capsys) -> None:
    target = _module(tmp_path)
    try:
        assert main(["native-validate", target, "--input", '{}']) == 1
    finally:
        sys.path.remove(str(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "invalid"
    assert payload["issues"] == ["$.name: field is required"]


def test_native_inspect_reports_requirements_without_engine_setup(tmp_path: Path, capsys) -> None:
    path = tmp_path / "native_inspect_example.py"
    path.write_text(
        """from collections.abc import Mapping
from cobalt_wren.native import NativeWorkflowContext, workflow
@workflow('Inspect', provider_profiles=('default',), tools=('echo',), artifact_store=True)
async def example(ctx: NativeWorkflowContext, request: Mapping[str, object]):
    del ctx, request
    return {}
"""
    )
    sys.path.insert(0, str(tmp_path))
    try:
        assert main(["native-inspect", "native_inspect_example:example"]) == 0
    finally:
        sys.path.remove(str(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["requirements"]["provider_profiles"] == ["default"]
    assert payload["requirements"]["tools"] == ["echo"]
    assert payload["requirements"]["artifact_store"] is True
    assert any("durable resume" in item.lower() for item in payload["limitations"])


def test_native_validate_returns_config_suggestion_for_missing_provider(tmp_path: Path, capsys) -> None:
    path = tmp_path / "native_required_example.py"
    path.write_text(
        """from collections.abc import Mapping
from cobalt_wren.native import NativeWorkflowContext, workflow
@workflow('Required', provider_profiles=('default',))
async def example(ctx: NativeWorkflowContext, request: Mapping[str, object]):
    del ctx, request
    return {}
"""
    )
    sys.path.insert(0, str(tmp_path))
    try:
        assert main(["native-validate", "native_required_example:example"]) == 1
    finally:
        sys.path.remove(str(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["issues"] == ["missing provider_profile 'default'"]
    assert payload["suggestions"][0]["config"]["providers"]["llm"]["default"]["provider"] == "litellm"


def test_native_validate_reports_warning_without_changing_valid_status(tmp_path: Path, capsys) -> None:
    path = tmp_path / "native_lint_example.py"
    path.write_text(
        """from collections.abc import Mapping
from cobalt_wren.native import NativeWorkflowContext, workflow
@workflow('Lint')
async def example(ctx: NativeWorkflowContext, request: Mapping[str, object]):
    del request
    await ctx.tool.run('lookup', 'echo')
    return {}
"""
    )
    sys.path.insert(0, str(tmp_path))
    try:
        assert main(["native-validate", "native_lint_example:example"]) == 0
    finally:
        sys.path.remove(str(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "valid"
    assert payload["warnings"][0]["requirement_type"] == "tool"
    assert payload["warnings"][0]["requirement_name"] == "echo"


def test_native_validate_strict_requirements_fails_on_warning(tmp_path: Path, capsys) -> None:
    path = tmp_path / "native_strict_lint_example.py"
    path.write_text(
        """from collections.abc import Mapping
from cobalt_wren.native import NativeWorkflowContext, workflow
@workflow('Strict lint')
async def example(ctx: NativeWorkflowContext, request: Mapping[str, object]):
    del request
    await ctx.tool.run('lookup', 'echo')
    return {}
"""
    )
    sys.path.insert(0, str(tmp_path))
    try:
        assert main(["native-validate", "native_strict_lint_example:example", "--strict-requirements"]) == 1
    finally:
        sys.path.remove(str(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "invalid"
    assert payload["cause_type"] == "NativeRequirementLintError"
    assert payload["warnings"][0]["code"] == "NATIVE_REQUIREMENT_UNDECLARED"
