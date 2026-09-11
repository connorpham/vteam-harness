# VT-21 — command verification

## AC1 + AC2 — the two steps, and the difference between them
```
▶ schedule: python3 .vteam/scripts/schedule_check.py
❌ schedule_check: OFF SCHEDULE or stale plan — the desk report must lead with this line plus a plan (cut scope / slip / add capacity).
▶ evd-ui: python3 .vteam/scripts/evd_ui_check.py --sweep
🟡 advisory schedule: FAILED — reported, not blocking; the condition is about the project, not about this change
GATE: GREEN (13 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
```

On the field repo, where a real UI pack exists:
```
⚠️  TB-8 [Done]: 1 problem(s) — reported, not failed, because the pack predates the NN_<description>.png layout, so nothing in it has ever been judged by this checker
     - 106 image(s) live in subfolders and none at dev/
✅ evd_ui_check --sweep: 0 pack(s) green, 1 reported without failing
```

## AC3 — advisory is guarded in four directions
```
gate selftest: OK (green + substitution, red stops, run-less red, silent-skip red, declared skip loud, requires_cmd green/skip/red, 2 WEAK banners, echo-test tripwire, advisory: fails-without-blocking, still-prints, banners on GREEN, passes silently, never softens a hard red)
```

## AC4 — the lens is read where it was required and ignored
```
/ba    reviewer lens x2
/pm    reviewer lens x1
/dev   reviewer lens x2
/qa    reviewer lens x2
(before this ticket: /ba 0, /pm 0)
```

## AC5 + AC6 — a declared-owned file stops parking .new
```
$ (field repo) echo '"owned": [".vteam/profiles/nextjs-prisma/gates.yaml"]' into .vteam/manifest.json
$ vteam update
📌 1 file(s) this repo OWNS moved upstream — kept yours, nothing parked:
  .vteam/profiles/nextjs-prisma/gates.yaml
  Declared in .vteam/manifest.json → owned. Merge by hand when you want the change;
  remove it from `owned` to go back to receiving the framework's version.
$ ls .vteam/profiles/nextjs-prisma/*.new
(no matches — the chore is gone, the signal is not)
```

`.githooks/pre-push` is deliberately NOT in this repo:
```
owned: []
```

## What is still not covered

The UI sweep judges LAYOUT and image quality, never whether an image shows what its caption
claims. TB-8's 106 subfolder images are now visible as unjudged; making them judged means
curating frames to dev/ with NN_ names, which is a ticket for whoever owns that pack, not a
gate that can be tightened.
