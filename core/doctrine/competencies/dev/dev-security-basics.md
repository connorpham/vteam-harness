---
name: dev-security-basics
description: "Use when code handles a request, a session, a secret, a file upload, a query built from input, or anything a user can address by id — and whenever the change touches auth, roles, money, personal data or deletion."
role: dev
loads: T3
applies: always
---

# Security basics — every request is hostile until proven otherwise

## Identity

You assume every input is crafted, every id is guessed, every client is a
script. You authorize per resource, validate at the edge, parameterize every
query, keep secrets out of code and logs, and hash passwords with a
password hash. You do not invent crypto, sessions or auth; you use the
framework's and configure it correctly.

## When this applies

- Every handler, action, job or webhook — the surface *is* the attack surface.
- Anything reading `params`, `query`, `body`, headers, cookies, files.
- Any SQL, shell, HTML, template, or path built from a value.
- Secrets, tokens, passwords, personal data, money, deletion.

## Decide

| Situation | Do | Because |
|---|---|---|
| Endpoint reads a resource by id | Load it **scoped to the caller** (`where: { id, ownerId: user.id }`) or check ownership; 404 either way | IDOR is the #1 real API bug |
| Role-based action | Enforce on the server per request; the UI hiding a button is not a control | Clients are optional |
| Input arrives | Validate against a schema (type, length, range, allow-list) before any use; reject unknown fields on writes | Mass assignment and injection start with "extra fields are fine" |
| Query built with a value | Parameterized / ORM query API; never string concatenation | SQLi still tops the charts |
| Shell/exec needed | `execFile` with an argument array, no shell, timeout, bounded output | Interpolation into a shell is command injection |
| Passwords | bcrypt/scrypt/argon2 via the framework; never a general hash | General hashes are fast — for the attacker too |
| Secrets | Env/secret manager; never in code, commits, logs or error bodies | The pre-push scan catches the obvious ones; you catch the rest |
| Session/JWT | Framework default: httpOnly, Secure, SameSite cookies; short expiry; rotate on privilege change | Hand-rolled sessions are always wrong somewhere |
| File upload | Validate type by content, cap size, store outside web root under a generated name | Path traversal and stored XSS ride on uploads |
| Logging | Log who/what/when with a correlation id; never tokens, passwords, card numbers, full PII | Logs are read by more people than the database |

## Rules

- **Authorize on every request, at the resource.** *Otherwise:* one forgotten
  middleware exposes everything behind it.
- **Deny by default.** New route → protected until proven public. *Otherwise:*
  the admin route ships open for a sprint.
- **Validate server-side, always, even when the client already did.**
  *Otherwise:* `curl` skips your React form.
- **Output-encode for the context** (HTML, attribute, URL, JS); trust the
  framework's escaping; never `dangerouslySetInnerHTML`/`innerHTML` with user
  data. *Otherwise:* stored XSS in a username.
- **Money and irreversible actions: server-side re-check of amount, ownership,
  and state inside the same transaction.** *Otherwise:* a tampered client
  request pays $0.
- **Dependencies pinned; lockfile committed; audit in CI.** *Otherwise:* a
  transitive package becomes your incident.
- **Error responses are generic; details go to the log with an id.**
  *Otherwise:* the attacker gets a stack trace with table names.

## Reviewer lens

- For each new/changed handler: where is authentication, and where is the per-resource authorization?
- Try another user's id; a payload with an extra field; a 10 MB body; a string of 10 000 chars.
- Grep the diff for template strings inside SQL/exec/HTML.
- Do any logs or responses contain a token, password, or full personal record?

## Sources

OWASP Cheat Sheet Series (Authorization, Input Validation, SQL Injection
Prevention, Password Storage, Secrets Management, Mass Assignment, Logging,
Session Management, File Upload) · github/awesome-copilot
`security-and-owasp` (anti-pattern catalog with detection patterns) ·
nodebestpractices §6 Security.

Rationalizations, red flags and a worked example live in `reference/dev-security-basics.md` — opened when needed, never loaded by default.
