---
name: dispatch
description: Autonomously match a free-form task description (or GitHub issue) against this project's pipeline manifests and run the matching pipeline(s) — single or chained — without asking for confirmation. Invoke when an inbound task description may have a pre-authored pipeline. /pipeline:find is the ask-first inspection variant.
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Agent
argument-hint: <free-form task description or GitHub issue URL>
---

# Dispatch a Task to the Right Pipeline

Given a task description (or GitHub issue ref) in `$1`, select the best-matching pipeline(s) from the current project's `.pipeline/` and run them in order — autonomously, without confirmation. This is the auto-run sibling of `/pipeline:find` (which is the inspection variant that asks before running).

## Three-tier token cost ladder (CRITICAL)

This skill is engineered so most calls cost near-zero LLM tokens. Each call walks down a ladder; you stop at the first tier that produces a usable answer.

1. **Deterministic match (free).** Always runs first. Shells out to the `pipeline match` command that scores manifests with Okapi BM25 over the positive corpus and hard-filters on `Scope.Out`. Returns ranked JSON. ~zero LLM tokens. Most tasks resolve here.
2. **LLM disambiguation (cheap, Haiku).** Only when the matcher returns 2+ candidates with **comparable** scores (top1/top2 ratio < 2.0). Spawns the `pipeline-disambiguator` subagent (Haiku 4.5) with the task text and the 2–5 ambiguous candidates' manifests inlined. Tokens scale with ambiguity, not with project size — typically a few thousand tokens of Haiku, total cost is fractions of a cent.
3. **LLM chain detection (expensive, Sonnet/main).** Only when the matcher returns 0 candidates AND the task contains chain phrasing (`then`, `after that`, `followed by`, etc.). Loads every project manifest into your context and reasons over them to produce a chain. This is the only path that costs what dispatch used to cost on every call before the refactor — now it runs maybe 5% of the time.

The 80% case (one pipeline obviously matches): tier 1 only, no LLM tokens. The 15% case (ambiguous match): tier 1 + tier 2, Haiku tokens only. The 5% case (chain across pipelines): tier 1 + tier 3, full reasoning. Average token cost per dispatch drops by ~90% versus the pre-refactor design.

## What you are doing

1. Detect input shape (free-form task vs GitHub issue URL/ref).
2. Run the deterministic matcher (`pipeline match`).
3. Apply the decision tree below to pick a tier.
4. Resolve to one pipeline (or a 2-pipeline chain).
5. Run via `/pipeline:run` — once per matched pipeline, in order.
6. Report progress compactly (the report may be relayed to a remote caller).

## Token discipline

- **Never `Read` `PIPELINE.md` files yourself in tier 1.** The matcher reads them inside its own process; you only consume the small JSON result it prints to stdout.
- **In tier 2, do NOT load all manifests into your context.** Read only the 2–5 ambiguous candidates' manifests (each ≤ 300 tokens) and inline them into the disambiguator's prompt. The disambiguator runs on Haiku and reasons over them.
- **Tier 3 is the only path where you load all manifests.** Save it for genuine chain detection — never as a generic fallback when the matcher gave a usable answer.
- **Never `Read` iteration files (`steps/**/*.md`).** Hand the path to `/pipeline:run`; let the executor read.

## Prerequisites

- `$1` is non-empty. If empty, ask the user what task to dispatch. Do not proceed.
- Current working directory is the consumer project's root.
- The `pipeline` CLI is installed and on PATH (`@baizor/pipeline`; see `docs/running-pipelines.md`) — the matcher runs through it.
- For `--issue` inputs only: `gh` CLI installed and authenticated.
- At least one pipeline exists under `./.pipeline/`. If none, stop and tell the user to run `/pipeline:design` first.

## Procedure

### Step 1 — Resolve input

Inspect `$1`:

- Starts with `https://github.com/.../issues/<n>` → GitHub issue URL.
- Matches `owner/repo#<n>` → issue shorthand.
- Plain digits AND user explicitly framed it as an issue → numeric issue ref.
- Anything else → free-form task text.

For the issue cases, you do NOT need to call `gh` yourself — `the matcher` accepts `--issue` and fetches the title+body internally. Pass it through.

### Step 2 — Run the deterministic matcher (tier 1)

Invoke the matcher (`pipeline match`):

```bash
pipeline match \
  --pipelines-dir "./.pipeline" \
  --task "<verbatim task text>"     # OR --issue "<issue ref>"
  --top 5
```

Quote the task verbatim — do not paraphrase. For tasks with shell-significant characters, write to a temp file and use `--task "$(cat tmpfile)"`.

Parse the JSON result. The script writes one JSON object to stdout with keys `task`, `candidates`, `excluded`. Each candidate has `name`, `manifest`, `first_iteration`, `end_state`, `score`, `matched_terms`.

### Step 3 — Decision tree

Let `C` = `result.candidates` (already sorted by `score` descending).

- **`len(C) == 1`** → single confident match. **Skip tier 2.** Go to step 5 with this pipeline.

- **`len(C) >= 2`** → check confidence ratio:
  - Compute `ratio = C[0].score / C[1].score`.
  - If `ratio >= 2.0` → confident top match. **Skip tier 2.** Go to step 5 with `C[0]`.
  - If `ratio < 2.0` → ambiguous. Go to step 4 (tier 2 — disambiguator).

- **`len(C) == 0`** → no positive match. Check task text for chain phrasing — case-insensitive search for any of: `then`, `after that`, `after which`, `followed by`, `and then`, `next,`, `subsequently`, `, then `.
  - If chain phrasing found → tier 3 (chain detection). Go to step 4b.
  - If no chain phrasing → genuinely no match. Stop and report:
    ```
    No pipeline matched "<task>" deterministically. Excluded by Scope.Out:
    <list excluded entries from result.excluded with their matching_terms>
    Suggest: /pipeline:design <goal>  (to author a new pipeline) or
    rephrase the task and try again.
    ```

### Step 4 — Tier 2: spawn `pipeline-disambiguator` (Haiku)

Build the prompt. For each candidate in `C[:5]`, read its manifest content via `Read` (each ≤ 300 tokens — bounded read). Compose:

```
## Task
<verbatim task text or issue title+body>

## Candidates

### <candidate.name>
- manifest: <candidate.manifest>
- first_iteration: <candidate.first_iteration>
- score: <candidate.score>
- matched_terms: <candidate.matched_terms>

<verbatim manifest content>
---

### <next candidate>
...
```

Spawn via the `Agent` tool with `subagent_type: "pipeline-disambiguator"`, passing the composed prompt as the entire input. Do NOT add other instructions — the agent's system prompt has its protocol.

Parse the agent's `Disambiguation Result`:
- `chosen.first_iteration` is set, `chained_after` is null → run that single pipeline (step 5).
- `chosen.first_iteration` is set, `chained_after` is set → run the two pipelines in order (step 5, twice).
- `chosen` is null (refusal) → surface the rationale to the user and stop. Do NOT silently fall back to tier 3 — Haiku has more context than the matcher and its refusal is informative.

### Step 4b — Tier 3: chain detection (only on 0 candidates + chain phrasing)

This is the expensive path. Enumerate every project manifest with the `Glob` tool: `./.pipeline/**/PIPELINE.md`.

`Read` each manifest (still ≤ 300 tokens each by plugin convention; the bulk read is safe).

Reason over the manifests in your own context (you are the main session). Produce an ordered chain of pipelines whose End States, run sequentially, satisfy the task. Each step in the chain is one pipeline's first iteration path.

If you cannot construct a chain, stop and report:

```
Task seems to span multiple pipelines but no consistent chain found.
Candidates considered: <list>
Suggest: rephrase, or /pipeline:design <goal> for the missing piece.
```

### Step 5 — Announce and run

For the chosen pipeline (or chain), output a compact structured message (≤ 300 tokens):

```
▶ Task: <verbatim $1>
▶ Matched: <pipeline-name>[ → <next-pipeline-name>]
▶ End state: <End State of the last pipeline in the chain — read it now from PIPELINE.md if you don't have it>
▶ Why: <one sentence — for tier 1: "BM25 confident match (ratio X.X)"; for tier 2: disambiguator's rationale verbatim; for tier 3: your own chain reasoning summarized>
```

Then for each pipeline in the chain (just one, in the common case), invoke:

```
/pipeline:run <pipeline.first_iteration>
```

Wait for the chain to finish before starting the next pipeline. If a chain halts on a blocker, STOP — do not start the next pipeline. Report the blocker.

### Step 6 — Final report

After all pipelines complete (or one halts):

```
✓ Completed: <comma-separated pipeline names>
```

or

```
✗ Halted at <pipeline>/<iteration>
Blocker: <text from the executor>
```

## Tuning the confidence ratio

The default `ratio >= 2.0` threshold for "skip disambiguation" is empirical, not sacred. If you observe disambiguator calls that ALWAYS pick the top BM25 candidate anyway, raise the threshold (e.g. 1.5) — running Haiku for nothing wastes tokens. If you see disambiguator picks differing from BM25's top often, lower it (e.g. 3.0) — the deterministic matcher's confidence is overstated.

This is the one knob worth tuning over time. Don't tune it from a single bad call; gather a handful of examples first.

## Do not

- **Do not invoke `step-executor` directly.** Always go through `/pipeline:run`.
- **Do not modify pipeline files during dispatch.** Matching is read-only.
- **Do not silently skip a pipeline in a declared chain.** If your match result says A → B, run A, then B. If you think B isn't needed, say so and let the user confirm before skipping.
- **Do not paraphrase the user's task before passing it to the matcher.** The deterministic matcher tokenizes the verbatim text — paraphrasing changes the token set and shifts scores. If the task is too short to score well, you'll see 0 candidates; let the chain-detection path or the user handle it.
- **Do not fall back from a disambiguator refusal to tier 3.** The disambiguator has more context than the matcher; if it refuses, surface its rationale and stop. Tier 3 is reserved for the genuinely-no-candidates case.
