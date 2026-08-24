# Decision queue — everything that needs the owner, in one place

Statuses: `🔴 OPEN` · `🟡 PROVISIONAL (machine) <date> — pending acceptance` ·
`✅ DECIDED <date>`. Rows are NEVER deleted. Deadlines are real dates
(YYYY-MM-DD) — a deadline written as words is invisible to every reminder
machine (schedule_check warns on them).

## 1. Open questions

| # | Question (searched-where · two-sided proposal · reversal cost) | Blocks | Status | Due |
|---|---|---|---|---|
| D1 | Keep the stored .checkpoint file (PR #35) or rework resume as a derived reader? Stored = convenient but a second source of truth no gate keeps honest (ops-247 §1); reader = derives from claim/branch/evidence/ledger, cannot lie. Reversal cost of reader: none (it stores nothing). | PR #36 | ✅ DECIDED 2026-08-24 — reader; checkpoint store deleted, doctrine amended per supersession law | 2026-08-24 |
| D3 | Owner escalation: the 2026-08-24 review + rework rounds (PR #36, #37, self-install) ran on `frontier` at the owner's direct instruction ("tiến hành hoàn thiện") — recorded here so perf_report's frontier flag has its approval trail. | — | ✅ DECIDED 2026-08-24 — approved by owner | 2026-08-24 |
| D2 | Should the vteam repo adopt vteam itself? Cost: rendered docs + gate CI in-repo; benefit: self-audit 62/C → 91/A, every release now ledgered and evidenced. Reversal: delete config + .vteam + docs/team (uninstall path documented in Known limits). | VT-1 | ✅ DECIDED 2026-08-24 — adopted; minimal own fence kept (stated in evd/VT-1/manifest.md) | 2026-08-24 |

## 2. Owner-only actions

| # | Action | Why machine-exempt | Status | Due |
|---|---|---|---|---|

## 3. ADRs pending

| ADR | Decision | Status |
|---|---|---|
