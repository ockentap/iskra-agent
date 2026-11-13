#!/usr/bin/env python3
"""Reapply the Iskra rebrand on top of a freshly merged upstream Hermes tree.

The fork keeps Hermes' internal module names, ``HERMES_*`` environment
variables and config keys untouched so that upstream merges stay cheap; only
the user-facing surface is renamed.  That surface lives in a small, known set
of files, and this script is the single source of truth for it.

    python scripts/iskra_rebrand.py --check    # report only, exit 1 on drift
    python scripts/iskra_rebrand.py --apply    # rewrite what needs rewriting

Each rule is one of two shapes:

* literal  -- ``old`` must appear (then it is rewritten) or ``new`` must
              already be there (nothing to do).
* regex    -- searched across a glob; same idempotency contract.

When neither the upstream text nor the rebranded text is present, the rule is
reported as DRIFT: upstream changed that line and a human has to decide what
the rebranded version should say.  ``--apply`` never guesses.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OK = "ok"
APPLIED = "applied"
DRIFT = "drift"


@dataclass
class Rule:
    path: str
    old: str
    new: str
    count: int = 1                 # literal: expected occurrences; 0 = any
    name: str = ""

    def label(self) -> str:
        return self.name or f"{self.path}: {self.old[:48]!r}"


@dataclass
class RegexRule:
    glob: str
    pattern: str
    replacement: str
    name: str = ""
    found: int = 0

    def label(self) -> str:
        return self.name or f"{self.glob}: /{self.pattern}/"


LITERAL_RULES: list[Rule] = [
    # --- packaging -------------------------------------------------------
    Rule("pyproject.toml", 'name = "hermes-agent"', 'name = "iskra-agent"',
         name="pyproject: distribution name"),
    Rule("pyproject.toml",
         'description = "The self-improving AI agent — creates skills from experience, '
         'improves them during use, and runs anywhere"',
         'description = "Iskra — a self-improving AI agent that creates skills from '
         'experience, improves them during use, and runs anywhere"',
         name="pyproject: description"),
    Rule("pyproject.toml",
         'hermes = "hermes_cli.main:main"\nhermes-agent = "agent.legacy_cli:main"\n'
         'hermes-acp = "acp_adapter.entry:main"',
         'iskra = "hermes_cli.main:main"\niskra-agent = "agent.legacy_cli:main"\n'
         'iskra-acp = "acp_adapter.entry:main"',
         name="pyproject: console scripts"),
    Rule("pyproject.toml", '"hermes-agent[', '"iskra-agent[', count=0,
         name="pyproject: extras self-references"),

    # --- agent identity --------------------------------------------------
    Rule("agent/prompt_builder.py",
         '"You are Hermes Agent, built by Nous Research. Be direct:',
         '"You are Iskra. Be direct:',
         name="prompt: agent identity"),

    # --- data directory --------------------------------------------------
    Rule("hermes_constants.py", 'base / ("hermes" + suffix)', 'base / ("iskra" + suffix)',
         name="constants: windows data dir"),
    Rule("hermes_constants.py", 'user_home() / (".hermes" + suffix)',
         'user_home() / (".iskra" + suffix)',
         name="constants: posix data dir"),
    Rule("hermes_constants.py", 'pw_dir) / ".hermes"', 'pw_dir) / ".iskra"',
         name="constants: sudo fallback"),

    # --- banners / version ----------------------------------------------
    Rule("hermes_cli/banner.py", "Hermes Agent v{get_version_info().derived_version}",
         "Iskra v{get_version_info().derived_version}", count=0,
         name="banner: version label"),
    Rule("agent/legacy_cli.py", 'version=f"Hermes Agent v{__version__}',
         'version=f"Iskra v{__version__}',
         name="legacy_cli: --version"),
    Rule("agent/legacy_cli.py", 'prog="hermes-agent"', 'prog="iskra-agent"',
         name="legacy_cli: prog name"),
    Rule("agent/legacy_cli.py", 'description="Legacy single-query Hermes Agent runner.',
         'description="Legacy single-query Iskra runner.',
         name="legacy_cli: description"),
    Rule("hermes_cli/_parser.py",
         'description="Hermes Agent - AI assistant with tool-calling capabilities"',
         'description="Iskra - AI assistant with tool-calling capabilities"',
         name="parser: description"),

    # --- gateway ---------------------------------------------------------
    Rule("gateway/platforms/whatsapp_common.py", '☤ *Hermes Agent*', '☤ *Iskra*',
         name="gateway: whatsapp reply prefix"),

    # --- updater ---------------------------------------------------------
    Rule("hermes_cli/source_releases.py", 'OFFICIAL_REPOSITORY = "NousResearch/hermes-agent"',
         'OFFICIAL_REPOSITORY = "ockentap/iskra-agent"',
         name="updater: official repository"),
    Rule("hermes_cli/source_releases.py",
         '    except (OSError, ValueError, subprocess.SubprocessError) as exc:\n'
         '        logger.warning("Could not resolve the stable source release: %s", exc)\n'
         '        raise ValueError(_describe_release_failure(exc)) from exc',
         '    except (OSError, ValueError, subprocess.SubprocessError) as exc:\n'
         '        # A fork with no published releases is not a warning-level event.\n'
         '        if "404" not in str(exc):\n'
         '            logger.warning("Could not resolve the stable source release: %s", exc)\n'
         '        raise ValueError(_describe_release_failure(exc)) from exc',
         name="updater: quiet 404 for fork without releases"),
    Rule("hermes_cli/update_cmd_git.py",
         'OFFICIAL_REPO_URLS = {\n'
         '    "https://github.com/NousResearch/hermes-agent.git",\n'
         '    "git@github.com:NousResearch/hermes-agent.git",\n'
         '    "https://github.com/NousResearch/hermes-agent",\n'
         '    "git@github.com:NousResearch/hermes-agent",\n'
         '}\n'
         'OFFICIAL_REPO_URL = "https://github.com/NousResearch/hermes-agent.git"',
         'OFFICIAL_REPO_URLS = {\n'
         '    "https://github.com/ockentap/iskra-agent.git",\n'
         '    "git@github.com:ockentap/iskra-agent.git",\n'
         '    "https://github.com/ockentap/iskra-agent",\n'
         '    "git@github.com:ockentap/iskra-agent",\n'
         '}\n'
         'OFFICIAL_REPO_URL = "https://github.com/ockentap/iskra-agent.git"',
         name="updater: official repo urls"),

    # --- installer -------------------------------------------------------
    Rule("scripts/install.sh",
         'REPO_URL="${HERMES_REPO_URL:-https://github.com/NousResearch/hermes-agent.git}"',
         'REPO_URL="${HERMES_REPO_URL:-https://github.com/ockentap/iskra-agent.git}"',
         name="installer: repo url"),
    Rule("scripts/install.sh", 'HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"',
         'HERMES_HOME="${HERMES_HOME:-$HOME/.iskra}"',
         name="installer: home dir"),
    Rule("scripts/install.sh", 'INSTALL_DIR="${INSTALL_DIR:-$HERMES_HOME/hermes-agent}"',
         'INSTALL_DIR="${INSTALL_DIR:-$HERMES_HOME/iskra-agent}"',
         name="installer: install dir"),

    # --- container layer -------------------------------------------------
    # The image still names its UNIX user `hermes`; only the *binary* it
    # drops to changes, because the fork installs `iskra` entry points.
    Rule("docker/main-wrapper.sh", '    drop hermes\nfi', '    drop iskra\nfi',
         name="docker: default command"),
    Rule("docker/main-wrapper.sh", 'drop hermes "$@"', 'drop iskra "$@"',
         name="docker: passthrough command"),
    Rule("docker/hermes-exec-shim.sh", "REAL=/opt/hermes/.venv/bin/hermes",
         "REAL=/opt/hermes/.venv/bin/iskra",
         name="docker: exec shim binary"),

    # --- tests -----------------------------------------------------------
    Rule("tests/test_hermes_constants.py", '"""When HERMES_HOME is not set, returns ~/.hermes."""',
         '"""When HERMES_HOME is not set, returns ~/.iskra."""',
         name="tests: constants docstring"),
    Rule("tests/test_hermes_constants.py",
         'assert get_default_hermes_root() == tmp_path / ".hermes"',
         'assert get_default_hermes_root() == tmp_path / ".iskra"',
         name="tests: posix default root"),
    Rule("tests/test_hermes_constants.py",
         '"""Native Windows falls back to %LOCALAPPDATA%\\\\hermes, not ~/.hermes."""',
         '"""Native Windows falls back to %LOCALAPPDATA%\\\\iskra, not ~/.iskra."""',
         name="tests: windows docstring"),
    Rule("tests/test_hermes_constants.py",
         'assert get_default_hermes_root() == local_appdata / "hermes"',
         'assert get_default_hermes_root() == local_appdata / "iskra"',
         name="tests: windows default root"),
    Rule("tests/agent/test_legacy_cli.py", '"usage: hermes-agent"', '"usage: iskra-agent"',
         name="tests: legacy cli usage"),
    Rule("tests/agent/test_legacy_cli.py", '"Hermes Agent v"', '"Iskra v"',
         name="tests: legacy cli version"),
    Rule("tests/agent/test_legacy_cli.py", '"hermes-agent"', '"iskra-agent"', count=0,
         name="tests: legacy cli script name"),
]

REGEX_RULES: list[RegexRule] = [
    RegexRule("hermes_cli/**/*.py", r'prog="hermes(?=[ "]?)', 'prog="iskra',
              name="cli: argparse prog names"),
    # Command strings that are not wrapped in backticks, e.g. f"hermes -p {p} auth add …".
    # A quote, the bare name and a space: module names contain an underscore and
    # never match, and prose keeps reading naturally after the rename.
    RegexRule("agent/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: agent bare commands"),
    RegexRule("hermes_cli/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: cli bare commands"),
    RegexRule("gateway/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: gateway bare commands"),
    RegexRule("tools/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: tools bare commands"),
    RegexRule("cron/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: cron bare commands"),
    RegexRule("tui_gateway/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: tui bare commands"),
    RegexRule("acp_adapter/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: acp bare commands"),
    RegexRule("plugins/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="copy: plugin bare commands"),
    RegexRule("tests/**/*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="tests: bare commands"),
    # Root-level modules (hermes_state_*.py, run_agent.py, …) carry copy too.
    RegexRule("*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="root: command hints"),
    RegexRule("*.py", r"""(["'])hermes(?=\s)""", r"\1iskra",
              name="root: bare commands"),
    # Copy that tells the user which command to run. Only backticked command
    # forms are touched: `hermes <sub>`, `hermes`, `hermes-agent`. Module
    # references such as `hermes_cli` keep their underscore and never match.
    RegexRule("agent/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: agent command hints"),
    RegexRule("hermes_cli/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: cli command hints"),
    RegexRule("gateway/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: gateway command hints"),
    RegexRule("tools/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: tools command hints"),
    RegexRule("cron/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: cron command hints"),
    RegexRule("tui_gateway/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: tui command hints"),
    RegexRule("acp_adapter/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: acp command hints"),
    RegexRule("plugins/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="copy: plugin command hints"),
    # Tests assert on the copy the code emits, so they follow the same rename.
    RegexRule("tests/**/*.py", r"`hermes(?=[ `\-])", "`iskra",
              name="tests: command hints"),
    # Localised copy: user-visible strings live in YAML values, never in keys.
    # Only the product name, backticked commands and the data-directory path
    # are rewritten; `hermes_cli/...` module references and YAML keys keep
    # their names because code looks them up verbatim.
    RegexRule("locales/*.yaml", r"`hermes(?=[ `{])", "`iskra",
              name="locales: command hints"),
    RegexRule("locales/*.yaml", r"/\.hermes/", "/.iskra/",
              name="locales: data dir paths"),
    RegexRule("locales/*.yaml", r"\.hermes/", ".iskra/",
              name="locales: relative data dir paths"),
    RegexRule("locales/*.yaml", r"\bhermes(?=\s)", "iskra",
              name="locales: bare commands"),
    RegexRule("locales/*.yaml", r"\bHermes\b", "Iskra",
              name="locales: product name"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _rebrand_status_header(text: str) -> tuple[str, str]:
    """Centre '☤ Iskra Status' in the /status box, preserving its width."""
    lines = text.split("\n")
    border_inner = 0
    for line in lines:
        if "┌" in line and "┐" in line:
            border = line[line.index("┌"):line.rindex("┐") + 1]
            border_inner = len(border) - 2
            break
    out, changed, seen_iskra = [], False, False
    for line in lines:
        if "Hermes Agent Status" in line and "│" in line:
            start, end = line.index("│"), line.rindex("│")
            segment = line[start:end + 1]
            inner = border_inner or len(segment) - 2
            label = "☤ Iskra Status"
            left = (inner - len(label)) // 2
            rebuilt = "│" + " " * left + label + " " * (inner - len(label) - left) + "│"
            line = line[:start] + rebuilt + line[end + 1:]
            changed = True
        elif "Iskra Status" in line:
            seen_iskra = True
        out.append(line)
    if changed:
        return "\n".join(out), APPLIED
    return text, (OK if seen_iskra else DRIFT)


def _ensure_launcher(report: list[tuple[str, str, str]]) -> None:
    launcher, source = ROOT / "iskra", ROOT / "hermes"
    if launcher.exists():
        report.append((OK, "launcher: iskra", ""))
        return
    if not source.exists():
        report.append((DRIFT, "launcher: iskra", "neither iskra nor hermes launcher present"))
        return
    body = _read(source).replace("Hermes Agent CLI launcher", "Iskra CLI launcher")
    body = body.replace("the installed `hermes` command", "the installed `iskra` command")
    _write(launcher, body)
    launcher.chmod(0o755)
    report.append((APPLIED, "launcher: iskra", ""))


def run(apply: bool) -> int:
    report: list[tuple[str, str, str]] = []

    for rule in LITERAL_RULES:
        path = ROOT / rule.path
        if not path.exists():
            report.append((DRIFT, rule.label(), f"missing file {rule.path}"))
            continue
        text = _read(path)
        has_old = rule.old in text
        has_new = rule.new in text
        if has_old:
            if apply:
                new_text = text.replace(rule.old, rule.new)
                _write(path, new_text)
                report.append((APPLIED, rule.label(), ""))
            else:
                report.append((APPLIED, rule.label(), "would rewrite"))
        elif has_new:
            report.append((OK, rule.label(), ""))
        else:
            report.append((DRIFT, rule.label(), "neither upstream nor rebranded text found"))

    for rule in REGEX_RULES:
        pattern = re.compile(rule.pattern)
        files = sorted(ROOT.glob(rule.glob))
        hits = 0
        for path in files:
            text = _read(path)
            new_text, n = pattern.subn(rule.replacement, text)
            if n:
                hits += n
                if apply:
                    _write(path, new_text)
        if hits:
            report.append((APPLIED, rule.label(), f"{hits} occurrence(s)"))
        else:
            # Backreferences in the replacement are not literal text; probe the
            # literal part so an already-renamed tree reports OK, not drift.
            probe = re.sub(r"\\[1-9]", "", rule.replacement)
            if probe and any(probe in _read(p) for p in files):
                report.append((OK, rule.label(), ""))
            else:
                report.append((DRIFT, rule.label(), "no upstream text found"))

    status_path = ROOT / "hermes_cli/status.py"
    if status_path.exists():
        text = _read(status_path)
        new_text, verdict = _rebrand_status_header(text)
        if verdict == APPLIED and apply:
            _write(status_path, new_text)
        report.append((verdict, "status: box header", ""))
    else:
        report.append((DRIFT, "status: box header", "missing file"))

    _ensure_launcher(report)

    width = max(len(label) for _, label, _ in report) + 2
    for verdict, label, detail in report:
        print(f"{verdict.upper():8} {label:<{width}} {detail}".rstrip())

    applied = sum(1 for v, _, _ in report if v == APPLIED)
    drift = [label for v, label, _ in report if v == DRIFT]
    print()
    print(f"{applied} rule(s) {'applied' if apply else 'need applying'}, "
          f"{len(report) - applied - len(drift)} already correct, {len(drift)} drift")
    if drift:
        print("\nDRIFT — upstream changed these; rebrand by hand:")
        for label in drift:
            print(f"  - {label}")
        return 1
    if not apply and applied:
        print("\nRe-run with --apply to rewrite them.")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Reapply the Iskra rebrand.")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="report only (default)")
    group.add_argument("--apply", action="store_true", help="rewrite what needs rewriting")
    args = ap.parse_args(argv)
    return run(apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
