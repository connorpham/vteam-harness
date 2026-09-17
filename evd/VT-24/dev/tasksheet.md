# Tasksheet — VT-24 (fix the code-review defects)

CODE-SCOPE: core/scripts/ profiles/ src/cli/ adapters/ tests/ core/templates/ README.md CHANGELOG.md package.json

## Plan (the 13 findings, in fix order)
1. gate.py `--help` + unknown-flag refusal; preflight.sh:82 stops invoking the whole gate
2. stale_verdict_check as a gate step in all 6 profiles (declared skip on remote trackers); BOOKKEEPING += stale-verdict
3. update.mjs installs providers from the CURRENT config (tracker/design), not only the ones already present
4. copilot/windsurf adapters quote `description:` (valid YAML)
5. claude-code adapter routes agents + hook through the manifest guard (write callback gains a mode arg)
6. ManifestGuard.prune(): orphaned framework files removed when unmodified, kept+reported when modified, owned never touched
7. detectProfile requires `next` for nextjs-prisma; typegen step guarded by requires_cmd
8. bdd_report_check --root arg parsing
9. ctx.py/ctx.mjs: empty inline-list element and dedent-below-first-key both die, same message, conformance fixtures
10. evdpack.replace_section — attach replaces ONLY the TRACKER ATTACHMENTS section
11. schedule_check: Due column by header, last-date fallback
12. graph_check ALWAYS_LEGAL / log_check path check / route_check code scope read paths.* from config
13. dead code: util.copyDir, evd_check dead assert

## Proof
Every fix carries a selftest or e2e assertion that was RED before the fix (recorded in evd/VT-24/dev/proof.md).
