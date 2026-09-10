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
| D4 | Field-study breadth: read the core of each domain (766 files) or all 2,622? Core = reviewable in one sitting, risks missing the tail where the rare cases live; all = complete map, large review burden. Reversal: none (reading only). | VT-13 | ✅ DECIDED 2026-09-10 — owner chose all 2,622 | 2026-09-10 |
| D5 | Mobile scope: both natives (android+ios+kotlin+swift-ui, 592 files), cross-platform only (202), or one of each (284)? Both natives = deepest on the platform differences that actually break, skips cross-platform leaks. Reversal: none. | VT-13 | ✅ DECIDED 2026-09-10 — owner chose both natives | 2026-09-10 |
| D6 | Depth strategy: map only, follow the ~24k curated links, or map + small code experiments? Links = slow and network-bound; experiments = catches what I only think I understood. Reversal: none. | VT-13 | ✅ DECIDED 2026-09-10 — owner chose map + code experiments (34/34 JS assertions and all-pairs coverage verified by execution) | 2026-09-10 |
| D7 | "Upgrade the project" = vteam (install the new competencies) or upstream developer-roadmap (file issues for the curriculum gaps) or both? Reversal for vteam: revert the PR. | VT-13 | ✅ DECIDED 2026-09-10 — owner chose vteam | 2026-09-10 |
| D8 | `qa-accessibility-verification`: `always` or conditionally routed? `always` guarantees a11y is never skipped but adds ~1,100 words to every QA session on a lane already at 6,367; routed costs nothing on a UI-less ticket but relies on `label:ui`/`term:form` matching. I recommended `always` in the assessment, then reversed after measuring the lane was near saturation and a11y is meaningless without a UI. Reversal cost: one token in frontmatter. | VT-13 | 🟡 PROVISIONAL (machine) 2026-09-10 — pending acceptance: shipped as ROUTED, not always | 2026-09-17 |
| D9 | `qa-user-mindset` moved from `always` to routed on the same reasoning (its description says "any UI verification"). Same reversal cost: one token. | VT-14 | 🟡 PROVISIONAL (machine) 2026-09-10 — pending acceptance | 2026-09-17 |
| D10 | Lane-step vocabulary for `design`, `devops`, `sa`, `specialists`: what are their numbered steps? `/dev` has T0–T6, `/qa` V0–V7, `/ba` B0–B5, `/pm` P0–P4; these four have none, so `loads` has no honest value. `competency_check` does NOT validate the value, so an invented step passes the gate while guaranteeing the file is never loaded — a green that lies. Options: (a) name steps per lane, (b) add a workflow for each first, (c) leave the four roles without competencies. Reversal: cheap either way (frontmatter only). | the next competency ticket | 🔴 OPEN | 2026-09-24 |
| D11 | `.githooks/pre-push` diverges 117 lines from the packaged version; `vteam update` parks `pre-push.new` on every run. Options: (a) keep this repo's own fence and delete the parked file, (b) merge the framework version in. This repo deliberately customises its fence ("the rules this repo ships to others apply to itself"), which argues for (a). Currently held in `git stash@{0}` so the publish gate could pass. Reversal: trivial. | publish hygiene | 🔴 OPEN | 2026-09-17 |

| D12 | **`graph_check`'s ALWAYS_LEGAL covers one doctrine deploy target and not its twin.** The list is `docs/ evd/ .vteam/ .githooks/ .github/ vteam.config.yaml .gitattributes .gitignore`. `docs/` silently includes `docs/team/`, the doctrine mirror `vteam update` generates; `.claude/skills/` is the other mirror of the same generated source and is **not** on the list. So every doctrine ticket trips MAST 2.3 unless it remembers to name `.claude/skills/` in its CODE-SCOPE — which VT-15 did not, and the gate correctly reded it. Options: (A) leave as is — the gate asks for a deliberate widening and that is arguably the point; (B) add `.claude/skills/` to ALWAYS_LEGAL, making the two mirrors symmetric, at the cost that a commit could silently rewrite a deployed skill without scope review; (C) teach graph_check that a path is always-legal when it is a KNOWN GENERATED target declared by the adapter, so the rule follows the generator rather than a hand-kept list. Reversal: A→B is one line; C is real work. Recorded from VT-15, where the gate caught the author. | none — loosening scope enforcement is the owner's call, and (C) changes a gate's contract | 🔴 OPEN | 2026-09-24 |

## 2. Owner-only actions

| # | Action | Why machine-exempt | Status | Due |
|---|---|---|---|---|
| A3 | Publish `vteam-harness@0.18.0` to npm — blocked on 2FA: `npm publish` returned EOTP. Prepublish gate passed all five refusals (clean tree, HEAD==origin/main, version free, tests green, no build artefacts); tarball verified 163 files, 0 credential matches. | npm 2FA is owner-held; an OTP cannot be delegated | 🔴 OPEN — run `npm publish --otp=XXXXXX` | 2026-09-17 |

## 3. ADRs pending

| ADR | Decision | Status |
|---|---|---|
