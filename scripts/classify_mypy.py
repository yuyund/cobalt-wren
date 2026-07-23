from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

ERROR_RE = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): error: (?P<message>.*?)(?:  \[(?P<code>[^]]+)\])?$")
DJANGO_PATH_MARKERS = (
    "apps/automation/models/",
    "apps/automation/selectors/",
    "apps/automation/admin.py",
    "apps/automation/apps.py",
    "apps/automation/services/runs.py",
    "apps/automation/ui/",
    "apps/web/",
    "config/asgi.py",
    "config/settings.py",
    "config/urls.py",
    "config/wsgi.py",
    "migrations/",
    "integrations/observability/django_event_sink.py",
)


def classify(path: str, message: str, code: str | None) -> str:
    if code == "import-untyped":
        return "external_stub"
    if "tuple[str, str]" in message and any(marker in path for marker in DJANGO_PATH_MARKERS):
        return "django_choice_typing"
    return "internal_code"


def run_mypy() -> tuple[int, list[str]]:
    process = subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return process.returncode, process.stdout.splitlines()


def summarize(lines: list[str]) -> dict[str, object]:
    categories: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    files: Counter[str] = Counter()
    parsed = 0
    for line in lines:
        match = ERROR_RE.match(line)
        if not match:
            continue
        parsed += 1
        path = match.group("path")
        code = match.group("code") or "unknown"
        category = classify(path, match.group("message"), code)
        categories[category] += 1
        codes[code] += 1
        files[path] += 1
    return {
        "total": parsed,
        "categories": dict(sorted(categories.items())),
        "codes": dict(sorted(codes.items())),
        "files": dict(sorted(files.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path("config/mypy-baseline.json"))
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--check-baseline", action="store_true")
    args = parser.parse_args()

    _, lines = run_mypy()
    summary = summarize(lines)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write_baseline:
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    if args.check_baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        regressions: list[str] = []
        for category, count in summary["categories"].items():
            allowed = int(baseline.get("categories", {}).get(category, 0))
            if int(count) > allowed:
                regressions.append(f"{category}: {count} > {allowed}")
        if int(summary["total"]) > int(baseline.get("total", 0)):
            regressions.append(f"total: {summary['total']} > {baseline.get('total', 0)}")
        if regressions:
            print("mypy baseline regression: " + "; ".join(regressions), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
