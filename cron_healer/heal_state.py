"""Cron self-healer: attempt tracking + eligibility over the cron incident ledger.

Additive self-healing for Hermes/Iskra cron. A monitor-gated healer job wakes only when a
new, un-healed failure incident appears; the healing agent triages it, auto-fixes job-level
faults, re-runs to verify, and escalates box-level faults. This module is the deterministic
bookkeeping: which incidents are eligible, how many attempts each has had, and cooldowns so
the healer never loops or burns tokens on the same failure every tick.

State lives at <hermes_home>/cron_healer_state.json. The healer's own job id is stored here
at setup so it never tries to heal itself.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

MAX_ATTEMPTS = 2          # bounded heal attempts per incident signature
COOLDOWN_MINUTES = 30     # min gap between attempts on the same incident
OPEN_STATES = ("detected", "alerted")


def _home() -> Path:
    try:
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home())
    except Exception:
        return Path.home() / ".hermes"


def state_path() -> Path:
    return _home() / "cron_healer_state.json"


def load_state() -> dict:
    p = state_path()
    if p.exists():
        try:
            d = json.loads(p.read_text())
            if isinstance(d, dict):
                d.setdefault("config", {})
                d.setdefault("incidents", {})
                return d
        except Exception:
            pass
    return {"config": {}, "incidents": {}}


def save_state(d: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def configure(healer_job_id: str, max_attempts: int = MAX_ATTEMPTS,
              cooldown_minutes: int = COOLDOWN_MINUTES) -> None:
    d = load_state()
    d["config"] = {"healer_job_id": healer_job_id, "max_attempts": max_attempts,
                   "cooldown_minutes": cooldown_minutes}
    save_state(d)


def _now() -> float:
    return time.time()


def _parse_iso(s):
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(s)).timestamp()
    except Exception:
        return 0.0


def eligible_incidents() -> list[dict]:
    """Open incidents the healer should act on now: not itself, under max attempts, not
    escalated, and past the per-incident cooldown. Returns incident dicts (newest first)."""
    from cron.incidents import list_incidents
    d = load_state()
    cfg = d.get("config", {})
    healer_id = cfg.get("healer_job_id")
    max_attempts = int(cfg.get("max_attempts", MAX_ATTEMPTS))
    cooldown = float(cfg.get("cooldown_minutes", COOLDOWN_MINUTES)) * 60
    rec = d.get("incidents", {})
    out = []
    for inc in list_incidents():
        if inc.get("state") not in OPEN_STATES:
            continue
        if healer_id and inc.get("job_id") == healer_id:
            continue  # never heal the healer
        r = rec.get(inc["id"], {})
        if r.get("escalated"):
            continue
        if int(r.get("attempts", 0)) >= max_attempts:
            continue
        last = _parse_iso(r.get("last_attempt_at")) if r.get("last_attempt_at") else 0.0
        if last and (_now() - last) < cooldown:
            continue
        out.append(inc)
    return out


def record_attempt(incident_id: str, outcome: str = "") -> dict:
    d = load_state()
    r = d["incidents"].setdefault(incident_id, {"attempts": 0})
    r["attempts"] = int(r.get("attempts", 0)) + 1
    r["last_attempt_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z") or time.strftime("%Y-%m-%dT%H:%M:%S")
    r["outcome"] = outcome[:300]
    save_state(d)
    return r


def mark_escalated(incident_id: str, reason: str = "") -> dict:
    d = load_state()
    r = d["incidents"].setdefault(incident_id, {"attempts": 0})
    r["escalated"] = True
    r["escalation_reason"] = reason[:300]
    save_state(d)
    return r


def reset_incident(incident_id: str) -> None:
    """Clear tracking when an incident resolves (so a future recurrence starts fresh)."""
    d = load_state()
    if incident_id in d.get("incidents", {}):
        del d["incidents"][incident_id]
        save_state(d)


def _cli(argv) -> int:
    """Agent-facing CLI: list | attempt <id> [outcome] | escalate <id> [reason] | show <id>."""
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        for inc in eligible_incidents():
            print(f"{inc['id']}  job={inc.get('job_id')}  type={inc.get('failure_type')}  "
                  f"err={str(inc.get('error'))[:90]}")
        return 0
    if cmd in ("attempt", "escalate") and len(argv) >= 2:
        iid = argv[1]
        note = " ".join(argv[2:])
        if cmd == "attempt":
            r = record_attempt(iid, note)
            print(f"recorded attempt {r['attempts']} for {iid}")
        else:
            mark_escalated(iid, note)
            print(f"escalated {iid}")
        return 0
    if cmd == "show" and len(argv) >= 2:
        from cron.incidents import get_incident
        inc = get_incident(argv[1])
        print(json.dumps(inc, indent=2, ensure_ascii=False) if inc else f"no incident {argv[1]}")
        return 0
    print("usage: heal_state.py [list | attempt <id> [outcome] | escalate <id> [reason] | show <id>]")
    return 2


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv[1:]))