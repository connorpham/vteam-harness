# VT-6 — coord_check probes (real runs, 2026-09-08)
```console
# A: handoff REFLECTED in scopes (DEMO-1 released order.ts, DEMO-2 owns it) → green
✅ coord_check: 1 peer handoff(s) all reflected in CODE-SCOPE, rounds ≤ 3
exit=0

# B: chat agreed the handoff but DEMO-1 NEVER RELEASED it (still in its scope) → red
❌ coord_check: 1 coordination problems in docs/pm/coordination.md
   - handoff DEMO-1→DEMO-2 of src/lib/order.ts not reflected: DEMO-1 STILL owns it — the giver never let go
exit=1

# C: round past team.coord_budget=3 → red
❌ coord_check: 1 coordination problems in docs/pm/coordination.md
   - round 9 > team.coord_budget 3 — bounded coordination, not endless chat (DEMO-1→DEMO-2 src/lib/order.ts)
exit=1
```
