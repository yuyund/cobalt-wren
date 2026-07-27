# Native Quick Start

## Create

```bash
cobalt-wren init-workflow --name document-review --kind acme.document_review --framework native
```

## Author

```python
from typing import TypedDict
from cobalt_wren.native import NativeWorkflowContext, workflow

class Request(TypedDict):
    document_id: str

class Result(TypedDict):
    status: str

@workflow("Document review")
async def review(ctx: NativeWorkflowContext, request: Request) -> Result:
    status = await ctx.step("review", review_document, request["document_id"])
    await ctx.progress.update(current=1, total=1, message="Complete")
    return {"status": status}
```

## Inspect and validate

```bash
cobalt-wren native-inspect package.workflow:review
cobalt-wren native-validate package.workflow:review --input '{"document_id":"D-100"}'
```

`native-inspect` does not assemble runtime dependencies. `native-validate` validates configuration, declared requirements, and optional sample input.

## Run

```bash
cobalt-wren native-run package.workflow:review --input '{"document_id":"D-100"}'
```

Input and output are checked against inferred schemas. A validation failure occurs before the workflow body for input and after output normalization for output.
