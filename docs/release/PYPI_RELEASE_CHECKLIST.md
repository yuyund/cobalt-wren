# PyPI Release Checklist

## One-time setup

1. Confirm ownership and trademark clearance for “Cobalt Wren”.
2. Create the `cobalt-wren` project on TestPyPI or publish the first test build.
3. Configure the GitHub `pypi` environment with required reviewers.
4. Add a PyPI Trusted Publisher for this repository and `publish.yml`.
5. Confirm the repository's public URL, then add `[project.urls]` metadata.
6. Confirm the copyright owner remains `Yudai Maruyama`.
7. Re-verify vendored frontend asset versions and license files whenever
   Tabler or htmx is upgraded.

## Per release

1. Update `CHANGELOG.md` and replace `Unreleased` with the release date.
2. Set a unique release candidate or final version in `pyproject.toml`.
3. Run `scripts/validate_release.sh`; it performs lint, types, tests, build, artifact inspection, and clean-room installation.
9. Publish to TestPyPI and install from TestPyPI in a clean environment.
10. Tag the exact commit and create a GitHub release.
11. The release event publishes to PyPI through Trusted Publishing.
12. Install the final version from PyPI and run the same smoke tests.

Never upload with a long-lived PyPI API token when Trusted Publishing is available.
