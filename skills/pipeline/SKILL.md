---
name: pipeline
description: Use when designing or advancing a file-based multi-step pipeline in a repository.
---

# Pipeline

Treat `.pipeline/<name>/PIPELINE.md` (or its v2 `pipeline.yml`) and its ordered
step files as the source of truth — never the conversation, never what a
previous run remembers. Inspect the repository before changing a pipeline,
preserve completed-step evidence, and advance one explicit next step at a time.
No skipping ahead, no batching several steps into one edit.

If the `pipeline` CLI (`bun add -g @baizor/pipeline`) is not installed, say
which runtime is missing and stop — never invent command output you did not
get, whether designing or advancing.

## Designing a pipeline

Prepare or extend `.pipeline/<name>/PIPELINE.md` and its ordered `steps/*.md`
files (or the equivalent `pipeline.yml`) directly. Keep every step
self-contained — a step is read once, in a fresh context, so anything it does
not say is not known when it runs. When the CLI is available, `pipeline plan`
validates a manifest without running it.

## Advancing (running) a pipeline

**`pipeline next` decides what runs next, in every mode — you never do.** It is
a deterministic state machine; the model's job is to call it, act on what it
says, and record the outcome. The mode a pipeline runs under is its own
choice, declared as the top-level `runner:` key in `pipeline.yml` (or the
`runner:` frontmatter key in a v1 `PIPELINE.md`) — never inferred from chain
length or guessed.

There are exactly four mode names. Codex supports two of them today:

| `runner:` | Codex support |
| --- | --- |
| `driver` | **Yes — and no plugin code is needed.** `pipeline drive …` is a self-contained headless loop with no model in the orchestration; a bare terminal runs it exactly as well as Codex does. Shell it out (or tell the user the command) when asked to run a pipeline this way. |
| `session` | **Yes — this is what the rest of this skill implements.** The Codex session calls `pipeline next` itself, spawns a subagent per step, and drives the chain to completion. Follow [`references/session-loop.md`](references/session-loop.md) exactly — it has two preflight refusals and a rule about what you must never read, and both are load-bearing. |
| `manager` (the **default** when `runner:` is absent) | **Not implemented by this plugin.** Say so plainly. Offer `session` if the user wants Codex to drive the run now, or `driver` for a headless run — never silently substitute one without saying which mode the manifest actually named. |
| `standalone` | **Never, by design.** It means executing steps through a second provider's Agent SDK, which is an explicit non-goal for a Codex plugin. Point the user at the pipeline's own hosted/runner path instead of attempting it here. |

If the manifest names `session`, or the user asks Codex to advance/run a
pipeline directly and no other mode was requested, read
[`references/session-loop.md`](references/session-loop.md) before doing
anything else — it is a procedure, not background reading.
