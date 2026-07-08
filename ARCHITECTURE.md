# Architecture

This document describes the internal architecture of **skill-retriever**, a Hermes Agent plugin that performs semantic skill retrieval using a capability tree and LLM-guided search.

## High-Level Flow

```
                       ┌───────────────────────┐
  User Query ─────────▶│ pre_llm_call hook      │
                       │ (plugin/__init__.py)   │
                       └───────────┬───────────┘
                                   │
                                   ▼
                       ┌───────────────────────┐
                       │ Searcher.search()      │
                       │ (search/searcher.py)   │
                       └───────────┬───────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
   ┌──────────────┐      ┌──────────────────┐   ┌──────────────────┐
   │ Load Tree    │      │ LLM Node Select  │   │ Parallel Child   │
   │ (YAML→Tree)  │      │ (tree navigation)│   │ Search           │
   └──────────────┘      └──────────────────┘   └──────────────────┘
                                   │                      │
                                   ▼                      ▼
                        ┌──────────────────┐   ┌──────────────────┐
                        │ Skill Selection  │   │ Pruning          │
                        │ (leaf node)      │   │ (dedup + rank)   │
                        └──────────────────┘   └──────────────────┘
                                   │
                                   ▼
                       ┌───────────────────────┐
                       │ Hint injection         │
                       │ "[Skill Retrieval ...]" │
                       │ prepended to message   │
                       └───────────────────────┘
```

## Plugin Layer

**File:** `plugin/__init__.py`

Registers a single Hermes hook: `pre_llm_call`. On each user message, it:

1. Checks `SKILL_RETRIEVER_DISABLE=1` — short-circuits if set
2. Ignores messages < 10 characters (greetings, follow-ups)
3. Lazy-loads the `Searcher` singleton
4. Calls `searcher.search(user_message)`
5. Formats top-5 results as a `[Skill Retrieval Hint]` block
6. Returns `{"context": hint_block}` — prepended to the user message

The LLM sees the hints before the user's message and may call `skill_view(name)` to load a suggested skill.

**Borrow-mode:** LLM credentials are read from the environment (`OPENAI_*` or `SKILL_RETRIEVER_LLM_*`), so the plugin needs no separate API key configuration.

## Searcher

**File:** `search/searcher.py`

The core retrieval engine. Key design:

### Tree Loading

- Loads a pre-built YAML capability tree from `src/skill_retriever/capability_tree/tree.yaml`
- Supports two tree formats:
  - **Recursive** (new): `{id, name, description, children: [...], skills: [...]}`
  - **Legacy** (old): `{domains: {domain: {types: {type: {skills: [...]}}}}}`
- After loading, enriches skills with metadata from `data/skill_seeds/skills.json` (github_url, stars, etc.)

### Recursive Search

`_search_node()` is the core recursive function. At each node:

1. **Leaf nodes** (have skills, no children): Call LLM to select relevant skills directly
2. **Intermediate nodes** (have children): Either:
   - **Auto-expand:** If children count ≤ `expand_threshold`, explore all children
   - **LLM select:** Otherwise, call LLM to pick relevant children
3. **Early stop optimization:** If exactly 1 child is selected and it has few skills, collect all without further recursion
4. **Parallel search:** Multiple selected children are searched concurrently via `ThreadPoolExecutor`

### LLM Pruning

After collecting skills from all branches, a final LLM call:

- Deduplicates overlapping skills
- Orders by relevance using a workflow-stage model (upstream/production/downstream)
- Caps at 9 skills max

### Configuration

All search parameters are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILL_RETRIEVER_LLM_MODEL` | `gpt-4o` | LLM model for gate |
| `SKILL_RETRIEVER_LLM_API_KEY` | `OPENAI_API_KEY` | API key |
| `SKILL_RETRIEVER_BRANCHING_FACTOR` | `3` | Tree branching factor |
| `SKILL_RETRIEVER_MAX_PARALLEL` | `5` | Max parallel branches |
| `SKILL_RETRIEVER_TEMPERATURE` | `0.3` | LLM temperature |
| `SKILL_RETRIEVER_PRUNE` | `true` | Enable pruning step |
| `SKILL_RETRIEVER_DISABLE` | — | Set `1` to disable |

## Tree Builder

**File:** `tree/builder.py`

Builds the capability tree from a directory of SKILL.md files.

### Build Process

1. **Scan:** Read all SKILL.md files from the skills directory
2. **Root assignment:** Use LLM to assign skills to 5 fixed root categories (Content Creation, Data Processing, Development, Automation, Domain Specific)
3. **Recursive splitting:** For each oversized category, call LLM to split into sub-groups. Max depth of 6 levels, configurable branching factor (default 8)
4. **Leaf termination:** When a group has ≤ `max_skills_per_node` skills, stop splitting
5. **Output:** Serialize tree to YAML + optional HTML visualization

### Concurrent Execution

Uses `ThreadPoolExecutor` with `FIRST_COMPLETED` pattern — multiple splits run in parallel. Progress bar via Rich.

## Skill Scanner (Corpus)

**File:** `tree/skill_scanner.py`

Scans a directory of `SKILL.md` files (the AgentSkillOS corpus in `data/`). Extracts:

- **id:** Directory name
- **name:** From frontmatter or directory name
- **description:** From frontmatter `description` field, or first paragraph of body
- **content:** Body content after YAML frontmatter
- **metadata:** From optional `skills.json` (github_url, stars, etc.)

## Skill Scanner (Hermes)

**File:** `scanner.py`

Scans the user's local Hermes skill directories (`~/.hermes/skills/` and `~/.hermes/hermes-agent/skills/`). Used by the plugin for context — not for building the capability tree. Reads same `SKILL.md` format but returns flat list with category context.

## Plugin Config

**File:** `src/config.py`

Unified configuration module. All settings are env-var driven with sensible defaults. Imported by both the plugin and the skill_retriever package.

## Capability Tree Data

**Directory:** `src/skill_retriever/capability_tree/`

Pre-built trees:
- `tree.yaml` — Full tree (all AgentSkillOS skills)
- `tree_top1000.yaml` — Top 1000 skills subset
- `tree_top500.yaml` — Top 500 skills subset

Corresponding `.html` files provide interactive visualizations.

## Skill Corpus Data

**Directory:** `data/` (gitignored — 240MB)

- `data/skill_top500/` — Top 500 AgentSkillOS skills with SKILL.md files
- `data/skill_top1000/` — Top 1000 skills

These are downloaded separately and extracted here. The tree builder uses either of these as input.

## Directory Map

```
skill-retriever/
├── plugin/
│   ├── __init__.py      ← Hermes plugin (pre_llm_call hook)
│   └── plugin.yaml      ← Plugin manifest
├── src/
│   ├── config.py        ← Unified env-based configuration
│   ├── scanner.py ← Hermes skills scanner (for plugin)
│   └── skill_retriever/
│       ├── __init__.py  ← Public API exports
│       ├── __main__.py  ← CLI entry point
│       ├── cli.py       ← CLI commands (search, build, list, info)
│       ├── config.py    ← Module config (re-exports + LiteLLM cache)
│       ├── search/
│       │   └── searcher.py  ← Core search engine
│       ├── tree/
│       │   ├── builder.py   ← Tree builder
│       │   ├── prompts.py   ← LLM prompts
│       │   ├── schema.py    ← Data classes (TreeNode, Skill, etc.)
│       │   ├── skill_scanner.py ← Corpus scanner
│       │   └── visualizer.py    ← HTML tree visualization
│       └── capability_tree/  ← Pre-built trees (YAML + HTML)
├── data/                 ← Skill corpus (gitignored)
├── tests/                ← Test suite
├── scripts/install.sh    ← One-click Hermes plugin install
├── ARCHITECTURE.md       ← This file
├── README.md
└── pyproject.toml
```
