---
name: educoder-cli
description: Solve EduCoder/Touge homework tasks with educoder-cli. Use when the user asks to solve a Touge/EduCoder experiment, write an answer, fetch problem statements, download remote code, submit for evaluation, or debug a failed evaluation.
---

# EduCoder CLI

## Overview

Use `educoder-cli` as the data pipeline for task context. Work from real task data. Keep credentials and submitted code out of logs. Treat submission as a remote state-changing action.

Read `references/educoder-cli.md` for commands, selector rules, JSON fields, and verified paths.

## Setup

1. Install the CLI (or confirm it's already available):

   ```bash
   uv tool install git+https://github.com/hecongnan/educoder-cli
   ```

   Or from local clone:

   ```bash
   cd <project-root> && pip install -e .
   ```

2. Discover the CLI command. Try these in order, use the first that works:

   ```bash
   educoder --help
   uv run educoder --help
   python main.py --help
   ```

   Record the working prefix as `$CLI` for subsequent commands.

3. Log in (one-time):

   ```bash
   $CLI login --login <account>
   ```

   Let the CLI prompt for the password. Never ask the user to paste passwords, cookies, `zzud`, `autologin`, or `_educoder_session` in chat.

## Workflow

1. Verify credentials:

   ```bash
   $CLI status --json
   ```

2. Discover targets. If the user did not specify a course/homework, list candidates:

   ```bash
   $CLI courses --json
   $CLI homeworks --course <course> --json
   ```

   Prefer exact identifiers. If multiple plausible targets exist, ask the user to choose.

3. Read the real problem context:

   ```bash
   $CLI task --course <course> --homework <homework> --json
   $CLI task --course <course> --homework <homework>
   ```

   Extract: `challenge.path`, `challenge.task_pass` (problem statement), `test_sets`, `last_compile_output`, `game.status`, `next_game`, `prev_game`.

4. Fetch remote code:

   ```bash
   $CLI code --course <course> --homework <homework> --output <local-file> --force --json
   ```

   Use the returned `path` as the remote answer path. Keep code in normal working files, not in chat logs.

5. Solve locally. Inspect the statement and tests first. Preserve file type and path.

6. Submit only when target is unambiguous:

   ```bash
   $CLI submit --course <course> --homework <homework> --file <local-file> --timeout 60 --json
   ```

   `submit` saves code remotely and triggers evaluation. Do not run unless the course/homework target is confirmed.

7. Iterate from feedback. On failure, inspect `test_sets[].output` vs `test_sets[].actual_output` and `last_compile_output`. Avoid pasting full submitted source into chat.

8. Multi-level tasks. After a pass, check `next_game`. If non-null, the homework has another level. Re-run `task` and continue.

## Safety Rules

- Never print or persist `zzud`, `autologin`, `_educoder_session`, cookies, headers, request bodies, or raw API payloads.
- Do not store downloaded or submitted source code in skill references or research files.
- Treat `code --output` as local file creation and `submit` as remote mutation.
- If the CLI reports ambiguous matches, show candidate names/IDs and ask for one target.
- If a task has no `game_identifier`, tell the user to open the experiment in the EduCoder web UI first.

## Key Fields

See `references/educoder-cli.md` for the full command reference and JSON field documentation.
