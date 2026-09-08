# VT-6: Peer coordination — /team DEV agents talk directly, decisions become artifacts

- status: In Progress
- assignee: Connor Pham
- estimate: 1d
- labels: workflow, no UI

## Why

`parallel_check` (VT-5) stops FILE conflicts (disjoint CODE-SCOPE) but not
FUNCTIONAL ones: agent A defines a type/API/DB field that agent B consumes from
a different file — two files, one hidden contract, and B breaks when A's shape
moves. The owner's call (2026-09-08): let parallel DEV agents **talk directly**
to split/hand off work so division is accurate. Direct peer chat is enabled;
this ticket adds the guardrails that keep it honest — because a chat agreement
that never becomes an artifact is the exact ephemeral, unauditable failure vteam
exists to prevent.

## Spec / oracle

Governing rule: spec §`team.md` "Token discipline" (the "agents do NOT chat"
line is amended, NOT for reviewers) and §`pm.md` principle #5 (single-writer
ledger) + #3 (disjoint scope). `review-standard.md` §1 (reviewer isolation) is
preserved untouched. The coordination log is a committed artifact like the
ledger (`ops-247.md` §7 append-only discipline).

## Acceptance criteria (testable)

0. **Given** a coordination log with a handoff row (from-ticket gives a path to
   to-ticket) whose CODE-SCOPEs do NOT reflect it (giver still owns the path, or
   receiver doesn't), **When** `coord_check.py` runs, **Then** it exits 1 — a
   chat agreement that did not become real scope is red; **and Given** the
   scopes match the handoff, **Then** it exits 0.
1. New gate `coord_check.py` — inert-green when `team.parallel <= 1` or no
   coordination log exists; when present it reds a malformed row, a round past
   `team.coord_budget`, and a handoff not reflected in the tasksheets' scopes.
   `--selftest` proves each rule can red. Wired into every profile + doctor.
2. `team.md` peer-coordination rules: parallel DEV agents MAY message each other
   (SendMessage) to negotiate scope + hand off contracts; every scope/contract
   DECISION is appended to `{paths.pm}/coordination.md` (a committed artifact);
   rounds bounded by `team.coord_budget`; **reviewers stay fresh/isolated** (the
   channel is DEV-coordination only); the ledger stays the PM's single hand.
2b. `pm.md` P1/dispatch notes the coordinator hands each parallel DEV agent the
   others' agent handles + the coordination-log path, and re-runs
   `parallel_check` + `coord_check` after any handoff.
3. Config knob `team.coord_budget` (default 3) in config + init + example +
   DESIGN §2; conformance/e2e green; no unresolved `{vars}`.
4. `gate.sh` GREEN incl. the new gate; a real smoke test where two spawned
   agents message each other to resolve a would-be conflict, recorded in evidence.

## Out of scope

- Changing review isolation (reviewers never chat — unchanged).
- A chat UI/transport — the platform's SendMessage/agent channel is the transport.
- Auto-merge policy, review_check/evd_check thresholds.

## Comments

### 2026-09-08 Connor Pham
claimed 2026-09-08T14:00:00Z · branch feat/VT-6-agent-coordination
