"""Example 1: Minimal LLM call with automatic Arize Phoenix OpenTelemetry tracing.

Before running:
  1. Copy `.env.example` -> `.env` and configure your LLM endpoint (Ollama / Kaggle / free API).
  2. Start Phoenix: `docker compose up -d`
  3. Run: `python examples/01_llm_ping.py`
  4. Open http://localhost:6006 to inspect your first recorded Trace!
"""

from __future__ import annotations

import os
import socket
from dotenv import load_dotenv
from openai import OpenAI


def setup_tracing() -> None:
    """Register OpenTelemetry instrumentation for OpenAI -> Arize Phoenix."""
    try:
        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
        project = os.getenv("PHOENIX_PROJECT_NAME", "pr-crew-hw3")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("localhost", 6006)) != 0:
                print(
                    "[Tracing] Arize Phoenix not listening on port 6006 "
                    "(start via `docker compose up -d`). Continuing without live spans..."
                )
                return

        from phoenix.otel import register
        from openinference.instrumentation.openai import OpenAIInstrumentor

        tracer_provider = register(project_name=project, endpoint=endpoint)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        print(f"[Tracing] Connected to Phoenix at {endpoint} (project: {project})")
    except Exception as exc:
        print(f"[Tracing] Skipping Phoenix setup ({exc})")


def main() -> None:
    load_dotenv()
    setup_tracing()

    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
    )
    model = os.getenv("LLM_MODEL", "qwen3.5:4b")

    print(f"Pinging model '{model}' ...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a concise software engineering assistant."},
            {"role": "user", "content": "In one sentence, what is a topological sort in a DAG?"},
        ],
        temperature=0.0,
        max_tokens=600,
    )

    print("\nResponse:")
    msg = response.choices[0].message
    reply = (
        msg.content
        or getattr(msg, "reasoning", None)
        or getattr(msg, "reasoning_content", None)
        or "(Empty response)"
    )
    print(reply)
    if response.usage:
        print(
            f"\nTokens -> prompt: {response.usage.prompt_tokens}, "
            f"completion: {response.usage.completion_tokens}"
        )


if __name__ == "__main__":
    main()
