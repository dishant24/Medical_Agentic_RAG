# medical-rag-agent

An agentic RAG system for querying clinical documentation (radiology reports,
discharge summaries, treatment guidelines) with multi-hop questions. Built
phase-by-phase as a learning project — see `docs/specs/` for the full
roadmap and `docs/superpowers/plans/` for implementation plans per phase.

## Setup

1. Install [uv](https://docs.astral.sh/uv/) if you haven't already: `pip install uv`
2. Install dependencies: `uv sync`
3. Copy the environment template and fill in your Groq API key:
   ```
   cp .env.example .env
   ```
4. Run the test suite: `uv run pytest`

## Project status

Phase 0 (scaffolding) complete. See `docs/specs/2026-07-07-medical-rag-agent-design.md`
for the full phase roadmap.
