# TaskFlow (v0.3.1)

A lightweight, zero-dependency Python engine for defining, validating, inspecting, caching, and executing DAG-based task workflows.

## Quick Commands

```bash
# Run public test suite
pytest -v

# Run a workflow via CLI
PYTHONPATH=src python -m taskflow.cli run workflows/demo.tfw

# Validate a workflow file
PYTHONPATH=src python -m taskflow.cli validate workflows/etl_pipeline.tfw

# Inspect workflow structure & blast radius
PYTHONPATH=src python -m taskflow.cli inspect workflows/etl_pipeline.tfw

# Export dependency graph in Graphviz DOT format
PYTHONPATH=src python -m taskflow.cli graph workflows/etl_pipeline.tfw
```

See `docs/ARCHITECTURE.md` for an overview of the modules.
