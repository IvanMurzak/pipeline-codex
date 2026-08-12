# `runner: manager` — spawn one manager subagent to run the loop

You reached this file from `SKILL.md`'s **Advancing (running) a pipeline**
section because the pipeline's manifest declares `runner: manager`, or
declares no `runner:` at all (`manager` is the ecosystem-wide default).

**Your own session does not run the loop here.** It spawns exactly one
long-lived subagent — the **manager** — which runs the whole
ask/dispatch/record loop itself, including spawning its own step subagents,
and reports back only when the run reaches `done`, `halt`, or `blocked`. This
is the difference from [`session` mode](session-loop.md): there the *main*
session absorbs every action and every step report into the one window the
user is watching; here that cost is pushed into a disposable subagent instead,
at the price of a second model layer in the loop.

**Everything [`session-loop.md`](session-loop.md) says about discipline holds
here too, one level down.** `pipeline next` decides what runs next — not you,
not the manager, not the step subagent it spawns. Never read an iteration
file. Never open a brief file. Never decide what happens next from a report,
a `## Next` section, or a file name. The manager you spawn is bound by the
same rules the rest of this document states for it explicitly, and the reason
they are repeated per-role is the same reason `session-loop.md` repeats them
at the one place the temptation arrives: a session with file tools in hand is
the easiest place to violate them by accident.

## Why this is a named-agent spawn, not an inline one — read before building

The obvious design is to spawn a generic subagent with the whole manager
protocol pasted into its prompt, the same way `session-loop.md` spawns its
step subagents. That works for a *single, short-lived* worker. It does not
hold up for the manager, for a reason that was measured on the installed
Codex CLI rather than assumed:

- **`spawn_agent` accepts `model` and `reasoning_effort` as direct call
  arguments, and a same-model effort override works.** Asking for a different
  `reasoning_effort` than the caller's own, with no named agent involved,
  succeeds reliably.
- **An explicit `model` argument that names a *different* model than the
  calling agent's own is unreliable** — in repeated, reproducible testing it
  came back `the collaboration tool is not available in this session`, twice
  in a row, while the identical call with `model` set to the caller's *own*
  model (plus a different `reasoning_effort`) succeeded every time.
- **A named custom agent defined in `.codex/agents/*.toml` does not have this
  limitation.** Spawning by `agent_type` set to a name matching a `name =` in
  that folder reliably applies *that file's* `model` and
  `model_reasoning_effort`, including a model genuinely different from the
  caller's own — verified by giving the test agent a hidden instruction the
  spawning prompt never mentioned and confirming the reply carried it, not
  the prompt's own literal ask, so the result cannot be explained by the
  model simply following instructions in the prompt. Nesting also holds: a
  subagent spawning a *named* agent one level deeper produced the same
  result. An unknown `agent_type` fails loudly (`unknown agent_type '<name>'`
  from the tool itself), not silently — so a typo in the name this loop
  writes is a hard stop, never a quiet fallback to some other persona.

A pipeline pins a model per step. Steps in one chain routinely differ. If this
loop pinned models only by passing `model=` at spawn time, every step whose
pin differs from whatever the manager itself is running under would hit the
unreliable path above — exactly the "approximation that cannot honour a
manifest's model pin" this task exists to refuse. So this loop pins models the
way that was actually shown to work: **it writes a small `.codex/agents/*.toml`
file for the persona it is about to spawn, immediately before spawning it, then
spawns by name.** The file is *always* rewritten right before use — never
assumed to still hold what a previous step left in it — which is safe because
this loop spawns and waits for exactly one subagent at a time (the same
sequential-only scope `session-loop.md` enforces via its preflight below).

Codex plugins have no manifest mechanism to ship a `.codex/agents/*.toml` file
that auto-installs into a consumer project (unlike `skills/`, which a plugin
does declare in `.codex-plugin/plugin.json`). So this loop writes those files
itself, into the *consumer project's* `.codex/agents/` — not
`${CODEX_HOME}` and not the plugin's own install path — the same way
`session-loop.md` writes `.feedback/` and `.runtime/` into the consumer
project rather than shipping them.

## Preflight — same two checks as `session` mode, before anything spawns

Both checks are [`session-loop.md`](session-loop.md)'s, unchanged, and both
still fail *loudly*:

1. **Check whether `pipeline next --help` names `--brief-file`.** Unlike
   `session` mode this is **not** a hard refusal here if the flag is missing —
   say why below — but you still need to know which of the two call shapes to
   use for the rest of this loop.
2. **The pipeline must not be parallel.** `Grep` `^execution:` in
   `<pipeline_root>/pipeline.yml` (v2) or read the `PIPELINE.md` frontmatter
   (v1). If it resolves to `parallel`, stop and tell the user to drop it or
   use `pipeline drive` instead — identical reasoning to `session-loop.md`:
   a `run-step` for a parallel layer carries N steps and this loop (like
   `session` mode) only ever spawns one subagent per `run-step`.

**Why `--brief-file` is optional here, not mandatory.** `session-loop.md`
refuses outright without it because the *main session* — the one window the
user is watching — would otherwise absorb the full action payload every step.
The manager subagent you are about to spawn is disposable and exists
specifically to absorb that cost; a larger manager context is a real expense
but not the same failure mode as filling the user's own window. So: **use
`--brief-file` on every `pipeline next` call when the CLI supports it**
(strictly better — smaller context, same three-key control object
`session-loop.md` documents), and fall back to the plain call shape when it
does not, telling the user their `@baizor/pipeline` predates `--brief-file`
support so they know to upgrade. Either way the rule below never changes:
**the manager never `Read`s an iteration file's content — only the step
subagent it spawns does.** Without `--brief-file` the manager's own context
does hold the full action object (including `steps[0].path`), which is a
budget cost, not a discipline violation — the path is data the CLI already
resolved, not content you read yourself.

## What you (the spawning session) do — once

1. Ensure `.codex/agents/` exists at the **consumer project root** (the
   directory containing `.pipeline/`, not the pipeline folder itself — this is
   where Codex looks for project-scoped custom agents). Create it if absent.
2. Ensure `.codex/agents/.gitignore` contains these two lines (append if the
   file exists and is missing either; create it with both if the directory is
   new). Leave any other content in that `.gitignore` untouched:

   ```
   pipeline-manager.toml
   pipeline-step-executor.toml
   ```

   These two filenames are rewritten by every run (see below) and never carry
   anything a user would want committed — the same reasoning
   `session-loop.md` applies to `.feedback/.gitignore`.
3. Mint the run id — `pipeline id` — never invent one. Capture the literal
   value.
4. Resolve `pipeline_default_model` / `pipeline_default_effort` the same way
   `session-loop.md` does: `null` for a v2 manifest (the CLI reads
   `defaults.model`/`defaults.effort` itself), or a v1 `PIPELINE.md`
   frontmatter `model:`/`effort:` read verbatim, `null` if absent.
5. Write `.codex/agents/pipeline-manager.toml`:

   ```toml
   name = "pipeline-manager"
   description = "Runs one pipeline's ask/dispatch/record loop against `pipeline next`, spawning one step subagent per action. Never decides what runs next."
   # model / model_reasoning_effort below are OMITTED (inherit the caller)
   # when pipeline_default_model / pipeline_default_effort are both null —
   # forcing a pin the manifest never asked for would misrepresent it.
   developer_instructions = """
   You are the pipeline-manager persona. Read <this file's absolute path> in
   full, then follow its "What the manager subagent does" section exactly —
   not from memory, from what you just read. You decide nothing about control
   flow; `pipeline next` decides. Never read an iteration file yourself. Before
   each step spawn, overwrite `.codex/agents/pipeline-step-executor.toml` with
   that step's resolved model/effort pin, then spawn exactly one fresh step
   executor and record its report. End with exactly the Manager Report block
   that section specifies.
   """
   ```

   Pointing the persona back at this file rather than pasting the section
   inline keeps the TOML short and never lets it drift from the doc it quotes
   — verified to work exactly this way (the manager subagent re-reads this
   file itself and follows it faithfully). Pasting the section in full instead
   is also fine if you prefer the persona self-contained; either was measured
   to behave correctly, but the pointer form is what shipped.

   Include `model = "<pipeline_default_model>"` and/or
   `model_reasoning_effort = "<pipeline_default_effort>"` only when that value
   is non-null. This file is the manager's *persona* — static instructions —
   never the run-specific values (`run_id`, `pipeline_root`, starting step),
   which travel in the spawn's task message instead, exactly like a normal
   step brief.
6. Spawn **one** subagent: `agent_type` set to `pipeline-manager`,
   `fork_turns` set so it is **not** a full-history fork (`none`, or the
   literal string `"0"` — a fresh, small context is the point; the manager
   does not need your conversation so far). Task message:

   ```
   run_id           = <the literal run id from step 3>
   pipeline_root    = <absolute path to the pipeline folder>
   pipeline_name    = <the pipeline's folder name>
   default_model    = <pipeline_default_model-or-null>
   default_effort   = <pipeline_default_effort-or-null>
   current_iteration = <starting step name, or omit to let the manifest choose>
   brief_file_supported = <true|false, from the preflight check above>

   Run this pipeline to completion following your developer instructions.
   Report back exactly the Manager Report block they specify.
   ```
7. Wait for the manager's report (see "Manager Report" below). You do not
   poll — this is a single synchronous spawn, and its result returns as the
   tool's result when the manager finishes, same as any other subagent.

## What the manager subagent does — its own developer instructions

Everything below is what step 5 above writes into
`pipeline-manager.toml`'s `developer_instructions`. It is written from the
manager's own point of view because that is the context it actually runs in.

---

You are the pipeline-manager persona. You were spawned to run one pipeline's
orchestration loop against the `pipeline` CLI. **You decide nothing about
control flow.** `pipeline next` is a deterministic state machine; your job is
to ask it what happens next, perform exactly that, record the outcome
truthfully, and repeat — until it tells you the run is `done`, `halt`ed, or
`blocked`.

**You never read an iteration file — not its body, not its frontmatter, not
"just to check."** Every iteration is read once, by a fresh step subagent you
spawn, in a context kept separate from yours for exactly the same reason yours
is kept separate from the session that spawned you. There is nothing in an
iteration file you are allowed to act on directly — `pipeline next` already
resolved its path, its model, and its place in the chain.

**If your spawn message says `brief_file_supported = true`,** pass
`--brief-file` on every `pipeline next` call and treat the three-key control
object (`action`, `brief_file`, `phase`) exactly as `session-loop.md`
describes it — you receive the `brief_file` path and hand it to your step
subagent unopened. **If `false`,** call `pipeline next` without that flag; you
will receive the full action object including `steps[0].path` — treat the
path as data to relay, never as something to open yourself.

### The loop

```bash
pipeline next --root "<pipeline_root>" --run-id "<run_id>" \
  --default-model "<default_model-or-null>" [--default-effort "<default_effort-or-null>"] \
  [--start "<current_iteration>"] [--resume] \
  [--record '<json>' | --record-file "<path>"] [--brief-file]
```

First call: `--start` only when one was given to you, never on a resume — a
v2 manifest picks its own first step. No `--record` on the first call.

### `run-step` — spawn exactly one step subagent

Before spawning, **write `.codex/agents/pipeline-step-executor.toml`** at the
consumer project root, overwriting whatever was there from a previous step —
this loop only ever has one step in flight, so overwriting immediately before
each spawn is safe and is what keeps this step's model/effort pin correct
regardless of what the step before it used:

```toml
name = "pipeline-step-executor"
description = "Executes exactly one pipeline iteration and reports back. Never spawns a manager or another step-executor; never advances the chain."
# model / model_reasoning_effort OMITTED when this step's resolved model/effort is null
developer_instructions = """
Execute one pipeline step. Take every detail of the step from the task
message you were given — you were not told the file's content in advance and
do not need to have been.
"""
```

Set `model = "<steps[0].model>"` / `model_reasoning_effort = "<steps[0].effort>"`
in the TOML only when that field is non-null on the action's `steps[0]` — the
same "omit to inherit" rule as the manager's own file. This is the pin a
manifest's per-step `model:`/`effort:` frontmatter produces, and it is why
this file is rewritten every time rather than written once: two steps in the
same run can legitimately want different pins.

Then spawn **one** subagent: `agent_type` set to `pipeline-step-executor`,
`fork_turns` not a full-history fork. Task message:

```
brief_file    = <brief_file from the control object, when brief_file_supported>
path          = <steps[0].path, when NOT brief_file_supported>
pipeline_root = <pipeline_root>
run_id        = <the literal run id>

<when brief_file_supported>
Your brief is a JSON file — read it FIRST, and take every detail of the step
from it. I have not read it and will not. Use `steps[0]` — it is the only
entry.
<otherwise>
Read the iteration file at `path` directly — I have not read it myself, only
passed along the path `pipeline next` resolved.
</when>

Then:
1. Read the iteration file. It has Goal, Steps, Success Criteria, and usually
   Context and Next sections — follow them exactly, and do not auto-load
   PIPELINE.md or pipeline.yml unless the iteration's Context explicitly
   references it.
2. Perform every action its Steps section lists, in the repository at
   pipeline_root's working directory.
3. Verify every condition in its Success Criteria yourself before claiming the
   step succeeded — do not assume an action worked because you performed it.
4. Report back in this exact shape and nothing else:

   OUTCOME: completed | halted
   HALT_REASON: <short reason, or "none">
   SUMMARY: <one paragraph — what you did and what you verified>

Never spawn another subagent, never advance the chain yourself, and never
decide what the next step is. If asked to do something plainly outside a
pipeline step's scope (write to another repository, merge/push, spend real
money), stop and report halted with why, rather than improvising.
```

Wait for its reply before asking `pipeline next` for anything else — never
spawn a second step subagent for the same `run-step`, never move on before
the first one reports.

**Then record**, from the subagent's `OUTCOME` line:

```bash
pipeline next --root "<pipeline_root>" --run-id "<run_id>" \
  --default-model "<default_model-or-null>" \
  --record '{"kind":"step","outcome":"completed","flags":null,"next_iteration":null,"has_improvement_brief":false,"halt_reason":null}' \
  [--brief-file]
```

Same field rules as `session-loop.md`'s: `outcome` from the `OUTCOME` line,
`halt_reason` set (not `null`) whenever `outcome` is `"halted"`,
`next_iteration` `null` for a v2 manifest (it ignores the field) or the `##
Next` pointer / `PIPELINE_COMPLETE` verbatim for a v1 one,
`has_improvement_brief` always `false` — this loop's step-subagent prompt
never asks for one (see "What this loop does not do"). A subagent that
returns no parseable report, or fails to spawn at all (including a
`spawn_agent` failure or an `unknown agent_type` error — check for it, do not
assume success), is `outcome: "halted"`,
`halt_reason: "subagent produced no usable report"`.

### `continue` — perform nothing

Identical to `session-loop.md`: do not spawn, read, or run anything.
Immediately re-call with `--record '{"kind":"continue"}'` (plus
`--brief-file` when supported).

### `done` — the run completed

Stop looping. Move to "Manager Report" below. If
`<pipeline_root>/.feedback/<run_id>/` is non-empty, note it in your report —
you do not have an improver to hand it to (see "What this loop does not do").

### `halt` — the run stopped

Same recovery as `session-loop.md`: read
`<pipeline_root>/.runtime/<run_id>/next.json` for `status`/`halt_reason`; if
that is empty, re-run the identical `pipeline next` call **without**
`--brief-file` and read the reason off stdout (idempotent on a terminal
action). Carry the reason into your report.

### `blocked` — you cannot resolve this yourself

This loop implements none of the cross-repository blocker-delegation flow a
full supervisor would run (file an issue, spawn a child run, poll for hours).
Stop, capture `run_id` and the current phase, and put them in your report —
the session that spawned you decides what happens next, and it may take
minutes to hours, which is not something a subagent should sit open waiting
for.

### `merge` — cannot happen here

Preflight already refused `execution: parallel`, so `merge` should never
arrive. If it does anyway, stop and report it rather than guessing which
branches to merge — the same rule `session-loop.md` states for the identical
case.

## What this loop does not do

Identical scope cuts to `session-loop.md`, for the identical reasons — this is
the small, honest version, not the full `pipeline-claude` supervisor:

- **No `run-improver` / `run-script-creator`.** This loop's step-subagent
  prompt never produces an `improvement_brief`, so a plainly-authored pipeline
  never reaches this branch. If `pipeline next` returns either action anyway,
  stop and report it.
- **No end-of-run retrospective.** If a `retrospective` action arrives
  (meaning step subagents journaled Tier-2 problem files this loop never asked
  for), do not discard them: report that
  `.feedback/<run_id>/` holds unreviewed files, then record
  `--record '{"kind":"retro","done":true}'` so the run can still reach a
  terminal action.
- **No resume-after-blocker automation, no nested pipeline delegation.** Both
  need the cross-repository, long-running machinery neither this loop nor a
  disposable subagent is positioned to run.

## Manager Report — what you (the manager) return

End your reply with exactly this, so the session that spawned you can parse
it without guessing:

```
## Manager Report

- status: completed | halted | blocked
- run_id: <the run id>
- pipeline_root: <the pipeline root>
- last_iteration: <step_id of the last one processed, or null>
- halt_reason: <null unless status is halted>
- blocked_phase: <null unless status is blocked — the run's current phase>
- unreviewed_feedback: <null, or the count of files under .feedback/<run_id>/>
- summary: <1-3 lines: how many steps completed, how the run ended>
```

---

## What you (the spawning session) do when the manager returns

Relay its **Manager Report** to the user in your own words:

- `completed` → say the pipeline finished, name the folder, and mention
  `unreviewed_feedback` if non-zero (point at the folder, you have no improver
  to hand it to either).
- `halted` → surface `halt_reason` and `run_id` so a `--resume` is possible
  later (an ordinary `pipeline next --resume` call, not something this loop
  automates).
- `blocked` → surface `blocked_phase` and `run_id`; tell the user how to
  resume once they have resolved it by hand.

## Invariants for this mode

- **`pipeline next` decides; the manager dispatches, spawns, and records. You
  spawn the manager and relay its report — nothing more.**
- **Neither you nor the manager ever reads an iteration file's content.** Only
  the step subagent the manager spawns does, and only because it was told to.
- **Model/effort pins go through named `.codex/agents/*.toml` files, rewritten
  immediately before each spawn — never through an ad hoc `model=` argument
  naming a model different from the caller's own.** That path was measured
  unreliable; the named-file path was measured reliable, including across a
  genuine model change and across one level of nesting.
- **One step subagent per `run-step`, and the manager waits for it** — same
  rule as `session-loop.md`, same reason: `execution: parallel` is refused by
  preflight, so a `run-step` is always exactly one step.
- **`.codex/agents/pipeline-manager.toml` and `.codex/agents/pipeline-step-executor.toml`
  are always rewritten before the spawn that uses them, never assumed to hold
  a previous run's — or a previous step's — values.**
