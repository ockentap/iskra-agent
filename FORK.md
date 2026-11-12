# Iskra — fork notes

Iskra is a rebranded fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent),
MIT-licensed. Upstream copyright is retained in `LICENSE`; the fork is maintained
at `ockentap/iskra-agent`.

## What this fork changes (surface rebrand)

Everything below is user-facing naming only. Internal module names (`hermes_cli/`,
`hermes_state_*`, `hermes_constants.py`), environment variables (`HERMES_*`), config
keys, database schema and skill/plugin APIs are deliberately **unchanged**, so this
fork can still merge upstream and can still load existing Hermes skills and plugins.

| Area | Change |
|------|--------|
| Distribution | `pyproject.toml`: `name = "iskra-agent"`, extras self-references updated |
| CLI entry points | `iskra`, `iskra-agent`, `iskra-acp` (was `hermes`, `hermes-agent`, `hermes-acp`) |
| Launcher | `./iskra` at repo root |
| Agent identity | `agent/prompt_builder.py`: "You are Iskra." |
| Version banner | `hermes_cli/banner.py`, `agent/legacy_cli.py`, `hermes_cli/status.py` |
| Data directory | default `~/.iskra` (was `~/.hermes`), `hermes_constants.py` |
| Gateway header | WhatsApp default reply prefix → `☤ *Iskra*` |
| Updater | `OFFICIAL_REPOSITORY` / `OFFICIAL_REPO_URL(S)` → `ockentap/iskra-agent` |
| Installer | `scripts/install.sh`: repo URL and install dir defaults |

`_UPSTREAM_ADD_CMD` is intentionally left pointing at `NousResearch/hermes-agent`:
`origin` is the fork, `upstream` stays the original project for merges.

## Compatibility notes

- `HERMES_HOME` still overrides the data directory. Set `HERMES_HOME=~/.hermes`
  to share an existing Hermes install's config, sessions and skills.
- The systemd unit and Windows task names remain `hermes-gateway*`. Renaming them
  means touching the update-pause, journal and health-check paths that match on
  that prefix; deferred on purpose so an Iskra gateway can coexist with a Hermes
  one during migration.
- `HERMES_*` environment variables are unchanged.

## Not done yet (deliberately out of scope for the base pass)

- `website/` Docusaurus site (title, domain, org) and the 242 files that link to
  `hermes-agent.nousresearch.com`.
- `ui-tui` npm package name (`hermes-tui`), `apps/desktop` bundle identifiers,
  Windows/macOS code signing.
- 56 GitHub Actions workflows — most need Nous infrastructure, release channels,
  notarization and signing secrets that do not transfer to a fork.
- Bundled `skills/`, `optional-skills/`, `plugin-catalog/` still describe Hermes
  commands in their prose. Cosmetic; the commands themselves are aliased by the
  entry points only if you also install the `hermes` shim.
- `.github/`, `Dockerfile`, `docker-compose.yml`, `flake.nix` image/tag names.

## Install (from this repo)

```bash
git clone https://github.com/ockentap/iskra-agent.git ~/.iskra/iskra-agent
cd ~/.iskra/iskra-agent
uv sync --python 3.14
uv run iskra --version        # or: .venv/bin/iskra
```

## Updating from upstream

```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch upstream && git merge upstream/main
```

Conflicts should be limited to the table above; that is the cost of keeping the
internal names untouched.
