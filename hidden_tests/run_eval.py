"""Run public + hidden evaluation tests against target_repo.

Usage:
  python hidden_tests/run_eval.py            # Run public tests + all 7 hidden issue suites
  python hidden_tests/run_eval.py --issue 1  # Run public tests + hidden test for ISSUE-01
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_SRC = ROOT / "target_repo" / "src"
PUBLIC_TESTS = ROOT / "target_repo" / "tests"
HIDDEN_DIR = ROOT / "hidden_tests"
ALL_ISSUES = [1, 2, 3, 4, 5, 6, 7]


def run_pytest(test_path: Path, label: str) -> bool:
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{TARGET_SRC}{os.pathsep}{existing_pp}" if existing_pp else str(TARGET_SRC)

    python_cmd = sys.executable
    check = subprocess.run([python_cmd, "-m", "pytest", "--version"], capture_output=True)
    if check.returncode != 0:
        for cand in (
            ROOT / ".venv" / "bin" / "python",
            ROOT / ".venv" / "Scripts" / "python.exe",
        ):
            if cand.exists():
                python_cmd = str(cand)
                break

    print(f"\n=== Running {label}: {test_path.relative_to(ROOT)} ===")
    proc = subprocess.run(
        [python_cmd, "-m", "pytest", "-v", str(test_path)],
        env=env,
        cwd=str(ROOT),
    )
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate agent patches on TaskFlow.")
    parser.add_argument(
        "--issue",
        type=int,
        choices=ALL_ISSUES,
        default=None,
        help="Specific issue number to evaluate (default: all 7 issues).",
    )
    parser.add_argument(
        "--skip-public",
        action="store_true",
        help="Skip regression check on public target_repo/tests.",
    )
    args = parser.parse_args()

    summary: dict[str, bool] = {}

    if not args.skip_public:
        summary["Public Regression Suite"] = run_pytest(PUBLIC_TESTS, "Public Tests")

    issue_nums = [args.issue] if args.issue else ALL_ISSUES
    for num in issue_nums:
        test_file = HIDDEN_DIR / f"test_issue_0{num}.py"
        summary[f"ISSUE-0{num} Hidden Tests"] = run_pytest(test_file, f"ISSUE-0{num}")

    print("\n" + "=" * 56)
    print("EVALUATION SUMMARY")
    print("=" * 56)
    for name, passed in summary.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print("=" * 56)

    return 0 if all(summary.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
