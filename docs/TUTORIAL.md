# The 15-minute tour — watch the gates go red, then green

No theory. You'll install vteam into a scratch repo, write a ticket, watch every
gate refuse you for the right reason, then satisfy it. Everything runs locally —
zero external services (the markdown tracker), zero AI calls.

**Prereqs:** git, Node ≥20, Python 3.9+ (`python3 --version`), bash.
Optional: `pip install pillow` (image evidence checks).

## 1. A scratch repo + install (2 min)

```bash
mkdir vteam-tour && cd vteam-tour && git init -b main
git remote add origin "$(pwd)/../vteam-tour-remote" && git init --bare ../vteam-tour-remote
npx vteam-harness init --yes --key TOUR --tracker markdown --design none --tools claude-code
git add -A && git commit -m "vteam install" && git push -u origin main
npx vteam-harness doctor
```

`doctor` ends green: config parses, ~17 gate selftests each prove they can FAIL
(that's the house rule: a check that has never been red does not exist), and the
preflight pings what's configured.

## 2. Your first ticket — rejected, correctly (3 min)

Tickets are just files under `docs/backlog/`. Write a lazy one:

```bash
cat > docs/backlog/TOUR-1.md <<'EOF'
# TOUR-1: Make the greeting nicer
- status: To Do
- estimate: 0.5d

Improve the greeting somehow.
EOF
python3 .vteam/scripts/dor_check.py TOUR-1
```

**RED**, with the three real reasons: no Given/When/Then, no spec citation, no
out-of-scope section. This is the Definition-of-Ready gate — underspecified work
bounces BEFORE anyone burns a session on it. Now fix the ticket:

```bash
cat > docs/backlog/TOUR-1.md <<'EOF'
# TOUR-1: Greeting names the user
- status: To Do
- estimate: 0.5d

Spec: spec §1.1 (docs/specs/greeting.md)
AC: Given a user named Mai / When the app greets / Then the output is "Hello, Mai!"
(boundary) Given an empty name / When the app greets / Then the output is "Hello!" with no dangling comma
Out of scope: localization
no UI
EOF
python3 .vteam/scripts/dor_check.py TOUR-1     # ✅ ready to code
```

## 3. Code + the verification gate (3 min)

```bash
git switch -c feat/TOUR-1-greeting
mkdir -p src && cat > src/greet.js <<'EOF'
export const greet = (name) => name ? `Hello, ${name}!` : "Hello!";
EOF
cat > .vteam/test.sh <<'EOF'
node --input-type=module -e '
import { greet } from "./src/greet.js";
if (greet("Mai") !== "Hello, Mai!") { console.error("FAIL greet(Mai)"); process.exit(1); }
if (greet("") !== "Hello!") { console.error("FAIL greet(empty)"); process.exit(1); }
console.log("2 checks passed");'
EOF
bash .vteam/scripts/gate.sh
```

`GATE: GREEN` — and note it lists what ran and what was skipped WITH reasons.
A step it can't run without a declared reason would be RED: silent skips are
forbidden. (Break the test on purpose and re-run if you want to see it stop.)

## 4. The push fence — two refusals, then through (4 min)

```bash
git add -A && git commit -m "feat(TOUR-1): greeting names the user"
git push -u origin feat/TOUR-1-greeting
```

**BLOCKED**: the diff touches code, and there is no committed review dossier.
Code leaves the machine only with its reviews attached. Write the dossier
(in real use two fresh agents write these; the gate enforces the form —
verdict, a tried-to-break list, traces into real files):

```bash
mkdir -p evd/TOUR-1/dev && cat > evd/TOUR-1/dev/review.md <<'EOF'
## R1 — spec reviewer
APPROVE
Tried to break:
- ran `bash .vteam/test.sh` — both AC checks pass
- checked the empty-name boundary at src/greet.js:1 — no dangling comma
- grepped for other greeting call sites — single definition
Traces: src/greet.js:1, docs/backlog/TOUR-1.md:7

## R2 — challenger
APPROVE
Tried to break:
- called greet(undefined) via `node -e` — falls into the "Hello!" branch, matches the boundary AC
- called greet(0) — numeric falsy also safe
- reviewed the diff for scope creep — one file, one function
Traces: src/greet.js:1, .vteam/test.sh:2
EOF
git add -A && git commit -m "feat(TOUR-1): review dossier"
git push -u origin feat/TOUR-1-greeting          # ✅ through
```

Also try `git switch main && git push origin main` — direct pushes to main are
refused too (the escape hatch exists, and it writes an audit line when used).

## 5. The part nothing else does: verdicts that expire (3 min)

Merge, record a QA verdict pinned to the exact commit it examined:

```bash
git switch main && git merge --squash feat/TOUR-1-greeting && git commit -m "feat(TOUR-1): greeting (#1)"
mkdir -p evd/TOUR-1/TC_1
printf 'TYPE: NON-UI\nRESULT: PASS\n' > evd/TOUR-1/TC_1/manifest.md
printf '$ bash .vteam/test.sh\n2 checks passed\n' > evd/TOUR-1/TC_1/cmd_verify.md
printf 'TOUR-1: 1 TC, PASS.\n' > evd/TOUR-1/manifest.md
printf '### verifier\nPASS. MY WEAK SPOT: only ran the script.\n### challenger\nRe-ran with node 20 and 22 — same. No dissent.\n' > evd/TOUR-1/debate.md
cat > evd/TOUR-1/REPORT.md <<EOF
# Verification report TOUR-1 — PASS
COMMIT: $(git rev-parse HEAD)
VERIFIED-AT: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## 1. What does this ticket ask for?
The greeting names the user; an empty name still greets cleanly.
## 2. How did I check?
| # | What I did | Expected | Actual | Match? |
|---|---|---|---|---|
| 1 | ran the check script | both AC hold | 2 checks passed | ✅ |
## 3. Evidence — what to look at, where?
TC_1/cmd_verify.md → the real command output.
## 4. Conclusion
Requirement met.
EOF
python3 .vteam/scripts/evd_check.py --evd evd/TOUR-1 --expect-tcs 1   # ✅
python3 .vteam/scripts/stale_verdict_check.py                          # ✅ clean

# now change the code AFTER the verdict…
echo "// TOUR-1 tweak" >> src/greet.js
git add -A && git commit -m "fix(TOUR-1): post-verdict tweak"
python3 .vteam/scripts/stale_verdict_check.py                          # ⚠️ STALE — names the exact commit
```

*A verdict is valid only for the code it examined.* The running version has
never been checked, so the gate says so — this is the check that catches the
"it was tested… three commits ago" lie every other setup misses.

## Where to next

- Point your AI tool at the repo and type `/team` — the workflows installed in
  step 1 run this whole discipline with agents in the seats.
- Real tracker? Set `tracker.provider: jira` or `github` in `vteam.config.yaml`.
- Have an idea but no code or docs? `/plan`. Code but no docs? `/docs`.
- Grade any repo's accountability first: `npx vteam-harness audit`.
