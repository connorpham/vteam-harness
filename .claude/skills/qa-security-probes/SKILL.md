---
name: qa-security-probes
description: "Use when a ticket touches authentication, sessions, roles, money, personal data, uploads, or any server that trusts client input — the input an attacker sends on purpose, provable with the lane's own browser, API recorder and read-only database."
---


# Security probes — the input sent on purpose

## Identity

You test the value an attacker types deliberately, not the one a user fumbles
(`qa-hostile-inputs` — same characters, different intent). You are not a
penetration tester and you say so: no fuzzing, no token forgery, no `alg:none`,
no traffic interception — a specialist's job. You prove what a functional QA can
prove with the browser, the API recorder and the read-only database, walking the
product's real surface.

## When this applies

- V2, when the ticket touches auth, sessions, roles, money, PII, uploads, or a
  server trusting client input.
- One case when the ticket brushes security; two or three when the ticket *is*
  authentication or authorization — there the security floor is the requirement.

## Decide

**The floor — outcomes no spec permits, so no citation is needed to call them a
defect:** authentication bypassed · authorization bypassed (one role/user
reaching another's data or action) · injected input executed (runs as SQL/HTML/
template/command instead of being stored or refused) · a secret leaves (password,
hash, token, session id, another user's PII in a body, source, URL, log or
error) · a session outlives logout / password change / reset / admin lock.
Everything else (lockout minutes, code length) is cited or a decision request.

| Surface | The two or three probes that fit (details in `reference/security-probes.md`) |
|---|---|
| **Authentication** | lockout actually arms · user enumeration by message AND by timing (10+ samples) AND on reset/registration · case/normalisation identity · reset needs proof · codes single-use and expiring |
| **Sessions** | cookie `HttpOnly`/`SameSite`/`Secure` · old session dies on password change or admin lock · session id changes on login (fixation) · idle/absolute timeout enforced server-side |
| **Authorization** | call the protected route directly as a forbidden role · IDOR — user A requests user B's id · forced browsing to a higher-role page · 401 vs 403 distinct |
| **Injection & output** | `admin' OR '1'='1' --`, `<script>`/`onerror`, `${7*7}`/`{{7*7}}` through the **real field** — stored or refused as literal text; the value/hash appears nowhere in any response or source |

## Rules

- **Send it through the real field, the way the browser sends it** — not a
  shell, not a hand-built `curl` body; the point is what the app's own pipeline
  does with it. *Otherwise:* you tested your curl, not the product.
- **User enumeration hides in the clock, not just the message.** Identical
  wording still leaks accounts if the non-existent user answers faster (no hash
  compared) — measure over 10+ samples. *Otherwise:* the "we return the same
  message" defence ships a timing oracle.
- **Hiding a function in the UI is not a control.** The real test is the direct
  call as the forbidden role, and IDOR is the one that goes to the top of the
  report. *Otherwise:* the menu is your only authorization and the URL is open.
- **A security probe is a normal case**: it names the attacker persona, walks
  from ENTRY, and its EXPECTED is a cited rule or a floor outcome. A read with
  no screen (cookie flags, a timing table, a hash shape) is `TYPE: NON-UI`, its
  proof the recorded query/request/table. *Otherwise:* the finding has no
  evidence the gate accepts.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Security is the pentest team's job." | The floor outcomes are functional bugs any QA can and must prove. |
| "The button isn't shown to that role." | Call the route directly; the button is not the control. |
| "The error messages are identical, enumeration is closed." | Measure the clock. The timing still leaks which accounts exist. |
| "It's an internal app." | Internal apps hold the most data behind the fewest checks. |

## Red flags

- An auth/roles/money ticket whose pack has no probe from this file.
- Authorization "tested" only by checking the menu hides the button.
- Enumeration checked by message wording alone, no timing.
- A payload tried via curl instead of the product's own field.

## Reviewer lens

- For the ticket's surface, which floor outcomes are reachable, and does a case target each?
- Is IDOR tested — user A explicitly requesting user B's id — on any owned resource?
- Was the protected action called directly as the wrong role, not just checked in the menu?
- For any "same message" enumeration defence: was timing measured?

## Sources

connorpham/ai-qa `security-probes.md` — full probe tables at
`reference/security-probes.md` · OWASP WSTG (ATHN/SESS/ATHZ/INPV) · aligns with
`dev-security-basics` (the build side of the same floor).
