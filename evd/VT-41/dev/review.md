# Review dossier — VT-41 (one CodeQL version, one PR)

**Provenance, stated plainly:** both cards were written by the implementing session, not by spawned
reviewer agents. Every bullet is a command run on 2026-09-18; outputs are in `proof.md`.

## R1 — implementation review
APPROVE

Tried to break:
- checked the replacement SHA is real and not a typo from a PR body: `gh api repos/github/codeql-action/commits/b96794f015dfd88f77b49b1c93e0fa7110f94c63` returns a commit dated 2026-09-09 titled "update-v4.38.0", and the tag listing shows it is reachable from both `v4.38.0` and `v4` — so the `# v4` comment at .github/workflows/codeql.yml:25 stays true rather than becoming a lie beside a pin.
- checked no usage was left behind: `grep -rc <old sha> .github/` returns zero files, and the three remaining `codeql-action` lines (.github/workflows/codeql.yml:25, :27 and .github/workflows/scorecard.yml:26) all carry the new SHA. A partial bump is exactly the state that made #69 and #70 red.
- checked the grouping syntax parses rather than assuming: `python3 -c "yaml.safe_load(open('.github/dependabot.yml'))"` prints `groups: ['codeql-action']`. A malformed dependabot file is ignored silently by GitHub, which would have left the root cause open while looking fixed.
- checked nothing else in the repository pins these actions: the only three usages are the ones changed.

Traces: .github/workflows/codeql.yml:25, .github/workflows/scorecard.yml:26, `gh api repos/github/codeql-action/commits/b96794f015df…`, `grep -rn codeql-action .github/workflows`

## R2 — adversarial read: is this a supply-chain change worth making?
APPROVE

Tried to break:
- asked whether moving the pin forward is safe at all: it is a SHA, not a tag, so the content is immutable; the risk is upstream's own change between 2026-08-26 and 2026-09-09, and the mitigation is the same as for any dependency — CI runs the whole gate against it, and the diff is three pin lines that a reader can verify against the upstream tag in one command.
- asked whether grouping HIDES a bump: a grouped PR still lists every action it moves, and a group cannot swallow an unrelated ecosystem — the pattern is `github/codeql-action*` only, so a bump to `actions/checkout` still arrives on its own.
- asked whether this should instead be auto-merge: no. An auto-merged dependency PR would have merged #69 alone and broken CodeQL analysis for everyone, which is precisely the failure being fixed here. The out-of-scope line says so.
- checked the three dependabot PRs will not resurrect: they are closed pointing at this change, and dependabot closes its own superseded PRs once the pin it proposes is already in the base branch.
- checked the package's exposure honestly: this package ships zero runtime dependencies, so the CI actions ARE its supply chain, and a three-week-stale pin on the security-scanning action is the one staleness that matters most.

Traces: .github/dependabot.yml, .github/workflows/codeql.yml:27, `gh pr checks 69`, `gh api repos/github/codeql-action/tags`
