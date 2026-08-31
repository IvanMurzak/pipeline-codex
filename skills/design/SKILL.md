---
name: design
description: Design a new repeatable long-chain AI workflow as a pipeline — a pipeline.yml manifest plus the markdown its steps read — under this project's .pipeline/. Invoke only for workflows that will be re-run many times, such as releases, recurring audits, and generic task templates; route one-shot tasks through an existing generic pipeline or a regular agent instead.
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Glob, Grep, WebFetch, WebSearch, Agent
argument-hint: <high-level goal>
---

# Design a Pipeline

Design the pipeline directly. The goal is `$1`, the argument passed after
`/pipeline:design`; do not delegate its authoring to a specialised subagent.

## Start

1. If `$1` is empty, ask for the high-level workflow to design.
2. Read [the authoring protocol](references/authoring-protocol.md) in full
   before inspecting or writing pipeline files. It is the authoritative contract
   for repeatability, folder structure, manifests, iterations, variables,
   models, parallelism, scripts, and the final report.
3. Apply the protocol in the consumer project, never in the plugin directory.
   Pipelines belong under `<project-cwd>/.pipeline/`.

## One-shot requests

Do not create a pipeline for a single bug fix, PR, cleanup, or migration that
will not be repeated. First look for a suitable generic pipeline and route the
task through `/pipeline:run` or `/pipeline:dispatch`; if none exists, use a
regular agent. Explain the alternative briefly. If the user explicitly insists,
create the pipeline and note that it is an exception.

## What you write

A pipeline is **one `pipeline.yml`** — which declares every step, in order, with
its type, model and body — plus the markdown those steps read. Nothing about a
step comes from disk: not its identity, not its order, not its model. A step is
an entry in the manifest identified by `name:`; the files under `steps/` are
only prose it is handed, they carry no frontmatter, and their names carry no
ordering prefix.

Write the manifest FIRST. It is the design; the markdown is what the design says
to do.

## Report

After writing the pipeline, report:

- its absolute folder path;
- its ordered step names; and
- the command to begin: `/pipeline:run <absolute-path>`.
