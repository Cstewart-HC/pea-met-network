#!/usr/bin/env python3
import json, subprocess, os

os.chdir('/mnt/fast_data/workspaces/pea-met-network')

# validation.json
v = json.load(open('docs/validation.json'))
print(f"LAST_REVIEWED: {v.get('last_reviewed_commit', 'NONE')}")
print(f"VERDICT: {v.get('verdict', 'NONE')}")

# ralph-state.json
s = json.load(open('docs/ralph-state.json'))
cb = s.get('circuit_breaker', {})
print(f"CIRCUIT_BREAKER: tripped={cb.get('tripped', False)} reason={cb.get('trip_reason', 'none')}")
print(f"PHASE: {s.get('phase')} STATUS: {s.get('status')}")

# git log since last reviewed
lr = v.get('last_reviewed_commit', 'NONE')
if lr == 'NONE':
    print("GIT_LOG_SRC_TESTS: (no last_reviewed_commit)")
else:
    r = subprocess.run(['git', 'log', '--oneline', f'{lr}..HEAD', '--', 'src/', 'tests/'],
                       capture_output=True, text=True)
    print(f"GIT_LOG_SRC_TESTS:\n{r.stdout if r.stdout.strip() else '(no commits touching src/ or tests/)'}")
    r2 = subprocess.run(['git', 'log', '--oneline', f'{lr}..HEAD'],
                        capture_output=True, text=True)
    print(f"GIT_LOG_ALL:\n{r2.stdout if r2.stdout.strip() else '(no new commits)'}")
