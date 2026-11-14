#!/usr/bin/env python3
"""Cron self-healer monitor (cheap, no LLM). Prints the set of heal-eligible incident ids.

Attached as ``monitor_script`` on the healer job: cron hashes this output each tick and only
wakes the healing agent when it CHANGES (a new un-healed failure appeared). Idle ticks cost
nothing. Output is byte-stable: sorted incident ids, one per line, nothing else.

Run standalone to inspect: python3 heal_monitor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# heal_state.py sits next to this file once installed under <home>/scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    try:
        import heal_state
        eligible = heal_state.eligible_incidents()
    except Exception as exc:
        # Fail-open: a monitor error must not wedge the healer; surface it once so the
        # change-detection wakes the agent, which can then report the monitor fault.
        print(f"MONITOR_ERROR {type(exc).__name__}: {exc}")
        return 0
    for inc in sorted(eligible, key=lambda x: x.get("id", "")):
        print(inc["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())