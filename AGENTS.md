# Working in this repository

This is a public collection of Agent Skills (the open `SKILL.md` format from
https://agentskills.io). There is no application code. These notes apply to any
coding agent working here: Claude Code, Codex, Cursor, Copilot, Gemini CLI and
others.

- Every skill lives in `skills/<name>/SKILL.md`; the folder name and the
  frontmatter `name` must match. Scaffold new ones with
  `python3 scripts/new_skill.py <name>` rather than by hand.
- Run `python3 scripts/validate_skills.py` before committing. CI runs the same
  script, plus the template check `--path templates --skip-manifests`.
- Skills must stay portable. Use only spec frontmatter fields (`name`,
  `description`, `license`, `metadata`, `allowed-tools`) unless a Claude Code
  only field is clearly needed; other agents ignore those. Avoid
  `compatibility` even though the spec allows it: ChatGPT's skill validator
  rejects it, so state requirements in the body. In the body, say "the
  agent", not a product name, and avoid product-specific slash commands.
- When you add, rename or remove a skill, update the table in `README.md` and
  bump `version` in both `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`.
- `scripts/install.py` links or copies skills into each agent's skills
  directory. When a tool changes where it scans, update the `AGENTS` table
  there and the matching rows in `README.md`.
- Keep `SKILL.md` files focused: description says what and when, body explains
  the workflow and why it matters, long material goes to `references/`.
- Never commit secrets, tokens, or private company material. The repo is public.
