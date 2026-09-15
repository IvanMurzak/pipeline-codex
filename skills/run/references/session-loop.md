# `runner: session` — the main session drives the loop itself

You reached this file from `$pipeline:run`'s **Runner selection** section because
the pipeline's manifest declares `runner: session`. In this mode the main Codex
Code session calls `pipeline next` itself and spawns one `step-executor` per
action. **There is no `pipeline-manager` in this run.**

**This file replaces steps 5.1–5.3 of `SKILL.md`'s Procedure and nothing else.**
Steps 1–4 (resolve the pipeline, banner, mint the run id, `pipeline.started`,
`write-liveness`, `register-mirror-binding`) already ran and are unchanged. So
are the **Resume Procedure**, the **Nested-Blocker Flow**, the **Supervisor
invariants**, and the **Report format** — you are still the supervisor at depth 0,
you have simply absorbed the manager's loop instead of delegating it.

**E1 holds here exactly as it holds everywhere: `pipeline next` decides what runs
next.** You ask, you perform, you record, you repeat. You never compute the next
step, route a graph, or decide whether the improver or the retrospective runs.
The difference between this mode and `manager` is *where* the loop runs — never
*what* it decides.

## Choose this only for a short chain — and know what you are trading

Say this to the user in your own words if they ask why the run feels heavy; do
not oversell the mode.

- **The cost is your context, and it is the user's context too.** Every action
  plus every step-executor report lands in the one window they are watching.
  `--brief-file` shrinks the *requests* to three keys each; it does nothing for
  the *reports* coming back, which are the larger half. **A twenty-step chain
  will fill the main session.** That accumulation is the entire reason `manager`
  exists, and `manager` remains the default (E10).
- **Prefer `manager` when** the chain is long, when the user wants the main
  session to stay clean, or when the run may need to sit through an hours-long
  blocker.
- **Prefer `manager` or `driver` when the pipeline pins per-step models or
  efforts.** In this mode a step's own `model:` / `effort:` are **not applied**
  — see "Model and effort" below. That is a real capability difference, not a
  detail.
- **`execution: parallel` is not supported here.** Preflight refuses it; use
  `manager`.
- What you gain: fewest moving parts, one fewer model layer in the loop, and the
  user watches every step happen in front of them.

## Preflight — two checks, before the first `pipeline next`

Both are cheap, and both fail *loudly*. A wrong answer here is not a degraded
run, it is a run that looks fine and is not.

1. **The CLI must support `--brief-file`.** Run
   `pipeline next --help` and
   confirm the usage text names `--brief-file`. An older CLI **ignores unknown
   flags silently**, prints the full action instead of the control object, and
   your spawn would hand the executor an absent `brief_file`. If the flag is
   missing, stop, tell the user their `@baizor/pipeline` is too old for
   `runner: session` (`bun add -g @baizor/pipeline`), and offer to run this
   pipeline through the `manager` path instead — that path is always correct and
   is what an absent `runner:` selects anyway.

2. **The pipeline must not be parallel.** `Grep` `^execution:` in
   `<pipeline_root>/pipeline.yml` (v2) or the `PIPELINE.md` frontmatter you
   already read (v1). If it resolves to `parallel`, stop: a parallel layer's
   `run-step` carries N steps and a `merge` action carries a branch list, and
   **both payloads live in the brief file you are not allowed to open** — you
   would silently spawn one executor for a layer of three. Tell the user to
   either set `runner: manager` or drop `execution: parallel`. Do not guess, and
   do not fall back silently: a mode the manifest did not declare is a mode the
   author did not choose.

This second check is load-bearing for everything below: it is *why* a `run-step`
here is always exactly one step, and why `merge` can never arrive.

## Run-start setup (once, before the loop)

The manager normally does this; in this mode it is yours. One Bash call:

```bash
mkdir -p "<pipeline_root>/.feedback/<run_id>" "<pipeline_root>/.runtime/<run_id>/records" \
  && printf '*\n' > "<pipeline_root>/.feedback/.gitignore"
```

Leave an existing `.gitignore` stub alone. This tree lives inside the consumer
project, never under `${CODEX_PLUGIN_ROOT}`.

**`isolation: external` runs:** skip this — the CLI scaffolds the folders inside
the worktree it provisions, and every action carries `worktree_pipeline_root`.
You never see that field (it is in the brief), so you do not thread it anywhere:
each subagent reads it from its own brief. Keep passing the MAIN `pipeline_root`
as `--root` on every `pipeline next` call.

## The loop

Every call, first and last, carries `--brief-file` and the maximum Bash
`timeout: 600000` — `type: script` steps execute *inside* the call.

```bash
pipeline next \
  --root "<pipeline_root>" --run-id "<run_id>" --default-model "<pipeline_default_model-or-null>" \
  [--default-effort "<level-or-null>"] [--model "<step_id>=<model>" ...] \
  [--effort "<step_id>=<level>" ...] [--start "<step-name>"] [--resume] \
  [--record '<json>' | --record-file "<path>"] --brief-file
```

First call: `--start "<current_iteration>"`, no `--record`; add `--resume` when
you arrive here from the Resume Procedure or after a nested blocker landed. Any
`step_model_overrides` / `step_effort_overrides` pairs go on that first call only
— the CLI persists them. Surface any `warnings` the init output carries.

### What you get back — and it is all you get

```json
{ "action": "run-step", "brief_file": "…/.runtime/<run_id>/briefs/07.json", "phase": "await-step" }
```

Exactly three keys. **You dispatch on `action`. The `brief_file` is addressed to
the subagent, not to you — you pass the path along and never open it.** That is
the whole point of the flag: the eighteen-member action stays on disk instead of
in the window the user is watching.

`phase` is the state the run is parked in (`await-step`, `await-improver`,
`await-script`, `await-retro`, `blocked`, `terminal`, …). Use it to sanity-check
your own bookkeeping; never to decide.

### `run-step` — spawn exactly one `step-executor`

> **Read this before every spawn — it is the rule this mode exists to test.**
> You are holding `Read`, `Glob` and `Grep`, which the `pipeline-manager` never
> has. Therefore, in this mode and at this exact step:
>
> - **Never read an iteration file. Not its body, not its frontmatter, not
>   "just to check" the path is right.** Every iteration is read once, by a
>   fresh executor, in a context you are trying to keep out of this one. There
>   is nothing you could learn from it that you are allowed to act on — the CLI
>   already resolved the path, the model and the routing.
> - **Never open the brief file.** It is the executor's input. Opening it puts
>   back exactly the block `--brief-file` just took out, and reading `steps[0]`
>   to "check" the step is how a session starts deciding.
> - **Never decide what runs next.** Not from a report, not from a `## Next`
>   section, not from a file name. You record what happened; `pipeline next`
>   routes.
>
> The temptations are specific and they will arrive. A report names an iteration
> file — you still do not open it. A step halts and you want to explain why —
> the halt reason comes from the report and the cursor, not from the step's
> source. The user asks what the next step does — say it will land in the
> context this mode is conserving, and let them ask for it deliberately, after
> the run.

Resolve `roles/step-executor.md` relative to this reference file. Call Codex's
native `spawn_agent` ONCE without an agent type, with `fork_turns: "none"` and a
message starting `Read <absolute role path> fully before acting.`, then wait
for that agent with `wait_agent` so its report returns before the loop
advances. Never start a child and poll an output file.
Use a task label such as `<pipeline_name> · step <NN>`, where `NN` is your own loop
counter (`01`, `02`, …) — you do not know the `step_id`, and you are not going
to look it up.

Prompt shape:

```
Execute one pipeline step. Your brief is a JSON file — read it FIRST, and take
every detail of the step from it. I have not read it and will not.

brief_file       = <brief_file from the control object>
run_id           = <the literal run id>
pipeline_root    = <pipeline_root>
step_record_file = <pipeline_root>/.runtime/<run_id>/records/session-<NN>.json

The brief is one `pipeline next` action object. Use `steps[0]` — it is the only
entry, this run is sequential. `path` is the iteration file to execute; a
`.runtime/…/rendered/…` path is CORRECT and authoritative, never "fix" it back
to a source file. Also honour these fields when the brief carries them:

- `worktree_pipeline_root` — the run's pipeline root for feedback/records paths,
  in place of the one above.
- `steps[0].external_worktree: true` — the run has a consumer-provisioned
  worktree at `worktree_path` with env file `worktree_env_file`: cd there and
  source it per the iteration's Context, and SUPPRESS your native-parallel
  self-detection (do not commit, do not report a worktree branch).
- `steps[0].fallback: "script-failure"` — this step's script failed; its
  `failure_record` names the record. Achieve the iteration's Goal per your
  fallback protocol and return a NORMAL step record.

Then follow the step-executor protocol: read the iteration file, execute its
Steps, verify its Success Criteria, and end with a structured Step Executor Final
Report. Do not auto-load PIPELINE.md unless the iteration's Context references
it. Never spawn a pipeline-manager or step-executor and never advance the chain
yourself — chain hand-offs go through your final report to me. Spawning an
iteration-instructed helper for this step's own work is allowed per your
"Intra-step fan-out" rules. Immediately before your final report, write your
machine-readable step record JSON to step_record_file (your "Step record file"
protocol).

As you execute, journal any problems you hit (doc-flaw / ambiguity /
script-candidate / project-issue / env / friction) as individual files under
<pipeline_root>/.feedback/<run_id>/ per your "Problem journal (Tier-2 feedback)"
protocol. I created that folder at run start.

<if a partial_work_note applies to this step on a resume>
This is a resumption after a nested-blocker delegation landed. The previous
executor paused with this note — use it to pick up cleanly:

<partial_work_note>
</if>
```

**Model and effort — the honest limitation.** `spawn_agent` model routing is set
by the *caller*, and the resolved `steps[].model` is in the brief
you do not read. So:

- Pass `model: "<pipeline_default_model>"` when step 3 resolved a non-null
  pipeline-level default (v1 pipelines only); otherwise pass no `model` and let
  the executor inherit the session's.
- **A step's own `model:` — and any `--model` override — is therefore not
  applied in this mode.** The CLI still resolves it, records it, and stamps
  `resolved_model` on the journal event, so the journal will disagree with what
  actually ran. Say so when it matters, and tell a user who relies on per-step
  models to run under `manager` or `driver`.
- Pass a resolved non-inherited effort as `reasoning_effort` when the available
  `spawn_agent` schema exposes it. If that field is absent, inherit the session
  effort; never smuggle it through the prompt text.

**Depth guard.** You are at depth 0, so a step-executor sits at depth 1 with
plenty of headroom — the manager's depth ceiling does not bind here. If a spawn
nevertheless returns nothing usable, record that step as `depth-exhausted`
rather than looping as though work happened.

**Then parse the Step Executor Final Report** for `iteration.outcome`,
`next_iteration.file`, `result_flags`, `improvement_brief`, `blocker_delegation`
and `halt_reason`. **Keep the `improvement_brief` and any `blocker_delegation`**
— the next `run-improver` or `blocked` action needs them, and they will not be
handed to you again.

**Then record**, preferring the executor's own file:

- `test -f "<step_record_file>"` → `--record-file "<step_record_file>"`. The
  executor wrote the record; the chain advances on its values with no
  transcription.
- Missing, unparseable, contradicting the markdown report (trust the markdown,
  and say so in your progress output), or needing an override (malformed report
  → `halted`; failed spawn → `depth-exhausted`) → inline:
  `--record '{"kind":"step","outcome":"completed|halted|blocked-delegating|depth-exhausted","flags":<result_flags-object-or-null>,"next_iteration":"<abs-path>|PIPELINE_COMPLETE|null","has_improvement_brief":<true|false>,"halt_reason":"<short>|null"}'`

### `run-improver` — spawn `pipeline-improver`

Resolve `roles/pipeline-improver.md` relative to this reference file. Call
`spawn_agent` without an agent type and with `fork_turns: "none"`; begin the
message with `Read <absolute role path> fully before acting.` Request
`gpt-5.6-sol` and high effort when supported; otherwise inherit and report the
unapplied hint. Wait with `wait_agent`. The task is the `improvement_brief` you
kept from that step's report, verbatim, under one line that hands it the action
file so it reads its own targets:

```
Your action file is <brief_file>. Read it: `iteration_path` is the file you must
edit (on a worktree-scoped external run it points into the RUN WORKTREE's
pipeline copy — edit THAT tree, never the main checkout), and `frozen_files`,
when present, lists files you may NOT edit.

<the improvement_brief, verbatim>
```

Wait for its report, parse its `script_creation_briefs` **LIST** (0..N) and keep
it — the script-creator actions index into it. Record
`--record '{"kind":"improver","applied":<true|false>,"script_briefs":<N>}'`. A
refusal is `applied:false, script_briefs:0`; surface it.

### `run-script-creator` — spawn `pipeline-script-creator`

The CLI emits these one at a time, in order, never two at once — so **count your
own dispatches since the improver**: the first is brief 1, the second brief 2.
You do not need to open the action file to learn `number`.

Resolve `roles/pipeline-script-creator.md` relative to this reference file. Call
`spawn_agent` without an agent type and with `fork_turns: "none"`; begin the
message with `Read <absolute role path> fully before acting.` Request
`gpt-5.6-sol` and high effort when supported; otherwise inherit and report the
unapplied hint. Pass that brief verbatim under the same one-line preamble
(`Your action file is <brief_file>. Read it for iteration_path, number, of.`).
Wait with `wait_agent` for the `Script Creator Final Report`, then record
`--record '{"kind":"script","outcome":"created|updated|converted|repaired|refused","script_path":"<abs-or-null>"}'`
— pass the reported `outcome` through **verbatim**, never re-mapped.

### `retrospective` — run the Tier-2 retrospective

Read `roles/pipeline-manager.md` relative to this reference file and follow its
**"End-of-run Retrospective"** section as written — you are performing the
manager's role for this run, and duplicating that contract here would let the
two drift. Two adjustments, and only two:

- The action's optional `lint_warnings` are in the action file. Hand
  `<brief_file>` to the batch improver and let it read them, exactly as above;
  do not open it yourself.
- The retrospective's `improver.*` / `script_creator.*` events are yours to
  emit, as they are the manager's, with `run_id` passed literally on every call.

That `Read` is real context, spent once, and only on a run that journaled a
problem. Mention it if the user is watching their window fill.

Record `--record '{"kind":"retro","done":true}'` when finished.

### `continue` — perform nothing

The CLI paused a chain of script steps against the call budget. Do not spawn,
read, or run anything. Immediately re-call with
`--record '{"kind":"continue"}' --brief-file` in a fresh Bash call. The explicit
record is required — a bare no-record call means something else.

### `blocked` — relay upward to yourself

A step reported `blocked-delegating`. You already hold its `blocker_delegation`
brief from its Final Report — that is where the manager gets it too, so nothing
is lost by not opening the action file. Do **not** run the retrospective and do
**not** clean up the feedback folder: the run is not over.

Run `SKILL.md`'s **Nested-Blocker Flow** unchanged. On successful resolution,
re-enter this loop with a `--resume` first call, `--start` at the same
iteration, and the `partial_work_note` threaded into that first spawn. On
terminal failure, emit `pipeline.halted` + `clear-liveness` and stop.

### `done` — the run completed

Emit `pipeline.completed` + `clear-liveness`. Remove the per-run feedback folder
(`rm -rf "<pipeline_root>/.feedback/<run_id>"`), keeping the `.gitignore` stub;
on an external run whose teardown already reaped it, skip. Report per
`SKILL.md`'s **Report format**.

### `halt` — the run stopped, and the reason is not in your hands

The reason lives in the action file. Read the run's **cursor** instead —
`<pipeline_root>/.runtime/<run_id>/next.json`, the small orchestration-cursor
file `SKILL.md`'s token-discipline section already permits you to read in full —
and take `status` and `halt_reason` from it.

If that file is absent or carries no reason (a plan that failed validation
before any state was persisted), re-run **the identical `pipeline next` command
without `--brief-file`** and read the reason off stdout: a terminal action is
idempotent (`phase: "terminal"`), so this re-runs and re-decides nothing.

Then emit `pipeline.halted` (with `halt_reason`) + `clear-liveness`, clean up
the feedback folder as above, and surface the reason to the user.

### `merge` — cannot happen, and must not be improvised

`merge` is emitted only for a parallel layer under worktree isolation, which
preflight already refused. If one arrives anyway, **stop**: its `branches` list
is in the brief file, and guessing which branches to merge is how a run
corrupts a repository. Emit `pipeline.halted` with that as the reason, clear
liveness, and report it — it means preflight was bypassed or the manifest
changed mid-run, and both are worth telling the user about.

## Invariants for this mode

Everything in `SKILL.md`'s **Supervisor invariants** still binds you. These are
the additions that only exist because the loop is in your context:

- **`pipeline next` decides; you perform and record.** Never compute the next
  step, route a graph, or gate the improver or retrospective yourself (E1).
- **Never read an iteration file — not even its frontmatter.** You have the
  tools; that is exactly why this is written down.
- **Never open a brief file.** Every payload is consumed by the subagent that
  action dispatches to. The one file you may read on the loop's behalf is the
  `.runtime/<run_id>/next.json` cursor, on a `halt`.
- **One step-executor per action, spawned synchronously, never backgrounded and
  never polled.** No `until [ -f … ]`, no `sleep` spins.
- **Every `pipeline next` call carries `--brief-file`, `--root`, `--run-id`,
  `--default-model` and Bash `timeout: 600000`.**
- **Record every action before asking for the next one.** An unrecorded action
  is a run that silently re-does or skips work.
- **You emit run-level lifecycle, liveness, the mirror binding and the
  retrospective's events; `pipeline next` auto-emits the per-iteration ones**
  (`--brief-file` changes delivery only — every event still fires). Do not
  double-emit `iteration.*`.
- **Never merge, never improvise a git operation the brief was supposed to
  describe.**
