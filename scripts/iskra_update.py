#!/usr/bin/env python3
"""Pull upstream Hermes into the Iskra fork and reapply the rebrand.

    python scripts/iskra_update.py            # fetch + merge + rebrand + commit
    python scripts/iskra_update.py --dry-run  # fetch and report only

Conflict policy: the only files this fork ever edits are the ones listed in
``iskra_rebrand``.  If the merge conflicts in those files, upstream wins and
the rebrand script rewrites our side afterwards — that is the whole point of
keeping the rename rule-driven.  Conflicts anywhere else abort the merge and
are left for a human.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from iskra_rebrand import LITERAL_RULES, run as rebrand_run

# Files the rebrand owns; upstream wins on these during a merge.
REBRAND_PATHS: set[str] = {rule.path for rule in LITERAL_RULES} | {
    "hermes_cli/status.py",   # box header is rewritten by a custom handler
    "iskra",                  # launcher
}

# Trees the rebrand rewrites in place (command hints). Every local edit under
# these is rule-driven, so taking upstream's side and re-running the script
# reconstructs the fork exactly. Nothing hand-written lives there.
REBRAND_DIRS: tuple[str, ...] = (
    "agent", "hermes_cli", "gateway", "tools", "cron",
    "tui_gateway", "acp_adapter", "plugins",
)


def rebrand_owned(path: str) -> bool:
    return path in REBRAND_PATHS or path.split("/", 1)[0] in REBRAND_DIRS


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True, capture_output=True, check=check,
    )


def out(*args: str) -> str:
    return git(*args).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Update Iskra from upstream Hermes.")
    ap.add_argument("--remote", default="upstream")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    dirty = [p for p in out("status", "--porcelain").splitlines() if not p.startswith("??")]
    if dirty:
        print("Working tree is dirty; commit or stash first:", file=sys.stderr)
        for line in dirty:
            print("  " + line, file=sys.stderr)
        return 2

    print(f"fetching {args.remote}/{args.branch} …")
    git("fetch", args.remote, args.branch)
    upstream_ref = f"{args.remote}/{args.branch}"
    target = out("rev-parse", upstream_ref)

    already = git("merge-base", "--is-ancestor", target, "HEAD", check=False).returncode == 0
    if already:
        print("already up to date with upstream.")
        return rebrand_run(apply=False)

    head = out("rev-parse", "--short", "HEAD")
    print(f"merging {args.remote}/{args.branch} ({target[:12]}) into {head} …")
    if args.dry_run:
        count = out("rev-list", "--count", f"HEAD..{upstream_ref}")
        print(f"dry run: {count} commit(s) behind, nothing changed.")
        return 0

    merge = git("merge", "--no-commit", "--no-ff", upstream_ref, check=False)
    if merge.returncode != 0:
        conflicted = out("diff", "--name-only", "--diff-filter=U").split()
        outside = [p for p in conflicted if not rebrand_owned(p)]
        if outside:
            print("conflicts outside the rebrand surface — aborting:", file=sys.stderr)
            for p in outside:
                print("  " + p, file=sys.stderr)
            git("merge", "--abort", check=False)
            return 1
        print(f"resolving {len(conflicted)} rebrand conflict(s) in favour of upstream …")
        for path in conflicted:
            git("checkout", "--theirs", "--", path)
            git("add", "--", path)

    verdict = rebrand_run(apply=True)
    if verdict != 0:
        print("\nRebrand reported drift; merge left staged for review.", file=sys.stderr)
        return verdict

    # `-u` only: a merge stages new upstream files itself, and an untracked
    # stray directory (test HERMES_HOME leftovers) must never ride along.
    git("add", "-u")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("nothing to commit (already up to date after rebrand).")
        return 0

    git("commit", "--no-verify", "-m",
        f"merge {args.remote}/{args.branch} ({target[:12]}) and reapply Iskra rebrand")
    print(f"\nmerged into {out('rev-parse', '--short', 'HEAD')}.")
    print("next: uv lock && uv sync --python 3.14 && .venv/bin/iskra --version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
