# Launch drafts — the campaign's one home

Every file here is a **draft the owner posts**, never an agent. This index records
which channels are open, which are gated, and the date each gate opens — so the
sequence is decided by arithmetic instead of enthusiasm.

Status as of **2026-08-18**: repo first commit on `main` 2026-08-17, 2 stars,
`vteam-harness@0.3.0` live on npm, CI green.

## Channel gates

| Channel | Gate | Status | Act |
|---|---|---|---|
| [Anthropic plugin directory](plugin-directory-submission.md) | none (public repo + `validate` + manifest quality) | **open** — pre-flight verified green | **now** |
| [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) (skills section) | ≥10 stars | 2/10 | at 10 stars |
| [awesome-claude-code](awesome-claude-code-submission.md) | ≥14 days old **or** ≥100 stars | attempt 1 auto-closed 2026-08-18 | **on/after 2026-08-31** |
| [HN essay](hn-essay-outline.md) · [Reddit](reddit-post.md) · [X thread](x-thread.md) | none, but they spend attention once | held | after the demo GIF exists |

The two directory gates are why the original week-1 plan needed re-sequencing: one
list rejects on arithmetic, the other does not care. Submit where the door is open,
and let the closed door open on its own schedule.

## What the awesome-claude-code rejection actually taught

The bot closed issue #2560 without a human reading it, because the repo was one
day old with two stars — a ground-rule miss, not a quality verdict. Two lessons,
both cheap:

1. **Read the eligibility rule before writing the submission, not after.** The
   draft already carried the rule; the submission went out anyway. Cost: a
   closed issue and a two-week wait that had to happen regardless.
2. **A rejected submission is a formatting review you got for free.** The
   description was five lines and read as a pitch; the guidelines demand one
   factual line. That is fixed in the draft now, so the 2026-08-31 attempt is
   strictly better than the one that failed.

## Sequence

1. **Now** — submit the plugin directory (ungated, pre-flight green). Record a
   30-second demo GIF: the live funnel `audit 0/F → init → doctor GREEN →
   audit 91/A` in a clean repo, which is the whole product thesis in four
   commands and needs no narration.
2. **When the GIF exists** — X thread, then the Reddit evidence story. Both lead
   with the artifact, not the announcement.
3. **~2026-08-31** — resubmit awesome-claude-code (arithmetic satisfied), and
   publish the HN essay once the repo has something a visitor can react to
   beyond a README.
4. **Continuously** — keep the release cadence visible (~2 weeks). The competitor
   research flagged the counter-example: a peer tool lost ~72% of its downloads
   in the eight months after its releases stopped.

## Honest note on one channel

`awesome-claude-skills` accepts *resources* (articles) with no star gate, and
[docs/COMPARISON.md](../COMPARISON.md) would technically fit the format. Do not
submit it there: the list rejects content that exists to promote a tool, and a
comparison whose conclusion favors its own author is exactly that, however fair
its numbers. Submit vteam to the **skills** section when it reaches 10 stars, and
let the comparison earn its readers from the repo and the essay.
