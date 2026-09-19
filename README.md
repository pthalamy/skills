# skills

My personal collection of [Agent Skills](https://agentskills.io), written and
maintained by me. Each skill is a folder with a `SKILL.md` that teaches an AI
agent a workflow I use often enough to want it repeatable.

Agent Skills is an open standard, so the same files work across the major AI
providers' coding agents: Claude Code, OpenAI Codex, Cursor, GitHub Copilot,
Gemini CLI and a couple dozen others. Nothing here is tied to one vendor.

## Skills

| Skill | What it does |
| ----- | ------------ |
| [gedcom-maintainer](skills/gedcom-maintainer/SKILL.md) | Maintain GEDCOM family trees as an evidence-backed graph: sourced, QUAY-graded edits only, conflicts and hypotheses recorded in notes, Genealogical Proof Standard guidance, plus scripts to validate structure, links, dates and chronology, and to inspect and diff large files. |

## Install

Pick whichever route matches your tooling. All of them end up with
`<skills-dir>/<skill-name>/SKILL.md` in the place your agent scans.

### Any agent, from this repo (recommended)

Clone once, then link the skills into every agent you use. Symlinks mean a
later `git pull` updates all of them.

```bash
git clone https://github.com/pthalamy/skills.git
cd skills
python3 scripts/install.py --list                        # see supported agents
python3 scripts/install.py --agent claude-code agents    # Claude Code + the shared .agents dir
python3 scripts/install.py --agent all                   # everything
```

Useful flags: `--scope project --project-dir <path>` installs into a single
project, `--mode copy` copies instead of linking, `--skill a b` limits the set,
`--uninstall` reverses it, `--dry-run` previews.

### With a package-manager style CLI

The repo follows the `skills/<name>/SKILL.md` layout these tools discover
automatically:

```bash
# Vercel skills CLI, targets 75+ agents at once
npx skills add pthalamy/skills                # pick skills interactively
npx skills add pthalamy/skills -a claude-code -a codex -a cursor -g

# GitHub CLI (>= 2.90), for Copilot, Claude Code and others via --agent
gh skill install pthalamy/skills <skill-name> --scope user

# Gemini CLI
gemini skills install https://github.com/pthalamy/skills --consent

# Amp
amp skill add https://github.com/pthalamy/skills --global
```

### Provider-specific routes

| Provider / agent | How |
| ---------------- | --- |
| Claude Code | `/plugin marketplace add pthalamy/skills` then `/plugin install pthalamy-skills@pthalamy-skills`. Skills appear as `/pthalamy-skills:<name>`. |
| Claude.ai / Claude API | Zip one skill folder and upload it under Customize (claude.ai) or with the Skills API (`client.skills.create`). |
| OpenAI Codex | Inside Codex: `$skill-installer install https://github.com/pthalamy/skills/tree/main/skills/<name>`. |
| ChatGPT | Zip one skill folder and upload it under Skills, Create, Upload (Business, Enterprise and Edu plans). |
| Cursor | Reads `.agents/skills` and `~/.cursor/skills`; use the install script or `npx skills add`. |
| GitHub Copilot | `gh skill install pthalamy/skills <name>` or `copilot skill add <url>`; project skills live in `.github/skills`. |
| Gemini CLI | `gemini skills install <repo-url>` or the install script. |
| Others | OpenCode, Amp, Goose, Factory, Windsurf, Cline, Kiro, Zed, Warp, Augment, Letta: see `scripts/install.py --list` for the directory each one scans. |

### Where each agent looks

| Agent | User-level | Project-level |
| ----- | ---------- | ------------- |
| Shared convention | `~/.agents/skills/` | `.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/`, `~/.codex/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/`, `~/.agents/skills/` | `.cursor/skills/`, `.agents/skills/` |
| GitHub Copilot / VS Code | `~/.copilot/skills/`, `~/.agents/skills/` | `.github/skills/`, `.agents/skills/`, `.claude/skills/` |
| Gemini CLI | `~/.gemini/skills/`, `~/.agents/skills/` | `.gemini/skills/`, `.agents/skills/` |
| OpenCode | `~/.config/opencode/skills/`, `~/.agents/skills/` | `.opencode/skills/`, `.agents/skills/` |
| Amp | `~/.config/agents/skills/` | `.agents/skills/` |
| Goose | `~/.agents/skills/` | `.agents/skills/` |
| Factory Droid | `~/.factory/skills/` | `.factory/skills/` |
| Windsurf | none | `.windsurf/skills/`, `.agents/skills/` |
| Cline | `~/.cline/skills/` | `.cline/skills/` |
| Kiro | `~/.kiro/skills/` | `.kiro/skills/` |
| Zed, Warp, Augment, Letta | see `scripts/install.py --list` | |

The shared `.agents/skills/` convention is read natively by most agents except
Claude Code, Kiro, Cline and Factory, which is why the install script offers
both the `agents` target and per-agent targets.

## Repository layout

```text
.
├── skills/                 # one folder per skill, each with a SKILL.md
├── templates/
│   └── skill-template/     # starting point copied by scripts/new_skill.py
├── scripts/
│   ├── new_skill.py        # scaffold a new skill from the template
│   ├── validate_skills.py  # lint frontmatter, names, portability, manifests
│   └── install.py          # link or copy skills into any supported agent
├── .claude-plugin/
│   ├── plugin.json         # makes the repo installable as a Claude Code plugin
│   └── marketplace.json    # lets Claude Code add the repo as a marketplace
├── AGENTS.md               # guidance for agents working in this repo
└── .github/workflows/
    └── validate.yml        # runs the validator on every push and PR
```

## Adding a skill

1. Scaffold it:

   ```bash
   python3 scripts/new_skill.py my-skill
   ```

2. Edit `skills/my-skill/SKILL.md`. The frontmatter `description` is what makes
   an agent pick the skill, so say both what it does and when to use it. Keep
   the body under about 500 lines and move long material into `references/`,
   executable helpers into `scripts/`, and output templates into `assets/`.

3. Validate:

   ```bash
   python3 scripts/validate_skills.py
   ```

   The validator warns about frontmatter fields outside the specification,
   since other agents ignore them.

4. Add a row to the table above and bump `version` in the two
   `.claude-plugin/*.json` files.

Anthropic's `skill-creator` skill is a good companion for drafting,
test-driving and tuning a skill's description before it lands here. The
reference validator from the standard, `skills-ref validate <path>`, is another
useful check.

## Conventions

- Skill names are kebab-case, at most 64 characters, and match their folder name.
- Descriptions are written in the third person, state what the skill does and
  when to trigger it, and stay under 1024 characters.
- Skills stay portable: spec frontmatter fields only unless there is a good
  reason, "the agent" rather than a product name in the body, scripts in
  Python 3 or POSIX shell with no agent-specific dependencies.
- Instructions favour explaining *why* over shouting MUST. Agents are smart;
  give them the reasoning and they generalise better.
- Skills never contain secrets, credentials or customer data. Anything private
  stays in a private repo.

## License

[MIT](LICENSE)
