# VT-7 — verification (branch feat/VT-7-orca-transport, 2026-09-08)

```console
# transport helper — REAL runs against the live Orca runtime (v1.4.196)
$ bash .vteam/scripts/orca_team.sh status
✅ Orca transport reachable via 'orca' — parallel DEV agents coordinate on the Run mailbox.

$ bash .vteam/scripts/orca_team.sh open-run "VT-7 transport self-test"
RUN=run_f2216d7b3740
COORD=docs/pm/coordination.md
→ dispatch each DEV agent bound to this Run (see docs/team/parallel-transport.md) …

# degrade path (documented): with Orca absent, `status` prints the text-relay
# fallback and exits 0 — never a crash (fallback() branch, verified by reading).

$ node bin/vteam.mjs update            # syncs orca_team.sh → .vteam/scripts, doctrine → docs/team
$ bash .vteam/scripts/orca_team.sh status   → still reachable from the runtime copy
$ grep -l '{(paths|…)\.[a-z_]*}' .claude/skills/*/SKILL.md → none
$ python3 .vteam/scripts/dor_check.py VT-7 / log_check.py → ✅ / ✅
$ bash .vteam/scripts/gate.sh          → GREEN (no new gate; coord/parallel inert at parallel=1); e2e GREEN
```

Bus itself proven in VT-6 (run/task/send/check/ack round-trip). This ticket adds
the helper + doctrine + workflow wiring so /team's parallel mode uses it.
