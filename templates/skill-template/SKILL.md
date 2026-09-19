---
name: skill-template
description: >-
  One or two sentences on WHAT this skill does, then WHEN Claude should use it.
  Be explicit and a little pushy about triggers: list the phrases, file types,
  or situations that should activate it, even when the user does not name the
  skill. Example: "Use whenever the user mentions X, Y or Z, or wants to ...".
# Optional Claude Code fields. Delete the ones you do not need.
# argument-hint: "[input-file] [format]"
# allowed-tools: Bash(git *) Read Grep
# disable-model-invocation: false   # true = only the user can invoke it via /skill-name
# user-invocable: true              # false = hidden from the / menu, Claude-only
# paths: "**/*.sql"                 # auto-load only when matching files are in play
# license: MIT
# metadata:
#   author: Pierre Thalamy
#   category: writing | code | data | ops
---

# Skill Name

One paragraph on the goal of this skill and the outcome it produces. Write for
Claude: explain *why* the steps below matter rather than piling up MUSTs.

## When to use

The frontmatter `description` is what triggers the skill. Use this section for
nuance only: near-miss situations where the skill should *not* be used, or how
it relates to a neighbouring skill.

## Workflow

1. First step. Prefer the imperative form.
2. Second step. Point to bundled files when they are needed, e.g.
   "read `references/style-guide.md` before drafting".
3. Third step. If a deterministic task repeats every time (a conversion, a
   lookup, a validation), ship it as a script in `scripts/` and call it instead
   of re-deriving it.

## Output format

Describe the shape of the result. A template is often the clearest way:

```markdown
# [Title]
## Summary
## Details
## Next steps
```

## Examples

**Example 1**

Input: what the user said or provided.
Output: what the skill should produce.

## Bundled resources (optional)

Keep `SKILL.md` under about 500 lines. Move anything larger into:

- `references/` for documentation Claude reads on demand.
- `scripts/` for executable helpers.
- `assets/` for files used in the output (templates, images, fonts).
