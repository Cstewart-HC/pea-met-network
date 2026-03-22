#!/bin/bash
# Post-commit hook: sync ralph-state.json to latest commit hash
# Uses a flag file to prevent infinite recursion (amend triggers post-commit again)

cd /mnt/fast_data/workspaces/pea-met-network
FLAG="/tmp/.ralph-post-commit-lock"

if [ -f "$FLAG" ]; then
    rm -f "$FLAG"
    exit 0
fi

touch "$FLAG"
python scripts/sync_state.py --write 2>/dev/null
git add docs/ralph-state.json
git commit --amend --no-edit --no-verify 2>/dev/null
rm -f "$FLAG"
