<p align="center">
  <img src="logo.png" alt="Skill Retriever" height="130">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
</p>

# Skill Retriever

> **Composer-based dynamic skill curation for Hermes Agent.**

Walks a YAML capability tree once to build a flat index (~50KB, ~400 skills), then uses a **single LLM call** to curate a query-specific bundle of 3-20 skills — complete with load levels (★/▸/·), confidence scores, and reasoning.

## Why Composer?

Old approach: recursive LLM tree descent (5 levels × branching 3 = **~243 calls/query**). Unusable for real-time.

New approach: flat index pre-filter → single LLM curation → **1 call/query**, sub-second latency.

## How It Works

```
User Query → flat index pre-filter (top 50) → LLM picks best 3-20 → inject hints
```

Each skill gets:

| Field | Meaning |
|-------|---------|
| `name` | Skill name (call `skill_view(name)` to load) |
| `load_as` | `must` ★ / `should` ▸ / `consider` · |
| `confidence` | `high` / `medium` / `low` |
| `reason` | Why this skill fits the query |

### Hint Block (injected into user message)

```
[Skill Capability Chain]

These skills are curated for this query.
Call skill_view('<name>') to load each one.

  ★ cloudflare-tunnel — Tunnel deployment + credential management
  ▸ infrastructure-as-code — Terraform for Cloudflare tunnels
  · devops — Broader deployment workflows
```

## Quick Start

```bash
pip install skill-retriever
skill-retriever install          # optional: install bundled community skills
```

No plugin development needed — the Hermes plugin is registered automatically.

## CLI

```bash
# Rebuild the flat index (after adding new skills)
skill-retriever rebuild

# Compose a bundle for a query
skill-retriever compose "deploy a cloudflare tunnel"

# Show index info
skill-retriever info
```

## Integration Points

| Point | What | When |
|-------|------|------|
| `pre_llm_call` hook | Inject curated bundle | Every turn |
| Subagent dispatch | Inject per-task bundle | `delegate_task()` |
| Deepthink planning | Phase-sectioned coverage | Planning phase |
| Skills logger | JSONL usage tracking | Every compose |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for flat-index details, plugin wiring, and the reasoning model handling (LongCat-2.0 `reasoning_content` field).

## System Requirements

- Hermes Agent v0.18+
- Python 3.10+
- ~50MB for flat index
- OpenAI-compatible LLM endpoint (LongCat, OpenAI, etc.)

## Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `SKILL_RETRIEVER_DISABLE` | — | Set `1` to disable |
| `SKILL_RETRIEVER_LLM_MODEL` | from Hermes config | LLM model override |
| `SKILL_RETRIEVER_LLM_API_KEY` | from Hermes config | API key |
| `SKILL_RETRIEVER_LLM_BASE_URL` | from Hermes config | Base URL |
| `SKILL_RETRIEVER_TEMPERATURE` | `0.3` | LLM temperature |

## Project Structure

```
skill-retriever/
├── plugin/                 # Hermes plugin (pre_llm_call hook)
├── src/
│   ├── skill_retriever/    # Core engine
│   │   ├── cli_compose.py  # CLI (rebuild, compose, info)
│   │   ├── compose.py      # Composer: skill curation (single LLM call)
│   │   ├── config.py       # LLM discovery (borrow Hermes config)
│   │   ├── build_flat_index.py
│   │   ├── search/         # Tree search (CLI only, not for real-time)
│   │   ├── subagent_binding.py  # Per-task bundle injection
│   │   ├── planning_with_skills.py  # Phase-sectioned bundles
│   │   └── skill_usage_logger.py  # JSONL tracking
│   ├── scanner.py  # Hermes skills scanner
├── data/                   # Skill corpus (gitignored)
├── tests/                  # pytest suite
└── ARCHITECTURE.md
```

## Trust & Safety

- Composer prompts for **confidence per skill**
- Bundle is capped to LLM token budget (max ~50 skills in prompt)
- Reasoning models (LongCat-2.0, DeepSeek R1) return responses in `reasoning_content` — handled correctly

## License

MIT. Community skills may have separate licenses.
