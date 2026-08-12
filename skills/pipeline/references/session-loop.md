# `runner: session` — the Codex session drives the loop itself

You reached this file from `SKILL.md`'s **Advancing (running) a pipeline**
section because the pipeline's manifest declares `runner: session`, or because
you were asked to advance/run a pipeline and no other mode applies. In this
mode **your session** — not a separate orchestrator — calls `pipeline next`
itself and spawns one subagent per action. There is no `pipeline-manager`
equivalent in this plugin; `manager` is a different, unimplemented mode (see
`SKILL.md`'s table).

**`pipeline next` decides what runs next, in every mode — this holds exactly as
hard here as anywhere else.** You ask, you dispatch, you record, you repeat.
You never compute the next step, never route around what the CLI returned, and
never decide whether a step succeeded well enough to skip a later one. A
session with file tools in hand — which is exactly what Codex gives you — is
the easiest place to violate this by accident, which is why it is repeated at
the one place below where the temptation actually arrives.

## Choose this only for a short chain

Say this to the user in your own words if they ask why the run feels heavy; do
not oversell the mode.

- **The cost is your context, and the user's.** Every action plus every
  subagent report lands in the one window the user is watching. A long chain
  will fill it.
- **There is no `manager` fallback here today.** In the Claude plugin this mode
  trades context for `manager`, which absorbs the loop into a subagent and
  keeps the main session clean. This plugin does not implement `manager` (see
  `SKILL.md`), so for a genuinely long chain the honest alternative is
  `driver` — `pipeline drive …`, which runs with no model in the loop at all —
  not "run it here and hope the context holds."
- **`execution: parallel` is not supported here.** Preflight refuses it below.
- What you gain: fewest moving parts, and the user watches every step happen
  in front of them.

## Preflight — two checks, before the first `pipeline next`

Both are cheap, and both fail *loudly*. A wrong answer here is not a degraded
run, it is a run that looks fine and is not.

1. **The CLI must support `--brief-file`.** Run `pipeline next --help` and
   confirm the usage text names `--brief-file`. An older CLI **ignores unknown
   flags silently**, prints the full action instead of the three-key control
   object, and your spawn would hand the subagent an absent `brief_file`.
   **A matching version number is not proof by itself** — a local build can be
   ahead of what was last published under the same version string, so check
   the actual `--help` text, not `pipeline --version`. If the flag is missing,
   stop, tell the user their `@baizor/pipeline` is too old for `runner:
   session` (`bun add -g @baizor/pipeline` to update), and offer `pipeline
   drive` as the alternative that needs no plugin support at all. Do not
   attempt the loop without the flag — see "What you get back" below for why.

2. **The pipeline must not be parallel.** `Grep` `^execution:` in
   `<pipeline_root>/pipeline.yml` (v2) or read the `PIPELINE.md` frontmatter
   (v1). If it resolves to `parallel`, stop: a parallel layer's `run-step`
   carries N steps and a `merge` action carries a branch list, and **both
   payloads live in the brief file you are not allowed to open** — you would
   silently spawn one subagent for a layer of three. Tell the user to drop
   `execution: parallel` or run this pipeline through `pipeline drive`
   instead. Do not guess, and do not fall back silently.

This second check is load-bearing for everything below: it is *why* a
`run-step` here is always exactly one step, and why `merge` can never arrive.

## Run-start setup (once, before the loop)

One shell call, before the first `pipeline next`:

```bash
mkdir -p "<pipeline_root>/.feedback/<run_id>" "<pipeline_root>/.runtime/<run_id>/records"
```

Leave an existing `.feedback/.gitignore` stub alone if one exists; if the
folder is new, `printf '*\n' > "<pipeline_root>/.feedback/.gitignore"` so a
later `git add -A` in the consumer project cannot sweep run state into a
commit. This tree lives inside the consumer project, never under the plugin
install path.

**Mint the run id from the CLI — never invent one or generate a UUID
yourself:**

```bash
pipeline id
```

Capture the literal value it prints and pass it as `--run-id` on every call
below.

## The loop

Every call, first and last, carries `--brief-file`:

```bash
pipeline next --root "<pipeline_root>" --run-id "<run_id>" \
  --default-model "<pipeline_default_model-or-null>" \
  [--default-effort "<level-or-null>"] [--start "<step-name>"] [--resume] \
  [--record '<json>' | --record-file "<path>"] --brief-file
```

First call: pass `--start` only when the user named a starting step, not on
every run — a `pipeline.yml` manifest decides its own first step, and passing
none lets it. No `--record` on the first call. **`--default-model`:** for a v2
manifest, pass `null` and let the CLI read the manifest's own `defaults.model`;
for a v1 `PIPELINE.md`, `Read` only its frontmatter (the same handful of lines
this rule always means, never the body) for a `model:` field and pass it
through verbatim, or `null` if absent.

### What you get back — and it is all you get

```json
{ "action": "run-step", "brief_file": "…/briefs/07.json", "phase": "await-step" }
```

Exactly three keys. **You dispatch on `action`. The `brief_file` is addressed
to the subagent you spawn, not to you — you pass the path along and never open
it.** That is the whole point of the flag: the full action payload stays on
disk instead of in the window the user is watching. If a call ever returns
more than these three keys, the preflight check above was skipped or the CLI
is older than it claimed — stop and re-run the preflight.

`phase` is the state the run is parked in (`await-step`, `await-retro`,
`blocked`, `terminal`, …). Use it to sanity-check your own bookkeeping; never
to decide.

### `run-step` — spawn exactly one subagent

> **Read this before every spawn — it is the rule this mode exists to test.**
> You have `Read`, and Codex has file tools generally available to it.
> Therefore, in this mode and at this exact step:
>
> - **Never read an iteration file. Not its body, not its frontmatter, not
>   "just to check" the path is right.** Every iteration is read once, by a
>   fresh subagent, in a context you are trying to keep out of this one. There
>   is nothing you could learn from it that you are allowed to act on — the
>   CLI already resolved the path, the model and the routing.
> - **Never open the brief file.** It is the subagent's input, not yours.
>   Opening it puts back exactly the block `--brief-file` just took out, and
>   reading `steps[0]` to "check" the step is how a session starts deciding.
> - **Never decide what runs next.** Not from a report, not from a `## Next`
>   section, not from a file name. You record what happened; `pipeline next`
>   routes.
>
> The temptations are specific and they will arrive. A report names an
> iteration file — you still do not open it. A step halts and you want to
> explain why — the halt reason comes from the report, not from the step's
> source. The user asks what the next step does — say it will land in the
> context this mode is conserving, and let them ask for it deliberately, after
> the run.

Spawn **one fresh subagent** to execute the step and wait for its result
before asking for the next action — never spawn more than one for a single
`run-step`, and never move on before it reports back. Use whatever your
environment calls that primitive; in Codex today that is `spawn_agent` with a
**generic `agent_type`** (`default` or `worker`, not a named one). **Do not
target a named custom agent.** This plugin ships no `.codex/agents/*.toml`,
and even a self-authored one would not help: invoking a *named* custom agent
from a tool-backed session is unreliable today — the tool surface takes an
`agent_type` plus prompt/model overrides, with no parameter that names a
repo-local agent. Everything the subagent needs to behave correctly therefore
has to be in the prompt you send it, not in a referenced agent file.

**If your environment exposes no subagent-spawning tool at all** (a bare
scripted invocation with no delegation capability), this mode cannot honor the
never-open-the-brief-file rule — there is nothing else to hand it to. Stop and
tell the user to run this pipeline with `pipeline drive` instead, which needs
no session participation.

Prompt shape:

```
Execute one pipeline step. Your brief is a JSON file — read it FIRST, and take
every detail of the step from it. I have not read it and will not.

brief_file    = <brief_file from the control object>
pipeline_root = <pipeline_root>
run_id        = <the literal run id>

The brief is one `pipeline next` action object. Use `steps[0]` — it is the
only entry; a parallel layer was already refused before this run started, so
this run is always sequential. `path` is the iteration file to execute; a
`.runtime/…/rendered/…` path is CORRECT and authoritative — never "fix" it
back to a source file.

Then:
1. Read the iteration file at `path`. It has Goal, Steps, Success Criteria,
   and usually Context and Next sections — follow them exactly, and do not
   auto-load PIPELINE.md or pipeline.yml unless the iteration's Context
   explicitly references it.
2. Perform every action its Steps section lists, in the repository at
   pipeline_root's working directory.
3. Verify every condition in its Success Criteria yourself before claiming the
   step succeeded — do not assume an action worked because you performed it.
4. Report back in this exact shape and nothing else:

   OUTCOME: completed | halted
   HALT_REASON: <short reason, or "none">
   SUMMARY: <one paragraph — what you did and what you verified>

Never spawn another subagent, never advance the chain yourself, and never
decide what the next step is — that is not your job here. If the iteration
asks you to do something plainly outside a pipeline step's scope (write to
another repository, merge/push, spend real money), stop and report `halted`
with why, rather than improvising.
```

**Model and effort — the honest limitation.** A step's own `model:`/`effort:`
is resolved by the CLI and lives inside the brief file you do not read, so it
cannot reach the subagent through this prompt. Whether it applies at all
depends on whether your spawn primitive accepts a per-call model/effort
override — untested here, and likely to vary by Codex host. If it does not,
say so to a user who relies on per-step models, the same honest gap the
Claude plugin documents for its own `Agent` tool.

**Then record**, from the subagent's `OUTCOME` line:

```bash
pipeline next --root "<pipeline_root>" --run-id "<run_id>" \
  --default-model "<pipeline_default_model-or-null>" \
  --record '{"kind":"step","outcome":"completed","flags":null,"next_iteration":null,"has_improvement_brief":false,"halt_reason":null}' \
  --brief-file
```

- `outcome`: `"completed"` when the subagent's `OUTCOME` line said so;
  `"halted"` otherwise, with `halt_reason` set to its `HALT_REASON` (short
  string) — never `null` on a halted outcome.
- `next_iteration`: a v2 `pipeline.yml` ignores this field and advances by its
  own step list — pass `null`. A v1 `PIPELINE.md` step may end with a `##
  Next` pointer naming the following iteration file by absolute path, or
  `PIPELINE_COMPLETE` when it is the last one — pass that value verbatim if
  present, `null` otherwise.
- `has_improvement_brief`: always `false` here. This subagent prompt does not
  ask for one — see "What this loop does not do" below for why, and what
  happens if `pipeline next` asks for one anyway.
- A subagent that returns no parseable report, or fails to spawn at all, is
  `outcome: "halted"`, `halt_reason: "subagent produced no usable report"`.
  Do not loop again as though work happened.

### `continue` — perform nothing

The CLI paused a chain of script steps against its own call budget. Do not
spawn, read, or run anything. Immediately re-call with
`--record '{"kind":"continue"}' --brief-file`. The explicit record is
required — a bare re-call with no record means something else to the engine.

### `done` — the run completed

Report success to the user (see "Report format" below). If
`<pipeline_root>/.feedback/<run_id>/` is non-empty, say so and point at it —
see "What this loop does not do" below for why this loop does not clear it
automatically.

### `halt` — the run stopped, and the reason is not in your hands

The reason lives in the action file you are not allowed to open. Read the
run's **cursor** instead — `<pipeline_root>/.runtime/<run_id>/next.json`, a
small orchestration-cursor file, not iteration content — and take `status` and
`halt_reason` from it. If that file is absent or carries no reason, re-run the
identical `pipeline next` command **without** `--brief-file` and read the
reason off stdout: a terminal action is idempotent (`phase: "terminal"`), so
this re-runs and re-decides nothing. Surface the reason to the user.

### `blocked` — stop and hand it to the user

A step reported an outcome this loop does not resolve on its own. This mode
does **not** implement the blocker-delegation flow the Claude plugin's
supervisor runs (filing a tracking issue in another repository, polling for
its resolution, merging it back — an hours-long, cross-repository operation
that does not belong inside a single skill). Stop the loop, report the
run's `run_id` and current phase to the user, and tell them to resume with
`pipeline next --root … --run-id … --resume --brief-file` once the blocker is
resolved by hand.

### `merge` — cannot happen, and must not be improvised

`merge` is emitted only for a parallel layer, which preflight already refused.
If one arrives anyway, **stop**: its `branches` list is in the brief file, and
guessing which branches to merge is how a run corrupts a repository. Report it
to the user — it means preflight was bypassed or the manifest changed mid-run.

## What this loop does not do

Be upfront about this rather than letting a user discover it mid-run:

- **No `run-improver` / `run-script-creator`.** The Claude plugin's session
  mode dispatches these to `pipeline-improver` and `pipeline-script-creator`,
  two named agents this plugin does not ship — building them is future work,
  not this task's scope. This loop's subagent prompt never produces an
  `improvement_brief`, which is what would trigger `run-improver` mid-run, so
  a plainly-authored pipeline never reaches this branch. **If `pipeline next`
  returns `run-improver` or `run-script-creator` anyway, stop the loop and
  report it** — do not attempt to fix a pipeline doc or write a script
  inline; that is deciding what runs next by another name.
- **No end-of-run retrospective.** `pipeline next` only returns `retrospective`
  when the run journaled at least one Tier-2 problem file under
  `.feedback/<run_id>/` — a plainly-successful run never sees this action. If
  it does arrive, there is no improver here to hand it to: **do not discard
  the journaled problems.** Report to the user that `.feedback/<run_id>/`
  holds N unreviewed problem files, then record
  `--record '{"kind":"retro","done":true}' --brief-file` so the run can reach
  its terminal action — this only marks the *retrospective step* done, not the
  problems it would have acted on.
- **No resume-after-blocker automation and no nested pipeline delegation.**
  Both require the cross-repository, long-running machinery described under
  `blocked` above.

None of this affects an ordinary pipeline that runs its steps and finishes —
those never produce an `improvement_brief`, never journal a Tier-2 problem, and
never hit `blocked`. It matters for a pipeline that does, and it is better
learned here than discovered mid-run.

## Invariants for this mode

- **`pipeline next` decides; you dispatch, spawn, and record.** Never compute
  the next step or gate an action yourself.
- **Never read an iteration file — not even its frontmatter.**
- **Never open a brief file.** The one file you may read on the loop's behalf
  is the `.runtime/<run_id>/next.json` cursor, on a `halt`.
- **One subagent per `run-step`, and you wait for it.** Never spawn more than
  one for a single action, never move on before it reports.
- **Every `pipeline next` call carries `--brief-file`.**
- **Record every action before asking for the next one.** An unrecorded action
  is a run that silently re-does or skips work.
- **Never merge, never push, never improvise a git operation a brief was
  supposed to describe.**

## Report format

When the loop exits (`done`, `halt`, or `blocked`), tell the user:

- Which step ran last, and whether the pipeline completed, halted, or is
  waiting on a blocker.
- The `run_id` and `pipeline_root`, so a `--resume` is possible later.
- On `halt`: the `halt_reason`.
- On `done`: the pipeline folder path, and whether `.feedback/<run_id>/` holds
  unreviewed problem files (see "What this loop does not do").
