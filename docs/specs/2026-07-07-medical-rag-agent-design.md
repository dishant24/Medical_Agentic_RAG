# Medical Documentation RAG Agent — Project Design

## Overview

An agentic RAG system for querying scattered clinical documentation (radiology
reports, discharge summaries, treatment guidelines) with multi-hop questions,
e.g. "what changed between this patient's last two scans, and what did the
guideline recommend?"

This is a from-scratch project, built alongside (not inside) the existing
`Simple_RAG_Application`, reusing its retrieval *ideas* (hybrid FAISS+BM25
search, reranking) but rebuilt deliberately, phase by phase, for learning.

Built as a companion learning project: every phase should leave the builder
understanding *why* each piece exists, not just a working feature.

## Goals

- Hybrid retrieval (dense FAISS + BM25 sparse) tuned for clinical language
  (mixes exact terminology with paraphrased context).
- An agentic self-critique loop: before answering, the agent checks its own
  retrieved context for relevance/factual consistency and re-queries if
  unconvinced.
- Measurable trust improvements: answer precision on multi-hop queries,
  hallucination rate on a curated medical QA set — tracked before/after each
  major retrieval change.
- Deployed as a Dockerized FastAPI service with FHIR-compatible outputs and
  MLflow experiment tracking, using the Groq API for inference.

## Data

Public synthetic/de-identified clinical data — Synthea-generated patient
records, MIMIC-IV demo (public subset), MTSamples transcription reports,
and public clinical guideline PDFs (NICE/WHO) — chosen specifically to avoid
any PHI/privacy concern while remaining realistic.

## Environment

- Docker Desktop available, Groq API key available, CPU-only (no GPU) —
  all model choices (FAISS-CPU, sentence-transformers, Groq-hosted LLM) must
  run acceptably on CPU.
- Builder is comfortable with Python and basic ML, new to RAG/agentic
  systems specifically — explanations should focus on RAG- and agent-specific
  concepts (chunking tradeoffs, sparse vs. dense retrieval, self-critique
  loops, tool orchestration) rather than basic Python/ML mechanics.

## Phase Roadmap

Each phase is a separate learning increment: its own short design (where
needed), its own implementation plan, its own working result. Later phases
depend on earlier ones being in place.

| Phase | What gets built | What it teaches |
|---|---|---|
| 0 | Project scaffolding: repo structure, config, dependency setup | How a real (non-notebook) LLM project is organized |
| 1 | Medical data ingestion: pull sample docs, chunk clinical text | Why chunking strategy matters for mixed-structure clinical text |
| 2 | Baseline dense RAG: FAISS + embeddings + Groq, minimal FastAPI `/ask` endpoint | Core RAG mechanics end-to-end |
| 3 | Curated mini eval set (~30-50 multi-hop Q&A pairs) + scoring script (precision, hallucination rate) | How to measure a RAG system — the yardstick for every later phase |
| 4 | Hybrid retrieval: BM25 + dense + Reciprocal Rank Fusion | Why sparse+dense beats either alone on terminology-heavy text; re-run eval, observe precision delta |
| 5 | Agentic self-critique loop: context relevance/consistency check + re-query | The core agentic idea; re-run eval, observe hallucination-rate delta |
| 6 | FHIR-compatible structured output formatting | Translating free-text answers into a real healthcare interop schema |
| 7 | MLflow tracking wrapped around the pipeline | Experiment tracking discipline across retrieval configs/prompts |
| 8 | Dockerize as a deployable FastAPI service | Packaging an ML service for deployment |

## Phase 0 Design: Project Scaffolding

**Goal:** a clean, runnable skeleton at `D:\Projects\medical-rag-agent` that
every later phase builds on. No RAG logic yet — foundation only.

**Structure:**

```
medical-rag-agent/
├── .env.example          # GROQ_API_KEY placeholder, documents required vars
├── .gitignore
├── pyproject.toml        # uv-managed deps + project metadata
├── README.md
├── src/
│   └── medrag/
│       ├── __init__.py
│       └── config.py     # pydantic-settings: typed, validated env config
├── data/
│   ├── raw/               # downloaded source docs (gitignored)
│   └── processed/         # chunked output (gitignored)
├── tests/
│   └── __init__.py
└── docs/
    └── specs/             # phase design docs (this file lives here)
```

**Key decisions:**

- **`pydantic-settings` for config** instead of raw `os.getenv` — typed,
  validated, fails fast on a missing key. Same pattern reused by the FastAPI
  layer in Phase 2.
- **`src/` layout** (`src/medrag/...`) rather than a flat package — avoids
  accidental imports of uninstalled code, standard practice.
- **pytest wired up from day one**, even with a trivial smoke test — Phase
  3's eval harness leans on this heavily.
- **uv** for environment/dependency/lockfile management, Python 3.11.
- git initialized with an initial commit (done as part of this phase).

**Out of scope for Phase 0:** no document loading, no embeddings, no API
routes — those are later phases.

## Testing Strategy

- pytest for all phases from Phase 0 onward.
- Phase 3 introduces the eval harness (precision/hallucination scoring)
  which doubles as an integration test for the retrieval+agent pipeline —
  every later phase re-runs it to measure impact.
