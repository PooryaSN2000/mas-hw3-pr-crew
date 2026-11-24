"""Environment health check for the PR Crew Starter Kit."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def report(status: str, title: str, detail: str = "") -> None:
    tag = {"OK": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[status]
    msg = f"{tag} {title}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def check_python() -> None:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 10):
        report("OK", "Python version", f"{v.major}.{v.minor}.{v.micro}")
    else:
        report("FAIL", "Python version", f"{v.major}.{v.minor} (need >= 3.10)")


def check_packages() -> None:
    required = ["openai", "dotenv", "fastmcp", "networkx", "pytest"]
    missing = [pkg for pkg in required if importlib.util.find_spec(pkg) is None]
    if not missing:
        report("OK", "Core Python packages", ", ".join(required))
    else:
        report("WARN", "Missing Python packages", f"{', '.join(missing)} -> run `pip install -r requirements.txt`")


def check_env_file() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        report("OK", ".env configuration", "Found")
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except Exception:
            pass
    else:
        report("WARN", ".env configuration", "Not found -> copy `.env.example` to `.env`")


def check_docker() -> None:
    if shutil.which("docker") is None:
        report("WARN", "Docker CLI", "Not found in PATH (needed for Containment badge & Phoenix)")
        return
    res = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if res.returncode != 0:
        report("WARN", "Docker daemon", "Docker CLI found, but daemon is not running")
        return
    report("OK", "Docker daemon", "Running")

    img = subprocess.run(
        ["docker", "images", "-q", "pr-crew-sandbox"], capture_output=True, text=True
    )
    if img.stdout.strip():
        report("OK", "Sandbox image", "`pr-crew-sandbox` built")
    else:
        report(
            "WARN",
            "Sandbox image",
            "Not built yet -> run `docker build -f docker/sandbox.Dockerfile -t pr-crew-sandbox .`",
        )


def check_phoenix() -> None:
    url = "http://localhost:6006"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            if resp.status == 200:
                report("OK", "Arize Phoenix UI", f"Reachable at {url}")
                return
    except Exception:
        pass
    report("WARN", "Arize Phoenix UI", "Not reachable -> run `docker compose up -d`")


def check_llm() -> None:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "qwen3.5:4b")
    models_url = f"{base_url}/models"
    try:
        req = urllib.request.Request(
            models_url,
            headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY', 'ollama')}"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                report("OK", "LLM endpoint", f"{base_url} (model: {model})")
                return
    except Exception:
        pass
    report(
        "WARN",
        "LLM endpoint",
        f"Could not reach {models_url}. Start Ollama, Kaggle notebook tunnel, or configure .env",
    )


def check_baseline_tests() -> None:
    if importlib.util.find_spec("pytest") is None:
        report("WARN", "Baseline target_repo tests", "Skipped (install pytest via requirements.txt)")
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "target_repo" / "src")
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(ROOT / "target_repo" / "tests")],
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        last_line = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else "passed"
        report("OK", "Baseline target_repo tests", last_line)
    else:
        report("FAIL", "Baseline target_repo tests", "Failed! Run `python scripts/init_repo.py --reset`")


def main() -> int:
    print("PR Crew Starter Kit -- Environment Check")
    print("-" * 52)
    check_python()
    check_packages()
    check_env_file()
    check_baseline_tests()
    check_docker()
    check_phoenix()
    check_llm()
    print("-" * 52)
    return 0


if __name__ == "__main__":
    sys.exit(main())
