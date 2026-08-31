---
name: find
description: Find the best-matching pipeline in this project for a task description (or GitHub issue) using the deterministic, AI-free BM25 matcher. Returns a ranked candidate list with exclusion reasons, then asks the user to confirm before chaining into /pipeline:run. Invoke to discover the right pipeline for a task; /pipeline:dispatch is the auto-run variant.
user-invocable: true
allowed-tools: Bash, Glob, Read
argument-hint: <task-description-or-github-issue-url>
---

# Find a Pipeline by Task Description or GitHub Issue

You are matching a task (`$1`) against the consumer project's pipeline manifests using the deterministic `pipeline match` command — no language-model scoring, no embeddings, no per-call cost. Output a ranked candidate list with rationale, ask the user to pick one, then hand off to `/pipeline:run`.

## What you are doing

1. Detect whether `$1` is a GitHub issue (URL or `owner/repo#NUMBER` shorthand) or a free-form task description.
2. Invoke the `pipeline match` command with the appropriate flag. It:
   - Parses every `PIPELINE.md` under `./.pipeline/` into positive (name + End State + Scope.In + Glossary) and negative (Scope.Out) corpora.
   - Scores the task against the positive corpus using Okapi BM25.
   - Hard-filters pipelines whose Scope.Out shares ≥ `--neg-threshold` task tokens.
   - Returns ranked surviving candidates plus the excluded list as JSON.
3. Present the result to the user: top candidates with score and matched terms, plus excluded pipelines with the Scope.Out bullets that excluded them.
4. Ask the user to pick one (or confirm the single top candidate). Then invoke `/pipeline:run <first-iteration-path>` for the chosen pipeline.

## CRITICAL — token discipline

This skill exists precisely so the main session does NOT pay for reading every `PIPELINE.md` to find a match. The matcher does the reading; you only see the JSON result.

Rules:

- **Never `Read` `PIPELINE.md` or any iteration file (`steps/**/*.md`) yourself.** Let the `pipeline match` command do the reading.
- **Use `Bash` to invoke `pipeline match` and `Read` only the small JSON result.** The JSON is bounded (top N candidates + excluded list) — usually well under 2 KB.
- **Hand off to `/pipeline:run`, not directly to `step-executor`.** `/pipeline:run` is the supervisor; it spawns the `pipeline-manager` that parses executor reports and chains the improver / script-creator / next executor.

## Prerequisites

- The current working directory is the consumer project's root (where `./.pipeline/` lives). If unsure, confirm with the user before proceeding.
- The `pipeline` CLI is installed and on PATH (`@baizor/pipeline`; see `docs/running-pipelines.md`) — the matcher runs through it.
- For `--issue` input only: the `gh` CLI is installed and authenticated. If unavailable, fall back to asking the user to paste the task text.

## Procedure

1. **If `$1` is empty,** ask the user for a task description or a GitHub issue URL/ref. Do not proceed without one.

2. **Detect input shape:**
   - Starts with `https://github.com/...` and contains `/issues/<number>` → GitHub issue URL.
   - Matches `owner/repo#<number>` → GitHub issue shorthand.
   - Plain digits (`123`) AND the user's context suggests an issue (verbatim — do not infer; only when the user explicitly framed the input as an issue) → numeric issue ref.
   - Anything else → free-form task description.

3. **The matcher runs through the installed `pipeline` CLI** — no interpreter detection needed. If `pipeline` is somehow missing, stop and tell the user to install it (`bun add -g @baizor/pipeline` or `npm i -g @baizor/pipeline`; see `docs/running-pipelines.md`).

4. **Invoke the matcher.** Build the command:

   ```bash
   pipeline match \
     --pipelines-dir "./.pipeline" \
     --task "<verbatim task text>"     # OR --issue "<issue ref>"
     --top 5
   ```

   Pass exactly one of `--task` or `--issue`. Quote the task verbatim — do not paraphrase. If the user's task contains shell-significant characters (backticks, dollar signs, double quotes), prefer reading from a temporary file and using `--task "$(cat tmpfile)"` rather than inlining the string.

5. **Parse the JSON result.** The script writes a single JSON object to stdout with three top-level keys: `task`, `candidates`, `excluded`. Each candidate has `name`, `manifest`, `first_iteration`, `end_state`, `score`, `matched_terms`. Each excluded entry has `name`, `manifest`, `scope_out`, `matching_terms`.

6. **Render the result for the user.** Use this layout:

   ```
   ▶ Task: <task or issue title>

   Matches:
     1. <name> (score <score>, matched: <terms>)
        End state: <end_state>
        First iteration: <first_iteration>

     2. <name> (score <score>, ...)
        ...

   Excluded by Scope.Out:
     - <name>: Scope.Out includes <scope_out bullets that triggered the filter>
       Matching terms: <matching_terms>
     - ...
   ```

   Empty `candidates` array: tell the user no pipeline matched and suggest either re-running with `--neg-threshold 2` (more permissive — explain that this raises the bar for negative-corpus exclusion) or running `/pipeline:design <goal>` to author a new pipeline.

   Empty `excluded` array: omit that section entirely.

7. **Confirm with the user.**
   - Single candidate → `Run "<name>" now? [Y/n]`
   - Multiple candidates → `Pick one to run, or [c]ancel:`
   - User picks `c` or anything that isn't a listed option → stop without running.

8. **Hand off to `/pipeline:run`.** Once the user has confirmed, invoke `/pipeline:run <chosen.first_iteration>` exactly as if the user typed it themselves. Do not invoke `step-executor` directly — orchestration belongs to `/pipeline:run` and the `pipeline-manager` it spawns.

## Tuning the negative threshold

Default `--neg-threshold 1` means "any task token appearing in a pipeline's Scope.Out excludes that pipeline." That's strict and protects against the BM25-treats-negation-as-positive bug we built this for. Two reasons to raise it:

- The user has many pipelines with overlapping terminology (e.g. multiple pipelines with `Out: documentation`); a single common-noun overlap is excluding good candidates.
- Manual review shows specific exclusions are wrong (the Scope.Out bullet uses a common word coincidentally).

Re-run with `--neg-threshold 2` (require two-term overlap) before suggesting a manifest edit. If the wrong exclusion persists, the manifest's `Scope.Out` is the place to fix it — make the bullet more specific so it doesn't catch unrelated tasks.

## Do not

- **Do not invoke `step-executor` directly.** Always go through `/pipeline:run`.
- **Do not modify pipeline files during find.** Matching is read-only.
- **Do not paraphrase the user's task before passing it to the matcher.** The matcher tokenizes the verbatim text — paraphrasing changes the token set and shifts scores in unpredictable ways. If the user's task is too short to score well, ask them to expand it rather than expanding it yourself.
- **Do not fall back to LLM-based matching** silently if the matcher returns no candidates. Tell the user the deterministic matcher found nothing, and let them choose: try a different phrasing, raise `--neg-threshold`, or use `/pipeline:dispatch` (which is LLM-based) explicitly.
