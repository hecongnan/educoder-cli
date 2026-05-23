# educoder-cli

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

头歌（EduCoder / TouGe）平台命令行工具。登录 → 列出课堂 → 列出实验 → 查看题目 → 拉取代码 → 提交评测，全流程自动化。

## 目录

- [安装](#安装)
- [登录认证](#登录认证)
  - [方式一：密码登录](#方式一密码登录)
  - [方式二：手动提取浏览器 Cookie](#方式二手动提取浏览器-cookie)
  - [方式三：环境变量](#方式三环境变量)
- [命令参考](#命令参考)
  - [`status` — 验证登录状态](#status--验证登录状态)
  - [`courses` — 列出课堂](#courses--列出课堂)
  - [`homeworks` — 列出实验](#homeworks--列出实验)
  - [`task` — 查看实验关卡详情](#task--查看实验关卡详情)
  - [`code` — 拉取远程代码](#code--拉取远程代码)
  - [`submit` — 提交代码并评测](#submit--提交代码并评测)
  - [`version` — 查看版本](#version--查看版本)
- [典型工作流](#典型工作流)
- [JSON 输出模式](#json-输出模式)
- [多关卡实验](#多关卡实验)
- [项目结构](#项目结构)
- [API 逆向说明](#api-逆向说明)
- [已知问题](#已知问题)
- [License](#license)

## 安装

```bash
git clone https://github.com/hecongnan/educoder-cli.git
cd educoder-cli
pip install -e .
```

安装后 `educoder` 命令全局可用。

> **注意**：如果 `educoder` 提示找不到命令，将 Python Scripts 目录加入 PATH：
> ```bash
> # Windows
> setx PATH "%PATH%;%APPDATA%\Python\Python313\Scripts"
> ```
> 然后重新打开终端。

## 登录认证

`educoder-cli` 通过 Cookie 认证访问平台 API，本质上是模拟浏览器会话。提供三种方式设置凭证：

### 方式一：密码登录

```bash
educoder login --login 你的手机号/邮箱/用户名
```

提示输入密码后，自动保存凭证到 `%APPDATA%/educoder-cli/credentials.json`。

> 部分账号可能遇到 `status=-3`（密码错误），即使密码正确。这通常是平台风控限制，请改用方式二。

### 方式二：手动提取浏览器 Cookie

1. 在 Edge/Chrome 浏览器中登录 [头歌](https://www.educoder.net)
2. 按 `F12` → **Application** → **Cookies** → `data.educoder.net`
3. 复制两个 Cookie 值：
   - `_educoder_session`
   - `autologin_trustie`
4. 手动创建凭证文件：

**Windows：**
```powershell
mkdir %APPDATA%\educoder-cli
```

**`%APPDATA%/educoder-cli/credentials.json`：**
```json
{
  "zzud": "你的头歌用户名（手机号/邮箱）",
  "autologin": "从 Cookie 复制的 autologin_trustie",
  "session": "从 Cookie 复制的 _educoder_session"
}
```

**macOS：**
```
~/Library/Application Support/educoder-cli/credentials.json
```

**Linux：**
```
~/.config/educoder-cli/credentials.json
```

### 方式三：环境变量

每次使用时通过环境变量传入，不写入文件：

```bash
# Windows（CMD）
set EDUCODER_ZZUD=你的用户名
set EDUCODER_SESSION=你的_educoder_session值
set EDUCODER_AUTOLOGIN=你的autologin_trustie值

# macOS / Linux（Bash / Zsh）
export EDUCODER_ZZUD=你的用户名
export EDUCODER_SESSION=你的_educoder_session值
export EDUCODER_AUTOLOGIN=你的autologin_trustie值
```

## 命令参考

### `status` — 验证登录状态

```bash
educoder status
# → Authenticated.

educoder status --json
# → {"authenticated": true, "courses_checked": 1}
```

### `courses` — 列出课堂

```bash
educoder courses
educoder courses --page 2 --limit 50
educoder courses --json
```

输出表格包含：ID、Name、Identifier、Tasks。

### `homeworks` — 列出实验

```bash
educoder homeworks --course <课堂名称>
educoder homeworks --course 12345          # 按课堂 ID
educoder homeworks --course "CS2024001"    # 按标识符
```

`--course` 支持：课堂 ID、标识符（identifier）、名称精确匹配、名称模糊匹配。

输出表格包含：ID、Name、Progress（已完成/总数）、Status、End Time。

### `task` — 查看实验关卡详情

```bash
educoder task --course <课堂名称> --homework <实验名称>
educoder task --course <课堂名称> --homework 3635149  # 按实验 ID
```

显示：关卡标题、路径、当前状态（未开始 / 评测中 / 通过 / 未通过）、分数、题目描述（HTML 自动转为 Markdown）、测试集详情（预期输出 vs 实际输出）。

### `code` — 拉取远程代码

```bash
# 输出到终端
educoder code --course <课堂名称> --homework <实验名称>

# 保存到文件
educoder code --course <课堂名称> --homework <实验名称> -o answer.sql

# 强制覆盖已有文件
educoder code --course <课堂名称> --homework <实验名称> -o answer.sql --force

# 指定远程文件路径（默认使用当前关卡的路径）
educoder code --course <课堂名称> --homework <实验名称> --path "/path/to/file.sql"
```

### `submit` — 提交代码并评测

```bash
# 从文件提交
educoder submit --course <课堂名称> --homework <实验名称> -f answer.sql

# 从 stdin 提交
echo "SELECT * FROM student;" | educoder submit --course <课堂名称> --homework <实验名称> -f -

# 自定义超时（默认 30 秒）
educoder submit --course <课堂名称> --homework <实验名称> -f answer.sql --timeout 60

# 自定义轮询间隔（默认 2 秒）
educoder submit --course <课堂名称> --homework <实验名称> -f answer.sql --poll-interval 1.0

# 仅提交不等待结果
educoder submit --course <课堂名称> --homework <实验名称> -f answer.sql --no-wait
```

返回值：
- **通过**：绿色 `Evaluation passed.` 及详情表格
- **失败**：红色 `Evaluation failed.` 及测试集对比（预期 vs 实际）
- **退出码**：通过为 0，失败为 1，可用于脚本判断

### `version` — 查看版本

```bash
educoder version
# → educoder-cli 1.0.0
```

## 典型工作流

```bash
# 1. 验证登录
educoder status

# 2. 查看课堂
educoder courses

# 3. 查看某个课堂的实验列表
educoder homeworks --course <课堂名称>

# 4. 查看当前关卡题目
educoder task --course <课堂名称> --homework <实验名称>

# 5. 拉取已有代码（如果平台上有）
educoder code --course <课堂名称> --homework <实验名称> -o answer.sql

# 6. 编写/修改代码后提交
educoder submit --course <课堂名称> --homework <实验名称> -f answer.sql

# 7. 如果失败，查看 task 中的测试集对比，修改后重新提交
educoder task --course <课堂名称> --homework <实验名称>
```

## JSON 输出模式

所有命令均支持 `--json`，输出机器可解析的 JSON，方便脚本集成：

```bash
educoder courses --json | python -c "import json,sys; [print(c['name']) for c in json.load(sys.stdin)]"

educoder submit --course <课堂名称> --homework <实验名称> -f answer.sql --json
```

`submit --json` 返回结构：

```json
{
  "passed": true,
  "course": {"id": 12345, "name": "课程名", "identifier": "CS2024"},
  "homework": {
    "homework_id": 3635149, "name": "实验名称",
    "challenge_count": 6, "finished_challenge_count": 1
  },
  "task": {
    "challenge": "当前关卡标题",
    "path": "step1.sql",
    "status": "通过",
    "score": 100.0,
    "last_compile_output": ""
  },
  "test_sets": [
    {"result": true, "output": "预期输出...", "actual_output": "实际输出...", "is_public": true}
  ]
}
```

## 多关卡实验

头歌实验通常包含多个关卡（challenge），每个关卡是一道题。`educoder-cli` 的 `submit` 命令提交的是**当前关卡**。一个关卡通过后，可使用 `task` 查看详情，`next_game` 字段指向下一关。

```bash
# 第 1 关
educoder task --course <课堂名称> --homework <实验名称>
# → game.status: 0 (未开始)
educoder submit --course <课堂名称> --homework <实验名称> -f step1.sql

# 第 2 关 — 提交完第 1 关后平台自动推进
educoder task --course <课堂名称> --homework <实验名称>
# → challenge.subject 已变为第 2 关标题
educoder submit --course <课堂名称> --homework <实验名称> -f step2.sql

# ... 重复直到 finished_challenge_count == challenge_count
```

## 项目结构

```
educoder-cli/
├── main.py                          # 入口文件
├── pyproject.toml                    # 项目配置 & 依赖
├── requirements.txt                  # 依赖列表
├── README.md
├── .gitignore
├── src/
│   └── educoder_cli/
│       ├── __init__.py               # 版本号
│       ├── cli.py                    # Typer CLI 命令定义
│       ├── client.py                 # API 客户端（登录、请求、提交、轮询）
│       ├── models.py                 # 数据模型（Course, HomeworkCommon, TaskDetail 等）
│       ├── signature.py              # API 签名算法
│       ├── credentials.py            # 凭证持久化（读写 credentials.json）
│       └── errors.py                 # 自定义异常
└── skills/
    └── educoder-cli/
        ├── SKILL.md                  # Claude Code / Codex Skill 定义
        ├── references/
        │   └── educoder-cli.md       # 命令参考速查表
        └── agents/
            └── openai.yaml           # OpenAI 兼容 Agent 配置
```

## API 逆向说明

`educoder-cli` 通过逆向工程 EduCoder 平台的 Webpack 打包代码获得 API 签名算法。

**核心发现：**

- **API 服务器**：`https://data.educoder.net`
- **签名算法**：`md5(base64("method=METHOD&ak=AK&sk=SK&time=毫秒时间戳"))`
- **认证方式**：`Pc-Authorization` 请求头 = `_educoder_session` Cookie 值
- **关键请求头**：`X-EDU-Type: pc`、`X-EDU-Timestamp`、`X-EDU-Signature`

**提交评测流程（三步）：**

1. `POST /myshixuns/{id}/update_file.json` — 保存代码，获取 `commitID` 和 `sec_key`
2. `POST /tasks/{id}/game_build.json` — 触发评测
3. 轮询 `GET /tasks/{id}.json` — 等待 `game.status` 变为 2（通过）或 3（未通过）

**Game Status 状态说明：**

| 值 | 含义 |
|----|------|
| 0 | 未开始 |
| 1 | 评测中 |
| 2 | 通过 |
| 3 | 未通过 |

## 已知问题

### 密码登录可能失败

部分账号调用 `/accounts/login.json` 始终返回 `status=-3`（密码错误），即使密码正确。原因是平台可能对 API 登录实施了频率限制或风控。**解决方案**：使用浏览器 Cookie 手动填写凭证（见[方式二](#方式二手动提取浏览器-cookie)）。

### 未评测过的实验无法通过 CLI 提交

若实验从未在 Web 页面点击过"评测"按钮（`had_done: 0`），API 将拒绝构建（`game_build` 返回失败）。**解决方案**：在浏览器中首次手动点击一次"评测"，之后再使用 CLI 即可正常提交。

### Cookie 过期

浏览器 Cookie 有时效限制。过期后需重新从浏览器提取 `_educoder_session` 和 `autologin_trustie`，更新凭证文件。

## License

MIT
