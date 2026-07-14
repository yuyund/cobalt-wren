"""Framework error behavior tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import (
    ConfigError,
    FrameworkError,
    PluginRegistrationError,
    PluginResolutionError,
    PluginValidationError,
    RuntimeAssemblyError,
    SafetyBoundaryError,
)


def test_framework_error_stores_safe_message_and_str_matches() -> None:
    error = FrameworkError(
        'Configuration is invalid.',
        code='CONFIG_INVALID',
        category='config',
        component='config_loader',
    )

    assert error.safe_message == 'Configuration is invalid.'
    assert str(error) == 'Configuration is invalid.'
    assert error.code == 'CONFIG_INVALID'
    assert error.category == 'config'
    assert error.component == 'config_loader'
    assert error.retryable is None


def test_framework_error_stores_optional_fields_and_shallow_copies_metadata() -> None:
    metadata = {'plugin_name': 'github', 'nested': {'secret': 'value'}}

    error = FrameworkError(
        'Configuration is invalid.',
        code='CONFIG_INVALID',
        category='config',
        component='config_loader',
        retryable=True,
        metadata=metadata,
    )

    assert error.retryable is True
    assert error.metadata == metadata
    assert error.metadata is not metadata
    metadata['plugin_name'] = 'changed'
    assert error.metadata['plugin_name'] == 'github'


def test_framework_error_to_safe_dict_excludes_unsafe_fields_and_copies_metadata() -> None:
    error = FrameworkError(
        'Configuration is invalid.',
        code='CONFIG_INVALID',
        category='config',
        component='config_loader',
        retryable=False,
        metadata={'plugin_name': 'github'},
    )

    payload = error.to_safe_dict()

    assert payload == {
        'category': 'config',
        'code': 'CONFIG_INVALID',
        'safe_message': 'Configuration is invalid.',
        'component': 'config_loader',
        'retryable': False,
        'metadata': {'plugin_name': 'github'},
    }
    assert 'cause' not in payload
    assert 'traceback' not in payload
    assert 'diagnostic_message' not in payload
    assert payload['metadata'] is not error.metadata


def test_framework_error_to_safe_dict_omits_empty_optional_values() -> None:
    error = FrameworkError('Configuration is invalid.', code='CONFIG_INVALID', category='config')

    payload = error.to_safe_dict()

    assert payload == {
        'category': 'config',
        'code': 'CONFIG_INVALID',
        'safe_message': 'Configuration is invalid.',
    }


@pytest.mark.parametrize(
    ('kwargs', 'message'),
    [
        ({'safe_message': '', 'code': 'CONFIG_INVALID', 'category': 'config'}, 'safe_message must not be empty'),
        ({'safe_message': 'x', 'code': '', 'category': 'config'}, 'code must not be empty'),
        ({'safe_message': 'x', 'code': 'CONFIG_INVALID', 'category': ''}, 'category must not be empty'),
    ],
)
def test_framework_error_validates_required_fields(kwargs: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        FrameworkError(**kwargs)


def test_category_specific_errors_fix_categories() -> None:
    assert ConfigError('x', code='CONFIG_INVALID').category == 'config'
    assert PluginRegistrationError('x', code='PLUGIN_INVALID').category == 'plugin_registration'
    assert PluginResolutionError('x', code='PLUGIN_UNKNOWN').category == 'plugin_resolution'
    assert PluginValidationError('x', code='PLUGIN_VALIDATION_FAILED').category == 'plugin_validation'
    assert RuntimeAssemblyError('x', code='RUNTIME_ASSEMBLY_FAILED').category == 'runtime_assembly'
    assert SafetyBoundaryError('x', code='SAFETY_FAILED').category == 'safety'


def test_category_specific_errors_do_not_accept_category_override() -> None:
    error = ConfigError('x', code='CONFIG_INVALID', component='config_loader')

    assert error.category == 'config'
    assert error.component == 'config_loader'
