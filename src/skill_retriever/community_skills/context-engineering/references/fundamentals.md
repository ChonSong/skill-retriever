# Context Fundamentals

Context = all input provided to LLM for task completion.

## Anatomy of Context

| Component | Purpose | Token Impact |
|-----------|---------|--------------|
| System Prompt | Identity, constraints, guidelines | Stable, cacheable |
| Tool Definitions | Action specs with params/returns | Grows with capabilities |
| Retrieved Docs | Domain knowledge, just-in-time | Variable, selective |
| Message History | Conversation state, task progress | Accumulates over time |
| Tool Outputs | Results from actions | Majority of typical context |

## Attention Mechanics

- **U-shaped curve**: Beginning/end get more attention than middle
- **Attention budget**: n^2 relationships for n tokens depletes with growth
- **Position encoding**: Interpolation allows longer sequences with degradation
- **First-token sink**: BOS token absorbs large attention budget

## Progressive Disclosure Levels

1. **Metadata** (~100 words) - Always in context
2. **SKILL.md body** (<5k words) - When skill triggers
3. **Bundled resources** (Unlimited) - As needed

## Token Budget Allocation

| Component | Typical Range | Notes |
|-----------|---------------|-------|
| System Prompt | 500-2000 | Stable, optimize once |
| Tool Definitions | 100-500 per tool | Keep under 20 tools |
| Retrieved Docs | 1000-5000 | Selective loading |
| Message History | Variable | Summarize at 70% |
| Reserved Buffer | 10-20% | For responses |

## Document Management

**Strong identifiers**: `customer_pricing_rates.json` not `data/file1.json`
**Chunk at semantic boundaries**: Paragraphs, sections, not arbitrary lengths
**Include metadata**: Source, date, relevance score

## Guidelines

1. Treat context as finite with diminishing returns
2. Place critical info at attention-favored positions
3. Use file-system-based access for large documents
4. Pre-load stable content, just-in-time load dynamic
5. Design with explicit token budgets
6. Monitor usage, implement compaction triggers at 70-80%
