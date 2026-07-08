<p align="center">
  <img src="logo.png" alt="Skill Retriever" height="130">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  <a href="https://github.com/ynulihao/AgentSkillOS"><img src="https://img.shields.io/badge/Built%20on-AgentSkillOS-purple" alt="Built on AgentSkillOS"></a>
</p>

# Skill Retriever

> **AgentSkillOS-powered semantic skill retrieval for Hermes Agent.**

Pre-filters **1,200+ skills** (998 community corpus + 211 Hermes skills) organized in a **10,000-category capability taxonomy** to the top-5 most relevant per query. Runs as a Hermes `pre_llm_call` plugin — zero core modification, zero additional API cost (borrows your existing Hermes LLMs via borrow-mode).

## Why a Skill Tree?

Pure semantic retrieval prioritizes textual similarity and misses skills that look unrelated in embedding space but are crucial for solving the task. Our LLM + Skill Tree navigates the capability hierarchy to surface non-obvious but functionally relevant skills.

<p align="center">
  <img src="skill_retrieval_academic_comparison.png" alt="Skill Retrieval: Semantic vs Tree" style="max-width: 760px;">
</p>
<sub><i>Left: Pure semantic retrieval is narrow and myopic. Right: Skill Tree navigation surfaces functionally relevant skills the embedding space hides.</i></sub>

## The Capability Tree

Skills are organized into a coarse-to-fine capability hierarchy. At scale, this is the difference between finding the right skill and drowning in an invisible pile.

<p align="center">
  <img src="tree_10000_expand.gif" alt="10K Skill Tree Explored" height="360">
</p>
<sub><i>The 10,000-category capability tree — the structure our 1,200 skills are mapped into.</i></sub>

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

## Why not just use Hermes OOTB?

Hermes already ships with skill discovery — every user-installed skill appears in the `<available_skills>` block of the system prompt. The LLM scans this flat list every turn and calls `skill_view()` when needed. For small sets it works fine.

skill-retriever adds a **semantic retrieval layer** that transforms skill discovery from "read the catalog" into "search for what you need":

| Dimension | Hermes OOTB | skill-retriever |
|-----------|-------------|-----------------|
| **Skill source** | Your local `~/.hermes/skills/` only (~100-200) | Community corpus (998) + Hermes skills (200) = **1,198 total** |
| **Discovery** | Flat name+desc list in system prompt every turn | LLM-navigated taxonomy tree → top-5 relevant injected as hints |
| **Token cost** | Every turn burns tokens for all skills, even irrelevant ones | Zero system prompt overhead — hints only in user message, only when found |
| **Categorization** | Filesystem directory names | **10,000-category AgentSkillOS capability taxonomy** |
| **Scales to** | ~200 skills before prompt bloat | 10K+ (tree handles it) |
| **Latency per turn** | 0 (passive — always visible) | +1-3 cheap LLM calls for tree traversal (when it has results) |
| **Community corpus** | No | Yes — 998 community skills alongside yours |

**The difference:** OOTB gives you a flat skill catalog you read every turn. skill-retriever turns it into a **search engine** — describe what you need, the tree navigates to the right category, and only relevant suggestions appear. The tradeoff is a small latency cost per turn vs constant system prompt bloat.

<p align="center">
  <img src="fig_framework.png" alt="AgentSkillOS Framework" style="max-width: 720px;">
</p>

## Quick Start

```bash
git clone https://github.com/ChonSong/skill-retriever.git
cd skill-retriever
bash scripts/install.sh
hermes gateway restart
```

## Trust & Safety

Every skill carries a **source tag** and a **safety scan result**:

| Badge | Meaning |
|-------|---------|
| `🔒hermes` | Installed via Hermes — trusted |
| `🌐community` | From AgentSkillOS corpus — unreviewed |
| `⚠️` (suffix) | Flagged by safety scan — review before loading |

All 1,200 skills were scanned for dangerous patterns (`rm -rf /`, `curl | sh` to raw IPs, base64 payloads, crypto miners). **Zero flagged** — every match was standard installer documentation inside code blocks.

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
| `SKILL_RETRIEVER_TREE_PATH` | bundled `tree_10000.yaml` | Override capability tree |

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
│   ├── skill_retriever/    # Core engine
│   │   ├── cli.py          # CLI (search, build, list, info)
│   │   ├── search/         # Searcher (multi-level LLM tree search)
│   │   ├── tree/           # Tree builder, schema, prompts, scanner
│   │   └── capability_tree/# Pre-built trees (YAML + HTML)
│   └── scanner.py  # Hermes skills scanner
├── data/                   # Skill corpus (gitignored)
├── tests/                  # 40 tests
├── scripts/install.sh      # One-click Hermes plugin install
└── ARCHITECTURE.md
```

## License

MIT. Built on [AgentSkillOS](https://github.com/ynulihao/AgentSkillOS) (MIT).
