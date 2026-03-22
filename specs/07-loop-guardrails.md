# Autonomous Loop Guardrails

## Goal
Define safe, high-autonomy operating rules for the Ralph-style build loop.

## Loop Unit
Each loop must work on one small, concrete unit of progress only.
Examples:
- add inventory manifest generation
- implement UTC normalization helper
- add hourly resampling test
- implement FFMC calculation wrapper

Non-examples:
- finish the pipeline
- build all FWI logic
- do all redundancy analysis

## Required Loop Inputs
Every loop must consult at minimum:
- relevant spec files
- `docs/working-agreement.md`
- `docs/phases.md`
- `IMPLEMENTATION_PLAN.md`

## Completion Rule
Each loop must either:
- produce a passing commit, or
- stop and report a validated blocker

## Self-Heal Budget
A blocker must not be reported on first friction.
Per loop, allow bounded self-healing before escalation:
- up to 3 repair attempts for the same failing step
- up to 2 strategy pivots when the first approach is wrong

## Transient Issues
Treat these as retryable unless they persist beyond the self-heal budget:
- exec hiccups
- path mistakes
- parser edge cases
- temporary rate limits
- lint or formatting failures
- dependency/import mistakes
- local test failures caused by the latest edit

## Real Blockers
Escalate only after retries when issues such as these remain:
- required data is missing or corrupted
- assignment ambiguity blocks correct implementation
- authentication or credentials are required
- repeated failures suggest a spec contradiction
- repository state appears unsafe or inconsistent

## Validation Backpressure
Before commit, the loop must run relevant validation:
- Ruff must pass
- relevant tests must pass
- outputs must be coherent for the scope changed

## Code Quality Rules
- style target line length: 50
- hard line length enforced by tooling: 80
- target McCabe complexity: less than 10
- hard McCabe limit: 15
- public functions require type hints
- important logic must not live only in notebook cells

## Plan Hygiene
The loop must keep `IMPLEMENTATION_PLAN.md` current.
Completed tasks should be marked clearly.
Future tasks may be refined but should not churn without reason.

## Diary Requirement
At the end of each successful loop, append a short diary entry under
`docs/diary/` using Option C style:
- factual summary of work completed
- brief reflective note or uncertainty

## Standup Rhythm
The system is high-autonomy, not fully unsupervised.
Standup-style check-ins should surface:
- what changed
- what passed or failed
- current milestone
- blockers or decisions needed

## Repository topology guardrail

The repository root must remain clean and predictable.

Allowed root files:
- `README.md`
- `pyproject.toml`
- `requirements.txt`
- `.gitignore`
- `IMPLEMENTATION_PLAN.md`
- `cleaning.py` (only if required for assignment-facing execution)

Allowed root directories:
- `src/`
- `tests/`
- `docs/`
- `data/`
- `notebooks/`
- `specs/`

All other files or directories at repo root are violations unless the
working agreement and tests are updated first in the same change.

Validation requirement:
- the repository shape test must pass before commit
