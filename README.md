# Skill Retriever

> **AgentSkillOS-powered semantic skill retrieval for Hermes Agent.**

Pre-filters **1,200+ skills** (998 community corpus + 200 Hermes skills) organized in a **10,000-category capability taxonomy** to the top-5 most relevant per query. Runs as a Hermes `pre_llm_call` plugin — zero core modification, zero additional API cost (borrows your existing Hermes LLMs via borrow-mode).

## Quick Start

```bash
git clone https://github.com/ChonSong/skill-retriever.git
cd skill-retriever
bash scripts/install.sh
hermes gateway restart
```

## How It Works

```
User Query
    │
    ▼
┌──────────────────────────────────────┐
│ pre_llm_call hook (plugin)           │
│ Checks DISABLE flag, skips short Qs  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Searcher.search()                    │
│ 1. Load capability tree from YAML    │
│ 2. LLM-navigate tree (select nodes)  │
│ 3. Parallel child search (ThreadPool)│
│ 4. LLM prune (dedup + rank)          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Hint Injection                       │
│ Prepends top-5 skill hints as        │
│ natural-language block. LLM may call │
│ skill_view(name) to load any.        │
└──────────────────────────────────────┘
```

## CLI

```bash
python -m skill_retriever search "set up CI/CD pipeline"
python -m skill_retriever build              # rebuild capability tree
python -m skill_retriever list               # list all skills in corpus
python -m skill_retriever info               # system info + tree stats
```

## Configuration

All settings via environment variables — no config files needed.

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `SKILL_RETRIEVER_DISABLE` | — | Set `1` to disable entirely |
| `SKILL_RETRIEVER_LLM_MODEL` | `gpt-4o` | LLM model for skill gate |
| `SKILL_RETRIEVER_LLM_API_KEY` | `OPENAI_API_KEY` | API key |
| `SKILL_RETRIEVER_LLM_BASE_URL` | `OPENAI_BASE_URL` | Base URL |
| `SKILL_RETRIEVER_BRANCHING_FACTOR` | `3` | Tree branching (search) |
| `SKILL_RETRIEVER_MAX_PARALLEL` | `5` | Parallel search branches |
| `SKILL_RETRIEVER_TEMPERATURE` | `0.3` | LLM temperature |
| `SKILL_RETRIEVER_PRUNE` | `true` | Enable dedup/ranking step |
| `SKILL_RETRIEVER_TREE_PATH` | bundled `tree.yaml` | Override capability tree |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a technical deep-dive covering:

- Capability tree structure and build process
- LLM node selection algorithm
- Searcher internals (parallel search, early stop, pruning)
- Plugin hook integration
- Directory layout

## Requirements

- Hermes Agent v0.18+
- Python 3.10+
- ~500MB for capability tree index
- ~4GB for full skill corpus (optional, for rebuilding tree)

## Project Structure

```
skill-retriever/
├── plugin/                 # Hermes plugin (pre_llm_call hook)
├── src/
│   ├── config.py           # Unified env-based configuration
│   ├── skill_scanner.py    # Hermes skills scanner
│   └── skill_retriever/    # Core engine
│       ├── cli.py          # CLI (search, build, list, info)
│       ├── search/         # Searcher (multi-level LLM tree search)
│       ├── tree/           # Tree builder, schema, prompts, scanner
│       └── capability_tree/# Pre-built trees (YAML + HTML)
├── data/                   # Skill corpus (gitignored)
├── tests/                  # 30+ tests
├── scripts/install.sh      # One-click Hermes plugin install
└── ARCHITECTURE.md
```

## License

MIT. Built on [AgentSkillOS](https://github.com/ynulihao/AgentSkillOS) (MIT).
