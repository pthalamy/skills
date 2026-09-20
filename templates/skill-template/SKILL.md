---
name: skill-template
description: >-
  One or two sentences on WHAT this skill does, then WHEN an agent should use it.
  Be explicit and a little pushy about triggers: list the phrases, file types,
  or situations that should activate it, even when the user does not name the
  skill. Example: "Use whenever the user mentions X, Y or Z, or wants to ...".
# --- Optional fields from the Agent Skills specification (portable) ---
# license: MIT
# compatibility: Needs git and network access.   # max 500 chars; ChatGPT's validator rejects it, so state requirements in the body instead
# metadata:
#   author: Pierre Thalamy
#   category: genealogy | writing | code | data | ops   # groups the README table
# allowed-tools: Bash(git *) Read Grep            # pre-approved tools, experimental in the spec
# --- Optional Claude Code only fields (other agents ignore them) ---
# argument-hint: "[input-file] [format]"
# disable-model-invocation: false   # true = only the user can invoke it via /skill-name
# user-invocable: true              # false = hidden from the / menu, Claude-only
# paths: "**/*.sql"                 # auto-load only when matching files are in play
---

# Skill Name

One paragraph on the goal of this skill and the outcome it produces. Write for
the agent: explain *why* the steps below matter rather than piling up MUSTs.
Stay tool-agnostic: the same file is read by Claude Code, Codex, Cursor,
Copilot, Gemini CLI and others, so refer to "the agent", not to one product,
and avoid product-specific slash commands in the body.

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
   of re-deriving it. Prefer portable scripts (Python 3 or POSIX shell) with no
   agent-specific dependencies.

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

- `references/` for documentation the agent reads on demand.
- `scripts/` for executable helpers.
- `assets/` for files used in the output (templates, images, fonts).
