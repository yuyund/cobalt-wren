"""Small JSON-schema inference helpers for Native workflow annotations."""

from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
import inspect
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints, is_typeddict


def schema_for_type(annotation: object) -> dict[str, object] | None:
    if annotation in {inspect.Signature.empty, Any, object, None}:
        return None
    model_schema = getattr(annotation, "model_json_schema", None)
    if callable(model_schema):
        value = model_schema()
        return dict(value) if isinstance(value, dict) else None
    if is_typeddict(annotation):
        hints = get_type_hints(annotation, include_extras=True)
        required_keys = set(getattr(annotation, "__required_keys__", ()))
        properties = {name: schema_for_type(value) or {} for name, value in hints.items()}
        object_schema: dict[str, object] = {"type": "object", "properties": properties}
        if required_keys:
            object_schema["required"] = sorted(required_keys)
        return object_schema
    if isinstance(annotation, type) and is_dataclass(annotation):
        hints = get_type_hints(annotation, include_extras=True)
        properties = {field.name: schema_for_type(hints.get(field.name, field.type)) or {} for field in fields(annotation)}
        required = [field.name for field in fields(annotation) if field.default is MISSING and field.default_factory is MISSING]
        dataclass_schema: dict[str, object] = {"type": "object", "properties": properties}
        if required:
            dataclass_schema["required"] = required
        return dataclass_schema
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        values = list(args)
        result: dict[str, object] = {"enum": values}
        if values and all(isinstance(value, str) for value in values):
            result["type"] = "string"
        return result
    if origin in {Union, UnionType}:
        schemas = [schema_for_type(item) or {} for item in args]
        return {"anyOf": schemas}
    if origin in {list, tuple, set, frozenset}:
        item = schema_for_type(args[0]) if args else None
        result = {"type": "array"}
        if item is not None:
            result["items"] = item
        return result
    if origin in {dict}:
        value_schema = schema_for_type(args[1]) if len(args) > 1 else None
        result = {"type": "object"}
        if value_schema is not None:
            result["additionalProperties"] = value_schema
        return result
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {"enum": [item.value for item in annotation]}
    primitive = {str: "string", int: "integer", float: "number", bool: "boolean"}
    if annotation in primitive:
        return {"type": primitive[annotation]}
    return None


def infer_workflow_schemas(function: object) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    try:
        if not callable(function):
            return None, None
        signature = inspect.signature(function)
        hints = get_type_hints(function, include_extras=True)
    except (TypeError, NameError):
        return None, None
    parameters = list(signature.parameters.values())
    request_annotation = inspect.Signature.empty
    if len(parameters) >= 2:
        request_annotation = hints.get(parameters[1].name, parameters[1].annotation)
    return_annotation = hints.get("return", signature.return_annotation)
    return schema_for_type(request_annotation), schema_for_type(return_annotation)


__all__ = ["NativeSchemaValidationError", "infer_workflow_schemas", "schema_for_type", "validate_schema_value"]


class NativeSchemaValidationError(ValueError):
    def __init__(self, issues: list[str], *, phase: str) -> None:
        self.issues = tuple(issues)
        self.phase = phase
        super().__init__(f"Native {phase} validation failed: " + "; ".join(issues))


def validate_schema_value(value: object, schema: object, *, phase: str, path: str = "$") -> None:
    if not isinstance(schema, dict):
        return
    issues: list[str] = []
    _collect_schema_issues(value, schema, path, issues)
    if issues:
        raise NativeSchemaValidationError(issues, phase=phase)


def _collect_schema_issues(value: object, schema: dict[str, object], path: str, issues: list[str]) -> None:
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        if not any(
            not _issues_for(value, option, path)
            for option in any_of
            if isinstance(option, dict)
        ):
            issues.append(f"{path}: value does not match any allowed schema")
        return
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        issues.append(f"{path}: expected one of {enum!r}")
        return
    expected = schema.get("type")
    if isinstance(expected, str) and not _matches_type(value, expected):
        issues.append(f"{path}: expected {expected}, got {type(value).__name__}")
        return
    if expected == "object" and isinstance(value, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    issues.append(f"{path}.{key}: field is required")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, nested_schema in properties.items():
                if key in value and isinstance(key, str) and isinstance(nested_schema, dict):
                    _collect_schema_issues(value[key], nested_schema, f"{path}.{key}", issues)
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            known = set(properties) if isinstance(properties, dict) else set()
            for key, nested in value.items():
                if key not in known:
                    _collect_schema_issues(nested, additional, f"{path}.{key}", issues)
    if expected == "array" and isinstance(value, (list, tuple)):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _collect_schema_issues(item, item_schema, f"{path}[{index}]", issues)


def _issues_for(value: object, schema: object, path: str) -> list[str]:
    issues: list[str] = []
    if isinstance(schema, dict):
        _collect_schema_issues(value, schema, path, issues)
    return issues


def _matches_type(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, (list, tuple))
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True
