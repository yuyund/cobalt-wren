"""LLM integration contracts and observation wrappers.

Concrete provider adapters are optional and must be imported from their
provider-specific modules after the consumer installs that provider package.
"""

from .base import LLMClient, LLMRequest, LLMResult
from .observed_client import ObservedLLMClient

__all__ = [
    "LLMClient",
    "LLMRequest",
    "LLMResult",
    "ObservedLLMClient",
]
