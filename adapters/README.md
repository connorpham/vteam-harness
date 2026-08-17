# Adapters — one module per agent tool

An adapter is the ONLY tool-specific code in vteam: a thin renderer that turns
the tool-neutral workflows in `core/workflows/` into the format one agent tool
natively discovers. Everything else (gates, providers, doctrine, templates) is
shared verbatim across tools via `.vteam/` in the target repo.

## Contract

Each `<tool>.mjs` exports:

```js
export const id = "<tool>";          // the name used in `vteam init --tools`
export const marker = "<path>";      // file whose presence means "installed" (vteam update re-renders)
export function render(wf, ctx) {    // one workflow → one file
  // wf:  { name, description, args, body }   (body already config-substituted,
  //       and prefixed with the resolved model-routing block unless wf.name === "guidelines")
  // ctx: { root, cfg, noSubagentNote }       (the note explains how tools without
  //       subagent spawning run reviewer/challenger passes — fresh chat per pass)
  return { path: "<repo-relative output path>", text: "<file content>" };
}
export function pointers(root) { ... } // optional post-step: discovery pointers
                                       // (e.g. an AGENTS.md section); returns [changed paths]
```

Rules:

- **Render, never rewrite.** Adapters may add frontmatter, a preamble, and
  discovery pointers — they never edit workflow semantics. A gate or rule that
  needs tool-specific behavior belongs in core with a capability switch, not in
  an adapter fork.
- **Tools without subagents** must prepend `ctx.noSubagentNote` so
  reviewer/challenger passes run sequentially in fresh contexts with the same
  card requirements.
- **Model routing**: the resolved tier→model table for the tool is already in
  `wf.body` (rendered by `model_route.py --table --tool <id>`); adapters whose
  tool has no configured models will show its SET-ME banner rather than guess.

## Adding a tool

1. Copy the closest existing module, set `id`, `marker`, output paths.
2. Add the id to `TOOLS` in `src/cli/adapters.mjs` and to the tools map in
   `model-routing.data.yaml` (real model names, or SET-ME until known).
3. Prove it: `vteam init --tools <id>` into a scratch repo — every workflow
   renders, the routing block shows, `guidelines` stays clean.
