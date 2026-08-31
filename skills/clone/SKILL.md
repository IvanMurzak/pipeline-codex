---
name: clone
description: Scaffold a ready-made pipeline into this project by copying a template that ships with the installed pipeline CLI into ./.pipeline/<name>/. Use to bootstrap a working pipeline (e.g. support-answer, ship-feature, example-minimal) without authoring one from scratch. Also lists the available templates with --list.
user-invocable: true
allowed-tools: Bash
argument-hint: <template-name>  (or --list to see all)
---

# Clone a pipeline template

You are copying a ready-made pipeline TEMPLATE into the user's project so
they have a working pipeline to run and adapt — no authoring required. You
invoke the installed `pipeline` CLI (`@baizor/pipeline`; see
`docs/running-pipelines.md` if it is not on PATH) — the plugin ships no CLI
code of its own.

The template lands at `<cwd>/.pipeline/<name>/` — inside the **consumer
project**, never the plugin install dir. The template SOURCE ships with the
CLI itself; it resolves the template relative to its own location, so cloning
works identically wherever `pipeline` was installed from.

## CRITICAL — token discipline: this is a pure thin router

Do NOT `Read` the cloned `PIPELINE.md` or any `steps/**/*.md` content, and do not
open the template source. Your only job is to shell out to the installed CLI in
the user's current working directory and report what it printed. The CLI already
lists every file it created; relay that, do not re-read the tree to describe it.
(This skill's `allowed-tools` is `Bash` only, which enforces that.)

## Procedure

1. **Run `pipeline clone` in the consumer's current working directory**, passing
   the user's arguments through verbatim (the `<template-name>` plus any flags):

   ```bash
   pipeline clone <passthrough-args>
   ```

   - Bare form: `/pipeline:clone support-answer` → run `... clone support-answer`.
   - `/pipeline:clone --list` → run `... clone --list` to show the available
     templates (no clone happens).
   - Pass `--force` (overwrite an existing target) and `--dir <path>` (clone into a
     different project root instead of the cwd) straight through when the user
     supplies them. Do NOT invent or hardcode a `--dir`; the default (cwd) is
     correct almost always.
   - Run this from the consumer project's cwd — do NOT `cd` elsewhere first; the
     clone must happen relative to where the user is (or `--dir`, when given).

2. **Interpret the exit code and report:**
   - `0` — cloned (or `--list` / `--help`). Relay the CLI's output: the template
     name and the file list it printed. Then tell the user how to run it (step 3).
   - `1` — refused: `./.pipeline/<name>/` already exists (or the copy
     failed). Relay the CLI's message; offer `--force` to overwrite (which replaces
     the folder entirely) if that's what they want. Do not force it yourself.
   - `2` — usage: no name, unknown template, or a bad flag. The CLI prints the list
     of valid templates; relay it so the user can pick a real one.

3. **On a successful clone, tell the user briefly how to run it.** Keep it short:
   - Run it from here: `/pipeline:run <cwd>/.pipeline/<name>/steps/01-*.md`, or
   - Run it as a `driver` from a terminal: `pipeline drive <name>`.
   - For the **`support-answer`** template specifically, mention that it takes two
     pipeline variables — `PP_QUESTION` (the question to answer) and `PP_DOCS_DIR`
     (the folder to retrieve over) — passed as
     `--var PP_QUESTION=... --var PP_DOCS_DIR=...`.

## Notes

- **Requires the `pipeline` CLI on PATH** — install it once with
  `bun add -g @baizor/pipeline` (or `npm i -g @baizor/pipeline`); see
  `docs/running-pipelines.md`. If the command fails because `pipeline` is not
  found, point the user at that install line and stop; do not try to install it
  for them.
- The available templates are whatever `pipeline clone --list` prints — do not
  hardcode the list here; it grows over time.
- This skill never edits the template after cloning. If the user wants to adapt it,
  they edit the files under `./.pipeline/<name>/` themselves, or use
  `/pipeline:design` for a brand-new pipeline.
