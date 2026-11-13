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
| Copy | Backticked and bare `hermes <cmd>` hints → `iskra`, across code, root modules and tests (~3,900) |
| Locales | `locales/*.yaml`: product name → Iskra, `~/.hermes` → `~/.iskra`, 33 files / ~6,200 strings |
| Updater | `OFFICIAL_REPOSITORY` / `OFFICIAL_REPO_URL(S)` → `ockentap/iskra-agent`; no-release 404 stays quiet |
| Installer | `scripts/install.sh`: repo URL and install dir defaults |
| Docs links | every `hermes-agent.nousresearch.com` URL → `ockentap.github.io/iskra-agent` |
| Website | Docusaurus rebrand + spark art + animated landing, published to GitHub Pages |

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

## Website / GitHub Pages

The docs site is rebranded and published to GitHub Pages at
**https://ockentap.github.io/iskra-agent/** (project Pages, source = GitHub Actions,
deployed by `.github/workflows/pages.yml` on pushes to `iskra-rebrand`).

- `website/docusaurus.config.ts`: title/tagline → Iskra, `url`/`baseUrl` →
  `ockentap.github.io/iskra-agent/`, org/project → `ockentap/iskra-agent`, docs under
  `/docs/`, English-only, local search (`@easyops-cn/docusaurus-search-local`) in place
  of the Hermes Algolia index.
- New spark brand art in `website/static/img/` (logo, favicon, OG banner, apple icon)
  and an animated landing page at `website/src/pages/index.tsx`.
- Installers are hosted on Pages: `/install.sh` and `/install.ps1`.
- Every `hermes-agent.nousresearch.com` documentation link across the repo now points
  at the Iskra site (docs, installers, model catalog, llms.txt).

## Not done yet (deliberately out of scope for the base pass)

- The community **plugin catalog** pages (`website/plugins/plugin-catalog-pages`,
  ~2,100 upstream plugins → ~3,700 static pages) are disabled: they OOM the build and
  are upstream, not Iskra, content. The Skills hub (Iskra's bundled skills) is kept.
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
python scripts/iskra_update.py --dry-run   # how far behind
python scripts/iskra_update.py             # fetch, merge, reapply rebrand, commit
uv lock && uv sync --python 3.14
```

`scripts/iskra_rebrand.py` is the source of truth for the rename: every change
is a rule, `--check` reports drift and exits non-zero, `--apply` rewrites only
what upstream put back. The update script resolves conflicts inside the
rebrand-owned trees in favour of upstream and then re-applies, because nothing
hand-written lives there. Conflicts anywhere else abort the merge for a human.

The first merge from upstream (6,935 commits, v0.23.0 → 2026-11) needed zero
conflict resolution: 24/24 rules survived untouched.

Conflicts should be limited to the table above; that is the cost of keeping the
internal names untouched.
