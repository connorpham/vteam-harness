# Review dossier — VT-2: watchable dev & QA sessions

Base: origin/main · scope: the VT-2 commit (feature + rebase-era fixes).
Two independent reviewers (R1 workhorse/opus, R2 standard/sonnet per
model-routing), each ran a REQUEST-CHANGES round and a re-review round after
fixes. High-stakes triggers (review.high_stakes_paths/terms): none configured →
no R3 required.

---

## R1 — Trailing `--wait`/`--url` flag spins app_check.sh into an infinite loop; otherwise solid (model: opus)

VERDICT: REQUEST-CHANGES

Findings:
- CONFIRMED `core/scripts/app_check.sh:102-103` (and identical mirror `core/scripts/app_check.sh:102-103 (installed .vteam copy byte-identical)`): the arg loop does `--wait) WAIT="${2:-0}"; shift 2` / `--url) …; shift 2`. When the flag is the LAST argument, `shift 2` fails (`shift count must be <= $#`), leaves `$#` unchanged, and because the script runs under `set -u` with no `set -e` the failure is swallowed — so `while [ $# -gt 0 ]` never terminates. `bash app_check.sh --wait` hangs forever. The up-front `case "$WAIT" in *[!0-9]*` numeric guard is UNREACHABLE for this input because control never leaves the while loop. Distinct from the non-numeric `--wait` loop fixed pre-review (that fix guards the value, not the missing value). Fix ask: guard `[ $# -ge 2 ]` before consuming `$2`, both copies.
- QUESTION (not blocking): `envBlock()` at `src/cli/adapters.mjs:71` renders the raw `app.start` string into a markdown code-span; a start command containing a backtick would break the span. Config values are author-controlled — cosmetic, noted only.

Tried to break:
- `bash core/scripts/app_check.sh --wait` (flag as last arg): backgrounded, PID still alive after 2s → CONFIRMED infinite loop. Same hang for trailing `--url`.
- `bash core/scripts/app_check.sh --url 'http://127.0.0.1:59999/$(touch /tmp/brk/PWNED)' --wait 0` (shell-injection via URL): output `APP: DOWN http://…` and the marker file was never created — curl receives the URL as one literal arg. Safe.
- `open_files.sh` with a space-containing target ("src/my file" .ts, line 10) against a fake `code` on PATH: editor received `argc=2`, `[-g]`, `[src/my file …line 10]` (one argv entry) — spaces preserved, quoting correct. A filename literally `--dry-run`, an unknown flag (`--bogus` → clean exit 1) and garbage `app.headed` (defaults headed) also held.

Traces:
- `bash core/scripts/app_check.sh --wait` (backgrounded, `kill -0` after 2s) → "CONFIRMED HANG: pid 66231 still running after 2s"; `set -- --wait; shift 2` → `shift: shift count must be <= $#; rc=1; args unchanged`.
- core/scripts/app_check.sh:110 — the flag arms consuming `$2` (pre-fix: unconditional `shift 2`; mirror identical, confirmed via diff).
- `npm test` → `E2E: GREEN — 155/155 checks passed`; all four new selftests green (app_check, open_files, browser launch-SKIPPED without playwright, evd_check 9 mutations red).

---

## R1 — re-review after fix (model: opus)

VERDICT: APPROVE

Findings:
- RESOLVED — core/scripts/app_check.sh:110-113 and core/scripts/app_check.sh:110-113 (installed .vteam copy byte-identical): each flag now guards `[ $# -ge 2 ] || { echo "app_check: --<flag> needs a value"; exit 1; }` before `shift 2`. `bash app_check.sh --wait` no longer hangs — exits 1 immediately. The infinite-loop path is closed for both `--wait` and `--url` in both mirrored copies. A regression case was added to both selftests (lines 91-97) and both pass.

Tried to break:
- `--wait --url` (flag used as another flag's value): exit 1, `--wait takes a whole number of seconds (got '--url')` — guard accepts `--url` as a present value, numeric validator rejects it. Correct, no hang.
- `--wait ""` (empty-string value): exit 1 via the `''|*[!0-9]*` numeric check. Correct.
- `--url http://x --wait` (trailing flag AFTER a valid pair): exit 1, `--wait needs a value` — the guard fires mid-loop, not just on the first arg.
- `--wait 0` (valid usage regression): exit 0, `APP: SKIP — app.url not set …` — legitimate path unchanged.

Traces:
- `bash core/scripts/app_check.sh --wait` (watchdog-wrapped, 8s kill) → `app_check: --wait needs a value` / exit=1; same for `--url` and both `.vteam` copies — none hung.
- core/scripts/app_check.sh:110-113 — the two guarded flag arms with `[ $# -ge 2 ]` before `shift 2`.
- core/scripts/app_check.sh:93-97 — the regression case asserting `bash "$0" --wait` exits non-zero and names the reason (mirrored in the .vteam copy).
- `npm test` → `E2E: GREEN — 155/155 checks passed`.

---

## R2 — installed scripts diverge from core: two bugs survive in .vteam/scripts, manifest hash stale (model: sonnet)

VERDICT: REQUEST-CHANGES

Findings:
- BUG (shipped, runnable) `.vteam/scripts/app_check.sh` missing the numeric-`--wait` guard present in `core/scripts/app_check.sh:117-119`. `bash .vteam/scripts/app_check.sh --url http://localhost:3000 --wait abc` enters an infinite probe loop printing `[: abc: integer expression expected` each iteration. The fix landed in core but was not re-rendered into the installed copy. Fix: re-render from core + update the manifest hash.
- BUG (shipped, runnable) `core/scripts/open_files.sh:22-23 (installed .vteam copy byte-identical)` uses the pre-fix `command -v cursor >/dev/null && echo cursor` form: forced mode with the CLI absent exits 1, breaking the "never blocks the pipeline" contract; `core/scripts/open_files.sh:23-25` has the correct `if …; then …; fi` form. The installed selftest also omits the forced-mode/missing-CLI mutation. Fix: same re-render.
- MANIFEST HASH STALE — `.vteam/manifest.json` hashes for the new scripts match neither installed nor core; `vteam update` would park them as `.new` unnecessarily. Fix: regenerate hashes after re-rendering.
- DOCS CLAIM STALE — README claims "22 today" selftests in multiple places; the suite now discovers 25. The 155-check e2e count IS machine-verified; the selftest count is not fenced and will drift silently. Fix: update to 25.

Tried to break:
- Absent `app:` block (old-repo compat): config without `app:` → `APP: SKIP — app.url not set`, exit 0; `open_files.sh src/foo.ts` → `no editor CLI on PATH for 'auto'`, exit 0. Both degrade gracefully.
- Malformed `--wait abc` against the installed copy → confirmed infinite loop (repeated `[: abc: integer expression expected`); same input against core exits 1 correctly. Bug installed-only.
- HTTP 500 health endpoint (python server returning 500): `APP: DOWN …` exit 1 — the 2xx/3xx-only probe is correct.
- Forced editor mode with missing CLI: `command -v cursor && echo cursor` exits 1 vs the `if` form exits 0 — `pick_editor` propagates 1 through `open_all`, blocking callers.

Traces:
- `diff core/scripts/app_check.sh .vteam/scripts/app_check.sh` → `117,119d116 < case "$WAIT" in ''|*[!0-9]*) …` (the missing guard).
- core/scripts/open_files.sh:22-23 (installed .vteam copy byte-identical) — pre-fix `command -v code >/dev/null && echo code` vs core/scripts/open_files.sh:23-24 `if command -v code >/dev/null; then echo code; fi`.
- `node tests/e2e.mjs 2>&1 | tail -3` → `E2E: GREEN — 155/155` (the selftest e2e check uses ≥15, so the "22" README claim is unfenced).

---

## R2 — re-review after fixes (model: sonnet)

VERDICT: APPROVE

Findings:
- Finding 1 RESOLVED — `diff core/scripts/app_check.sh .vteam/scripts/app_check.sh` empty; byte-identical. Numeric guard at core/scripts/app_check.sh:117-119 (installed .vteam copy byte-identical) rejects `abc`, `-1`, `1.5` with exit 1; trailing-flag guard at lines 110-113 covers `--wait` and `--url`.
- Finding 2 RESOLVED — `diff core/scripts/open_files.sh .vteam/scripts/open_files.sh` empty; `pick_editor` at core/scripts/open_files.sh:24-25 (installed .vteam copy byte-identical) uses the `if` form (never propagates nonzero); selftest mutation at lines 86-87 verifies forced-mode/missing-CLI exits 0.
- Finding 3 RESOLVED — manifest hashes verified programmatically; `node bin/vteam.mjs doctor` → `manifest verified (59 framework-owned files intact)`, PREFLIGHT: GREEN.
- Finding 4 RESOLVED — `grep -c "25 today" README.md` = 3, `"22 today"` = 0 (README.md:46,161,354).

Tried to break:
- `--wait -1` → exit 1 immediately (`got '-1'`) — negatives rejected by the `''|*[!0-9]*` pattern.
- `--wait 1.5` → exit 1 — float strings rejected, closing that infinite-loop variant.
- `--wait 0` → probe runs once, `APP: DOWN … after 0s`, exit 1 — boundary value correct, no spin.
- `bash .vteam/scripts/open_files.sh --selftest` → exit 0, OK across all six mutations including forced-mode/missing-CLI.

Traces:
- `bash .vteam/scripts/app_check.sh --url http://localhost:3000 --wait abc` → `app_check: --wait takes a whole number of seconds (got 'abc')` / EXIT:1.
- core/scripts/app_check.sh:117-119 (installed .vteam copy byte-identical) — the numeric guard now present in the installed copy.
- `node bin/vteam.mjs doctor` → `gate selftests green (25 discovered checks prove they can red)` / PREFLIGHT: GREEN.
- `npm test` → `E2E: GREEN — 155/155 checks passed`.

---

## Answered QUESTIONS

- R1's non-blocking question (backtick in `app.start` breaking the rendered
  code-span, src/cli/adapters.mjs:71): acknowledged as cosmetic; config values
  are author-controlled and the Environment block is advisory prose. Left as-is
  deliberately; a sanitizer would add complexity for no observed failure.
