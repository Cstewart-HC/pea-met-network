# Autonomous Loop Guardrails

## Goal
Define safe, high-autonomy operating rules for the Ralph-style build loop.

## Single Source of Truth: ralph-state.json

All task state lives in `docs/ralph-state.json`. This is machine-readable.
No markdown parsing. No diary reads for state.

The JSON contains:
- `phase` / `phase_name` — derived from git by sync_state.py
- `tasks[]` — ordered list with `id`, `description`, `gate`, `depends`, `status`
- `status` — "running" or "paused"
- `blocker` — null or description
- `date` / `max_per_day` / `iteration` — loop cadence control

`IMPLEMENTATION_PLAN.md` is a human-readable mirror. The loop does NOT
read it for state. It may read it for context, but all authoritative
task/gate info comes from the JSON.

## Loop Startup Procedure (every iteration)

1. **Run `python scripts/sync_state.py`**
   This derives phase from git, reads gates from JSON, checks the next
   task's gate. Read its stdout to determine everything.
   Do NOT trust any cached state — sync_state.py IS the source of truth.

2. **Read `IMPLEMENTATION_PLAN.md`** (optional, for context only)
   Get background on the current task if needed. Do NOT parse it for
   task state or gate commands.

3. **Check the gate of the current task BEFORE starting work**
   sync_state.py already ran it. If `GATE_STATUS=ALREADY_PASSES`,
   mark the task done in ralph-state.json, commit, advance.

4. **Read relevant spec files** if the task references one.

## Loop Unit
Each loop must work on one small, concrete unit of progress only.

## Verification Gates (anti-pattern: self-referential trust)

Every task has a `gate` field in ralph-state.json — a shell command
that must exit 0 for the task to be considered done.

The loop may mark a task done ONLY if:
1. It ran the gate command
2. The gate exited 0

No diary entry, no checkbox, no "the file exists" observation counts
as proof. Run the gate.

### Detecting drift
Run `python scripts/sync_state.py --run-gates` to check ALL gates.
Tasks marked `done` whose gates now fail are reported as DRIFT.
Tasks marked `pending` whose gates already pass are reported as UNMARKED.

## Completion Rule
Each loop must either:
- produce a passing commit (gate + ruff + pytest), or
- stop and report a validated blocker

## Self-Heal Budget
Per loop:
- up to 3 repair attempts for the same failing step
- up to 2 strategy pivots when the first approach is wrong

## Validation Backpressure
Before commit, the loop must run:
- `ruff check .` — must pass
- `pytest` — must pass
- the current task's gate — must pass

## Code Quality Rules
- style target line length: 50
- hard line length enforced by tooling: 80
- target McCabe complexity: less than 10
- hard McCabe limit: 15
- public functions require type hints

## Diary Requirement
Append-only audit log under `docs/diary/`. The loop never reads it
for state — it is an audit log, not a decision source.

## Standup Rhythm
Standup-style check-ins should surface:
- what changed
- what passed or failed
- current milestone
- blockers or decisions needed
