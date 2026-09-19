# skills

My personal collection of [Agent Skills](https://agentskills.io) for Claude,
written and maintained by me. Each skill is a folder with a `SKILL.md` that
teaches Claude a workflow I use often enough to want it repeatable.

The repository is also a [Claude Code plugin](https://code.claude.com/docs/en/plugins),
so the whole collection can be installed with two commands.

## Skills

| Skill | What it does |
| ----- | ------------ |
| _none yet_ | Add the first one with `python3 scripts/new_skill.py <name>` |

## Install

### Claude Code, as a plugin (recommended)

```text
/plugin marketplace add pthalamy/skills
/plugin install pthalamy-skills@pthalamy-skills
```

Skills then show up as `/pthalamy-skills:<skill-name>` and Claude can invoke
them on its own when a task matches their description. Update later with
`/plugin update pthalamy-skills`.

### Claude Code, manual copy

Copy the skill folders you want into one of these directories:

| Scope | Directory |
| ----- | --------- |
| Personal, every project | `~/.claude/skills/` |
| One project only | `<project>/.claude/skills/` |

```bash
git clone https://github.com/pthalamy/skills.git
cp -r skills/skills/<skill-name> ~/.claude/skills/
```

### Claude.ai and the Claude API

Zip a single skill folder (the folder containing `SKILL.md`) and upload it in
Claude.ai under Settings, Capabilities, Skills, or attach it to an API request.
The same `SKILL.md` format works everywhere Agent Skills are supported.

## Repository layout

```text
.
├── skills/                 # one folder per skill, each with a SKILL.md
├── templates/
│   └── skill-template/     # starting point copied by scripts/new_skill.py
├── scripts/
│   ├── new_skill.py        # scaffold a new skill from the template
│   └── validate_skills.py  # lint frontmatter, names and plugin manifests
├── .claude-plugin/
│   ├── plugin.json         # makes the repo installable as a Claude Code plugin
│   └── marketplace.json    # lets Claude Code add the repo as a marketplace
└── .github/workflows/
    └── validate.yml        # runs the validator on every push and PR
```

## Adding a skill

1. Scaffold it:

   ```bash
   python3 scripts/new_skill.py my-skill
   ```

2. Edit `skills/my-skill/SKILL.md`. The frontmatter `description` is what makes
   Claude pick the skill, so say both what it does and when to use it. Keep the
   body under about 500 lines and move long material into `references/`,
   executable helpers into `scripts/`, and output templates into `assets/`.

3. Validate:

   ```bash
   python3 scripts/validate_skills.py
   ```

4. Add a row to the table above and bump `version` in the two
   `.claude-plugin/*.json` files.

Anthropic's own `skill-creator` skill is a good companion for drafting,
test-driving and tuning a skill's description before it lands here.

## Conventions

- Skill names are kebab-case, at most 64 characters, and match their folder name.
- Descriptions are written in the third person, state what the skill does and
  when to trigger it, and stay under 1024 characters.
- Instructions favour explaining *why* over shouting MUST. Claude is smart;
  give it the reasoning and it generalises better.
- Skills never contain secrets, credentials or customer data. Anything private
  stays in a private repo.

## License

[MIT](LICENSE)
