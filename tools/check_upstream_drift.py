"""Report upstream physical-flow drift without changing qualified pins."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "tools/workbench/toolchain.lock.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def read_candidate(lock_path: Path) -> tuple[str, str, str]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    physical = lock["official_cmos5l_qualification"]
    repository = physical["outer_action_repository"]
    upstream_ref = physical["upstream_ref"]
    qualified_commit = physical["outer_action_commit"]
    if not SHA_RE.fullmatch(qualified_commit):
        raise ValueError("qualified action commit is not a 40-character SHA")
    return repository, upstream_ref, qualified_commit


def fetch_commit(repository: str, upstream_ref: str, token: str | None) -> tuple[str, str]:
    encoded_ref = quote(upstream_ref, safe="/")
    url = f"https://api.github.com/repos/{repository}/git/ref/{encoded_ref}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "protocol-emulator-asic-upstream-canary",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    observed = payload["object"]["sha"]
    if not SHA_RE.fullmatch(observed):
        raise ValueError("GitHub returned an invalid commit SHA")
    return observed, url


def write_result(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_summary(result: dict[str, object]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    state = result["state"]
    lines = [
        "## Tiny Tapeout upstream canary",
        "",
        f"- State: **{state}**",
        f"- Watched ref: {result['repository']}@{result['upstream_ref']}",
        f"- Qualified commit: {result['qualified_commit']}",
        f"- Observed commit: {result.get('observed_commit', 'NOT_OBSERVED')}",
        "- Acceptance pins changed: **no**",
        "",
        "DRIFT means review is available; it does not update or invalidate the qualified flow.",
        "",
    ]
    with Path(summary_path).open("a", encoding="utf-8") as summary:
        summary.write("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare the qualified Tiny Tapeout action commit with its live upstream ref."
    )
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "build/upstream-canary/result.json",
    )
    parser.add_argument(
        "--observed-commit",
        help="Use a supplied SHA instead of the network; intended for deterministic self-tests.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checked_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    repository, upstream_ref, qualified_commit = read_candidate(args.lock)
    base_result: dict[str, object] = {
        "schema": "protocol-emulator-upstream-canary-v1",
        "checked_utc": checked_utc,
        "repository": repository,
        "upstream_ref": upstream_ref,
        "qualified_commit": qualified_commit,
        "acceptance_environment_changed": False,
    }

    try:
        if args.observed_commit:
            observed_commit = args.observed_commit.lower()
            if not SHA_RE.fullmatch(observed_commit):
                raise ValueError("--observed-commit must be a 40-character hexadecimal SHA")
            source_url = "supplied-for-self-test"
        else:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            observed_commit, source_url = fetch_commit(repository, upstream_ref, token)
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as exc:
        result = {
            **base_result,
            "state": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }
        write_result(args.output, result)
        append_summary(result)
        print(f"ERROR: could not observe upstream ref: {exc}", file=sys.stderr)
        return 2

    state = "CURRENT" if observed_commit == qualified_commit else "DRIFT"
    result = {
        **base_result,
        "state": state,
        "observed_commit": observed_commit,
        "source_url": source_url,
    }
    write_result(args.output, result)
    append_summary(result)

    if state == "CURRENT":
        print(f"CURRENT: {repository}@{upstream_ref} remains {qualified_commit}")
    else:
        message = (
            f"DRIFT: {repository}@{upstream_ref} is {observed_commit}; "
            f"qualified commit remains {qualified_commit}"
        )
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Tiny Tapeout upstream drift::{message}")
        print(message)
    print("UNCHANGED: the canary never edits the qualification lock or workflow pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
