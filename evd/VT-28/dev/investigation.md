# VT-28 · investigation — why the vteam arm's own e2e passed AC-A07, AC-D02, AC-D07 while the held-out probes failed

Run on 2026-09-18 against arm-a at its stop-state commit `356bfcc`. Nothing in the judge was modified.

## 1. The "tested on `next dev`" hypothesis is refuted

```
$ sed -n '/webServer/,/}/p' arm-a-vteam/playwright.config.ts
  webServer: { command: 'npx next start -p 3410', url: 'http://127.0.0.1:3410', reuseExistingServer: false, timeout: 120_000 }
```
RUNLOG E12 records that `next dev` did not hydrate on the host, and the arm moved its e2e to the production build.

## 2. The arm's own tests pass on a FRESH production build

```
$ npm run build            # arm-a, 356bfcc          → build ok
$ npx playwright test e2e/login.spec.ts e2e/a11y.spec.ts -g "AC-A07|AC-D02|AC-D07" --reporter=line
  7 passed (2.6s)
```

## 3. What each probe asserts vs what the arm renders

| AC | Probe (judge) | Arm | Verdict |
|---|---|---|---|
| AC-A07 | `locator('[role="alert"], [aria-live], [data-error]').first()` must be visible | `LoginForm.tsx:176` renders `<p class="auth-alert" role="alert">{formError}</p>` **present and empty from first render** (comment: "so it can be announced later"); the field error `#email-error role="alert"` with text is the *second* match | `.first()` picks the intentionally empty region; an empty `<p>` is not "visible". **Probe defect.** |
| AC-D02 | same `.first()` pattern on `[role="alert"], [aria-live=…]` after `triggerFieldError` | same markup; `aria-describedby="email-error"` present, target exists | same `.first()` defect. **Probe defect.** |
| AC-D07 | walks every `.ts/.tsx/.css` except `globals.css`; skips only lines that *start* with `//` or `*`; flags `HEX`/`rgb(`/`hsl(` | `app/auth.css:8` = prose inside a `/* */` block ("not one hex, rgb() or hsl() in this file"); `:164–167` = contrast-ratio notes inside a `/* */` block (`#ffffff vs #1f5eff -> 5.12`). The arm's own test strips `/* */` comments first | a comment is not a colour. **Probe defect.** |

arm-b never hit either defect: every one of its alerts is rendered conditionally with text and carries an `id`, and its CSS comments do not quote hex values. The defects are asymmetric by accident, not by design.

## 4. Conclusion

The three "contradicted claims" in the 2026-09-17 scorecard are three probe defects (fixture bugs, to be numbered J6 = comment stripping in the AC-D07 scanner, J7 = `.filter({ hasText: /\S/ })` before `.first()` in AC-A07/AC-D02). The arm's claims were true; the framework's claim layer did not fail here. What the benchmark still says about vteam stands: 4 h 29 min to the first feature commit vs 1 h 44 min, ~7 h of commit activity vs 2 h 28 min, 16 environment findings, a red unit suite at stop, no closing entry.

Whether to correct the probes, re-calibrate, re-score both arms and republish is **D18** — a change to a published exam after seeing the results is the owner's call, not the operator's.
