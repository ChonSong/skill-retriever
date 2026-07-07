"""
All prompts for skill_retriever - centralized and in English.
"""

# =============================================================================
# Tree Building Prompts (Recursive)
# =============================================================================

RECURSIVE_SPLIT_PROMPT = """You are organizing {count} skills into sub-categories.

{context_section}

## Skills to Organize
{skills_list}

## Grouping Rules
1. Group by capability domain, not technical implementation
2. **CRITICAL: Every skill MUST be assigned to exactly one group - no unassigned skills allowed**
3. Each group should have at least 2 skills (merge singleton skills into the most related group)
4. Use lowercase-with-hyphens for group IDs (e.g., "document-editing")
5. Write detailed descriptions (see format below)

## Number of Groups
Target: {min_groups}-{max_groups} groups. Adjust based on skill diversity.

## Output Format (JSON only)
{{
  "groups": {{
    "group-id": {{
      "name": "Group Name",
      "description": "2-3 sentences: What user goals this addresses. Types of skills included. When to look here.",
      "skill_ids": ["skill1", "skill2", "skill3"]
    }}
  }}
}}
"""

FIXED_CATEGORY_ASSIGNMENT_PROMPT = """You are assigning {count} skills to predefined categories.

## Fixed Categories
{categories_list}

## Skills to Assign
{skills_list}

## Assignment Rules
1. **CRITICAL: Every skill MUST be assigned to exactly one category - no unassigned skills allowed**
2. **DO NOT create new categories** - only use the categories listed above
3. Choose the category that best matches each skill's primary capability domain
4. When a skill could fit multiple categories, choose based on its PRIMARY use case
5. For each category that has assigned skills, write a description (2-3 sentences) that:
   - Explains what user goals this category addresses based on the assigned skills
   - Describes the types of skills included
   - Indicates when users should look here

## Output Format (JSON only)
{{
  "assignments": {{
    "category-id": {{
      "skill_ids": ["skill_id_1", "skill_id_2", ...],
      "description": "2-3 sentences describing this category based on assigned skills"
    }}
  }}
}}
"""

# =============================================================================
# Legacy Tree Building Prompts (kept for reference, may be removed later)
# =============================================================================

STRUCTURE_DISCOVERY_PROMPT = """You are a skill taxonomy expert. Analyze these {count} representative skills and design a hierarchical structure.

## Skills to Analyze
{skills_list}

## Seed Domains (expand only if necessary)
- content-creation: Content authoring (documents, images, presentations, copy)
- data-processing: Data analysis, visualization, transformation
- development: Developer tools (code generation, testing, APIs)
- automation: Browser automation, workflows, integrations
- domain-specific: Vertical domains (healthcare, finance, research)

## Design Principles
1. Group by user intent, not technical functionality
2. Each type should have 3-8 skills
3. Skills that users would typically use together should be in the same type
4. Use lowercase-with-hyphens for IDs (e.g., "document-creation", "image-generation")

## Output Format (JSON only, no explanation)
{{
  "domains": {{
    "domain-id": {{
      "name": "Domain Name",
      "description": "Brief description of this domain",
      "types": {{
        "type-id": {{
          "name": "Type Name",
          "description": "Brief description of this type",
          "example_skill_ids": ["skill1", "skill2"]
        }}
      }}
    }}
  }}
}}
"""

ANCHORED_CLASSIFICATION_PROMPT = """Classify these {count} skills into the established structure below.

## Established Structure
{structure_anchor}

## Skills to Classify
{skills_list}

## Rules
1. Use ONLY the types listed above - do not invent new types
2. If a skill truly does not fit ANY existing type, mark it with "new_type_needed": true
3. For ambiguous skills, choose the type that best matches user intent

## Output Format (JSON array only, no explanation)
[
  {{"id": "skill_id", "domain": "domain-id", "type": "type-id"}},
  {{"id": "another_skill", "domain": "domain-id", "type": "type-id", "new_type_needed": true, "suggested_type": "new-type-name", "reason": "why"}}
]
"""

NODE_SPLITTING_PROMPT = """Group these {count} skills into {min_groups}-{max_groups} sub-categories based on user intent.

## Skills to Group
{skills_list}

## Grouping Principles
1. Group by what users want to accomplish, not by technical implementation
2. Each group should have at least 2 skills
3. Use lowercase-with-hyphens for group IDs (e.g., "document-editing", "image-generation")
4. Provide a brief, clear name and description for each group

## Output Format (JSON only, no explanation)
{{
  "groups": {{
    "group-id": {{
      "name": "Group Name",
      "description": "Brief description of what this group does",
      "skill_ids": ["skill1", "skill2", "skill3"]
    }}
  }}
}}
"""

# =============================================================================
# Search Prompts
# =============================================================================

NODE_SELECTION_PROMPT = """User task: {query}

Select the relevant categories for this task from the options below:

{options}

## Selection Principles
- Select all categories that might be needed for the task
- Consider what the user ultimately wants to achieve
- If uncertain, select more rather than fewer

Output format (JSON array of selected IDs only):
{example}
"""

SKILL_SELECTION_PROMPT = """User task: {query}

Select the skills needed to complete this task:

{options}

## Selection Principles
- Select all skills that could help complete the task
- Consider skill combinations for complex tasks
- Prefer skills that directly address the user's intent

Output format (JSON array of skill IDs only):
["skill_id_1", "skill_id_2"]
"""

# =============================================================================
# Pruning Prompts
# =============================================================================
# V3: Workflow-Stage model - upstream/production/downstream
SKILL_PRUNE_PROMPT = """User task: {query}

## Skills to Evaluate
{skills_list}

## Your Task
Select skills by mapping out the COMPLETE WORKFLOW to achieve the goal.

## Step 1: Decompose into Workflow Stages

Think through what's needed at each stage:

### UPSTREAM (0-2 skills) - Gather & Prepare
What input/content needs to be accessed or extracted first?
- Reading documents, extracting data, gathering source material
- Ask: "What does the user need to START with?"

### PRODUCTION (1-5 skills) - Create & Build
What tangible deliverables or assets need to be CREATED?
- Think BROADLY: visuals, documents, presentations, websites, videos
- Ask: "What would the user SHOW, SHARE, or USE?"
- Ask: "What would a professional create for this task?"
- IMPORTANT: Different formats serve different purposes - a presentation is not a substitute for an image

### DOWNSTREAM (0-2 skills) - Deliver & Distribute
How will the created content reach its audience?
- Publishing, sharing, deploying, distributing

## Critical Thinking Prompts
Before selecting skills, ask yourself:
1. "What FORMATS could help achieve this goal?" (visual/document/web/social)
2. "What would make this goal SUCCESSFUL, not just done?"
3. "Am I selecting skills that CREATE things, or just skills that SOUND related?"

## Anti-Pattern Warning
Do NOT over-index on keyword-matching skills:
- "promote" ≠ only marketing/SEO skills
- Effective promotion requires ASSETS to promote
- Creation tools often matter MORE than distribution tools

## Output Format (JSON only)
{{
  "workflow_analysis": "1-2 sentence analysis of what stages this task needs",
  "upstream": [
    {{"id": "skill_id", "role": "What it prepares/extracts"}}
  ],
  "production": [
    {{"id": "skill_id", "role": "What deliverable it creates"}}
  ],
  "downstream": [
    {{"id": "skill_id", "role": "How it delivers the result"}}
  ],
  "eliminated": [
    {{"id": "skill_id", "reason": "Why not selected"}}
  ]
}}

LIMITS: upstream 0-2, production 1-5, downstream 0-2, total max 9
"""


SKILL_PRUNE_PROMPT = """User task: {query}

## Skills to Evaluate
{skills_list}

## Your Task
Filter, deduplicate, and RANK skills by relevance for the user's task.

## Rules
1. **Deduplicate**: If multiple skills have overlapping functionality, keep only the BEST one
2. **Keep generously**: Retain skills that could potentially help with ANY aspect of the task
   - Keep skills that create useful assets or materials (images, documents, presentations, etc.)
   - Keep skills that support the workflow: preparation → creation → delivery
   - Only remove skills that are CLEARLY unrelated and would confuse the user
3. Each skill ID can only appear ONCE
4. **CRITICAL: Order selected_skills by relevance (most relevant FIRST)**

## Output Format (JSON only)
{{
  "selected_skills": [
    {{"id": "most_relevant_skill", "reason": "Why this skill is most relevant"}},
    {{"id": "second_most_relevant", "reason": "Why this skill helps"}},
    ...
  ],
  "eliminated": [
    {{"id": "skill_x", "reason": "Duplicate of X / Clearly unrelated"}}
  ]
}}
"""
