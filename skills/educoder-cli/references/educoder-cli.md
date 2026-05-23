# educoder-cli 命令参考

## 安装与运行

从项目目录运行（已安装 httpx, rich, typer）：
```bash
cd C:\Users\hecon\educoder-cli
python main.py --help
```

## 命令

```bash
python main.py status --json
python main.py courses --json
python main.py homeworks --course <id|identifier|name> --json
python main.py task --course <course> --homework <id|name> --json
python main.py code --course <course> --homework <homework> --output <file> --force --json
python main.py submit --course <course> --homework <homework> --file <file> --timeout 60 --json
```

## 选择器规则

- Course: 支持 ID、identifier、名称、名称片段
- Homework: 支持 ID、名称、名称片段
- 模糊匹配到多个时需用户选择

## JSON 关键字段

- `course.identifier`: 稳定选择器
- `homework.homework_id`: 稳定选择器
- `homework.finished_challenge_count / challenge_count`: 完成进度
- `task.challenge.path`: 远端文件路径
- `task.challenge.task_pass`: 题面描述
- `task.last_compile_output`: 最近编译反馈
- `task.game.status`: 0=未开始 1=评测中 2=通过 3=未通过
- `task.test_sets[].output`: 期望输出
- `task.test_sets[].actual_output`: 实际输出
- `task.test_sets[].compile_success`: 编译结果
- `task.next_game`: 下一关 game identifier
