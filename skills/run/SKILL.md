---
name: run
description: Run (or resume) a pipeline that the $pipeline:design skill already wrote. Stays in the main session as the thin supervisor and spawns a single pipeline-manager that drives the whole chain in fresh-context step-executors. Invoke when the user wants to run or resume a pipeline.
user-invocable: true
argument-hint: <pipeline-dir-or-iteration.md> [--start <step-name>] [--model <step_id>=<model> ...] [--effort <step_id>=<level> ...] | --resume [<run_id>]
---

# Run a Pipeline

You are starting or resuming pipeline execution. `$1` is the PIPELINE to run — its folder under `./.pipeline/`. (A v1 pipeline may still be named by an iteration file path; see Prerequisites.)

## What you are doing

You are the **supervisor** running in the main session (depth 0). You do **not** loop over iterations yourself. Instead you spawn a single **`pipeline-manager`** subagent (depth 1) that drives the entire chain — spawning a fresh `step-executor` per iteration and running `pipeline-improver` / `pipeline-script-creator` between steps (the `pipeline next` CLI it drives auto-emits the per-iteration UI events and executes any external worktree hooks itself) — and returns a structured report when the run completes, halts, or hits an out-of-scope blocker.

You stay at depth 0 because three things must live in the main session and a subagent cannot do them: (a) own a stable pid for the run's liveness lockfile, (b) wait hours for an external condition (a blocker PR to merge) and resume, (c) eventually surface results to the human. So your job is: mint the run id (or, on `--resume`, re-enter an EXISTING one — see "Resume Procedure"), set up UI tracking, spawn the manager, and act on its report — including running the nested-blocker poll-wait and re-invoking the manager to resume.

## CRITICAL — token discipline: read almost nothing

This skill is a supervisor, not a reader. Every iteration file is read by a `step-executor` in its own fresh context; per-step model resolution happens inside the `pipeline-manager`.

- **Never `Read` an iteration file (`steps/**/*.md`).** You never touch them — not even their frontmatter. The manager resolves per-step models; you only pass it the pipeline-level default.
- **Read `PIPELINE.md` only as frontmatter (`limit: 50`), once, at chain start**, to extract the `model:` field for `pipeline_default_model` and nothing else. Do not pass its content to the manager. **On `--resume`, skip this read entirely** — `pipeline_default_model` comes from the existing run's persisted `next.json.default_model` instead (see "Resume Procedure"), which is what keeps a resume from adding a manifest read on top of the `next.json` read it already needs for `current_iteration`.
- The only files you may `Read` in full are ones you write yourself in the nested-blocker flow (issue bodies, partial-work notes) and, on `--resume`, the small `.runtime/*/next.json` orchestration-cursor file(s) — never an iteration file or `PIPELINE.md` body.

## Runner selection (experimental)

**Four modes exist, and `pipeline next` decides what runs next in every one of
them (E1) — never the loop that calls it.** They differ only in *where the
loop lives* and *what executes one step*:

| Mode | Loop lives in | Executes one step |
|---|---|---|
| `session` | this main session | Codex's native `spawn_agent`, in-session |
| `manager` *(default)* | a `pipeline-manager` subagent | Codex's native `spawn_agent` |
| `driver` | a process this plugin owns, no model in the loop (`pipeline drive`) | a fresh `codex exec` process per step |
| `standalone` | the same owned process as `driver` | the Agent SDK with your own API key — no Codex CLI session at all |

`driver` and `standalone` are easy to conflate because they share one loop and
differ only in the executor; do not confuse either with `pipeline drive`, which
is the command name for the `driver` path, not a synonym for the mode.
**The `pipeline` CLI implements `session`, `manager`, and `driver`** — v1
pipelines spell `driver` as `runner: headless` in `PIPELINE.md` frontmatter (see
below); `standalone` and a `pipeline.yml`-level `runner:` key belong to the
same four-mode design but are not wired into the CLI yet, so do not
tell a user either will run today.

**Resolve `runner:` alongside the `model:` read at Procedure step 3.** In a v2 pipeline it is a top-level key in `pipeline.yml` — `Grep` `^runner:` there, which reads one line and never opens a step file; in v1 it is `PIPELINE.md` frontmatter, already inside the ≤50 lines you read for `model:`. **Absent or unreadable ⇒ `manager`**, today's behaviour and the deliberate default (E10). A value that *is* declared but has no branch below still runs `manager` — but **say so in one line before you start**, because a mode the manifest did not declare is a mode the author did not choose. Never infer the mode from chain length: an invisible threshold makes one command behave two ways.

### `runner: session` — the main session runs the loop itself

Do NOT spawn a `pipeline-manager`. Read [the session loop](references/session-loop.md) and follow it **in place of Procedure steps 5.1–5.3**; everything else in this file — steps 1–4, the Resume Procedure, the Nested-Blocker Flow, the Supervisor invariants and the Report format — applies to you unchanged, because you are still the supervisor at depth 0 and have only absorbed the loop instead of delegating it.

That file carries the two preflight refusals this mode needs (a CLI too old for `pipeline next --brief-file`, and `execution: parallel`, whose payloads live in a brief the session may not open) and is honest about the trade: every action *and every step report* lands in the context the user is watching, so a long chain belongs in `manager` — which is precisely why `manager` is still the default.

### `runner: headless` (v1) — the `driver` mode

When the pipeline is v1 and the `PIPELINE.md` frontmatter you read for `model:` also carries `runner: headless` (v1's spelling of the `driver` mode — see the table above), do NOT spawn a `pipeline-manager`. Instead run the driver as a background process and supervise it:

```bash
pipeline drive \
  --executor codex-cli \
  --root "<pipeline_root>" --run-id "<run_id>" [--start "<step-name>"] \
  --default-model "<pipeline_default_model-or-null>" \
  [--default-effort "<level-or-null>"] \
  [--model "<step_id>=<model>" ...] [--effort "<step_id>=<level>" ...] --json [--resume]
```

Launch it as a long-running terminal command and retain the returned process/session handle. Wait on that handle rather than polling files, then act on its final JSON when it exits: exit 0 → emit `pipeline.completed`; exit 1 → emit `pipeline.halted` and surface the reason; exit 3 (`blocked`) → run the nested-blocker flow below, then re-run `drive` with `--resume`. Everything else about your supervisor role (run id, liveness, mirror binding, human reporting) is unchanged. This `driver` (v1: `runner: headless`) path skips self-improvement actions and leaves `.feedback/<run_id>/` intact — mention that in your final report so the user can run a manual improver pass. When `runner:` is absent or `manager`, proceed exactly as below.

## Model selection

A pipeline (and each iteration) may opt into a model via the OPTIONAL `model:` frontmatter field. The field defaults to inherited — omit it and the step-executor inherits the session model. You resolve only the **pipeline-level default** and hand it to the manager; the `pipeline next` CLI resolves the per-iteration effective model. The manager requests the resolved model through Codex's native spawn interface when that exact model is available, otherwise it inherits and reports the unapplied hint. Never pass a non-Codex model id to `spawn_agent`.

**Accepted Codex model vocabulary:** an exact `gpt-*` Codex model id, or `inherit` / absent (→ session default). Cross-client aliases such as `haiku`, `sonnet`, `opus`, and `fable` may still occur in shared pipeline manifests; they are execution hints, not Codex model ids. The manager maps them through its documented Codex routing table before spawning.

**Resolve `pipeline_default_model`:** in a v2 pipeline the CLI reads `defaults.model` from `pipeline.yml` itself — pass `null` and let it. Otherwise, if `<pipeline-root>/PIPELINE.md` exists, `Read` it with `limit: 50` and take the frontmatter `model:` value when it is a `gpt-*` id, one of the four shared aliases above, or `inherit`; `inherit`/absent → `null`. If `PIPELINE.md` is absent, use `null`. Warn once and fall through to `null` for any other value.

**Per-run step overrides (`step_model_overrides`):** the user may pin individual steps to a different model FOR THIS RUN ONLY — without editing any pipeline file — either with explicit flags after the path (`--model <step_id>=<model>`, repeatable) or in natural language. Normalize whatever they said into `<step_id>=<model>` pairs. Do not read a step file to validate the ids; the CLI validates them. Pass the pairs to the manager or, on the driver path, as repeated `--model` flags. No overrides mentioned ⇒ omit entirely.

## Effort selection (reasoning effort — the `model:` twin)

A pipeline and each iteration may also opt into a **reasoning effort** via the OPTIONAL `effort:` frontmatter field (levels: `low` / `medium` / `high` / `xhigh` / `max`; `inherit`/absent → the session's effort). It resolves through the same ladder as the model inside `pipeline next`. The manager passes the resolved `reasoning_effort` when Codex exposes it and otherwise inherits and reports the unapplied hint. The driver applies it directly to each executor process.

## Prerequisites

- A pipeline exists under the current project's `./.pipeline/` (typically authored with `$pipeline:design`).
- `$1` is the pipeline FOLDER under `./.pipeline/` (e.g. `./.pipeline/ship-feature`), which starts a FRESH run — this always mints a NEW run_id. `--start <step-name>` starts that fresh run at a named step instead of the manifest's first. An iteration file path is still accepted, and is how a v1 pipeline names a starting step. OR `--resume [<run_id>]` to re-enter an EXISTING run under its ORIGINAL run_id (see "Resume Procedure") — the only way to continue a dead session's run without orphaning its state.
- The current working directory is the consumer project's root — all file edits performed by iterations land here.

## Journal event emissions

You emit the **run-level lifecycle** to `<project>/.pipeline/.runtime/events.jsonl`; the per-iteration events (`iteration.*`, `improver.*`, `script_creator.*`, `worktree.*`) are auto-emitted in-process by the `pipeline next` CLI the manager drives (the manager itself emits only the retrospective's improver/script events). Because the whole run shares one `session_id`, the mirror binding you register below is what lets the analytics hook correlate the manager's and step-executors' tool calls to this run. Emissions are best-effort — never let a failure halt the run.

**One-time setup at the start of the Procedure:** mint the run id by calling the CLI — never generate one yourself or invent a format: `pipeline id`. Capture the literal value it prints (a UUIDv7, e.g. `019fc762-5762-7000-a9bf-922ed8fa00be`).

**CRITICAL — pass `run_id` literally on every writer call.** Codex CLI's Bash tool does not preserve shell state between invocations, so an exported env var does not reach the next `pipeline event` call. Pass `run_id=<the-literal-id>` as a k=v argument on EVERY call. k=v args have no spaces around `=`; single-quote a value containing spaces.

**Emission helper** (silent on success, exits 0 even on failure — do not check output):

```bash
pipeline event <event-type> run_id=<literal-id> [k=v ...]
```

**What you emit (one call per bullet):**

- **On `--resume`, this whole list does not apply** — the Resume Procedure emits only `write-liveness` + `register-mirror-binding` for the EXISTING run_id, and never `pipeline.started` (re-entering a run is not starting one). See "Resume Procedure".
- After the banner: `pipeline.started run_id=<id> pipeline_name=<name> first_iteration_path=<abs> pipeline_root=<abs> default_model=<model-or-null>`.
- Immediately after `pipeline.started`, write the **liveness lockfile** so a reader can tell this run died without a terminal event: `pipeline event write-liveness run_id=<id> pid=$PPID` (PowerShell: `pid=$PID`). Pass the OS pid of the process **driving** this supervisor — `$PPID` is the best portable handle for the persistent Codex session. The daemon only auto-retires a run when this pid is a real, dead process, so an untrustworthy value is a safe no-op.
- Immediately after, register the **mirror binding** so the analytics hook can resolve which run this session's events belong to: `pipeline event register-mirror-binding run_id=<id> pipeline_name=<name> iteration_path=<abs-first-iteration>`. Idempotent; silent on success. If `CODEX_SESSION_ID` is unset it writes `session_id=null`, and hook events fall back to `run_id: null`.
- On `status: completed`: `pipeline.completed run_id=<id> pipeline_name=<name>`.
- On `status: halted` / `depth-exhausted` (or any unrecoverable stop): `pipeline.halted run_id=<id> pipeline_name=<name> iteration_path=<abs> halt_reason=<short>`.
- On loop exit (**either** outcome), after the terminal event, clear the lockfile: `pipeline event clear-liveness run_id=<id>`. A cleanly-finished run leaves no lockfile; only a crash/kill leaves a stale one (dead pid), which is the hard-kill signal.

The writer pops `run_id`, `parent_run_id`, and `session_id` out of the kv args and uses them as envelope fields, so those names are reserved — do not use them as data-field names.

## Procedure

1. **Detect the resume form first.** If the invocation is `--resume` or `--resume <run_id>` (with or without a trailing run id — never a path), do NOT treat it as an iteration path: follow the **Resume Procedure** below instead, which re-joins this Procedure at step 5.1 once it has resolved `current_iteration` and the run's id. Otherwise, if `$1` is empty, ask the user which pipeline to run (suggest `./.pipeline/<pipeline>`). Do not proceed without one.
2. Verify `$1` exists and is under the current project's `.pipeline/` tree. If not, stop and ask the user to confirm it.
3. **Resolve the pipeline root — do not read iteration content.** If `$1` is a DIRECTORY it IS the pipeline root, and its basename is the pipeline name: nothing to walk. If `$1` is an iteration FILE (the v1 form), walk up until you reach `steps/`; the parent of `steps/` is the root.

   A root holds `pipeline.yml` (v2) or `PIPELINE.md` (v1) — `Glob` for existence only. **Where a `pipeline.yml` exists, the manifest decides where the run starts**: pass no `--start` at all and the CLI takes the manifest's first step. Pass one only when the user named a step (`--start <step-name>`); it is a NAME now, not a path. A v1 pipeline named by a directory behaves the same way — the CLI takes its first enumerated step.

   Show a one-line banner:

   ```
   ▶ Starting pipeline <pipeline-name>
   ```

   Verify the pipeline-root exists (`Glob` for `<pipeline-root>/PIPELINE.md` — existence only). Resolve `pipeline_default_model` per "Model selection" above.

4. **Generate the run id** and emit `pipeline.started`, then `write-liveness`, then `register-mirror-binding` (see "UI event emissions").

5. **Set up the chain state:** `current_iteration = $1`, `partial_work_note = null`. Then **enter the supervise loop**:

   ### 5.1 Spawn the `pipeline-manager`

   Call Codex's native `spawn_agent`, requesting the registered custom agent whose `name` is `pipeline-manager`, with `fork_turns: "none"`. Hand it the prompt below as its task message:

   ```
   Orchestrate this pipeline run. Drive the chain to completion via fresh
   step-executors, run the improver/script-creator between steps, and end with
   a structured Pipeline Manager Final Report. (The `pipeline next` CLI
   auto-emits the per-iteration UI events — you emit only the retrospective's.)

   run_id = <literal run id>
   pipeline_name = <name>
   pipeline_root = <abs path to the pipeline root folder>
   pipeline_default_model = <model-or-null>
   current_iteration = <current_iteration>

   <if PIPELINE.md frontmatter set an effort, or the user asked for one>
   pipeline_default_effort = <low|medium|high|xhigh|max|null>
   </if>

   <if the user asked for per-step model overrides>
   step_model_overrides = <step_id>=<model>, <step_id>=<model>
   </if>

   <if the user asked for per-step effort overrides>
   step_effort_overrides = <step_id>=<level>, <step_id>=<level>
   </if>

   <if partial_work_note is not null>
   partial_work_note (resume after a nested-blocker landed — pass into the first
   step-executor spawn, then clear):
   <partial_work_note>
   </if>

   <if this invocation came from the Resume Procedure (--resume <run_id>), even
   though partial_work_note is null>
   This is a RESUME of an existing run, not a fresh start — its
   `.runtime/<run_id>/next.json` already carries progress. Make your FIRST
   `pipeline next` call with `--resume` (the "Resume / re-entry" branch of
   "Starting / resuming the run"), exactly as you would after a nested-blocker
   landed, even though no partial_work_note is attached.
   </if>
   ```

   Do NOT pass any iteration or manifest content in the prompt — only the fields above. The manager reads what it needs from disk.

   ### 5.2 Parse the Pipeline Manager Final Report

   Extract `run.status`, `last_iteration.file`, `next_on_resume.file`, `blocker_delegation`, `halt_reason`, and `retrospective`. If the manager failed to emit the report in the expected shape, STOP, surface the raw output, emit `pipeline.halted` + `clear-liveness`, and exit — a malformed report likely means the agent hit an error mid-run.

   The `retrospective` section is the manager's **Tier-2 end-of-run summary** (`null` when the run journaled no problems). It reports what the run auto-improved (doc fixes applied + scripts extracted) and lists the HUMAN-ONLY problems (`project-issue` / `env` / `friction`) the run surfaced. You do NOT act on it — you only surface it to the user in your report (see "Report format"). Keep this section even when the run halted; the manager runs the retrospective on both `completed` and `halted`.

   ### 5.3 Act on `run.status`

   - **`completed`** → emit `pipeline.completed` + `clear-liveness`; exit the loop. Pipeline finished.
   - **`halted`** or **`depth-exhausted`** → emit `pipeline.halted` (with `last_iteration.file` and `halt_reason`) + `clear-liveness`; exit the loop. Surface `halt_reason` to the user.
   - **`blocked-delegating`** → run the **Nested-Blocker Flow** below. On successful resolution, set `current_iteration = next_on_resume.file`, set `partial_work_note` from the brief, and go back to 5.1 to re-invoke the manager. On terminal failure, emit `pipeline.halted` + `clear-liveness` and exit.

6. When the loop exits, deliver the report in the format below.

## Resume Procedure

Triggered by step 1 when the invocation is `--resume` (list candidates) or `--resume <run_id>` (resume that id directly) — a dead session's run re-entering under its EXISTING run_id instead of minting a new one and orphaning its state.

**`<pipeline-root>/.runtime/<id>/next.json`'s `phase` field is the SINGLE AUTHORITY on resumability.** `phase: "terminal"` (run finished, `done` or `halt`) — or a missing/unparseable file — means dead; anything else (`await-*` or `blocked`) means the run can be re-entered. The `.stats` SUMMARY "In-flight or crashed runs" section is for DISCOVERY ONLY, to help the human recall run ids — it is NEVER the refusal criterion: a crashed run's `.stats` entry is an unflushed timeline buffer, not a finalized record, so its mere presence or absence proves nothing about resumability.

1. **With an id** (`--resume <run_id>`): `Glob` `./.pipeline/*/.runtime/<run_id>/next.json` (existence only; at most one match across all pipelines in this project).
   - No match → refuse: "No run found with id `<run_id>`. Start fresh: `$pipeline:run ./.pipeline/<pipeline>`." Stop — do not proceed to step 4.
   - Match found → go to step 3.

2. **Without an id** (bare `--resume`): discover candidates, then ask — this is the ONLY branch that reads more than one `next.json`.
   - `Glob` `./.pipeline/*/.runtime/*/next.json`. For each match, `Read` the file (a small orchestration-cursor JSON, not iteration content) and keep it only when it parses AND `phase !== "terminal"`.
   - No non-terminal candidates → tell the user there is nothing to resume and suggest starting fresh (`$pipeline:run ./.pipeline/<pipeline>`). Stop.
   - One or more candidates → list them, one line each: `<pipeline-name> · <run_id> · currently at <current_step_id or current_path> · <phase>` (append `(blocked on an external delegation — resuming will re-attempt this iteration)` when `phase === "blocked"`, so the user can choose knowingly). Optionally cross-reference the `.stats` SUMMARY "In-flight or crashed runs" section (`pipeline stats`) to add a human-friendly "idle for Nh" hint — informational only, never filtering. Ask the user which to resume, or whether to start fresh instead. **This ask is user step 1 of the ≤2-step budget.**
   - On the user's answer (step 2): if they chose to start fresh, stop this flow and use the ordinary Procedure (step 1 onward) instead. If they chose a candidate, you already have its `next.json` content from this pass — skip the re-`Read` in step 3 and continue at step 4 with that id and state.

3. **Load and validate `next.json`** (skip when step 2 already read it): `Read` `<matched-path>`.
   - Unparseable → treat exactly like "missing" (refuse as in step 1).
   - `phase === "terminal"` → refuse: "Run `<run_id>` already finished (status: `<status>`). It can't be resumed — start a fresh run instead: `$pipeline:run ./.pipeline/<pipeline>`." Stop.
   - Otherwise, continue to step 4.

4. **Derive run context from the matched path and the state — no `PIPELINE.md` read, no `steps/**` read.** From `<pipeline-root>/.runtime/<run_id>/next.json`: `pipeline_root` = `<pipeline-root>` (two path segments up from `next.json`), `pipeline_name` = its basename. From the state JSON: `current_iteration = current_path` (per 08.3, the single authority — this is why the resume path never re-derives it from a fresh plan or manifest read), `pipeline_default_model = default_model` (already resolved and persisted at run init; reusing it — instead of re-`Read`ing `PIPELINE.md` frontmatter — is what keeps this path from adding a manifest read on top of the one `next.json` read).

5. **Re-emit liveness and the mirror binding for the EXISTING id.** Do NOT emit `pipeline.started` — this is not a new run, and re-minting would desync the UI's run list from the actual run_id. Show a one-line banner, then the two calls:

   ```
   ▶ Resuming pipeline <pipeline-name> (run <run_id>)
   ```

   `pipeline event write-liveness run_id=<run_id> pid=$PPID` (PowerShell: `pid=$PID`), then `pipeline event register-mirror-binding run_id=<run_id> pipeline_name=<pipeline_name> iteration_path=<current_iteration>`.

6. **Join the ordinary Procedure at step 5.1**, with `current_iteration` and `partial_work_note = null` set from step 4 above, and `run_id` = the EXISTING id (never regenerated). Use the `<if this invocation came from the Resume Procedure>` block in the 5.1 spawn-prompt template so the manager's first `pipeline next` call uses `--resume`. From there, 5.2/5.3 and step 6 of the Procedure are unchanged — including that a resumed run's `.stats` buffer finalizes normally on completion (the idempotent finalize guard is per-run-id, and this run was never finalized while dead — 08.3, 01§3.4).

## Nested-Blocker Flow (supervisor-side)

The manager relays a `blocker_delegation` brief (originally emitted by a step-executor) when an iteration hits an out-of-scope blocker. You run this sequence in the main session — neither the manager nor the step-executor can spawn an hours-long poll-wait or a git-merge loop across a finite context.

Brief fields: `parent_task_repo`, `parent_task_issue`, `parent_branch`, `parent_pipeline_iteration`, `blocker_target_repo`, `blocker_pipeline_first_iteration`, `blocker_worktree_source`, `new_issue_title`, `new_issue_body`, `partial_work_note`, `poll_interval_minutes` (default 5), `deadline_hours` (default 4).

1. **File the blocker issue** on `<blocker_target_repo>`:

   ```bash
   gh issue create --repo <blocker_target_repo> --title "<new_issue_title>" --body "<new_issue_body>"
   ```

   Record `blocker_issue_number` and `blocker_issue_url`. If a `--label` fails because the label doesn't exist, drop it and retry. Mint `child_run_id` for the child run the same way as the top-level run id — `pipeline id` — never invent a format. Emit `blocker.delegated run_id=<id> parent_iteration_path=<abs> blocker_issue_url=<url> child_run_id=<child-id> blocker_target_repo=<owner/repo>`.

2. **Back-link the parent's tracking issue** (skip when `parent_task_issue` is empty):

   ```bash
   gh issue comment <parent_task_issue> --repo <parent_task_repo> --body "Blocked by <blocker_issue_url> (from pipeline iteration <parent_pipeline_iteration>)."
   ```

3. **Resolve `blocker_pipeline_first_iteration`.** If it is `REQUIRES_DESIGN`, stop this blocker flow and report the brief to the user with the exact next action: `$pipeline:design <blocker_design_prompt>`. A skill is not a custom agent and cannot be selected through `spawn_agent`; after the user creates the repeatable blocker pipeline, resume from its first iteration.

4. **Spawn the child pipeline run** — call `spawn_agent`, again requesting the registered `pipeline-manager` with `fork_turns: "none"`, pointed at `blocker_pipeline_first_iteration`, with its own `run_id=<child_run_id>` and `parent_run_id=<id>` (pass `parent_run_id` literally on the child's events for UI nesting). Its prompt includes the brief fields plus the newly-minted `blocker_issue_number` / `blocker_issue_url`, and the instruction that the child's PR body MUST include `Closes #<blocker_issue_number>`. Provision the child's worktree/branch from `<blocker_worktree_source>`; the child never writes into the parent's worktree. You wait for the child's PR, not for the child subagent call to return.

5. **Poll-wait loop.** Every `poll_interval_minutes`, search for a PR closing the blocker issue and emit `blocker.polling run_id=<id> blocker_issue_url=<url> pr_state=<OPEN|MERGED|CLOSED|none>`:

   ```bash
   gh pr list --repo <blocker_target_repo> --state all --search "<blocker_issue_number> in:body" --json number,url,state,mergedAt,mergeCommit,headRefName
   ```

   Prefer PRs whose body contains `Closes #<blocker_issue_number>` or `Fixes #<blocker_issue_number>`. Classify:
   - `MERGED` → go to 6.
   - `CLOSED` (not merged) → STOP, surface the URL, fail the flow. Do NOT auto-retry.
   - `OPEN` / not-yet-created past `deadline_hours` → STOP, surface the last state, fail the flow.
   - Otherwise → sleep `poll_interval_minutes` and re-check.

6. **Merge the blocker into the parent's branch.** Confirm the parent branch is clean (`git status --porcelain` empty) and HEAD matches `<parent_branch>`; if unclean, STOP. Determine the repo path (same-repo → the parent's working dir; cross-submodule → the submodule path). Fetch and merge (append-only, never rebase-onto, never force):

   ```bash
   git -C <repo-or-submodule-path> fetch origin <base_branch>
   git -C <repo-or-submodule-path> merge origin/<base_branch> --no-edit -m "chore: merge <base_branch> after blocker #<blocker_issue_number> resolved"
   ```

   On conflict, STOP and surface the conflict list — do not auto-resolve. Emit `blocker.resolved run_id=<id> blocker_issue_url=<url> merged_pr_url=<url>`.

7. **Re-run the parent iteration's verification gate** (the Success Criteria commands from `<parent_pipeline_iteration>`). 0 failures required; on any failure STOP — the parent cannot resume on a red baseline.

8. **Resume.** Push the merged branch (never force-push). Return to 5.1: re-invoke the `pipeline-manager` with `current_iteration = <parent_pipeline_iteration>` and `partial_work_note` from the brief.

## Supervisor invariants

- **Spawn ONE manager per supervise-loop pass.** You never spawn `step-executor`, `pipeline-improver`, or `pipeline-script-creator` directly — those are the manager's. The only subagents you spawn are `pipeline-manager` (the run and any blocker-child run). A `REQUIRES_DESIGN` blocker is handed back to the user for `$pipeline:design`.
- **The Pipeline Manager Final Report is the only structured signal.** Don't infer intent from prose; act only on its fields.
- **Never read iteration files or `PIPELINE.md` content.** You read at most ~10 lines of `PIPELINE.md` frontmatter (for `pipeline_default_model`) and never touch `steps/**`.
- **Run-level events, liveness, and the mirror binding are yours; per-iteration events are auto-emitted by the `pipeline next` CLI** (the manager adds only the retrospective's improver/script events). Don't double-emit `iteration.*`.
- **One child per blocker.** If the child's PR is CLOSED without merge, STOP — no replacement.
- **No silent deadline extensions; no force-push, ever.** Cross-submodule blockers merge inside the submodule.
- **Always clear the liveness lockfile after the terminal event**, on either outcome.

## Report format

After the loop exits, show the user:

- Which iteration finished last (`last_iteration.file`).
- Whether the pipeline completed or halted (and on `halt_reason`, the iteration where it stopped).
- If completed: the pipeline folder path, so they can re-read iterations as a knowledge base.
- If any blocker-delegation cycles ran: the blocker issue URLs and their resolution.
- **The retrospective, when `retrospective` is non-null.** Surface it concisely:
  - **What the pipeline auto-improved this run** — from `retrospective.auto_improved` (how many problems fed the improver, the doc fixes applied, and the scripts extracted).
  - **Problems for you to handle** — the `retrospective.human_only` list (the `project-issue` / `env` / `friction` problems the run surfaced, each with its category, one-line summary, and iteration). These were NOT auto-fixed — they need a human. Show them as a short bullet list; omit this part when the list is empty. When `retrospective` is `null`, say nothing about it.
