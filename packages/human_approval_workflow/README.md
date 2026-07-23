# Human Approval Workflow

Independent LangGraph workflow distribution used to validate framework-neutral pause/resume support.

Patterns covered:

- `interrupt()`-based human approval
- durable opaque checkpoint persistence
- re-prepare before resume
- approve and reject branches
- revise-to-second-pause loop
- final decision artifact

The platform sees only `execute`, optional `resume`, `WorkflowResumeRequest`, and `WorkflowExecutionResult`. LangGraph state and checkpoint serialization remain inside this package.
