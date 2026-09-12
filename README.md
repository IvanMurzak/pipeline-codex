# Pipeline - Codex

[![Codex CLI](https://img.shields.io/badge/Codex_CLI-plugin-D97757?style=for-the-badge&logo=openai&logoColor=white&labelColor=0D1117)](https://github.com/openai/codex)
[![Release](https://img.shields.io/github/v/release/IvanMurzak/pipeline-codex?style=for-the-badge&logo=github&logoColor=white&label=release&labelColor=0D1117&color=3FB950)](https://github.com/IvanMurzak/pipeline-codex/releases)
[![CLI](https://img.shields.io/npm/v/%40baizor%2Fpipeline?style=for-the-badge&logo=npm&logoColor=white&label=CLI&labelColor=0D1117&color=CB3837)](https://www.npmjs.com/package/@baizor/pipeline)
[![License](https://img.shields.io/badge/license-MIT-6E7681?style=for-the-badge&labelColor=0D1117)](LICENSE)

![A pipeline run walking its steps: plan, implement, test, changelog, open PR, merge](docs/pipeline-flow.svg)

**Long AI work, as ordered files in your repo.** A pipeline is a folder of
numbered markdown steps. A deterministic CLI decides what runs next — not the
model — and every step gets a fresh context, so a chain that takes hours never
drags a hundred thousand tokens of history behind it.

Two commands. The second one from the project where you want pipelines to live.

## Install

**1. The plugin**, so Codex CLI can discover the `$pipeline:*` skills:

```bash
codex plugin marketplace add IvanMurzak/pipeline-codex-marketplace
codex plugin add pipeline@pipeline
```

Already inside Codex CLI? The same two through its built-in plugin commands:

```text
/plugin marketplace add IvanMurzak/pipeline-codex-marketplace
/plugin install pipeline@pipeline
```

**2. The CLI**, which is what actually decides what runs next. Since plugin
0.93.0 it is required, not optional: the hooks are CLI subcommands now, and a
session without it prints one actionable line and degrades every hook to a no-op.

```bash
bun add -g @baizor/pipeline
```

**3. Set up the project**, from wherever you want pipelines to live:

```bash
pipeline init
```

![`pipeline init` signs in, connects the project, installs the plugin, clones a starter pipeline and runs it](docs/pipeline-terminal.svg)

`pipeline init` is the whole setup: one browser consent screen, then it connects
this project to your account, installs this plugin into Codex CLI, clones a
starter pipeline into `./.pipeline/support-answer`, enrols this machine as a
runner that starts on boot, and offers to run that starter pipeline right there.
The install ends with a pipeline that has already run on your machine.

Restart Codex CLI afterwards — a running session does not pick up a newly
installed plugin.

**No account wanted?** `pipeline init --local` does all of the above except the
cloud. No browser, no account, nothing sent anywhere.

<details>
<summary><b>Prerequisites, escape hatches, and installing the plugin by hand</b></summary>

<br>

**Three prerequisites. `init` is explicit about the first two; the third only
applies on Windows.**

- **Bun.** The CLI's executable is TypeScript, so Bun is required, not preferred.
  `pipeline init` stops immediately with the install URL if `bun` isn't found.
- **Codex CLI, installed and authenticated** with your own subscription or API
  key. Pipeline steps are executed by `codex`; it is your account that runs them
  and your account that pays for them. If `codex` isn't on `PATH`, `init` says
  so, skips the plugin install and the starter run, and still exits 0 — the clone
  and the dashboard are done, and you re-run `pipeline init` once Codex CLI is
  there.
- **Git Bash — Windows only.** This plugin's hooks are pinned to `bash`, so a
  Windows machine needs one. Install
  [Git for Windows](https://git-scm.com/download/win), which bundles Git Bash, or
  run `winget install --id Git.Git -e --source winget`. Keep `bash.exe` on
  `PATH`, or install Git for Windows in its standard location under
  `C:\Program Files\Git`. **Without Git Bash** the hooks **fail visibly**: Codex CLI reports
  each hook it could not start, a few times per session, rather than silently
  doing nothing. That is the intended trade — an error you can see and act on,
  instead of hooks that look installed and quietly never run. It does not
  interrupt your work: a hook Codex CLI cannot start is a **non-blocking**
  error, so the session and the tool call carry on regardless.
  Codex CLI's own message suggests pinning the hooks to `powershell` instead —
  **don't**: the shim is POSIX shell, and PowerShell brings back the silent
  failure the pin exists to close. macOS and Linux are unaffected, `bash` is
  already there.

**The cloud step is the only network step, and it is not a trapdoor.** Nothing
about your code or your keys goes with it: the control plane coordinates runs and
shows you their status, and by default receives metadata only — statuses,
timings, token counts — filtered on your machine before anything is sent. You do
not need an account first; signing in creates one, and your first organization is
created for you.

- **`pipeline init --local`** — everything except the cloud.
- A **failed or declined** connect is a warning, not an error. `init` finishes
  locally and exits 0; `pipeline cloud connect` picks it up later.
- `--server`, `--org` and `--project` pass through to that connect. Under
  `--json` no browser is ever opened: set `PIPELINE_MACHINE_TOKEN` to connect
  non-interactively (CI, bots, agents), or the cloud step is skipped with a
  stated reason and the rest still runs.

Every step of `init` is idempotent (a re-run prints a `✓` per already-satisfied
step and changes nothing) and independently skippable: `--no-plugin`, `--no-run`,
`--no-runner`, plus `--yes` / `--json` for scripted setups, and
`pipeline init <template>` to start from a different template
(`pipeline clone --list` shows them).

**`init` installs the plugin too.** Step 1 above is the same thing `init` does
for you (it shells exactly those two commands), so doing both is harmless — a
re-run prints a `✓` and changes nothing. Step 1 is listed first because it is the
half that makes the commands appear, and because you may want the plugin on its
own without a starter pipeline.

**The global CLI is required, not optional.** Since plugin 0.93.0 the five hook
relays are CLI subcommands rather than files in this repository, so a session
started without `@baizor/pipeline` on `PATH` prints one actionable line from the
SessionStart hook and every hook then degrades to a silent no-op. Updates to the
plugin arrive via `/plugin update`; the CLI updates on its own npm version line.

</details>

## Your first pipeline

```text
$pipeline:clone support-answer
$pipeline:run ./.pipeline/support-answer
```

`run` takes the pipeline **directory** — the manifest decides which step is
first, and in what order the rest follow. Add `--resume` to pick a halted run
back up, or `--start <step-name>` to enter partway in.

Or describe what you want and let it author one:

```text
$pipeline:design a release pipeline — changelog, version bump, tag, GitHub release
```

Then, from any later task, stop choosing pipelines by hand:

```text
$pipeline:dispatch fix the flaky auth test in the checkout suite
```

`dispatch` matches your task against every pipeline manifest in the project with
a deterministic BM25 matcher — free, no model call — and only escalates to a
low-cost `gpt-5.6-luna` disambiguator when the top two candidates are genuinely close. Most
tasks resolve on the free tier.

## Watch it run, from anywhere

![The ai-pipeline.dev dashboard: stat tiles and a live run list](docs/pipeline-dashboard.svg)

`pipeline init` connects this project to [**ai-pipeline.dev**](https://ai-pipeline.dev),
where every run shows up live — status, step, elapsed, tokens, cost — with
pipelines rendered as node graphs that light up as they execute. A run that
parks for your approval says so, and you can answer it from the dashboard or
from your phone.

It runs on your metal. The cloud is a control plane, not a proxy: your
subscription, your API keys, your machines, and model traffic never touches it.
Metadata only by default — statuses, timings and token counts leave, transcripts
and code do not, unless you opt up per project. `pipeline init --local` opts out
of all of it and serves the same dashboard at `http://127.0.0.1:<port>/`.

---

## Documentation

- [What you get](#what-you-get) · [Token discipline](#token-discipline) · [Mental model](#mental-model) · [Execution modes](#execution-modes)
- [Using the plugin in a consumer project](#using-the-plugin-in-a-consumer-project) — [cheat sheet](#cheat-sheet--which-command-does-what), [day 1](#day-1--author-and-run-your-first-pipeline), [day 2+](#day-2--picking-the-right-pipeline-for-a-task), [pitfalls](#common-pitfalls)
- [Iteration file shape](#iteration-file-shape) · [Finding the right pipeline](#finding-the-right-pipeline-for-a-task) · [Self-improving pipelines](#self-improving-pipelines)
- [Script extraction](#token-cheap-iterations-via-script-extraction) · [Script steps](#script-steps-zero-token-steps) · [`ci-wait`](#waiting-on-github-ci-without-burning-tokens-pipeline-ci-wait)
- [Measuring every run](#measuring-every-run-pipelinestats--pipelineoptimize) · [Nesting](#nesting) · [Parallel / DAG pipelines](#parallel--dag-pipelines-opt-in)
- [Configuration reference](#configuration-reference) · [Where things live](#where-things-live) · [Watching a run](#watching-a-run)
- [Departments](#departments-mcp--background-notifier) · [Resuming a halted pipeline](#resuming-a-halted-pipeline) · [Tips](#tips)

Related repositories: the remote runner that lets connected compute pick up
dispatched work lives in [`IvanMurzak/pipeline-runner`](https://github.com/IvanMurzak/pipeline-runner),
and the Codex build of this plugin in [`IvanMurzak/pipeline-codex`](https://github.com/IvanMurzak/pipeline-codex).

## What you get

**Five Codex skills.**

| Command | What it does |
|---|---|
| `$pipeline:clone <template>` | Scaffolds a ready-made pipeline into `./.pipeline/<template>/`. `--list` shows them: `support-answer`, `ship-feature`, `example-minimal`. `--force` overwrites, `--dir` picks another project root. |
| `$pipeline:design <goal>` | Authors a new pipeline from a high-level goal — a `pipeline.yml` plus the markdown its steps read. Each step is one PR-sized unit of work. |
| `$pipeline:run <pipeline>` | Drives a pipeline end to end. Fresh context per step, resumable, liveness-tracked. |
| `$pipeline:dispatch <task>` | Picks the right pipeline for a task and runs it without asking. |
| `$pipeline:find <task>` | The same matcher with no model and no auto-run: ranked candidates, scores, matched terms, and every exclusion with its reason. Takes a GitHub issue URL, `owner/repo#N`, or a bare issue number. |

**Five subagents**, normally reached through those chains rather than by hand.

| Agent | Role |
|---|---|
| `pipeline-manager` | Drives one run's chain |
| `step-executor` | Runs a single step, in its own fresh context |
| `pipeline-improver` | Feeds what a run learned back into the pipeline's own prose |
| `pipeline-script-creator` | Extracts deterministic blocks out of markdown into scripts |
| `pipeline-disambiguator` | Breaks a close match — runs on `gpt-5.6-luna` to keep the ladder cheap |

**Departments.** A remote MCP server and a background notifier: hand a task to
another agent or team from inside Codex CLI, and hear back when it needs you or
finishes — even after this session ends.
[Details below](#departments-mcp--background-notifier).

## Token discipline

Every step is read by a fresh-context executor **on every run**. A token spent in
step markdown is therefore paid forever, not once — which is why the architecture
looks the way it does.

| Rule | In practice |
|---|---|
| **Skills read only their own role's input** | `$pipeline:run` is a router and never opens a step body. `$pipeline:design` reads the project only while authoring. `$pipeline:dispatch` reads manifests, capped at 300 tokens each, because matching needs them. |
| **Steps get leaner over time** | Long deterministic blocks — build sequences, filesystem work, multi-call API chains — become scripts under `scripts/`, replaced by a one-line invocation. The executor reads one line; the logic runs in Bash, never through the model. |
| **The manifest is metadata, not a step** | Capped at 300 tokens, never auto-loaded, opt-in per step via an explicit `Context` reference. Adding a pipeline does not raise anyone else's baseline cost. |

## Mental model

A **pipeline** is a folder with a manifest and the markdown its steps read.

**A step is not a file.** It is an entry in `pipeline.yml`, identified by its
`name:`. Nothing about a step comes from disk — not its identity, not its order,
not its model, not its type. The files under `steps/` are prose a step is handed.

```
<your-project>/.pipeline/
└── <pipeline-name>/
    ├── pipeline.yml           ← THE definition: every step, in order
    ├── PIPELINE.md            ← optional prose for humans; not parsed
    ├── scripts/               ← optional — scripts called by `type: script` steps
    │   └── <name>.py          ← stdlib-only, cross-platform
    ├── _shared/               ← optional — markdown several steps compose in
    │   └── <fragment>.md
    └── steps/                 ← the markdown each step reads
        ├── <step-name>.md     ← no numeric prefix: order lives in the manifest
        └── ...
```

All files live inside **your current project** (the working directory where
Codex CLI was launched). The plugin itself is read-only at runtime.

### The manifest — `pipeline.yml`

```yaml
schema: 2
name: release-api
description: Cut a release: bump, changelog, tag, publish.

execution: sequential
isolation: run

steps:
  - name: bump
    body: steps/bump.md
    model: gpt-5.6-luna

  - name: changelog
    body: steps/changelog.md
    model: gpt-5.6-sol

  - name: publish
    type: script
    script: scripts/publish.py
    timeout: 300
    self_improve: false
```

One file says everything: order, models, isolation, which steps are
deterministic scripts, which prompts an automated pass may not rewrite. **An
unknown value is an error**, never a warning with a silent fallback — a pipeline
that looks configured while behaving otherwise is the failure this format exists
to remove.

Three things follow from "a step is not a file":

- **Order comes from the manifest** (and `needs:` when a step depends on
  something other than its predecessor). A step does not choose its successor,
  so a step that forgets to can no longer end the run as a silent success.
- **A step's prompt may be composed** from several files — `body:` takes a list,
  optionally conditional — so the paragraph every step needs lives in one place.
- **Renaming a body file changes nothing.** It is a file; the step is its name.

A pipeline may keep a `PIPELINE.md` for humans reading the folder as a knowledge
base. It is **not parsed** — configuration put there does nothing.

**Already have a v1 pipeline?** `pipeline migrate --to-manifest --root <dir>`
generates the manifest and prints the old→new step-name map. v1 pipelines keep
running meanwhile.

## Execution modes

Every pipeline runs in one of four modes. **In all four, a deterministic CLI —
`pipeline next` — decides what runs next, not the model.** That guarantee holds
whether the loop asking it lives in this session, in a subagent, or in a
process with no model in it at all; only *where the loop lives* and *what
executes one step* change between them.

| Mode | Loop lives in | Executes one step |
|---|---|---|
| `session` | This Codex CLI session | Native `spawn_agent`, in-session |
| `manager` *(default)* | A `pipeline-manager` subagent | Native `spawn_agent` + `wait_agent` |
| `driver` | A process the plugin owns — no model in the loop | A fresh `codex exec` process per step, spawned by `pipeline drive --executor codex-cli` |
| `standalone` | The same owned process as `driver` | The Agent SDK, using your own API key — no Codex CLI session at all |

`session` and `manager` trade context for moving parts: `session` keeps every
action *and* every step report in the window you are watching (fewest moving
parts, cheapest for a short chain — see [`session-loop.md`](skills/run/references/session-loop.md)),
while `manager` hands the loop to a subagent so a long chain never fills your
session — which is why `manager` stays the default when a pipeline declares no
mode. `driver` and `standalone` share that same owned loop and differ only in
the executor: `driver` shells out to a fresh `codex exec` per step and rides
your existing Codex CLI subscription; `standalone` goes through the Agent SDK
with your own API key instead, so no Codex CLI installation is required at
all. Don't read `driver` (the mode) and `pipeline drive --executor codex-cli` (the command) as
interchangeable — one names a concept, the other names how you invoke it.

**What ships in this plugin today:** `session` and `manager` run through
`$pipeline:run`; `driver` runs through `pipeline drive --executor codex-cli`, which v1 pipelines
select via the `PIPELINE.md` field `runner: headless` (`driver`'s v1 spelling —
a rename with a read-time shim, so nothing that already sets it changes
behavior). `standalone` and a `pipeline.yml`-level `runner:` key belong to this
same four-mode design but are not wired into the `pipeline` CLI yet — nothing
here is a promise that either runs today.

## Using the plugin in a consumer project

This section is the practical walkthrough — install once, then a small set of commands you'll use day to day. Everything below assumes you've run the install commands from the "Install" section at the top and that your terminal's working directory is your **consumer project's root** (the project where you want pipelines to live, not the plugin's own folder).

### Cheat sheet — which command does what

| You want to… | Use | Asks before running? | Cost |
|---|---|---|---|
| Author a new repeatable workflow | `$pipeline:design <goal>` | n/a (writes files) | one-time design cost |
| Pick a pipeline for a task and **see** the match before running | `$pipeline:find <task or GH issue URL>` | yes | ~zero LLM tokens |
| Pick a pipeline for a task and **just run it** | `$pipeline:dispatch <task>` | no | ~zero for ~80% of tasks; low-cost Codex disambiguation when ambiguous; full only for chains |
| Run / resume a specific pipeline you already know the path of | `$pipeline:run <abs-path-to-pipeline-folder>` | no | n/a |

`$pipeline:design` is the only skill that **writes** files (your new pipeline). The matching skills (`find`, `dispatch`) are read-only inspections of `PIPELINE.md` manifests; the run skills (`run`, `dispatch`) execute pipelines that do whatever those pipelines say in their iteration `Steps`.

### Day 1 — author and run your first pipeline

1. **Decide on a *repeatable* goal.** Pipelines are for workflows that will run **many times** in this project — releases, audits, migration templates, "implement-task" scaffolds. **Do not** use them for one-shot tasks (single bug fix, single PR); the designer will push back on those by default.

2. **Design the pipeline.** From the project root:

   ```
   $pipeline:design Cut a release of the API server: bump version, run tests, build image, deploy staging, smoke-test, deploy prod
   ```

   The `$pipeline:design` skill will sketch the step list, confirm scope with you when non-trivial, then write the manifest and its step bodies under `./.pipeline/<pipeline-name>/` — a `PIPELINE.md` manifest plus an ordered `steps/01-*.md`, `steps/02-*.md`, …. Each iteration file is a self-contained PR-sized unit of work.

3. **Sanity-check the result.** Open the new folder yourself; read the manifest's `End State` and the first iteration's `Goal` / `Steps` / `Success Criteria`. The designer is good but not infallible — five minutes reading what it produced now saves ten minutes mid-execution. Edit by hand if needed; iteration files are just markdown.

4. **Run it.** Two equivalent options:

   ```
   $pipeline:run ./.pipeline/release-api
   ```

   …or, more naturally, hand the matcher a task and let it find the right pipeline:

   ```
   $pipeline:dispatch Cut a release of the API server with version 2.5.0
   ```

   `$pipeline:run` supervises; it does not execute.

   | Depth | Who | Does |
   |---|---|---|
   | 0 | `$pipeline:run` | Stays in your session. Owns liveness, the human-facing report, and the hours-long nested-blocker wait. |
   | 1 | `pipeline-manager` | Drives the chain forward until the pipeline completes or halts. |
   | 2 | `step-executor` | One per step, each in a fresh context. |

   You'll see banners in the terminal as it goes.

5. **Re-read the pipeline folder afterwards.** After a successful run, `.pipeline/<pipeline-name>/` is now both a workflow definition and a knowledge base — future maintainers (and future Codex sessions) can read it cold to understand the project's release process. Commit it to git.

### Day 2+ — picking the right pipeline for a task

Once you have a few pipelines in `.pipeline/`, you stop typing pipeline paths and start typing tasks. Two skills, same matcher, different ergonomics:

**Inspection — `$pipeline:find`.** Use when you want to see the match before committing.

```
$pipeline:find Reduce p99 latency on the /api/users endpoint by adding indexes
```

Output looks like:

```
▶ Task: Reduce p99 latency on the /api/users endpoint by adding indexes

Matches:
  1. optimize-db (score 3.42, matched: database, indexes, lookup, query)
     End state: Database query performance is improved through targeted index additions...
     First step: baseline

Excluded by Scope.Out:
  - tune-api-latency: Scope.Out includes ["database index changes"]; matching terms: ["database", "indexes"]

Run "optimize-db" now? [Y/n]
```

The "Excluded by Scope.Out" list shows pipelines the matcher rejected and **why**. That visibility is the whole point of the inspection variant — when the matcher excludes a pipeline you expected to win, the explanation tells you whether to fix the task wording, raise `--neg-threshold`, or edit the rejecting pipeline's `Scope.Out` bullet to be more specific.

**Autonomous run — `$pipeline:dispatch`.** Use when you trust the matcher.

```
$pipeline:dispatch Cut a release of the API server with version 2.5.0
```

Same first-tier match as `$pipeline:find` — stdlib BM25 plus a `Scope.Out`
hard-filter — then it escalates only as far as it has to:

| Outcome | What happens | Cost |
|---|---|---|
| One confident match *(the common case)* | Runs immediately. | Zero LLM cost on matching |
| Top-2 within 2× of each other | A `gpt-5.6-luna` disambiguator reads just those manifests and picks. | Low |
| Zero matches, and the task reads like a chain | Full-context chain detection in the main session. | Expensive, and rare |

**Working from a GitHub issue.** Either skill accepts a URL or `owner/repo#NUMBER` instead of free-form text:

```
$pipeline:find https://github.com/myorg/myrepo/issues/247
$pipeline:dispatch myorg/myrepo#247
```

The matcher calls `gh issue view --json title,body` and uses the issue's title+body as the task. Useful for triaging incoming issues without copy-pasting their text.

### Day-2 — when nothing matches

If `$pipeline:find` returns no candidates and the excluded list doesn't reveal an obvious cause:

1. **Re-read your task wording.** Pipelines match on terminology that appears in `End State` / `Scope.In` / pipeline name. If you describe a "schema migration" but the relevant pipeline calls it "database evolution", your wording and the matcher's vocabulary don't overlap.
2. **Try `--neg-threshold 2`** (you can pass `--` flags after the task in the command if you need to). Default is 1, which is strict. Raising it to 2 means "only exclude if at least 2 task tokens overlap with `Scope.Out`."
3. **Author a new pipeline** with `$pipeline:design <goal>` if no existing pipeline really covers the task and the workflow will repeat.
4. **Fall back to a regular Codex subagent** (`spawn_agent` with a suitable registered agent type, or a generic worker) for genuinely one-shot work — pipelines are for *repeatable* workflows.

### Day-N — letting pipelines improve themselves

Pipelines get better over time without you intervening, on **two tiers**:

**Tier 1 — between steps.** A step that found its own docs ambiguous, missing a
stage, or pointed at the wrong tool says so in its final report. The manager
dispatches `pipeline-improver` before the next step, so the next step reads the
corrected version. A step that notices a long deterministic block paying tokens
on every run flags that too, and `pipeline-script-creator` extracts it to
`scripts/<name>.py` and rewrites the step to one invocation.

**Tier 2 — end-of-run retrospective.** While the run is in flight, every step
writes down *every* problem it hits — not only the blocking ones — into a
gitignored `.feedback/` folder. At the end, one `gpt-5.6-sol` improver pass consolidates
the doc-related ones and fixes the pipeline in a batch.

The split matters: problems the improver cannot fix on its own — real code bugs,
environment issues, general friction — are surfaced to **you** in the final
report instead of being silently absorbed. The feedback folder is cleaned up
afterwards; improvements live in the docs, project problems live in the report.

You don't trigger any of this. It happens during normal `$pipeline:run` invocations. Over a few weeks of use, your pipelines drift toward "iterations contain only the parts that need agent judgment; everything else is in scripts" — which is the cheap-tokens steady state.

See "Self-improving pipelines" and "Token-cheap iterations via script extraction" sections below for the full mechanics.

### Common pitfalls

- **Running from the wrong directory.** Pipelines live in your **consumer project's** `./.pipeline/`, not in the plugin install folder. If `$pipeline:design` ends up writing somewhere unexpected, your CWD wasn't the project root. The plugin install dir (`${CODEX_PLUGIN_ROOT}`) is read-only at runtime; nothing should ever land there.
- **Designing one-shot pipelines.** Both `$pipeline:design` and the `$pipeline:design` skill agent will push back when your goal looks like a single-use task. Take the pushback — pipelines pollute `.pipeline/` if used for one-shot work, since that folder doubles as a knowledge base of your project's *recurring* processes.
- **Editing iteration files mid-chain.** If a pipeline is currently running (executor in flight), don't edit its iteration files by hand. Wait for the chain to halt or complete; then edit, then resume with `$pipeline:run <halted-iteration.md>`. Iterations are designed to be idempotent, so re-running from the halted step is safe.
- **Confusing the dispatch-tier-3 fallback for normal behavior.** If you find yourself paying full LLM cost on every `$pipeline:dispatch` call, your matcher is returning zero candidates because of vocabulary mismatch (your tasks don't share terms with manifest `Scope.In` / `End State`). Fix the manifests' wording or your task wording; don't accept tier 3 as the steady state.

## Iteration file shape

Every iteration file contains these sections (and the `$pipeline:design` skill agent enforces them):

```markdown
# <Iteration Title>

## Goal
One or two sentences.

## Context
- Links to prior iterations (absolute paths).
- Links to project files, specs, docs.

## Inputs
- Files to read, decisions already made, preconditions.

## Steps
1. Ordered, concrete actions — anything requiring agent judgment lives here.
2. Run: `python <abs-path>/scripts/<name>.py [args]` — for long deterministic blocks
   (build/test sequences, file-system manipulations, API call chains). These get
   extracted out of markdown into per-pipeline Python scripts to keep the
   per-iteration token cost low. See "Token-cheap iterations via script extraction" below.
3. More agent-judgment steps using the script's stdout / exit code.

## Success Criteria
- Verifiable, objective, binary.

## Next
- Absolute path to next iteration, OR "Pipeline complete."
```

## Finding the right pipeline for a task

Two user-facing skills, **same matcher under the hood, different ergonomics on top**:

- **`$pipeline:find <task-or-issue-url>`** — inspection variant. Deterministic-only (no LLM). Returns ranked candidates with score, matched terms, and excluded-with-reason output, then asks before running. Use when you want to see the match before committing.
- **`$pipeline:dispatch <task>`** — autonomous variant. Same matcher in tier 1, plus an LLM tiebreaker on ambiguity (tier 2) and a chain-detection fallback on no match (tier 3). Auto-runs without confirmation. Use when you trust the matcher to decide.

Both share the `pipeline match` command — Okapi BM25 over a **positive corpus**
(name, `End State`, `Scope.In`, `Glossary`), hard-filtered by a **negative
corpus** (`Scope.Out`) on keyword overlap.

The split exists because frequency scorers do not understand negation. To BM25 —
and to embeddings — *"update the database schema"* and *"do not update the
database schema"* share almost every token and look alike. Scoring one bucket and
filtering the other is the structural fix. So a pipeline whose `Scope.Out` reads
"database schema migrations" is **excluded, with the reason stated**, from a task
mentioning "database schema" — rather than ranked next to the pipeline you
actually wanted.

### `$pipeline:dispatch`'s three-tier cost ladder

Each call walks down the ladder; it stops at the first tier that produces a usable answer.

| Tier | What runs | When | Token cost |
|------|-----------|------|-----------:|
| 1 | `pipeline match` (BM25 + keyword filter, run with Bun) | always | ~zero |
| 2 | `pipeline-disambiguator` agent (`gpt-5.6-luna`) with 2–5 ambiguous candidates' manifests inlined | when the matcher returns ≥ 2 candidates with top1/top2 score ratio < 2.0 | low — scales with ambiguity, not project size |
| 3 | Main-session reasoning over all manifests to detect a chain | when the matcher returns 0 candidates AND task contains chain phrasing (`then`, `after that`, `followed by`, …) | full — same as the pre-refactor design used to cost on every call |

The 80% case (one pipeline obviously matches): tier 1 only, no LLM. The 15% case (ambiguous): tier 1 + low-cost Codex tier 2. The 5% case (chain across pipelines): tier 1 + tier 3. Average token cost per dispatch dropped by ~90% versus the pre-refactor design where every call paid the tier-3 cost.

Example output:

```
▶ Task: Cut a release of the backend server with a changelog update

Matches:
  1. release-server (score 5.0, matched: new, release, backend, server, changelog)
     End state: A new tagged release of the backend server is published to production with no rollback required.
     First step: bump

Excluded by Scope.Out:
  - migrate-db: Scope.Out includes ["server release"]; matching terms: ["release", "server"]
  - audit-deps: Scope.Out includes ["server release"]; matching terms: ["release", "server"]

Run "release-server" now? [Y/n]            # $pipeline:find — asks
▶ Why: BM25 confident match (ratio 4.2)    # $pipeline:dispatch — auto-runs
```

For a GitHub issue, run either skill with the URL: `$pipeline:find https://github.com/owner/repo/issues/123`. The matcher calls `gh issue view --json title,body` and uses that as the task. Useful when triaging incoming issues.

The disambiguator lives in this plugin; the matcher runs as `pipeline match` in the **`@baizor/pipeline` CLI**, which you install once (`bun add -g @baizor/pipeline`) and which this plugin requires anyway — see [Install](#install). Nothing extra is installed *per consumer project*. (`gh` is needed only for the `--issue` form.)

## Self-improving pipelines

Pipelines get better over time by feeding concrete lessons back into their own documentation. This works on **two tiers**.

**Tier 1 — between steps.** A `step-executor` that finishes and realises the step
*as written* would block the next one — a missing stage, an ambiguous success
criterion, an unstated precondition — emits a structured brief: what was wrong,
what the correct knowledge is, and the exact edits to apply.

The `pipeline-manager` picks it up and dispatches `pipeline-improver`
synchronously, before the next step spawns. (Depth 1: dispatching the improver is
between-steps chain orchestration, which is the manager's job, not a step's.) The
improver makes minimal surgical edits to the step file — or `PIPELINE.md` for a
pipeline-wide invariant — and the chain continues, so the next step reads the
corrected file from disk.

**Tier 2 — end-of-run retrospective.** Tier 1 carries only the single most
blocking flaw per step. Everything else is journalled as it happens into a
gitignored `<pipeline-root>/.feedback/<run_id>/`, one file per problem, written
immediately so it survives a crash.

When the run ends — completed or halted — the manager sorts what it collected:

| Bucket | Contains | Goes to |
|---|---|---|
| **Doc-actionable** | doc flaws, ambiguities, script-extraction candidates | One `gpt-5.6-sol` `pipeline-improver` batch pass that consolidates, dedups, and applies the fixes — reading current state first, so it never re-does what Tier 1 already landed — then hands confirmed extractions to `pipeline-script-creator`. |
| **Human-only** | real project bugs, environment issues, general friction | Straight to you, summarised in the run's final report. |

The pipeline never tries to auto-fix your code or your machine. The feedback
folder is deleted afterwards: doc improvements live in the step files, and the
human-only summary lives in the report.

Boundaries:

- Improvements target pipeline **documentation** only (files under `.pipeline/<name>/`). Never consumer project code.
- Project-side bugs (real code issues, flaky tests, environment problems) do NOT trigger doc improvements — they are surfaced to you in the retrospective summary instead. Only flaws in the iteration's own docs are auto-fixed.
- The improver refuses changes that would break the chain, delete Success Criteria, or renumber files.
- Tier-1: one improvement brief per iteration, max. Tier-2: one batch improver pass per run, run once at the end (a no-op when no problems were journaled).
- The `.feedback/` tree is gitignored by a self-contained `.feedback/.gitignore` (a single `*`), so feedback never lands in your commits.

You can also invoke the registered `pipeline-improver` custom agent directly through `spawn_agent` when you spot a pipeline-doc flaw yourself.

## Token-cheap iterations via script extraction

Iteration markdown is paid in tokens on every fresh-context run. A 60-line "do this then this then this" block of imperative shell-style detail in `Steps` becomes a permanent tax on every executor that ever reads the iteration. The plugin's `pipeline-script-creator` agent removes that tax by relocating deterministic procedural blocks to Python scripts.

How it lands automatically:

1. `step-executor` runs an iteration and notices a `Steps` block that is long, deterministic, and judgment-free. It includes a `SCRIPT-EXTRACTION CANDIDATE` bullet inside its `improvement_brief` (it does not extract scripts itself).
2. The `pipeline-manager` spawns `pipeline-improver` with the brief.
3. `pipeline-improver` applies any text edits, then — if the extraction is warranted — emits a `script_creation_briefs` list (0 or 1 entries in this between-steps path; several in the end-of-run retrospective) in its own structured final report. It does not write the script either; that is `pipeline-script-creator`'s job.
4. The `pipeline-manager` parses the improver's report and spawns `pipeline-script-creator` once per brief in the list, sequentially. The script-creator writes a cross-platform Python file under `<pipeline-root>/scripts/<name>.py`, runs `--help` to verify it parses, then rewrites the iteration's `Steps` to invoke the script with one command line.
5. The next executor starts in a fresh context and reads the slimmed-down iteration. Token cost on every future run drops accordingly.

Boundaries:

- Scripts live at `<your-project>/.pipeline/<pipeline-name>/scripts/<name>.py` — sibling to `steps/`, never inside it. Per-pipeline only; no cross-pipeline sharing in v0.8.0.
- Stdlib only by default. Cross-platform (`pathlib`, `tempfile`, no POSIX shell syntax). Argparse-driven CLI with `--help`. Idempotent.
- The script-creator refuses extractions that would require agent judgment, deletions of `Success Criteria`, renumbering, or breaking `Next` links. It is a leaf agent — it does not loop back to the executor or improver.

You can also invoke the registered `pipeline-script-creator` custom agent directly through `spawn_agent` when you've drafted a structured `script_creation_brief` yourself and want to apply it manually.

## Script steps (zero-token steps)

Script extraction (above) takes the *heavy procedural block* out of an agent
step — the agent still reads the result and decides what happens next. When the
**whole** step is deterministic (a build gate, a CI wait, a fixed file or API
sequence with no judgement in it), go one rung further and make the step itself
the program.

Set `type: script` and the `pipeline next` engine runs it **in-process, for zero
LLM tokens** — the same mechanism that runs `isolation: run` worktree hooks. A
step that used to cost a ~10–20k-token executor spawn now costs nothing.

The three-rung extraction ladder:

1. **Inline `Steps`** — only where agent judgment is needed.
2. **A script called from inside an agent step** — the script-extraction path above; the agent still reads the result and decides.
3. **`type: script`** — the whole step is the program (this section).

It is fully backward-compatible: absent `type:`, a step is an `agent` step exactly as before, and an old runtime that doesn't understand `type: script` treats the file as a plain agent step (via a one-line `## Steps` fallback).

A minimal script step — the whole declaration is a manifest entry:

```yaml
  - name: wait-ci
    type: script
    script: scripts/wait-ci.py     # path relative to the pipeline root
    timeout: 1800
    retries: 2                     # re-run transient failures (network blips)
    on_failure: halt               # or 'agent' to fall back to a step-executor
    params:
      pr_number:
        type: number
        required: true
        from: ${steps.open-pr.output.pr_number}
    output:
      ci_green:
        type: boolean
```

The script prints one JSON object as its last stdout line:
`{"ok": true, "flags": {"ci_green": true}, "output": {…}}`.

`ok:true` means "the step did its job" — a domain "no" (CI red, nothing to release) is still `ok:true` with a `flags` entry the pipeline's `## Graph` routes on. `ok:false` is reserved for "the step could not run at all" and (with `on-failure: halt`) stops the run. `flags` become the step's `result_flags`; anything in `output` is persisted so later steps can bind to `${steps.wait-ci.output.checks_passed}`.

Test a script step in isolation before wiring it into a chain — no run required:

```
pipeline step run ./.pipeline/release-api/steps/03-wait-ci.md --param pr_number=132 --json
```

The full contract lives in **[`docs/script-steps.md`](docs/script-steps.md)**:
manifest keys, the `params:` / `output:` vocabulary and `${…}` bindings, the
**frozen** process I/O contract (env vars, params file, stdin/stdout, exit
semantics, the `ok:false` rule), failure classes with `retries` / `on_failure`
agent fallback, the timeout and call-budget ladder, the attempt ledger that makes
retries idempotent, the outputs store, and secrets handling.

## Waiting on GitHub CI without burning tokens (`pipeline ci-wait`)

The classic agentic-workflow money pit: a step needs CI to pass, so the agent hand-rolls a poll loop — sleep, run `gh pr checks`, read the whole check table into context, repeat — burning a full agent turn per poll. Worse, agents happily wait **hours** for full CI completion when one job already failed (or hung) and the outcome was decided long ago.

`pipeline ci-wait` replaces the loop with ONE Bash call that blocks until CI reaches a terminal state and prints ONE compact result:

```
pipeline ci-wait --pr 123 --json          # wait on a pull request's checks
pipeline ci-wait --branch main --json     # wait on a branch's HEAD commit (sha pinned at start)
pipeline ci-wait --json                   # no selector = the repo's default branch
```

- **Fails fast by default.** The FIRST failed or cancelled check ends the wait immediately — even while other jobs are still running or stuck. Pass `--no-fail-fast` when you genuinely need the full picture.
- **Never blocks forever.** `--timeout <sec>` (default 1800) caps stuck CI → exit 3 with the still-pending check names; `--grace <sec>` (default 120) bounds the "CI never started" case → exit 4, deliberately distinct from success so "no checks" can never read as a green gate.
- **Silent while waiting.** No output until the verdict (opt into stderr heartbeats with `--verbose`); the result is one line, or one JSON object with `--json`.
- **Exit codes are the contract**: `0` all passed · `1` a check failed · `2` usage / `gh` missing · `3` timeout · `4` no checks appeared. An iteration step just runs it and branches on the code — no poll loops in step docs.

`--pr` accepts a number, URL, or head-branch name (via `gh pr checks`, covering Actions and third-party checks). `--branch`/`--sha` poll the commit check-runs API; a branch is resolved to its HEAD sha once at start, so a later push is a new gate rather than a moving target. Requires an authenticated `gh` CLI (`--repo <path>` selects which repo's remote to use; default: the current directory).

## Measuring every run (`.pipeline/.stats/` + `$pipeline:optimize`)

Every pipeline run is measured by **pure software — no AI agent, zero LLM tokens**. It is ON by
default (`PIPELINE_STATS_ENABLED=0` disables). The `pipeline next` engine appends a timeline as the
run progresses and finalizes it at the terminal action; token counts are then folded in from the raw
manager + subagent transcripts (the only complete token source) by whichever rung gets there first —
the `Stop`/`SubagentStop` relay, the next run's init, or
`pipeline stats backfill` on demand. All three call one shared core, so the numbers are identical
whichever one fills them in, and a run whose enrichment was missed is reconciled later instead of
staying blank forever. You get
simple text files to review whenever you like:

```
.pipeline/.stats/
  SUMMARY.md                      # the whole picture: per pipeline — runs, success rate,
                                  #   avg duration, avg out-tokens, avg tool fails,
                                  #   last run + recent-runs table
  <pipeline>/runs.jsonl           # one machine-readable record per finished run
  <pipeline>/runs/<run-id>.log    # human per-run timeline: step-by-step timings, outcome,
                                  #   tokens + a "tool fails" section (per-failure detail)
```

**Tool failures are measured, not just outcomes.** Enrichment also records how many tool calls
FAILED during the run (`tokens.tools_failed` + a per-tool breakdown like `{"Bash": 5}`), and
appends each failure — timestamp, tool, the step it happened in, the error the tool returned —
to the run's `.log`. A run can be "completed" and still be sick: dozens of failed calls mean the
steps are retrying their way to success on wrong instructions. `driver` (`pipeline drive --executor codex-cli`) runs
fold their pinned per-step session transcripts at the terminal action, so their failures carry
exact step attribution; manager runs attribute by step time-windows.

View from the terminal any time with `pipeline stats [--project <path>] [--json]` (regenerates and
prints `SUMMARY.md`). Crashed/killed runs surface in SUMMARY under "in-flight or
crashed" via their leftover timeline buffers.

**Closing the loop — `$pipeline:optimize`.** A deliberately **user-invoked-only** skill
(marked `USER-INVOKED ONLY` in its description so agents do not auto-trigger it): run it weekly
(or whenever) and it reads `SUMMARY.md`, flags pipelines whose halts/duration/tokens regressed
against their own history — and pipelines with recurring tool failures (same tool failing run
after run) — digs into the relevant `runs/<id>.log` files only, and — with your approval —
applies targeted fixes through `pipeline-improver`. Failure-driven fixes are held to a standard:
only pipeline-attributable patterns (wrong command/path in a step's instructions, missing
preflight) get edits; one-off environment noise is reported, not "fixed". The stats files then
serve as the before/after evidence for whether each optimization helped.

## Nested-blocker delegation

Sometimes a step hits a problem whose fix is clearly **outside the current
task's scope** and blocks all further progress — a broken tool in a module this
task depends on, a missing upstream API, a regression in `main` that has to land
before this can even compile.

The work is split across two depths, and the reason is structural: a subagent
cannot wait hours for a PR to merge, or hold a poll-and-merge loop across a
finite context.

| Who | Does |
|---|---|
| `step-executor` *(subagent)* | Recognises the blocker and prepares a brief. Nothing else. |
| `$pipeline:run` *(main session)* | Files the issue, spawns the child run, and does the waiting. |

1. The executor stabilizes the parent branch (commits what's done, or reverts the unfinished chunk so the branch is green) and picks the blocker's target repo and base branch.
2. The executor emits a `blocker_delegation` brief in its final report with a full issue body, the child pipeline's first iteration path, a `partial_work_note` for resumption, and poll/deadline settings.
3. The `pipeline-manager` relays the brief up to `$pipeline:run`, which files a
   **new GitHub issue** on the blocker's target repo, posts a back-link on the
   parent's issue so the relationship is visible from both sides, and spawns a
   **child run** via Codex's native `spawn_agent`. The child's worktree defaults to `main` of
   the target repo; the parent's branch is used as the base only when `main`
   lacks state that is strictly prerequisite to starting the fix.
4. `$pipeline:run` **waits** — polling for the child PR to merge (default interval 5 minutes, default deadline 4 hours) — instead of advancing the chain.
5. On merge, `$pipeline:run` fetches the blocker target's updated base, merges (or rebases) it into the parent's branch, re-runs the iteration's verification gate, and re-invokes the `pipeline-manager` to re-enter the original iteration with the `partial_work_note` embedded in the prompt.

Closed without merging, merge conflicts, a red verification gate, or a hit
deadline all **halt the chain for human review** rather than auto-retrying.

The protocol is deliberately split across two files, and they have to move
together:

| Side | Covers | Lives in |
|---|---|---|
| Executor | in-scope vs tangent vs blocker heuristics, brief shape, executor invariants | `step-executor`'s prompt, "Nested-Blocker Delegation" |
| Caller | issue creation, child spawn, poll-wait, merge, re-invocation | `$pipeline:run`'s skill, "Nested-Blocker Flow" |

If you edit one side, edit the other in lockstep.

## Nesting

When a single step is too large, split it into several steps. There is no
nesting to arrange: the manifest is a flat list, and `needs:` says what depends
on what — so "a sub-pipeline inside a step" is just more entries.

```yaml
steps:
  - name: plan
    body: steps/plan.md
  - name: scaffold
    body: steps/scaffold.md
  # what used to be a nested folder is three ordinary steps
  - name: core-module
    body: steps/core-module.md
  - name: adapters
    body: steps/adapters.md
  - name: wire-up
    body: steps/wire-up.md
  - name: verify
    body: steps/verify.md
```

## Parallel / DAG pipelines (opt-in)

Two fields turn concurrency on, and **both are required** — `needs:` alone stays
sequential:

```yaml
execution: parallel          # pipeline-level: may independent steps overlap?

steps:
  - name: build
  - name: lint       {needs: [build]}
  - name: typecheck  {needs: [build]}
  - name: test       {needs: [build]}
  - name: package    {needs: [lint, typecheck, test]}
```

`needs:` is data and always means what it says; `execution:` decides only how
much of the graph may run at once. Keep it sequential when in doubt —
parallelism is an optimisation for genuinely independent work, not a default.

In DAG mode, native manager subagents can overlap only when the pipeline owns a
safe manual-isolation strategy; they otherwise share the caller's working
directory. Per-step worktree isolation is provided by the process driver. A
manager-mode run that requests it halts with an actionable message instead of
pretending the subagents are isolated.

### `isolation:` — one axis, three values

Isolation is **scope, and nothing else**.

| Value | What you get | Use when |
|---|---|---|
| `none` | No worktree. Steps run in place. | Sequential pipelines that touch only their own outputs — the default, and right for most. |
| `step` | One throwaway git worktree per step, merged back on success by the process driver. | `execution: parallel`, where concurrent steps must not see each other's files. |
| `run` | One worktree for the whole run, provisioned by your own hooks. Sequential only. | Steps need what git alone cannot give: allocated ports, a rendered `.env`, dev secrets, submodule worktrees. |

> **v1's `worktree`, `manual` and `external` are gone.** They named three
> different axes — mechanism, ownership, provenance — and two were inert in
> sequential mode. An unknown value is now a hard **error**, not a warning with a
> fallback: `isolation: manager` once ran for months with no isolation at all,
> and that is the failure this refusal exists to prevent.

### `isolation: run` — the hook contract

The CLI executes your convention-path hooks itself, in-process, with no agent
involved:

| Hook | When | Must print |
|---|---|---|
| `.pipeline/.hooks/worktree-create` | Once at run start, before the first step | One JSON object: `worktree_path`, `branch`, `env_file`, `ports`. Idempotent per name. |
| `.pipeline/.hooks/worktree-finalize` | Once after the last step of a **completed** run, before teardown | `{"ok":true}` — or the run **halts with the worktree preserved**. Optional; its presence opts you in (or set `finalize: true`). |
| `.pipeline/.hooks/worktree-destroy` | Once on every terminal outcome, including halt | `{"ok":true}`, or soft-fail with `{"ok":false,"detail":"…"}`. |

Inputs arrive as `PIPELINE_WT_*` environment variables; finalize additionally
gets `PIPELINE_WT_ACTION=finalize`. Steps `cd` into the provisioned worktree and
source its env file — they never re-allocate anything. Declare which submodules
to include with `submodules: [a, b, c]`.

Three behaviours worth knowing before you rely on it:

- **Missing hooks halt the run.** It never silently falls back to running in
  place.
- **`isolation: run` + `execution: parallel`** degrades to `step` with a
  warning. Run-scoped isolation is sequential-only.
- **The finalize stage is generic.** The plugin has no idea what your hook does
  — commit, push, publish, anything. It only requires `ok`.

**Worktree-scoped I/O (default).** A run with `isolation: run` reads its pipeline
definition from — and self-improves into — the *worktree's* copy. So a branch
that modifies its own pipeline runs its own version, and improver edits ride your
finalize commit instead of dirtying the main checkout. Only **committed** state
reaches the run, and the CLI warns when the main pipeline directory is dirty. Run
bookkeeping (`next.json`, events, `.stats`) stays under the main checkout.
`PIPELINE_WORKTREE_SCOPED=0` restores the legacy main-scoped reads; the flag is
frozen per run at init.

### `pipeline submodule bump`

When a run advances a git submodule and the superproject's pointer has to be
recorded on its base branch, call this rather than hand-rolling `git`:

```bash
pipeline submodule bump --project-root <superproject>   [--submodules a,b] [--base <branch>] [--source-worktree <path>] [--dry-run] [--json]
```

The shared checkout is never `checkout`/`reset`/`switch`ed — its only mutation is
`fetch` + `merge --ff-only`; all branch work happens in a throwaway worktree off
`origin/<base>`. The guards make the dangerous mistakes impossible:

- refuses a pointer that differs only because the base advanced past the run's
  fork — **no accidental reverts**;
- skips a pointer the base changed since the fork — **no clobbering a concurrent
  bump**;
- only bumps to a commit reachable from the submodule's `origin/<default>`;
- self-cleans orphaned worktrees from prior killed runs before starting;
- stops on any error with a structured `halt_reason` and the exact manual
  recovery.

Pointers drifted from `.gitmodules` are auto-detected when `--submodules` is
omitted, and a project with no submodules is a no-op. Output is one JSON object
(`{status, bumped[], skipped[], pr, infra_sha, …}`); exit `0`/`1`/`2`. Needs
`git` and `gh` on `PATH`.

## Configuration reference

Everything configurable, in one place. All fields are OPTIONAL — a pipeline with no frontmatter at all is a plain sequential chain driven by a pipeline-manager, with every step inheriting your session model.

**`pipeline.yml` — pipeline-level keys:**

| Key | Values (default first) | What it does |
|---|---|---|
| `schema:` | `2` | Required, exact. A manifest that does not say which format it is written in is the ambiguity v2 removes. |
| `name:` | — | Required. The pipeline's name. |
| `description:` | — | One line — shown by `$pipeline:find`, and matched against your task. |
| `execution:` | `sequential` \| `parallel` | `parallel` dispatches each dependency layer at once. The graph itself is `needs:`; this decides only how much of it may run together. |
| `isolation:` | `none` \| `step` \| `run` | The SCOPE of a git worktree: none, one per step (parallel layers, merged after), or one per run (consumer-provisioned, sequential-only). |
| `defaults:` | — | `model:` / `effort:` inherited by every step that does not set its own. |
| `base_branch:` | `main` | `isolation: run` only — what your create hook forks the run worktree from. |
| `submodules:` | `[]` | `isolation: run` only — submodule names the worktree should include. |
| `vars:` | — | `${PP_NAME}` values substituted into step prompts. |
| `self_improve:` | `true` | Whether automated passes may edit step prompts. A step can override it. |
| `flow:` | — | Conditional routing: step name → edges. Absent ⇒ the step list is the order. |

**`pipeline.yml` — per-step keys:**

| Key | Values (default first) | What it does |
|---|---|---|
| `name:` | — | Required, unique. THE step's identity — in `needs:`, in `flow:`, in `--start`, in the journal. |
| `type:` | `agent` \| `script` \| `pipeline` \| `gate` | What runs it. |
| `body:` | — | The markdown it reads. A path, or a LIST to compose several (optionally conditional). Required for an agent step. |
| `needs:` | *(the previous step)* | Which steps must finish first. `[]` means none — that is how a step joins the first layer. |
| `model:` / `effort:` | *(pipeline default)* | Pin this one step. |
| `retries:` | `0` | Bounded re-dispatch after a transient failure (agent and script steps). |
| `self_improve:` | *(pipeline default)* | `false` freezes this step's prompt — and every file it composes. |
| `script:` | — | `type: script` — the script to run, pipeline-root-relative. |
| `timeout:` / `on_failure:` | `600` / `halt` | `type: script` — seconds, and `halt` or an `agent` fallback. |
| `params:` / `output:` | — | `type: script` — its inputs and what it publishes downstream. |
| `pipeline:` / `args:` | — | `type: pipeline` — a child pipeline and its inputs. |
| `required_role:` / `message:` | — | `type: gate` — who may approve, and the prompt they see. |

A key on a step kind that cannot use it is an **error**, not a warning. A step
whose declared inputs never bind is the loudest failure this format prevents.

**Per-run model & effort overrides (no file edits):** to run the SAME pipeline once with different models or reasoning efforts on specific steps, pass overrides on the command — they beat the manifest for that run only and are persisted so resumes keep them.

**`flow:` (optional)** — conditional routing, as data rather than a mode:

```yaml
flow:
  review:
    - { when: changes_needed, goto: implement, max: 3 }
    - { goto: package }
  package:
    - { done: true }
```

`when` matches a result flag a step reported; `max` bounds how many times an
edge may be taken per run. Always end a conditional node with a default edge.

**Environment variables** (dashboard on/off, prompt-match hook, `driver` executor command, hook timeouts, debug flags): see [Environment variables (reference)](#environment-variables-reference) below.

## No leaked branches or worktrees

Cleanup is part of the run contract, and it is outcome-aware:

- **Parallel / DAG runs** (`isolation: step`): after each clean merge the runtime deletes the merged branch (`git branch -d`) and removes its worktree (retrying with `--force` when build artifacts block it). A COMPLETED parallel run leaves zero `worktree-*` branches and zero entries under `.codex/worktrees/`.
- **External-isolation runs**: on a COMPLETED run the destroy hook is invoked with `PIPELINE_WT_DELETE_BRANCHES=1` so the run branch dies with the worktree (opt out via `delete_branches: false`). On `halted` / `depth-exhausted` the worktree AND branch are deliberately preserved for post-mortem and resume — that is not a leak, it is evidence.
- **Failure paths are surfaced, never silent**: a merge conflict or mid-layer halt enumerates every not-yet-merged branch + worktree path in the halt detail.

Verify (or clean) at any time with the CLI's janitor:

```
pipeline gc            # report: registered/stale worktrees, prunable records, orphaned worktree-* branches
pipeline gc --clean    # prune + remove merged-only worktrees + safe-delete (-d) merged worktree-* branches
```

**Submodules are scanned too** (skip with `--no-submodules`): external-isolation runs provision worktrees in every declared submodule, so historically each run leaked one `worktree-*` branch into EACH submodule repo. `gc` reports them per submodule against each repo's own default branch, and `--clean` applies the same safe rules inside every submodule.

`--clean` is conservative by design: it never force-deletes a branch, never
touches unmerged work or the current checkout, and lists everything it kept and
why.

One documented exception, scoped to the machine-owned namespace:
`--clean --force-worktree-branches` force-deletes (`-D`) **unmerged** `worktree-*`
branches. It is needed because a squash-merged run branch reads as "unmerged" to
git forever. It never touches a branch outside that pattern.

## Where things live

| What                          | Where                                             |
|-------------------------------|---------------------------------------------------|
| Your pipelines                | `<your-project>/.pipeline/<pipeline-name>/...` |
| Parallel-step worktrees       | Available through the process driver; native manager subagents share cwd and reject runtime worktree isolation |
| Per-pipeline scripts          | `<your-project>/.pipeline/<pipeline-name>/scripts/*.py` |
| Per-run feedback (Tier-2)     | `<your-project>/.pipeline/<pipeline-name>/.feedback/<run_id>/` (gitignored, transient — created at run start, deleted after the end-of-run retrospective) |
| Plugin agents                 | `${CODEX_PLUGIN_ROOT}/agents/*.toml` (read-only)   |
| Plugin skills                 | `${CODEX_PLUGIN_ROOT}/skills/*/SKILL.md` (read-only) |

The plugin never writes inside itself. Every pipeline file, every code edit performed by an executor, every log entry — all land in the consumer project's working directory.

## Watching a run

Runs are recorded as they happen in an append-only journal at
`<project>/.pipeline/.runtime/events.jsonl`. There are two ways to watch one.

**The hosted dashboard at [ai-pipeline.dev](https://ai-pipeline.dev)** is the UI.
Run `pipeline cloud connect` once and every run — from `$pipeline:run`,
`$pipeline:dispatch`, `pipeline drive --executor codex-cli`, or cloud dispatch — streams there: run
list, step tree, timings, token counts and cost, tool-call and failure counts,
the parked-question surface, and per-run analytics. It is installable as a web
app, so it works from a phone without exposing anything on your network. What it
receives is step metadata only — your prompts, transcripts, code, file paths,
tool arguments and error text never leave your machine — see
[Privacy tiers](docs/privacy-tiers.md), which lists the allowlist field by
field, and [Connecting to the cloud](docs/cloud-connect.md).

**`pipeline logs` is the offline path** and needs no account, no daemon and no
network — see the next section. `pipeline logs -f` tails the same journal live,
and `pipeline logs --chat <run-id>` renders a finished `driver` run's Codex CLI
transcript in the terminal, which is the post-mortem a Codex `pipeline drive --executor codex-cli` run
otherwise leaves scattered across files nobody opens.

> **Historical note.** Earlier versions shipped a *local* browser dashboard
> (`$pipeline:ui`, a background Bun daemon serving a React app). It was deleted:
> the hosted dashboard is already better at the shared 90%, and the two local
> capabilities without a cloud equivalent were moved into the CLI as
> `pipeline logs --chat` and `pipeline fix` before it went. `pipeline ui`,
> `$pipeline:ui`, the daemon and its `SessionStart` launcher no longer exist.

### Terminal logs — `pipeline logs`

Watch events scroll by in a terminal, pretty-printed as one line per event:

```bash
# from anywhere inside a pipeline project:
pipeline logs --follow
```

```
08:00:01 ▶ pipeline.started   abcdef12  build-cli [gpt-5.6-sol]
08:00:02 → iteration.started  abcdef12  #1 01-scaffold.md [gpt-5.6-sol]
08:00:03 · tool.called        abcdef12  Bash
08:00:05 ✓ pipeline.completed abcdef12  build-cli
```

Flags: `-f`/`--follow` to stream live, `--tail <n>` (default 20) for the initial backlog, `--all` for the whole journal, `--json` for raw JSON lines, `--no-color`, and `--project <path>` to point at a project other than the cwd. It is **read-only** — it starts no background process and writes nothing — so it works with or without a cloud account. Stop it with Ctrl-C.

`pipeline logs --chat <run-id>` is the other half: it renders that run's Codex CLI transcript(s) in the terminal — the post-mortem for a `driver` (`pipeline drive --executor codex-cli`) run, whose steps execute as separate processes and whose subagent transcripts otherwise become files nobody opens. It reads only what is already on your disk and uploads nothing.

### The journal/analytics master switch — `PIPELINE_JOURNAL_ENABLED`

**The analytics hooks are ON BY DEFAULT** — they work out of the box, with no setup. To turn the whole system off, explicitly opt out by setting the environment variable `PIPELINE_JOURNAL_ENABLED` to a falsy value (`0`, `false`, `no`, or `off`):

```jsonc
// .codex/settings.json  (per project — hooks inherit the session env)
{ "env": { "PIPELINE_JOURNAL_ENABLED": "0" } }
```

> Renamed from the `PIPELINE_UI_` prefix in plugin-thin `p4` (clean break, no alias — there were no users to break). That prefix was a leftover from the deleted local dashboard; these variables gate the **journal**, which is not going anywhere.

While it is **unset** (the default), or set to any non-falsy value, the system is on:

- the `SessionStart` hook writes `session.opened`,
- the analytics hooks (`PreToolUse`/`PostToolUse`/`SubagentStop`/`Stop`) emit events and mirror bindings (the `Notification` hook is separate — it keeps its own `PIPELINE_AWAITING_INPUT_ENABLED` switch and still reports a blocked run when the rest is opted out).

Opted out (`0`/`false`/`no`/`off`), the `SessionStart` hook does not write
`session.opened` and the analytics hooks emit nothing and touch no files. Your
pipelines run identically either way — the variable controls the observability
layer and nothing else. It can also be set in your shell or OS environment
before launching Codex CLI.

Two things it does *not* do:

- **It does not unregister the hooks.** Those registrations live in the plugin,
  so Codex CLI still launches each hook's instantly-exiting process. To remove
  even that, disable the plugin.
- **It does not silence `pipeline logs`.** The core run lifecycle is journalled
  by `$pipeline:run` regardless, so the terminal view keeps working.

> Performance note: `SubagentStop` only fires the hook for the `pipeline-manager` subagent (via a `matcher`), so the dozens of other subagent stops in a run no longer spawn a hook process.

### Transcript opt-out — `PIPELINE_JOURNAL_TRANSCRIPTS`

Keep the journal on, but opt **out of the one privacy-sensitive part**: reading your Codex CLI **transcripts**. `PIPELINE_JOURNAL_TRANSCRIPTS` is **ON BY DEFAULT** and, unlike the master switch above, gates **only** the transcript work — nothing else. Set it to a falsy value (`0`, `false`, `no`, or `off`) to disable just that:

```jsonc
// .codex/settings.json
{ "env": { "PIPELINE_JOURNAL_TRANSCRIPTS": "0" } }
```

What it gates (all OFF when opted out):

- the **transcript pointer** recorded on a run's mirror binding — the thing that makes a session's transcript reachable at all,
- the `Stop` hook's transcript **token tail** (`turn.usage`).

What keeps working:

- the basic pipeline-lifecycle events — `pipeline.*`, `iteration.*`, `tool.called`, `manager.stopped`, `session.opened` — and the run timeline/liveness they drive,
- run correlation: the mirror **binding is still written** (so events still attribute to the right run), just **without the transcript pointer**,
- `pipeline logs --chat`, which reads a transcript on your own disk on demand and never involves a pointer.

This switch is **orthogonal** to `PIPELINE_STATS_ENABLED` — the separate local `.pipeline/.stats/` measurement fold keeps its own switch and its own default. Setting `PIPELINE_JOURNAL_ENABLED=0` (the master switch) already turns everything off, so `PIPELINE_JOURNAL_TRANSCRIPTS` only matters while the hooks are on.

### Prompt match hook (opt-in) — `PIPELINE_PROMPT_MATCH_ENABLED`

The plugin also ships a `UserPromptSubmit` hook that surfaces a matching
pipeline for whatever you just typed — deterministic auto-discovery with **zero
always-loaded context**. It runs the same BM25 matcher as `$pipeline:find` and
`$pipeline:dispatch` against your prompt.

It speaks **only on a confident single match** — exactly one candidate, or a top
score at least 2× the runner-up, the same threshold `$pipeline:dispatch` uses —
and then injects one line suggesting `$pipeline:run` or `$pipeline:dispatch`. On
no match or an ambiguous one it stays completely silent. It never blocks or
modifies your prompt.

Unlike the journal/analytics system (on by default), this hook is **OFF BY DEFAULT** and gated by its own environment variable (same non-falsy value parsing as `PIPELINE_JOURNAL_ENABLED`, but its own opt-in default):

```jsonc
// .codex/settings.json  (per project — hooks inherit the session env)
{ "env": { "PIPELINE_PROMPT_MATCH_ENABLED": "1" } }
```

When enabled, it still skips silently for explicit skill/plugin commands, prompts shorter than 20 characters, and projects with no `.pipeline/` directory — so it only ever speaks up when a free-form task genuinely looks like one of your pre-authored pipelines.

### Environment variables (reference)

Everything the plugin reads from the environment, in one place. Set the per-project ones via `.codex/settings.json` → `"env": { ... }` (hooks and skills inherit the session environment).

**User-facing configuration:**

| Variable | Default | Purpose |
|---|---|---|
| `PIPELINE_JOURNAL_ENABLED` | **on** | Master opt-OUT for the journal/analytics hooks (`SessionStart` + `PreToolUse`/`PostToolUse`/`SubagentStop`/`Stop`). Enabled unless explicitly set to a falsy value; `0`/`false`/`no`/`off` disables, unset/empty/any other value enables. |
| `PIPELINE_JOURNAL_TRANSCRIPTS` | **on** | Opt-OUT for **only** the transcript work: the `transcript_path` pointer recorded on a mirror binding, and the `Stop` hook's token tail. `0`/`false`/`no`/`off` disables just that; the basic lifecycle events and run correlation keep working. Orthogonal to `PIPELINE_JOURNAL_ENABLED` and `PIPELINE_STATS_ENABLED`. |
| `PIPELINE_STATS_ENABLED` | **on** | Per-run measurement files under `.pipeline/.stats/` (durations, per-step timings, outcomes, tokens, tool failures — see "Measuring every run" above). Set `0`/`false`/`no`/`off` to disable. Independent of `PIPELINE_JOURNAL_ENABLED` and `PIPELINE_JOURNAL_TRANSCRIPTS`. |
| `PIPELINE_AWAITING_INPUT_ENABLED` | **on** | The `Notification` hook that journals `run.awaiting_input` when a permission prompt or an input request blocks the session — the `⏸` line in `pipeline logs` and the awaiting-input surface in the cloud dashboard. Deliberately INDEPENDENT of `PIPELINE_JOURNAL_ENABLED`: a blocked run is worth surfacing even when the rest is opted out. `0`/`false`/`no`/`off` disables. |
| `PIPELINE_PROMPT_MATCH_ENABLED` | off | Opt-in for the `UserPromptSubmit` pipeline-match hook (section above). Same non-falsy semantics. |
| `PIPELINE_DEPARTMENT_NOTIFY_ENABLED` | **on** | Opt-OUT for the departments background notifier (section above): its `SessionStart` launcher and the pending-notification drain. `0`/`false`/`no`/`off` disables; no-ops anyway until `pipeline cloud connect` has been run once. The old name, `PIPELINE_MESH_NOTIFY_ENABLED`, is still read as a fallback (with a deprecation warning) when this one is unset. |
| `PIPELINE_CLOUD_API` | `https://api.ai-pipeline.dev` | Overrides the control-plane API base used by `pipeline cloud connect` and the department notifier. |
| `PIPELINE_CLOUD_HOME` | platform default (`%APPDATA%\pipeline-codex` on Windows, `$XDG_CONFIG_HOME/pipeline-codex` / `~/.config/pipeline-codex` elsewhere) | Overrides the per-user directory holding the cloud credential store and the department notifier's journal/lock files. |
| `PIPELINE_MACHINE_TOKEN` | unset | The no-human path for `pipeline cloud connect` (bots, CI, autonomous agents): an `aip_m_<client-id>.<secret>` machine credential from your dashboard's Settings → Machine credentials. Its presence suppresses every prompt and browser/device-code attempt — pass `--org <slug>` too (a machine credential has no discoverable org). `--machine-token <token>` is the flag equivalent; the env var is preferred since argv is world-readable in `ps`. Combining either with `--device` is a usage error (exit 2). |
| `PIPELINE_DRIVE_EXECUTOR_CMD` | `codex exec --json --skip-git-repo-check --model {model} -c model_reasoning_effort={effort} --sandbox {permissions} --add-dir {record_dir}` | Overrides the command template the EXPERIMENTAL Codex process driver (`pipeline drive --executor codex-cli`) spawns per step. Whitespace-split; unresolved flag/value pairs are dropped, and the step prompt arrives on stdin. Equivalent to `--executor-cmd`. |
| `PIPELINE_HOOK_TIMEOUT_MS` | per-hook (600 000 create/finalize, 300 000 destroy) | Overrides the external-isolation worktree-hook timeout (positive integer, milliseconds). Mostly useful for testing hooks. |
| `PIPELINE_WORKTREE_SCOPED` | on | Worktree-scoped pipeline I/O for `isolation: run` runs (the run plans from, and self-improves into, the run worktree's pipeline copy — committed state only). `0`/`false` restores the legacy main-scoped reads. FROZEN per run into `next.json` at init — a mid-run flip never mixes path models within one run. |
| `PIPELINE_GIT_BIN` / `PIPELINE_GH_BIN` | `git` / `gh` from PATH | Override which `git`/`gh` binaries the CLI's guarded git operations (`pipeline submodule bump`) invoke. |
| `PIPELINE_JOURNAL_DEBUG` / `PIPELINE_RELAY_DEBUG` | off | `=1` prints diagnostic detail to stderr from the event writer / relay hooks. Debugging only. |

**Hook contract (set BY the plugin, read by your hook scripts):** every `PIPELINE_WT_*` variable passed to the `worktree-create` / `worktree-finalize` / `worktree-destroy` hooks is specified in [`docs/worktree-hook-contract.md`](docs/worktree-hook-contract.md) — that contract is frozen; write hooks against it, never set those variables yourself.

**Internal (do not set):** `PIPELINE_RUN_ID` / `PIPELINE_PARENT_RUN_ID` are run-correlation plumbing between `$pipeline:run` and the analytics hooks; setting them manually mis-attributes events. `PIPELINE_STATS_RUNNER` is set by `pipeline drive` to tag `driver` runs in the measurement files.

## Departments (`/mcp` + background notifier)

Separate from pipelines: a **department** is an agent somebody else runs, on
somebody else's machine, that yours can hand work to. It has a name, a
description and a list of skills. You don't install or clone it — you ask for it
by name, and [ai-pipeline.dev](https://ai-pipeline.dev) routes the task to
whoever is serving it.

This plugin is the client side of that, in three pieces:

| Piece | For |
|---|---|
| A remote **MCP server entry** | Calling departments from inside a live Codex CLI session. |
| A **background notifier** | So a delegated task isn't lost when you close that session before it finishes. |
| `pipeline department …` | Publishing a folder of your own as a department other people can call. |

**The walkthroughs live on ai-pipeline.dev** — five pages, in order, every command on them pasted from a terminal where it ran. This section is the plugin-side reference and deliberately does not repeat them:

| Page | Covers |
|---|---|
| [Get started](https://ai-pipeline.dev/docs/getting-started) | `bun add -g` → `pipeline init` → one browser approval → a completed run on your account. `--local` for the same thing with no cloud at all. |
| [Connect the cloud](https://ai-pipeline.dev/docs/connect-the-cloud) | What `init` did for you, on its own: `pipeline cloud connect` — one browser approval, no token typed or pasted — and what the Free plan includes. |
| [Use a department](https://ai-pipeline.dev/docs/use-a-department) | `/mcp`, delegating in plain language, and what happens when a department asks you something back. |
| [Build a department](https://ai-pipeline.dev/docs/build-a-department) | `department.yml`, then `new` / `validate` / `serve` / `status`, and running the same department on another machine. |
| [Privacy tiers](docs/privacy-tiers.md) | Field by field, what leaves your machine once any of this is connected — transcribed from the filter that runs, with its real output. |

The plugin-internal contract behind the two client pieces — why the MCP entry and the notifier deliberately don't share a transport, what the `timeout` is sized against, and every file involved — is [`docs/departments-mcp.md`](docs/departments-mcp.md).

### Connecting — 2 steps, 1 browser hop, no token to paste

```
/mcp
```

1. Running `/mcp` (or just asking to delegate work — Codex CLI triggers discovery automatically) lists `ai-pipeline-departments` as needing authorization; selecting it opens your browser to the departments' consent screen.
2. Log in if needed and approve — pick your org if you belong to more than one.

That's it, once per machine. Codex CLI holds an audience-bound, scope-limited, short-lived credential from here on — never a long-lived token sitting on disk, and nothing to copy-paste. This is the same flow you'd use to connect any other remote MCP server; the plugin just ships the server's URL for you.

Once connected, delegating work is one line in natural language — "have the Unity department review the save system" — and the agent calls the departments' tools (`departments.list`, `tasks.send`, `tasks.wait`, …) on your behalf. A clarifying question along the way costs exactly one extra turn (you answer it like any other question); the result and any artifacts land back in your session.

> **One-time re-consent when you update to this version.** The MCP server key is
> `ai-pipeline-departments`; before the terminology rename it was
> `ai-pipeline-mesh`. That key is embedded in every tool's callable name
> (`mcp__plugin_<plugin>_<server>__<tool>`) and stored OAuth grants are keyed by
> it — so to Codex CLI the renamed entry is a *new* server with no grant. Run
> `/mcp` and approve once more; nothing else about the connection changes.
>
> If you carry the old name in a local MCP permission rule or hook matcher,
> update that reference too.

### Publishing one of your own — the `pipeline department` commands

A department is a folder whose only required file is `department.yml`. [Build a department](https://ai-pipeline.dev/docs/build-a-department) walks that end to end; these are the verbs it uses.

| Command | What it does |
|---|---|
| `pipeline department new [<name>]` | Scaffolds `department.yml` and **nothing else** — no `.codex/`, no README, no starter agent. The name defaults to the folder's. `--engine <id>` picks the runtime engine; `--from-pipeline <name>` prefills the description and one skill from an existing `.pipeline/<name>/PIPELINE.md` and points the manifest at it. |
| `pipeline department validate` | Checks a hand-written or hand-edited file: schema + `apiVersion`, engine support, coherence, advisory nits, and the local paths it names. Non-zero exit on any error, `--json` for scripts. It ends by listing what it structurally *cannot* check (a runner, a credential, the control plane) — that list is `serve`'s job. |
| `pipeline department serve` | One command from an authored file to a live department: validate, sign in, register (or update the registration when the manifest changed), enrol this machine as a runner if it isn't one, bind the runtime, ensure a supervisor is installed, claim the install, report. No separate connect step, no runner token. Idempotent and resumable from any partial state, and it writes nothing **inside** the department folder, so a department stays clonable. |
| `pipeline department status [--follow]` | State, plan budget, and recent tasks — from the control plane when a credential is already stored, from this machine's own binding state when it isn't. Never triggers an interactive sign-in. Each task line names who asked (sender) and what ran it (engine), read from this machine's own runner journal; a task this machine did not run shows `?` for both, with the reason, rather than being attributed to somebody else. |
| `pipeline department stop` | Local only: finishes in-flight tasks, refuses new offers, unbinds from this machine's supervisor. It never contacts the control plane, so the registration survives and `serve` brings it straight back — and it works with the network down. |
| `pipeline department retire` | The unpublish verb (owner role): soft-deletes the department from the org, fails its open tasks with a stated reason, and only **then** unbinds locally. That order is deliberate — if the cloud half fails, this machine is left exactly as it was rather than unserved while the control plane keeps routing to it. Destructive; refused without `--yes` when not interactive. |

Two things worth knowing before you author one:

- **`serve` reports only what it observed.** It prints `online` when the control plane says so, `registered — not serving` with the reason and the fix when this machine has no live supervisor, and `could not confirm it is live` when neither could be read. It does not assert success it hasn't checked.
- **The declared engine has to be one `pipeline-runner` actually ships a module
  for.** For a Codex-authored pipeline department, select `--engine pipeline`.
  When no module exists for the declared engine, `serve` refuses and registers nothing rather than publishing a
  department that could not execute a single task — and `validate`'s
  engine-support line says the same thing before you get that far. One predicate
  sits behind both, so they cannot disagree.

  [Build a department](https://ai-pipeline.dev/docs/build-a-department) walks
  `engine: pipeline`, which turns a pipeline you already have into something your
  org can call, and states the current limit in the CLI's own words. Nothing
  about the file changes when a missing module ships: set `runtime.engine` and
  re-run `serve`.

### The background notifier — a parked task announces itself

Some department tasks take a while, and `tasks.wait` (the tool the agent loops on to watch a task) only blocks up to 45 seconds at a time by design — a live session loops it invisibly, but if a task needs your input or finishes **after you've closed that Codex CLI session**, a plain MCP client has no way to tell you. This plugin ships a small background piece so that doesn't mean silence:

- A lightweight daemon (`pipeline department notify`) starts automatically the first time a `SessionStart` hook sees you've connected the CLI to the cloud (`pipeline cloud connect` — see below), and keeps polling your open department tasks in the background, independent of any open Codex CLI session.
- The moment one of your tasks needs input or reaches a final state (done, failed, canceled, rejected), it fires a best-effort **OS-level notification** (a toast / notify-send / balloon, depending on your platform) right then.
- Every such transition is also written to a small durable queue, so even if you miss the toast (or your platform doesn't support one), the **next time you open Codex CLI — in any project** — a `SessionStart` hook drains that queue and adds it as context, and the agent tells you about it.

You don't do anything extra to get this: it reuses the same credential `pipeline cloud connect` already stores (see `<cli>/src/lib/cloud-config.ts`) and needs no separate setup or consent step of its own.

```bash
# one-time (if you haven't already connected the CLI to the cloud for other reasons):
pipeline cloud connect

# manual smoke-test / debugging — runs one poll cycle and exits. This is the
# same binary the hook spawns: since plugin v0.93.0 the plugin ships no CLI of
# its own, so there is only ever one copy and it is the globally installed one.
pipeline department notify --once --json
```

Opt out with `PIPELINE_DEPARTMENT_NOTIFY_ENABLED=0` (same falsy-value convention as `PIPELINE_JOURNAL_ENABLED`) if you never want the daemon spawned or the queue drained. (`pipeline mesh notify` and `PIPELINE_MESH_NOTIFY_ENABLED` still work as deprecated, warning aliases for anyone with an existing service definition or shell profile.)

> **Implementation note for the curious.** The notifier polls the departments'
> REST task surface with the credential `pipeline cloud connect` already stored,
> rather than the `/mcp` tool surface Codex CLI itself uses. A headless
> background process has no browser session to complete an OAuth consent flow in,
> so it reuses what is already there. Full reasoning is in the header comment of
> `<cli>/src/lib/department-notify.ts`.

## Resuming a halted pipeline

If an executor halts on a blocker, fix the underlying issue, then re-invoke:

```
$pipeline:run <absolute-path>/.pipeline/<pipeline-name>/steps/<NN-halted-iteration>.md
```

Iterations are designed to be idempotent, so re-running from the halted step is safe.

## Tips

- Start with a clear one-sentence end-state when calling `$pipeline:design`. Vague goals produce vague pipelines.
- Prefer flat linear chains. Nest only when an iteration is itself a mini-pipeline.
- Pipelines double as a knowledge base: after completion, the folder documents *what was done and why* and can be read by humans or future agents.
