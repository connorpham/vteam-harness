# Mutation probes — break the logic, keep the new selftest, it must go RED, restore

## orca: trust widens a created config to 0644 — `core/scripts/orca_team.sh`: `if existed else 0o600)` → `if existed else 0o644)`
```
$ bash core/scripts/orca_team.sh --selftest
exit 1
orca_team selftest: FAIL — trust did not record the flag as 0600
```

## orca: trust overwrites the backup every run — `core/scripts/orca_team.sh`: `        if not bak.exists():
            shutil.copy2(cfg, bak)` → `        if True:
            shutil.copy2(cfg, bak)`
```
$ bash core/scripts/orca_team.sh --selftest
exit 1
orca_team selftest: FAIL — the backup was overwritten on a later run
```

## auth: redirect flag dropped — `profiles/nextjs-prisma/scripts/auth.mjs`: `password, redirect: "false" },` → `password },`
```
$ node profiles/nextjs-prisma/scripts/auth.mjs --selftest
exit 1
auth selftest: FAIL — credentials form wrong: {"csrfToken":"tok-1","username":"admin","password":"pw"}
```

## fidelity: font-size gets the px tolerance — `profiles/nextjs-prisma/scripts/ui_fidelity.mjs`: `if (p === "font-size" && !Number.isNaN(pe) && !Number.isNaN(pm)) return pe === pm;` → `if (p === "font-size" && !Number.isNaN(pe) && !Number.isNaN(pm)) return Math.abs(pe - pm) <= 0.75;`
```
$ node profiles/nextjs-prisma/scripts/ui_fidelity.mjs --selftest
exit 1
ui_fidelity selftest: FAILED
  x font-size has no 'close enough'
```

## fidelity: off-list intent counted as INTENDED — `profiles/nextjs-prisma/scripts/ui_fidelity.mjs`: `if (typeof intent === "string" && INTENT_OK.test(intent.trim())) {` → `if (typeof intent === "string" && intent.trim()) {`
```
$ node profiles/nextjs-prisma/scripts/ui_fidelity.mjs --selftest
exit 1
ui_fidelity selftest: FAILED
  x off-list intent → WRONG, naming the intent
```

## evidence: CI no longer forces headless — `profiles/nextjs-prisma/scripts/ui-evidence.mjs`: `return !!headlessFlag || !!ci || appHeaded === "never";` → `return !!headlessFlag || appHeaded === "never";`
```
$ node profiles/nextjs-prisma/scripts/ui-evidence.mjs --selftest
exit 1
ui-evidence selftest: FAILED
  x CI → headless
```

## evidence: a shot without user accepted — `profiles/nextjs-prisma/scripts/ui-evidence.mjs`: `if (!s.anon && (typeof s.user !== "string" || !s.user)) return` → `if (false) return`
```
$ node profiles/nextjs-prisma/scripts/ui-evidence.mjs --selftest
exit 1
ui-evidence selftest: FAILED
  x no user and not anon refused
```

## prepublish: dirty tree no longer refuses — `tools/prepublish-check.mjs`: `  if (dirty) {
    bad(` → `  if (false) {
    bad(`
```
$ node tools/prepublish-check.mjs --selftest
exit 1
prepublish-check selftest: FAILED
  x dirty tree must refuse: 
```

## prepublish: bytecode in the tarball waved through — `tools/prepublish-check.mjs`: `const artifacts = (packed || []).filter((p) => /__pycache__|\.pyc$/.test(p));` → `const artifacts = [];`
```
$ node tools/prepublish-check.mjs --selftest
exit 1
prepublish-check selftest: FAILED
  x bytecode in the pack list must refuse: 
```
