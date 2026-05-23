# educoder-cli Command Reference

## Install

```bash
uv tool install git+https://github.com/lihaoze123/educoder-cli
# OR from local clone:
pip install -e .
```

## CLI Discovery

Try each, use the first that works (record as `$CLI`):
```bash
educoder --help
uv run educoder --help
python main.py --help
```

## Commands

```bash
$CLI status --json
$CLI courses --json
$CLI homeworks --course <id|identifier|name> --json
$CLI task --course <course> --homework <id|name> --json
$CLI code --course <course> --homework <homework> --output <file> --force --json
$CLI submit --course <course> --homework <homework> --file <file> --timeout 60 --json
```

## Selector Rules

- **Course**: matches ID → exact identifier → exact name → name substring
- **Homework**: matches ID → exact name → name substring
- Ambiguous results are local errors; present candidates and ask user to choose

## JSON Fields

### courses
- `id`, `name`, `identifier`, `school`, `tasks_count`

### homeworks
- `homework_id`: stable selector
- `name`, `shixun_identifier`, `myshixun_identifier`
- `challenge_count`, `finished_challenge_count`: progress
- `status`: e.g. `["已结束"]`, `["提交中"]`
- `end_time`

### task
- `challenge.path`: remote answer file path
- `challenge.subject`: challenge title
- `challenge.task_pass`: problem statement (HTML/Markdown)
- `challenge.position`, `challenge.score`
- `game.status`: 0=未开始 1=评测中 2=通过 3=未通过
- `game.final_score`, `game.accuracy`
- `homework_common_id`, `homework_common_name`
- `prev_game`, `next_game`: multi-level navigation
- `last_compile_output`: recent compiler feedback
- `time_limit`: seconds
- `test_sets[]`:
  - `result`: true/false/null
  - `output`: expected output
  - `actual_output`: actual output after evaluation
  - `compile_success`: compile result
  - `is_public`: whether this test is visible
  - `ts_time`, `ts_mem`: time/memory metrics

### code
- `path`: remote file path
- `content`: file content (when no `--output`)
- `output`: local file path (when `--output`)
- `written`: true when file was created

### submit
- `passed`: true/false/null (null = no-wait mode)
- `task_detail`: full task detail after evaluation
- `test_sets[]`: evaluation results

## Exit Codes

- 0: success (submit passes, or --no-wait accepted)
- 1: API error, context error, file error, or evaluation failed
- 2: missing credentials

## Multi-Level Tasks

After a `submit` passes, check `task_detail.next_game`. If non-null:
1. Re-run `task` to get the next level context
2. Repeat: code → solve → submit
3. Continue until `next_game` is null
