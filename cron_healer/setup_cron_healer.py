#!/usr/bin/env python3
"""Install the cron self-healer: copy scripts into <home>/scripts/ and create the monitor-gated
healer cron job. Idempotent — re-running updates the existing healer job instead of duplicating.

Usage:
  python3 setup_cron_healer.py [--deliver telegram] [--interval 5m] [--max-attempts 2] [--cooldown 30]

The healer is an agent cron job whose monitor_script lists heal-eligible failure incidents; the
agent only wakes when a NEW un-healed failure appears (idle ticks cost nothing). It auto-fixes
job-level faults, re-runs to verify, and escalates box-level faults to --deliver.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deliver", default="telegram", help="where heal reports go (platform / platform:chat_id / all)")
    ap.add_argument("--interval", default="5m", help="monitor poll interval (agent only wakes on new failures)")
    ap.add_argument("--max-attempts", type=int, default=2)
    ap.add_argument("--cooldown", type=int, default=30, help="minutes between attempts on one incident")
    args = ap.parse_args()

    from hermes_constants import get_hermes_home
    home = Path(get_hermes_home())
    scripts = home / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ("heal_state.py", "heal_monitor.py"):
        shutil.copyfile(HERE / name, scripts / name)
    print(f"installed scripts -> {scripts}")

    playbook = (HERE / "HEALER_PLAYBOOK.md").read_text()
    prompt = (
        playbook.replace("<scripts_dir>", str(scripts))
        + f"\n\nHealer state CLI: {scripts}/heal_state.py\n"
        + f"Profile python: {sys.executable}\n"
    )

    from cron.jobs import create_job, load_jobs, update_job
    existing = next((j for j in load_jobs() if j.get("name") == "cron-healer"), None)
    schedule = f"every {args.interval}" if not args.interval.startswith("every") else args.interval
    if existing:
        update_job(existing["id"], {"prompt": prompt, "schedule": schedule,
                                    "monitor_script": "heal_monitor.py", "deliver": args.deliver})
        job_id = existing["id"]
        print(f"updated existing healer job {job_id}")
    else:
        job = create_job(
            prompt=prompt, schedule=schedule, name="cron-healer",
            monitor_script="heal_monitor.py", deliver=args.deliver,
            enabled_toolsets=["terminal", "file"],
        )
        job_id = job["id"]
        print(f"created healer job {job_id}")

    sys.path.insert(0, str(scripts))
    import heal_state
    heal_state.configure(job_id, max_attempts=args.max_attempts, cooldown_minutes=args.cooldown)
    print(f"configured healer state (self-exclusion={job_id}, max_attempts={args.max_attempts}, cooldown={args.cooldown}m)")
    print("Done. The healer wakes only when a new un-healed cron failure appears.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())