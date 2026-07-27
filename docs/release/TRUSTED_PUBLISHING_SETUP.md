# Trusted Publishing Setup

Cobalt Wren uses separate GitHub environments and Trusted Publisher records for
TestPyPI and PyPI. No long-lived repository secret is required.

## GitHub environments

Create these environments after the repository exists:

- `testpypi`
- `pypi`

Optional required reviewers may be configured for both. Production publishing
should require review.

## TestPyPI publisher

Register a pending or normal Trusted Publisher with:

- owner: the GitHub account or organization that owns the repository
- repository: `cobalt-wren`
- workflow: `publish-testpypi.yml`
- environment: `testpypi`

Run **Publish to TestPyPI** manually. The release candidate version must be
unique on TestPyPI.

## PyPI publisher

Register the production Trusted Publisher with:

- owner: the GitHub account or organization that owns the repository
- repository: `cobalt-wren`
- workflow: `publish.yml`
- environment: `pypi`

Production publishing is triggered only by publishing a GitHub Release.

## Release candidate install check

```bash
python -m venv /tmp/cobalt-wren-testpypi
/tmp/cobalt-wren-testpypi/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  cobalt-wren==0.1.0rc1
/tmp/cobalt-wren-testpypi/bin/python -c 'import cobalt_wren'
/tmp/cobalt-wren-testpypi/bin/cobalt-wren --help
```
