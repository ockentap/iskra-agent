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
]

REGEX_RULES: list[RegexRule] = [
    RegexRule("hermes_cli/**/*.py", r'prog="hermes(?=[ "]?)', 'prog="iskra',
              name="cli: argparse prog names"),
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
        elif any('prog="iskra' in _read(p) for p in files):
            report.append((OK, rule.label(), ""))
        else:
            report.append((DRIFT, rule.label(), "no prog= found"))

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
