---
name: educoder-cli
description: 使用 educoder-cli 解决头歌/EduCoder 实验习题。当用户要求做题、提交代码、获取题面、下载远端代码、调试评测失败时触发。
---

# EduCoder CLI

## 概述

使用 `educoder-cli` 作为真实题面数据源。从真实任务数据入手，保护凭证和提交内容不外泄，将提交视为远端状态变更操作。

实际 CLI 路径：`C:\Users\hecon\educoder-cli`，使用 `python main.py` 运行。

## 工作流

1. **验证 CLI 和凭证**：
   ```bash
   cd C:\Users\hecon\educoder-cli && python main.py status --json
   ```

2. **选择目标**。用户未指定时先发现候选：
   ```bash
   python main.py courses --json
   python main.py homeworks --course <course> --json
   ```
   优先用精确 ID/identifier。多个匹配时询问用户。

3. **读取题面**：
   ```bash
   python main.py task --course <course> --homework <homework> --json
   ```
   提取 challenge.path、task_pass（题面）、test_sets、last_compile_output、game.status。

4. **获取远端代码**：
   ```bash
   python main.py code --course <course> --homework <homework> --output <local_path> --force --json
   ```

5. **本地解题**。先读题面和测试用例。保持远端文件类型和路径。

6. **提交评测**：
   ```bash
   python main.py submit --course <course> --homework <homework> --file <local_path> --timeout 60 --json
   ```

7. **迭代**。失败时根据 test_sets 的 output/actual_output 和 last_compile_output 调整代码。

## 安全规则

- 不输出 zzud、autologin、session、cookie 到聊天记录
- 不将提交的源码存到 skill references
- 提交前确认目标明确
- 未开始的实验（无 game_identifier）需先在 Web UI 打开
