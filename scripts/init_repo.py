"""Initialize (or cleanly reset) target_repo as a standalone Git repository.

Usage:
    python scripts/init_repo.py           # Initialize if .git does not exist
    python scripts/init_repo.py --reset   # Hard-reset target_repo back to initial commit
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_REPO = ROOT / "target_repo"


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(TARGET_REPO),
        text=True,
        capture_output=True,
    )


def init_repo(reset: bool = False) -> int:
    if shutil.which("git") is None:
        print("[ERROR] git CLI not found in PATH. Please install Git first.", file=sys.stderr)
        return 1

    git_dir = TARGET_REPO / ".git"
    if not git_dir.exists():
        print(f"Initializing fresh Git repository in {TARGET_REPO} ...")
        for cmd in [
            ("init", "-b", "main"),
            ("config", "user.name", "TaskFlow Maintainer"),
            ("config", "user.email", "maintainer@taskflow.local"),
            ("add", "."),
            ("commit", "-m", "chore: initial TaskFlow v0.3.1 codebase"),
        ]:
            res = run_git(*cmd)
            if res.returncode != 0:
                print(f"[ERROR] git {' '.join(cmd)} failed:\n{res.stderr}", file=sys.stderr)
                return 1
        print("[OK] target_repo initialized on branch 'main' with clean initial commit.")
        return 0

    if reset:
        print("Resetting target_repo back to clean 'main' branch ...")
        run_git("checkout", "main")
        run_git("reset", "--hard", "HEAD")
        run_git("clean", "-fd")
        branches = run_git("branch", "--format=%(refname:short)").stdout.splitlines()
        for br in branches:
            if br and br != "main":
                run_git("branch", "-D", br)
        print("[OK] target_repo cleanly reset to initial state.")
        return 0

    print("[INFO] target_repo is already a Git repository. Pass --reset to restore clean state.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize or reset target_repo Git state.")
    parser.add_argument("--reset", action="store_true", help="Discard all changes and extra branches.")
    args = parser.parse_args()
    return init_repo(reset=args.reset)


if __name__ == "__main__":
    sys.exit(main())
