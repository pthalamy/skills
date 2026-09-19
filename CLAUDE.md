# Working in this repository

This is a public collection of Agent Skills. There is no application code.

- Every skill lives in `skills/<name>/SKILL.md`; the folder name and the
  frontmatter `name` must match. Scaffold new ones with
  `python3 scripts/new_skill.py <name>` rather than by hand.
- Run `python3 scripts/validate_skills.py` before committing. CI runs the same
  script, plus the template check `--path templates --skip-manifests`.
- When you add, rename or remove a skill, update the table in `README.md` and
  bump `version` in both `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`.
- Keep `SKILL.md` files focused: description says what and when, body explains
  the workflow and why it matters, long material goes to `references/`.
- Never commit secrets, tokens, or private company material. The repo is public.
