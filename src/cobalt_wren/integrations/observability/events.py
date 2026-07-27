'''Event type and span type constants for observability.'''

from __future__ import annotations

SEMANTIC_PREFIX = 'semantic'

RUN_STARTED = 'run.started'
RUN_COMPLETED = 'run.completed'
RUN_FAILED = 'run.failed'
RUN_CANCELLED = 'run.cancelled'

SPAN_STARTED = 'span.started'
SPAN_COMPLETED = 'span.completed'
SPAN_FAILED = 'span.failed'
SPAN_CANCELLED = 'span.cancelled'

NODE_STARTED = 'node.started'
NODE_COMPLETED = 'node.completed'
NODE_FAILED = 'node.failed'

LLM_STARTED = 'llm.started'
LLM_COMPLETED = 'llm.completed'
LLM_FAILED = 'llm.failed'

TOOL_STARTED = 'tool.started'
TOOL_COMPLETED = 'tool.completed'
TOOL_FAILED = 'tool.failed'

ARTIFACT_CREATED = 'artifact.created'
CHECKPOINT_SAVED = 'checkpoint.saved'
STATE_UPDATED = 'state.updated'

LEVEL_DEBUG = 'debug'
LEVEL_INFO = 'info'
LEVEL_WARNING = 'warning'
LEVEL_ERROR = 'error'

SPAN_GRAPH = 'graph'
SPAN_NODE = 'node'
SPAN_LLM = 'llm'
SPAN_TOOL = 'tool'
SPAN_CHECKPOINT = 'checkpoint'
SPAN_ARTIFACT = 'artifact'


def semantic_event_type(name: str) -> str:
    normalized = name.strip().lstrip('.')
    if not normalized:
        return SEMANTIC_PREFIX
    if normalized.startswith(f'{SEMANTIC_PREFIX}.'):
        return normalized
    return f'{SEMANTIC_PREFIX}.{normalized}'
