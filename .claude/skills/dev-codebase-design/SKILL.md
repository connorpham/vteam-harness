---
name: dev-codebase-design
description: "Use when deciding where new code lives, when adding a function, module, service or abstraction, when a change touches more than two files for one behavior, or when a test needs to reach past a public interface to check something."
---


# Codebase design — deep modules, small interfaces, real seams

## Identity

You design for the reader and the tester. A module earns its place by hiding
real behavior behind a small interface at a seam that actually varies; it does
not earn it by existing. You ask "if I deleted this, where would the complexity
go?" before you add anything, and you put code next to the code it changes
with, not next to code that merely looks similar.

## When this applies

- You are about to create a file, class, hook, service or helper.
- One behavior change requires edits in three or more places.
- You want to test something the public interface does not expose.
- A "utils" or "helpers" file is about to grow.

## Decide

| Question | Choose | Because |
|---|---|---|
| New abstraction or inline code? | Inline until the second real caller exists | One adapter is a hypothetical seam; two is a real one |
| Where does the new function live? | With the code that changes for the same reason | Locality: change, bugs and knowledge concentrate in one place |
| Interface: more methods or fewer? | Fewer methods, simpler params, more behind them | Depth is leverage per unit of interface a caller must learn |
| Dependency: create inside or accept? | Accept it (parameter, constructor, context) | Tests replace it at the seam instead of monkey-patching |
| Side effect or return value? | Return the result; let the edge apply it | Pure cores are testable and reusable; effects are neither |
| Tests need private access | Reshape the module — the interface is the test surface | Testing past the seam means the seam is in the wrong place |

## Rules

- **The deletion test.** Before adding a module, imagine deleting it: if
  complexity vanishes it was pass-through; if it reappears across N callers it
  earns its keep. *Otherwise:* the codebase fills with shallow layers that
  forward calls and hide nothing.
- **Interface = everything a caller must know.** Types, invariants, ordering,
  error modes, required config, performance shape — not just the signature.
  Document the non-obvious ones at the seam. *Otherwise:* the caller learns the
  invariant from a production stack trace.
- **Unidirectional flow.** App → features → shared; features never import each
  other; shared never imports up. Enforce with a lint rule where the stack
  allows. *Otherwise:* a change in one feature breaks another through an import
  nobody remembers adding.
- **Feature folders over layer folders.** `features/orders/{api,components,
  hooks,types}` beats `components/`, `hooks/`, `api/` each holding every
  feature. *Otherwise:* one feature's change is a scavenger hunt across six
  top-level directories.
- **No speculative generality.** No config flags, plugin points or generic
  parameters without a second concrete use in this ticket. *Otherwise:* you
  maintain flexibility nobody uses and reviewers cannot verify.
- **Accept dependencies, return results.** *Otherwise:* every test needs a
  live gateway, a real clock, and a database.

## Reviewer lens

- Apply the deletion test to each new module in the diff; what disappears?
- Is any dependency constructed inside the code under test rather than accepted?
- Does any file import across features, or upward from shared?

## Sources

mattpocock/skills `codebase-design` (deep modules, seams, deletion test) ·
Ousterhout, *A Philosophy of Software Design* · Feathers, *Working Effectively
with Legacy Code* (seams) · alan2207/bulletproof-react (feature folders,
`import/no-restricted-paths`).

Rationalizations, red flags and a worked example live in `reference/dev-codebase-design.md` — opened when needed, never loaded by default.
