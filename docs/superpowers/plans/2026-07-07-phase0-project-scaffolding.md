# Phase 0: Project Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a clean, runnable `medical-rag-agent` project skeleton (uv-managed, src-layout, typed config, pytest wired up) that every later phase builds on.

**Architecture:** A single `medrag` Python package under `src/`, managed by `uv`. Configuration is centralized in `src/medrag/config.py` using `pydantic-settings` (typed, validated, `.env`-driven) rather than scattered `os.getenv` calls — this is the same config pattern the FastAPI app in Phase 2 will reuse.

**Tech Stack:** Python 3.11, `uv` (env/dependency manager), `pydantic-settings` (config), `pytest` (testing).

---

### Task 1: Install uv and initialize the project structure

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `src/medrag/__init__.py`
- Create: `README.md` (uv default stub, replaced in Task 4)
- Create: `.gitignore` (uv default, extended in Task 2)

- [ ] **Step 1: Confirm uv is not already installed, then install it**

Run: `powershell -Command "uv --version"`
Expected: command not found (already confirmed in this session)

Install uv via pip (works cross-platform without touching system PATH config manually):

Run: `pip install uv`
Expected: `Successfully installed uv-<version>`

Verify:

Run: `uv --version`
Expected: `uv <version>` printed with no error

- [ ] **Step 2: Initialize the uv package project**

From `D:\Projects\medical-rag-agent`:

Run: `uv init --package --name medrag --python 3.11`
Expected output includes: `Initialized project ` and creates `pyproject.toml`, `.python-version`, `README.md`, `.gitignore`, `src/medrag/__init__.py`

- [ ] **Step 3: Verify the generated structure**

Run: `ls src/medrag` (or `dir src\medrag` on Windows)
Expected: `__init__.py` present

Run: `cat pyproject.toml` (or `type pyproject.toml`)
Expected: `[project]` section with `name = "medrag"` and `requires-python = ">=3.11"`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .python-version .gitignore README.md src/
git commit -m "Initialize uv-managed project structure"
```

---

### Task 2: Environment file handling and gitignore rules

**Files:**
- Modify: `.gitignore`
- Create: `.env.example`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`

- [ ] **Step 1: Append project-specific ignores to `.gitignore`**

Add these lines to the end of the existing `.gitignore` (created by `uv init` in Task 1):

```
# Environment
.env

# Data (populated in Phase 1, never committed)
data/raw/*
data/processed/*
!data/raw/.gitkeep
!data/processed/.gitkeep
```

- [ ] **Step 2: Create `.env.example`**

```
# Copy this file to .env and fill in real values. .env is gitignored.

GROQ_API_KEY=your-groq-api-key-here
APP_ENV=development
```

- [ ] **Step 3: Create placeholder data directories**

Since git doesn't track empty directories, add placeholder files so the folder structure exists after clone:

Run: `mkdir -p data/raw data/processed` then create empty files `data/raw/.gitkeep` and `data/processed/.gitkeep` (empty file content).

- [ ] **Step 4: Verify gitignore works**

Run: `touch data/raw/dummy.txt && git status`
Expected: `dummy.txt` does NOT appear in untracked files (it's ignored), but `.gitkeep` files do appear as untracked (about to be added)

Run: `rm data/raw/dummy.txt`

- [ ] **Step 5: Commit**

```bash
git add .gitignore .env.example data/raw/.gitkeep data/processed/.gitkeep
git commit -m "Add env file template and data directory placeholders"
```

---

### Task 3: Typed config with pydantic-settings (TDD)

**Files:**
- Modify: `pyproject.toml` (adds `pydantic-settings` and dev dependency `pytest`)
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `src/medrag/config.py`

- [ ] **Step 1: Add dependencies**

Run: `uv add pydantic-settings`
Expected: `pyproject.toml` gains a `dependencies = ["pydantic-settings>=..."]` entry, `uv.lock` is created/updated

Run: `uv add --dev pytest`
Expected: `pyproject.toml` gains a `[dependency-groups] dev = ["pytest>=..."]` entry

- [ ] **Step 2: Create the tests package**

Create empty file: `tests/__init__.py`

- [ ] **Step 3: Write the failing tests**

Create `tests/test_config.py`:

```python
import pytest
from pydantic import ValidationError

from medrag.config import Settings


def test_settings_loads_groq_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    settings = Settings(_env_file=None)
    assert settings.groq_api_key == "test-key-123"


def test_settings_defaults_app_env_to_development(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-123")
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"


def test_settings_raises_when_groq_api_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'medrag.config'` (or ImportError)

- [ ] **Step 5: Implement `src/medrag/config.py`**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application configuration loaded from environment/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = Field(..., description="API key for Groq inference")
    app_env: str = Field(default="development", description="Deployment environment name")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock tests/__init__.py tests/test_config.py src/medrag/config.py
git commit -m "Add typed Settings config with pydantic-settings (TDD)"
```

---

### Task 4: README with real setup instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the uv-generated stub with real content**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Add real README with setup instructions"
```

---

### Task 5: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite from a clean environment**

Run: `uv sync && uv run pytest -v`
Expected: all tests pass (3 passed), no errors

- [ ] **Step 2: Verify final structure matches the Phase 0 spec**

Run: `find . -not -path './.git*' -not -path './.venv*' -type f | sort` (or equivalent directory listing)
Expected: matches the structure in `docs/specs/2026-07-07-medical-rag-agent-design.md` Phase 0 section — `pyproject.toml`, `.env.example`, `.gitignore`, `README.md`, `src/medrag/__init__.py`, `src/medrag/config.py`, `tests/__init__.py`, `tests/test_config.py`, `data/raw/.gitkeep`, `data/processed/.gitkeep`, `docs/specs/...`, `docs/superpowers/plans/...`

- [ ] **Step 3: Confirm git log shows all Phase 0 commits**

Run: `git log --oneline`
Expected: 5 commits total (design doc + 4 implementation commits), most recent first
