# Skill Retriever

> **AgentSkillOS-powered semantic skill retrieval for Hermes Agent.**

Pre-filters 200k+ skills to the top-5 most relevant per query. Runs as a Hermes `pre_llm_call` plugin — zero core modification, zero additional API cost (borrows your existing Hermes LLMs).

## Quick Start

```bash
git clone https://github.com/<user>/skill-retriever.git
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
│ Skill Scanner                        │
│ Reads ~/.hermes/skills/ SKILL.md     │
│ Extracts name, description, category │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ Capability Tree (AgentSkillOS)       │
│ Organizes 200k+ skills hierarchically│
│ by capability domain (LLM-built)     │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ LLM Tree Navigation                  │
│ Borrows your active Hermes model     │
│ Recursively descends tree to find    │
│ relevant branches → skill candidates │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ pre_llm_call Injection               │
│ Prepends top-5 skill hints to your   │
│ user message as natural-language     │
│ instructions. LLM decides to load    │
│ or ignore.                           │
└──────────────────────────────────────┘
```

## Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `SKILL_RETRIEVER_DISABLE` | — | Set `1` to disable entirely |

No API keys needed. The plugin borrows your active Hermes LLM model for the retrieval gate.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a technical deep-dive covering:

- Skill tree construction and caching
- LLM node selection algorithm
- Capability tree traversal
- Plugin hook integration

## Requirements

- Hermes Agent v0.18+
- Python 3.10+
- ~4GB disk for full 200k skill corpus
- ~500MB disk for index cache

## License

MIT. Built on [AgentSkillOS](https://github.com/ynulihao/AgentSkillOS) (MIT).
