---
name: pipeline
description: Use when designing or advancing a file-based multi-step pipeline in a repository.
---

# Pipeline

Treat `.pipeline/<name>/PIPELINE.md` and its ordered step files as the source of truth. Inspect the repository before changing a pipeline, preserve completed-step evidence, and advance one explicit next step at a time. Use the installed `pipeline` CLI when it is available; otherwise explain the missing runtime and prepare the next step without inventing command output.
