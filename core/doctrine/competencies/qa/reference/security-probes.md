<!-- Reference table for qa-security-probes. Verbatim from connorpham/ai-qa core/doctrine/security-probes.md
     (read 2026-09-07). The competency is the METHOD for choosing from these; this is the data. -->

# Security probes — the input an attacker sends on purpose

> `/qa` opens this in V2 when the ticket touches **authentication, sessions,
> roles, money, personal data, uploads, or any server that trusts something the
> client sent**. `/triage` opens it when a report smells like a bypass. Pick the
> two or three probes that fit the surface in front of you; never paste the whole
> file into a plan.

`hostile-inputs.md` is the value a real user types **by accident**. This is the
value an attacker types **on purpose** — and the difference is the intent, not
the character. The same apostrophe that breaks `O'Brien`'s name is the start of
`' OR '1'='1`. You are not a penetration tester and this file does not pretend to
be a pentest (no fuzzing, no CSRF-token forgery, no JWT `alg:none`, no traffic
interception — those are a specialist's job and saying so is how nobody claims
they were covered). This is the security a functional QA can **prove with the
lane's own tools** — the browser, the API recorder, the read-only database —
walking the product's real surface.

## The oracle rule, sharpened

Most of QA cites a spec. Security has a floor **below** the spec: outcomes no
specification anywhere permits, so no citation is needed to call them a defect.

- **Authentication is bypassed** — any path into a session without valid
  credentials.
- **Authorization is bypassed** — one role reaching another role's data or
  another role's action; one user reaching another user's record.
- **Injected input is executed** — a payload runs as SQL, as HTML/JS, as a
  template, as a command, instead of being stored or refused as ordinary text.
- **A secret leaves the building** — a password, hash, token, session id, or
  another user's personal data appears in a response body, the page source, a
  URL, a log line, or an error message.
- **A session outlives the event that should end it** — logout, password change,
  password reset, or an admin lock, and the old session still works.

Everything else — the exact lockout minutes, whether the reset code is 6 digits
or 8 — is cited from the spec or written up as a decision request, exactly as
everywhere else. Below the floor, the finding stands on its own.

## Authentication (OWASP WSTG-ATHN)

| Probe | Send | A defect looks like |
|---|---|---|
| **Lockout is real** | the wrong password N times, then the right one | the right password lets you in after the threshold — the lockout never armed |
| **Lockout scope** | wrong passwords across *many* accounts from one client; and one account from many clients | per-account only, so a slow spray across accounts is never throttled (WSTG notes lockout should consider the source, not only the account) |
| **User enumeration — message** | a real username + wrong password, then a username that does not exist | the two messages differ by one word — the attacker now has a list of real accounts |
| **User enumeration — timing** | the same two, measured over 10+ samples | the non-existent user answers markedly faster because no hash was compared — the message is identical but the *clock* leaks the account |
| **User enumeration — the other doors** | the same probe on password-reset and registration | login says nothing but reset says "no such account", or registration says "already taken" — the same list, a different door |
| **Case / normalization identity** | log in with the username in UPPERCASE; register `Admin` when `admin` exists | uppercase is refused (identity is meant to be case-insensitive) or a second account is created (two identities for one person) — see `test-design.md`, equivalence across representation |
| **Weak-password floor** | set a password of `123456` or the username itself, where the spec names a rule | the banned password is accepted |
| **Reset needs proof** | reach the set-new-password step without the code / without the current password | the new password saves without ever proving control of the account |
| **Codes and links are single-use and expiring** | reuse a used reset code; use one after its stated lifetime | a used or expired code still works |

## Sessions (OWASP WSTG-SESS)

| Probe | Read / do | A defect looks like |
|---|---|---|
| **Cookie flags** | read the session cookie after login | missing `HttpOnly` (script can read the token — one XSS steals every session); missing `SameSite` (CSRF surface); missing `Secure` **on HTTPS** (localhost http is the one honest exception, and say so) |
| **Invalidation on the events that demand it** | change or reset the password, or have an admin lock the account, then use the OLD session | the old session still works — this is the concrete test behind "terminate all active sessions", and the one most often only half-built |
| **Session fixation** | note the session id before login, log in, read it again | the id did not change on login — an id an attacker planted is now authenticated |
| **Idle / absolute timeout** | leave a session past its stated life, then act | the server still honours it — the timeout was only a client-side clock |

## Authorization (OWASP WSTG-ATHZ)

| Probe | Do | A defect looks like |
|---|---|---|
| **Server enforces, not the menu** | call the protected route directly (API recorder, or paste the URL) as a role the matrix forbids | 200 and the action happens — the control was only the hidden button. This is the concrete test behind "hiding a function on the UI is not a control." |
| **IDOR — someone else's row** | as user A, request user B's id (order, wallet, profile) | B's record comes back — ownership was never checked, only role |
| **Forced browsing** | as a lower role, reach a higher role's page/endpoint by its address | the page renders, or the endpoint answers |
| **401 vs 403** | not-signed-in vs signed-in-wrong-role on the same route | the two are the same, so the app cannot tell "log in" from "you may not" — a smaller issue, but it usually means the check is in the wrong layer |

## Injection & output (OWASP WSTG-INPV, and the output side)

Send each through the **real field**, the way the browser sends it — not a shell,
not `curl` with a hand-built body, because the point is what the app's own
pipeline does with it.

| Send into the field | Must happen | A defect looks like |
|---|---|---|
| `admin' OR '1'='1' --` and `'; SELECT …` | stored or refused as ordinary text; the login just fails as normal | a raw database error, a different response, or a login that succeeds — the input reached the query |
| `"><img src=x onerror=alert(1)>` and `<script>` | shown as literal characters wherever it is echoed back | an alert fires, or the page source contains the raw unescaped tag — it will run in the next viewer's browser |
| `${7*7}`, `{{7*7}}`, `#{7*7}` | shown literally | the screen shows `49` — a template engine evaluated user input |
| a value, then read every response and the page source | the password / hash / token is **nowhere** | the field value or a hash appears in the DOM, a hidden input, a JSON response, or an error |

## How to run it, and where it lands

No new tooling. Drive the form with `browser.mjs`, record request/response with
`api_check.mjs`, read the stored shape read-only with `db_verify.py` — the same
three the rest of `/qa` uses. A security probe is a normal case: it names a
`PERSONA:` (here, the attacker, or the curious user with someone else's link),
walks from ENTRY, and its EXPECTED is either a cited rule or one of the
no-citation floor outcomes above. When a probe is a **read** with no screen
(cookie flags, a timing table, a hash shape) the case is `TYPE: NON-UI` and its
proof is the recorded query, request/response, or the measured table — exactly
as the gate already expects.

One case in the pack is enough when the ticket only brushes security; a ticket
that **is** authentication or authorization spends two or three of its five here,
because on those tickets the security floor *is* the requirement.
