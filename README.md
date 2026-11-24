# Agent Expedition: The Pull Request Crew — Starter Kit (`v0.3.1`)

Welcome to the ready-to-use playground for **HW3: Multi-Agent Systems**.
This starter kit provides a realistic 16-module Python repository (`taskflow`), seven curated GitHub-style issues spanning easy single-file bugs to multi-module concurrency & architecture features (plus a dual-layer Indirect Prompt Injection trap), hidden evaluation tests, Docker sandboxing, Arize Phoenix tracing, and minimal building-block scripts.

---

## Repository Layout

```text
mas-hw3-pr-crew/
├── README.md                     # This quickstart guide
├── .env.example                  # Copy to .env (LLM, Phoenix, safety limits)
├── requirements.txt              # Starter Python dependencies
├── docker-compose.yml            # Arize Phoenix (default) + Neo4j (optional --profile graph)
├── docker/
│   └── sandbox.Dockerfile        # Non-root isolated Docker sandbox for running agent tests
├── target_repo/                  # Target Python project (`taskflow` v0.3.1)
│   ├── docs/ARCHITECTURE.md      # Module architecture map
│   ├── src/taskflow/             # 16 interconnected Python modules (~1,930 lines)
│   ├── tests/                    # Public pytest suite (20/20 green at baseline)
│   └── workflows/                # Sample .tfw workflow fixtures
├── issues/                       # 7 curated issues (Easy -> Hard + Injection Trap)
├── hidden_tests/                 # Hidden evaluation oracle (do NOT expose to your agent!)
│   └── run_eval.py               # Local evaluator for verifying agent fixes
├── scripts/
│   ├── init_repo.py              # Initialize or cleanly reset target_repo's Git history
│   ├── check_env.py              # One-command environment diagnostics
│   └── kaggle_llm_server.ipynb   # Zero-cost Kaggle GPU setup (Mode A: 100% Cloud | Mode B: Tunnel)
└── examples/
    ├── 01_llm_ping.py            # First LLM call + Arize Phoenix trace
    ├── 02_mcp_minimal.py         # Minimal FastMCP server with safe repo-scoped tools
    └── 03_code_graph.py          # Lightweight AST + NetworkX code knowledge graph
```

---

## 5-Minute Quickstart

### 1. Create a virtual environment and install base packages
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure `.env` & Avoid Ollama's 4096-Token Trap (Zero-Cost Policy)
```bash
cp .env.example .env
```
> **Important Ollama Tip:** Ollama defaults to a **4,096-token context window** and often ignores `num_ctx` sent through the OpenAI `/v1` API. Always start Ollama with a larger context window (or create a Modelfile with `PARAMETER num_ctx 12288`) so your agent does not forget the issue prompt mid-run:
> ```bash
> # For 6GB VRAM GPUs (e.g. RTX 4050 / 3060 Laptop):
> OLLAMA_CONTEXT_LENGTH=12288 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve
> 
> # For 8GB+ VRAM / Cloud:
> OLLAMA_CONTEXT_LENGTH=16384 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve
> ```

### 3. Initialize the target Git repository
```bash
python scripts/init_repo.py
```
Whenever you want to reset `target_repo` cleanly back to `main`:
```bash
python scripts/init_repo.py --reset
```

### 4. Start Tracing UI (Arize Phoenix) & Build the Sandbox Image
```bash
# Option A (Docker): Start Arize Phoenix at http://localhost:6006
docker compose up -d

# Option B (No Docker — e.g., inside Kaggle):
pip install arize-phoenix
phoenix serve &

# Build isolated Docker sandbox (for local host machines):
docker build -f docker/sandbox.Dockerfile -t pr-crew-sandbox .
```

### 5. Running on Kaggle (Zero-Cost GPU & No Docker Required)
If you do not have a capable local GPU, use `scripts/kaggle_llm_server.ipynb` on Kaggle (`GPU T4 x2`, `Internet = ON`):
- **Mode A (100% Inside Kaggle):** Run both the LLM and your agent crew directly inside the Kaggle notebook. Kaggle's ephemeral cloud environment is already containerized, so **Docker is not required**.
- **Mode B (Hybrid Cloud Server):** Run Ollama on Kaggle's 30 GB VRAM (`T4 x2`), start the free Cloudflare tunnel provided in the notebook, and point your local `.env` (`LLM_BASE_URL=https://...trycloudflare.com/v1`) to run agent code on your laptop without using any local GPU memory.

### 6. Run the Environment Health Check & Examples
```bash
python scripts/check_env.py
python examples/01_llm_ping.py
python examples/02_mcp_minimal.py --demo
python examples/03_code_graph.py
```

---

## Running Tests Safely Inside Docker (Local PC)

```bash
docker run --rm --network=none --memory=512m --cpus=1 \
  -v "$(pwd)/target_repo:/workspace" pr-crew-sandbox pytest -v
```

Only `target_repo/` is mounted into `/workspace`. Your agent cannot see `hidden_tests/`.

---

## The 7 Curated Issues (`issues/`)

| Issue | Difficulty | Modules Involved | What It Tests |
| :--- | :--- | :--- | :--- |
| `ISSUE-01-retry-off-by-one.md` | Easy | `runner.py` | Base Camp smoke test & retry hook behavior |
| `ISSUE-02-stale-cache-invalidation.md` | Easy-Medium | `cache.py`, `runner.py` | Cross-module cache key hashing without breaking cache hits |
| `ISSUE-03-dry-run-and-json-report.md` | Medium | `runner.py`, `reporter.py`, `cli.py` | Clean feature addition across engine, formatter & CLI |
| `ISSUE-04-release-audit-workflow-crash.md` | Medium | `workflows/`, `graph.py` | User bug report requiring cycle-detection root-cause fix |
| `ISSUE-05-parser-comments-and-duplicates.md` | Medium | `parser.py`, `workflows/` | Real parser fixes + resisting layered Indirect Prompt Injection (`Injection Survivor`) |
| `ISSUE-06-parallel-execution-and-state-isolation.md` | Medium-Hard | `runner.py`, `cache.py` | Deep-copy state isolation, parallel `fail_fast`, deterministic order & cache RLock |
| `ISSUE-07-conditional-when-execution.md` | Hard | `models.py`, `parser.py`, `runner.py` | Cross-cutting `when:` conditional DSL (`always`, `on_failure`, `upstream.X == V`) |

---

## Evaluating Your Agent's Fix

```bash
# Check public regression tests + a specific issue's hidden tests
python hidden_tests/run_eval.py --issue 1

# Or evaluate all 7 issues
python hidden_tests/run_eval.py
```

**Remember:** Do **not** mount or feed `hidden_tests/` to your agent—treat them strictly as an external grading oracle!
