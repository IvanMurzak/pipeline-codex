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

There are exactly four mode names. Codex supports three of them today:

| `runner:` | Codex support |
| --- | --- |
| `driver` | **Yes — and no plugin code is needed.** `pipeline drive …` is a self-contained headless loop with no model in the orchestration; a bare terminal runs it exactly as well as Codex does. Shell it out (or tell the user the command) when asked to run a pipeline this way. |
| `session` | **Yes.** The Codex session calls `pipeline next` itself, spawns a subagent per step, and drives the chain to completion. Follow [`references/session-loop.md`](references/session-loop.md) exactly — it has two preflight refusals and a rule about what you must never read, and both are load-bearing. |
| `manager` (the **default** when `runner:` is absent) | **Yes.** The session spawns one long-lived **manager** subagent — a *named* custom agent (`.codex/agents/pipeline-manager.toml`, written by this loop) — which runs the whole loop itself, spawning its own per-step subagent the same way. This exists so a long chain does not fill the window the user is watching. Follow [`references/manager-loop.md`](references/manager-loop.md) — it explains, with measured evidence, why model/effort pins go through named agent files rather than plain spawn arguments, which is load-bearing for honouring a manifest's per-step model pin. |
| `standalone` | **Never, by design.** It means executing steps through a second provider's Agent SDK, which is an explicit non-goal for a Codex plugin. Point the user at the pipeline's own hosted/runner path instead of attempting it here. |

If the manifest names `session`, read
[`references/session-loop.md`](references/session-loop.md) before doing
anything else — it is a procedure, not background reading. If it names
`manager`, or names nothing at all (`manager` is the ecosystem default), read
[`references/manager-loop.md`](references/manager-loop.md) instead, under the
same rule.
