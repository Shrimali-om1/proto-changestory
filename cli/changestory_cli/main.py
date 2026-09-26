from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def _git_diff(repo: Path) -> str:
    result = subprocess.run(["git", "diff", "--no-ext-diff", "HEAD"], cwd=repo, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        raise ValueError("Could not collect a Git diff. Is this a usable Git repository?")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="changestory", description="Create a deterministic ChangeStory analysis report.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a local Git diff with the running ChangeStory API.")
    analyze.add_argument("--repo", type=Path, default=Path.cwd(), help="Git repository to inspect (defaults to current directory).")
    analyze.add_argument("--diff-file", type=Path, help="Unified diff file to analyze instead of Git changes.")
    analyze.add_argument("--api-url", default="http://127.0.0.1:8000", help="Running ChangeStory API URL.")
    analyze.add_argument("--no-browser", action="store_true", help="Do not open the report page after analysis.")
    args = parser.parse_args(argv)
    if args.command != "analyze":
        return 2
    try:
        repo = args.repo.resolve()
        if not repo.is_dir():
            raise ValueError("The requested repository path does not exist.")
        diff_text = args.diff_file.read_text(encoding="utf-8") if args.diff_file else _git_diff(repo)
        if not diff_text.strip():
            raise ValueError("No local Git changes were found.")
        payload = json.dumps({"diff_text": diff_text, "repository_path": str(repo), "source_mode": "local"}).encode()
        request = urllib.request.Request(f"{args.api_url.rstrip('/')}/api/v1/analyze", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            report = json.loads(response.read())
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as error:
        print(f"ChangeStory could not analyze this diff: {error}", file=sys.stderr)
        return 1
    summary = report["change_summary"]
    report_url = f"http://localhost:3000/report/{report['session_id']}"
    print("ChangeStory Analysis\n")
    # ASCII markers keep the CLI reliable in default Windows code pages.
    print(f"[ok] {summary['files_changed']} files changed")
    print(f"[ok] {summary['symbols_changed']} symbols changed")
    print(f"[ok] {summary['symbols_affected']} affected symbols")
    print(f"[!] {summary['potential_risks']} potential risks")
    print(f"[ok] {summary['test_recommendations']} test recommendations\n")
    print(f"Report:\n{report_url}")
    if not args.no_browser:
        webbrowser.open(report_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
