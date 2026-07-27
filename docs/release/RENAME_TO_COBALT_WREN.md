# Rename to Cobalt Wren

The public distribution is `cobalt-wren`, the Python package is `cobalt_wren`, and the CLI command is `cobalt-wren`.

The Django app label `automation`, existing database table names, workflow kinds, integration IDs, and event kinds remain unchanged. These are operational identities rather than branding.

For transition safety, the runtime accepts the legacy `LANGGRAPH_AUTOMATION_*` environment variables when the corresponding `COBALT_WREN_*` variable is absent. Plugin discovery uses only the authoritative `cobalt_wren.plugins` entry-point group. New packages and deployments must use the Cobalt Wren names.
