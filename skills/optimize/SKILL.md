---
name: optimize
description: USER-INVOKED ONLY (e.g. on a weekly schedule) — review the pipeline run measurements under .pipeline/.stats/ (durations, outcomes, tokens, tool failures), inspect run logs where something regressed or repeatedly failed, and apply targeted improvements to specific pipelines via pipeline-improver. Never auto-invoke this skill; it exists so measurement review costs zero tokens until the user explicitly asks for it.
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Bash, Glob, Grep, Agent, AskUserQuestion
argument-hint: "[pipeline-name … | leave empty to review everything]"
---

# Optimize pipelines from their run measurements

You are running the **periodic optimization pass** over the measurement files the stats system
(pure software, `PIPELINE_STATS_ENABLED`, default on) has been writing under
`<project>/.pipeline/.stats/`. The user invokes this deliberately (typically weekly).
`$ARGUMENTS` may narrow the pass to specific pipelines; empty means review everything.

## Token discipline

The measurement system itself never spends LLM tokens — all analysis cost lives in THIS skill,
which only the user can trigger (`disable-model-invocation: true`). Keep the pass cheap:

- Read `SUMMARY.md` first — it is the whole picture. Do NOT read every runs.jsonl.
- Drill into a per-run log (`.stats/<pipeline>/runs/<run-id>.log`) ONLY for pipelines you flagged.
- Read a pipeline's iteration files ONLY when you are about to propose a concrete improvement.
- Apply edits through ONE `pipeline-improver` spawn per flagged pipeline — never edit iteration
  files yourself from this skill, and never spawn improvers for healthy pipelines.

## Procedure

1. **Refresh + load the summary.** Run
   `pipeline stats` from the project root and read
   its output (it regenerates and prints `SUMMARY.md`). If it reports no measurements, say so and
   stop — nothing to optimize.

2. **Flag problem pipelines** (restricted to `$ARGUMENTS` when given). A pipeline is flagged when,
   compared with ITS OWN history in the summary/records:
   - halts or non-completed outcomes are frequent (≥ ~25% of recent runs), or a repeating
     `halt_reason` appears;
   - tool failures are frequent or recurring — the "Tool fails" columns (avg per run in the
     rollup; per-run count + worst offender, e.g. `7 (Bash 5)`, in Recent runs). Flag when recent
     runs repeatedly fail the SAME tool, or the fail rate jumped vs. the pipeline's history. A run
     can be `completed` and still be sick — dozens of failed calls mean steps are retrying their
     way to success and burning time/tokens on wrong instructions;
   - average duration or out-tokens drifted clearly upward across recent runs (bloat — steps
     re-reading too much, or iteration files growing);
   - a single step dominates the run duration in recent per-run logs (extraction candidate);
   - runs sit in "In-flight or crashed runs" with large buffer ages (crash/kill pattern).
   Healthy pipelines are reported as healthy in one line each — no further reading.

3. **Investigate each flagged pipeline, cheaply.** Read its 2–3 most recent
   `runs/<run-id>.log` files; correlate with `halt_reason`s from the summary. For tool failures,
   the evidence is IN the .log: enrichment appends a `tool fails (N):` section — one line per
   failure with timestamp, tool, `[step]` when attributable (exact for `driver` runs;
   timestamp-mapped for manager runs), and the error the tool returned. Classify each pattern:
   - **pipeline-attributable** — the same error recurs across runs and points at the iteration's
     instructions: a wrong/stale command or path in Steps, a missing preflight (tool not
     installed, server not running, file assumed to exist), wrong assumptions about repo layout,
     or a step retrying a forbidden operation. These justify an improvement.
   - **environment noise** — one-off network timeouts, transient lock contention, a tool erroring
     once and succeeding on the retry with no pattern across runs. Report it, but do NOT "fix"
     noise by editing the pipeline.
   If needed, check leftover feedback (`<pipeline>/.feedback/`) and design-time lint
   (`pipeline plan --root <pipeline> --json` → `warnings`). Form ONE concrete improvement hypothesis
   per pipeline: e.g. "step 03 halts on a missing preflight — add it to Steps", "step 02 fails
   `bun test` 5× per run because Steps says `bun test` but this repo needs `bun run test` — fix
   the command", "step 02 doubled in tokens — compact via replace-don't-append", "extract the
   deterministic block in step 04 to a script".

4. **Ask before applying** (one AskUserQuestion): list flagged pipelines with the one-line
   diagnosis + proposed improvement each, and let the user pick which to apply (multiSelect).
   Skip the question only when the user's invocation already named the pipelines AND asked to fix.

5. **Apply via the improver.** For each approved pipeline, spawn `pipeline:pipeline-improver` with
   a Tier-1-style improvement brief built from your diagnosis (symptom, evidence — run ids,
   durations, halt_reasons, and for failure-driven fixes the failing tool + the exact recurring
   error line from the .log — and the specific proposed edit; respect its token-budget
   counter-pressure rules). Relay its structured report. If the improver emits
   `script_creation_briefs`, spawn `pipeline:pipeline-script-creator` once per brief, sequentially.

6. **Report.** Per pipeline: status (healthy / improved / needs-human), what changed, and the
   measurement that should move next week. Remind the user the next `/pipeline:optimize` run will
   show whether the change helped (the stats files are the before/after evidence).

## Boundaries

- Blast radius: pipeline folders only (`.pipeline/**`) — never consumer code, never the
  plugin install, never `.stats/` contents (the evidence is append-only; do not "clean" it).
- This skill NEVER runs pipelines and NEVER deletes measurement files.
- If `.stats/` shows tokens `pending` everywhere, note that enrichment happens when a
  manager-driven run's session ends (`driver` runs enrich themselves at their terminal action) —
  that is expected, not a defect. Runs recorded BEFORE the plugin learned to persist tool
  failures show `—` in the Tool fails columns; that means "not measured", not "zero".
