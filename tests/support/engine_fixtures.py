"""Test fixtures for engine and service integration."""

from __future__ import annotations


def create_reference_engine_config() -> dict[str, object]:
    return {
        'version': 1,
        'environment': 'test',
        'providers': {
            'default': {
                'provider': 'litellm',
                'model': 'gpt-4.1-mini',
                'secrets': {
                    'api_key': {
                        'source': 'env',
                        'name': 'OPENAI_API_KEY',
                    },
                },
            },
        },
        'tools': {
            'allowlist': ['echo'],
        },
    }
