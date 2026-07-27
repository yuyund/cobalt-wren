# OSS Integration Workflows

A separately installable test distribution proving that external packages can contribute LangGraph and LlamaIndex Workflows implementations through the public plugin SPI.

The distribution exposes the `oss-integrations` entry point in the `cobalt_wren.plugins` group and contributes:

- `external.oss.langgraph`
- `external.oss.llamaindex`

It imports foundation APIs only from:

- `cobalt_wren.api.plugins`
- `cobalt_wren.api.workflow`
- `cobalt_wren.integrations.langgraph`
- `cobalt_wren.integrations.llamaindex_workflows`

The clean-room integration test builds this project and the foundation as wheels, installs them into a fresh virtual environment, discovers the entry point, migrates a temporary Django database, executes both workflows, persists spans and projections, and renders their Run detail pages.
