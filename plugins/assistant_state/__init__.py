"""assistant-state: curated goals/todos/reminders + autonomous update tool.

Prototype for the Iskra proactive-assistant loop. The hard part (per design) is
not injection but the agent reliably reasoning about WHEN to update the list,
WHEN to create a cron reminder, and HOW to deliver it — without being told. The
system-prompt section below carries those triggers; the tool persists updates and
returns the live list so the agent reasons from current state mid-session (the
prompt section itself is frozen at session start as the seed).
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

ENTRY_MAX_CHARS = 140          # per-entry character limit (Lav: don't overdo it)
SECTION_MAX_CHARS = 2200       # total bounded prompt section
KINDS = ("goal", "todo", "reminder")
_BUCKET = {"goal": "goals", "todo": "todos", "reminder": "reminders"}


def _store_path() -> Path:
    try:
        from hermes_constants import get_hermes_home
        home = Path(get_hermes_home())
    except Exception:
        home = Path.home() / ".iskra"
    return home / "assistant_state.json"


def _load() -> dict:
    p = _store_path()
    if p.exists():
        try:
            d = json.loads(p.read_text())
            if isinstance(d, dict):
                for b in _BUCKET.values():
                    d.setdefault(b, [])
                return d
        except Exception:
            pass
    return {"goals": [], "todos": [], "reminders": []}


def _save(d: dict) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def _clip(text: str) -> str:
    text = " ".join(str(text).split())
    return text[:ENTRY_MAX_CHARS]


def _render_list(d: dict) -> str:
    lines = []
    for kind, bucket in _BUCKET.items():
        items = [e for e in d.get(bucket, []) if e.get("status") not in ("done", "removed", "sent")]
        if not items:
            continue
        lines.append(kind.upper() + "S:")
        for e in items[:12]:
            due = f" (due {e['due']})" if e.get("due") else ""
            lines.append(f"  [{e['id']}] {e['text']}{due}")
    return "\n".join(lines) if lines else "(empty)"


INSTRUCTIONS = """You maintain a curated, persistent list of the user's GOALS, TODOS and REMINDERS.
The session-start snapshot is below; the authoritative LIVE state is the most recent assistant_state tool result.

TOOL CHOICE (mandatory): For the user's durable goals/todos/reminders you MUST use the assistant_state tool.
Do NOT use todo_list for these — todo_list is only for ephemeral step-tracking inside a single task.
assistant_state is the cross-session list that persists and is loaded into future sessions.

Update it AUTONOMOUSLY with the assistant_state tool when you detect these signals — do NOT wait to be told:
- GOAL: the user states an objective/intention ("I want to...", "my goal is...", "I'm trying to...") -> add/update a goal.
- TODO: the user commits to a task or a concrete next step emerges ("I need to...", "next I'll...") -> add a todo; mark it done when completed.
- REMINDER: a time-bound item ("remind me...", "by Friday", "don't let me forget...") -> add a reminder; if it has a time/deadline, create a cronjob to deliver it.
- DELIVERY: schedule reminders via the cron tool to the user's active channel at the right time; brief and actionable; never spam.
- HYGIENE: entries <=140 chars; only genuine durable items, not ephemeral chatter; complete/remove stale items; do not over-update.
A new session loads this state but does NOT auto-continue the previous conversation."""


def _section_content(session_info) -> str:
    d = _load()
    body = f"## Assistant state (goals / todos / reminders)\n{_render_list(d)}\n\n{INSTRUCTIONS}"
    return body[:SECTION_MAX_CHARS]


_SCHEMA = {
    "name": "assistant_state",
    "description": (
        "Read or update the user's curated goals/todos/reminders. Call this AUTONOMOUSLY when you "
        "detect a goal, a committed task, or a time-bound reminder (see the Assistant state section "
        "of the system prompt). Returns the live list after the change."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "add", "update", "complete", "remove"],
                        "description": "list=read; add/create; update text/due; complete=mark done; remove=delete"},
            "kind": {"type": "string", "enum": list(KINDS), "description": "goal | todo | reminder"},
            "id": {"type": "string", "description": "entry id (for update/complete/remove)"},
            "text": {"type": "string", "description": f"entry text, <= {ENTRY_MAX_CHARS} chars (add/update)"},
            "due": {"type": "string", "description": "optional ISO date/time for a reminder"},
        },
        "required": ["action"],
    },
}


def _handler(action: str = "list", kind: str = "todo", id: str = "", text: str = "", due: str = "", **_) -> str:
    d = _load()
    action = (action or "list").lower()
    if action == "list":
        return "Current assistant state:\n" + _render_list(d)
    if kind not in KINDS:
        return f"error: kind must be one of {KINDS}"
    bucket = _BUCKET[kind]
    if action == "add":
        if not text.strip():
            return "error: text required for add"
        entry = {"id": uuid.uuid4().hex[:6], "text": _clip(text), "status": "active",
                 "updated": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if due:
            entry["due"] = due
        d[bucket].append(entry)
        _save(d)
        return f"added {kind} [{entry['id']}].\n" + _render_list(d)
    # update / complete / remove need an id
    target = next((e for e in d[bucket] if e.get("id") == id), None)
    if target is None:
        return f"error: no {kind} with id {id!r}\n" + _render_list(d)
    if action == "update":
        if text.strip():
            target["text"] = _clip(text)
        if due:
            target["due"] = due
        target["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    elif action == "complete":
        target["status"] = "done"
    elif action == "remove":
        d[bucket] = [e for e in d[bucket] if e.get("id") != id]
    else:
        return f"error: unknown action {action!r}"
    _save(d)
    return f"{action}d {kind} [{id}].\n" + _render_list(d)


# --- Reliable autonomous update: post-turn extraction hook -------------------
# Prompt-only tool steering proved unreliable (the agent defaults to todo_list).
# Instead, a post_llm_call hook runs a single-purpose extraction (one job, no
# competing tools, constrained JSON) and merges durable items into the store.
# A cheap keyword pre-filter keeps the extra LLM call off turns with no signals.
_ctx = None

_SIGNALS = ("want to", "goal", "need to", "remind", "don't forget", "dont forget",
            "trying to", "plan to", "by friday", "by monday", "by tomorrow", "tomorrow",
            "deadline", "next week", "next i", "i'll ", "i will", "have to", "must ")


def _has_signal(text: str) -> bool:
    t = (text or "").lower()
    return any(s in t for s in _SIGNALS)


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


EXTRACT_INSTRUCTIONS = (
    "Extract DURABLE commitments from this conversation turn. Return ONLY JSON of the shape "
    '{"goals": [..], "todos": [..], "reminders": [{"text": .., "due": ..}]}. '
    "goal = a lasting objective the user wants to achieve. "
    "todo = a concrete task the user committed to do, not yet done. "
    "reminder = a time-bound thing the user wants to be reminded of; set due (ISO date or natural language) if stated, else empty. "
    "Only include items the user actually committed to. IGNORE ephemeral step-by-step task tracking, "
    "questions, hypotheticals, and anything already completed. Each text <= 140 chars. "
    "Use empty arrays when there is nothing durable. No prose, no markdown."
)


def _merge_extracted(parsed) -> int:
    if not isinstance(parsed, dict):
        return 0
    d = _load()
    added = 0
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    for kind, key in (("goal", "goals"), ("todo", "todos"), ("reminder", "reminders")):
        bucket = _BUCKET[kind]
        existing = {_norm(e.get("text", "")) for e in d[bucket]}
        for item in parsed.get(key, []) or []:
            if kind == "reminder" and isinstance(item, dict):
                text, due = item.get("text", ""), item.get("due", "")
            else:
                text, due = str(item), ""
            text = _clip(text)
            if not text or _norm(text) in existing:
                continue
            entry = {"id": uuid.uuid4().hex[:6], "text": text, "status": "active", "updated": now}
            if due:
                entry["due"] = str(due)[:60]
            d[bucket].append(entry)
            existing.add(_norm(text))
            added += 1
    if added:
        _save(d)
    return added


def _post_llm_hook(session_id=None, user_message=None, assistant_response=None, **_kw):
    try:
        if _ctx is None or not _has_signal(user_message or ""):
            return
        excerpt = f"USER: {user_message}\nASSISTANT: {str(assistant_response)[:1500]}"
        result = _ctx.llm.complete_structured(
            instructions=EXTRACT_INSTRUCTIONS,
            input=[{"type": "text", "text": excerpt}],
            json_mode=True, max_tokens=400, timeout=60,
        )
        if result.parsed is not None:
            _merge_extracted(result.parsed)
    except Exception:
        # Fail-open: never break the user's turn because of the state hook.
        pass


def register(ctx) -> None:
    global _ctx
    _ctx = ctx
    ctx.register_tool(
        name="assistant_state", toolset="assistant_state", schema=_SCHEMA,
        handler=_handler, description="Curated goals/todos/reminders; update autonomously.",
        emoji="🗂️",
    )
    ctx.register_system_prompt_section(
        id="assistant-state", content=_section_content,
        position="after_memory", max_chars=SECTION_MAX_CHARS,
    )
    ctx.register_hook("post_llm_call", _post_llm_hook)