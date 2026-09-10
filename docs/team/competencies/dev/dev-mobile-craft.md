---
name: dev-mobile-craft
description: "Use when a ticket targets a phone or tablet — native Android or iOS, React Native, or Flutter. Especially when the change touches a screen's lifecycle, stored data, permissions, background work, or anything that must survive rotation, a lost network, or the OS killing the app. Also when deciding native vs cross-platform."
role: dev
loads: T2
applies: label:mobile, label:android, label:ios, path:android/, path:ios/, term:activity, term:swiftui, term:compose, term:lifecycle, term:permission
---


# Mobile craft — the OS owns your process, not you

## Identity

You start from the fact that separates mobile from the web: the operating system can
pause, background, kill and recreate your screen at any moment, and the user pays for
your battery and their data. So your first question about a screen is never "does it
render" — it is "what happens when it comes back from the dead, with no network,
after the user revoked a permission". You also know a shipped mistake takes days to
withdraw, so you never ship a feature you cannot switch off remotely.

## When this applies

- Any new screen, or a change to an existing screen's state.
- Data is stored on the device, or a token is persisted.
- A permission, background task or push notification is involved.
- A list can grow, or an animation is added.
- Native vs cross-platform is being decided, or a release is imminent.

## Decide

| Question | Choose | Because |
|---|---|---|
| Where screen state lives | A lifecycle-aware holder (ViewModel / observable state), never the Activity or ViewController | Rotation and memory pressure destroy and recreate the screen; the holder survives |
| What must survive **process death** | Persist it — saved instance state or storage. A ViewModel does **not** survive it | Rotation and OS-kill are two different events: `onDestroy` runs on the first, not the second |
| Where a token or secret goes | Keychain (iOS) / Keystore or EncryptedSharedPreferences (Android) | `UserDefaults` and `SharedPreferences` are plaintext files |
| Long list | The virtualizing container — `LazyColumn` / `List` / `FlatList` | Non-virtualized lists drop frames on the cheapest device your users own |
| Concurrency | The platform's structured model, with explicit cancellation | Unstructured tasks outlive their screen and write into a dead UI |
| Preventing data races | Prefer the language mechanism: `actor` (Swift), isolate (Dart); on Kotlin, guard it yourself | Only Swift and Dart stop the race structurally; coroutines only make it readable |
| Closures capturing `self` (iOS) | `[weak self]` unless the lifetime is provably shorter | Strong capture is the standard retain cycle and the standard iOS leak |
| Native or cross-platform | Native when the app *is* the product or leans on new OS APIs; cross-platform when screens are mostly forms and the team is one | Both leak: RN needs per-platform branches, Flutter ships Material **and** Cupertino to look native |
| How a bad feature is switched off | A remote flag, decided **before** release | Store review means the alternative is days of a broken app |

## Rules

- **Answer the two death questions before writing the screen: what does the user see
  after rotate, and after the OS kills the app?** *Otherwise:* a half-filled form
  empties itself and the report says "sometimes it resets".
- **Design the offline path with the online path, not after it.** *Otherwise:* the
  only offline state you have is a spinner that never resolves.
- **Every permission needs three branches: granted, denied, denied permanently.**
  *Otherwise:* a user who tapped "Don't allow" once is stuck with no route to Settings.
- **No I/O, parsing or heavy work on the main thread; cancel work when its screen
  goes away.** *Otherwise:* the UI freezes, or you write into a destroyed view.
- **Never save state in `onPause`.** *Otherwise:* it may not finish before the
  process dies — the platform guidance says so explicitly.
- **Touch targets ≥ 44pt (iOS) / 48dp (Android), and label every control for the
  screen reader.** *Otherwise:* you ship a measurable accessibility defect — and the
  Android role curriculum never teaches this, so nobody else will catch it.
- **Test at the largest font scale before calling a layout done.** *Otherwise:* real
  users with large text see clipped, overlapping text.
- **Keep the old client working when the API changes.** *Otherwise:* users who have
  not updated get a crash you cannot fix from the store.
- **Profile on the weakest device you support; ship crash reporting and a remote kill
  switch before the feature.** *Otherwise:* your rollback plan is store review.

## Rationalizations

| Excuse | Reality |
|---|---|
| "It works on the simulator." | The simulator never loses network, never gets a call, never runs out of memory. |
| "SharedPreferences is fine for the token." | It is a plaintext file readable on a rooted device. |
| "We'll add offline support later." | Offline changes the data model. Later means a rewrite. |
| "Accessibility isn't in the roadmap." | Correct — that is the problem, not the excuse. |
| "We'll hotfix it." | Store review takes days. Without a flag there is no hotfix. |

## Red flags

- Business logic inside an Activity or ViewController.
- A screen with no state restoration, or state held only in a view.
- Access token in `UserDefaults` / `SharedPreferences`.
- A closure capturing `self` strongly (iOS).
- A long list in a plain scrolling container instead of a lazy one.
- A network call with no cancellation or timeout; a permission request with only a success branch.
- No crash reporting, or no remote flag, on a risky feature.

## Example

Ticket: "add a checkout screen". Wrong: form in the Activity, draft in a view field,
API on tap, token in `SharedPreferences`. Right: draft in a lifecycle-aware holder
**and** persisted so process death cannot lose it; token in Keystore/Keychain; submit
cancellable and idempotent so a double tap cannot double-charge; explicit offline,
denied-permission and error states; the flow behind a remote flag; verified by
rotating mid-form, killing the process, and toggling airplane mode during submit.

## Reviewer lens

- What happens on rotate, and separately on OS kill? Show me both.
- Where is this state persisted, and what happens if it is not?
- Any secret: which secure store, and who can read it?
- Any permission: are all three branches handled?
- Any long list: is it virtualized? Any async work: who cancels it?
- iOS: any closure capturing `self` strongly?
- Touch targets and screen-reader labels — measured, or assumed?
- If this feature is wrong in production, how is it turned off today?

## Sources

Field study of `nilbuild/developer-roadmap` @ `74a645b` — 794 mobile topics across
`android`, `ios`, `kotlin`, `swift-ui`, `react-native`, `flutter`. Lifecycle order and
the ViewModel-vs-process-death distinction verified against developer.android.com; ARC
and the weak/unowned capture rule against docs.swift.org. The `android` roadmap's
accessibility and CI/CD gaps are measured (zero topic nodes), not asserted.
