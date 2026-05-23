#!/usr/bin/env python3
"""EduCoder CLI - Head Song (TouGe) platform automation tool.

Complete workflow:
  educoder login                    登录（首次需账号密码，后续自动使用保存的会话）
  educoder classrooms               查看课堂
  educoder unfinished <course_id>   查看未完成的实验
  educoder auto <course_id>         自动完成所有未完成的实验
"""

import os
import sys
import json
import time
import click

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import (
    load_session, save_session, clear_session,
    validate_session, interactive_login, login_with_cookie,
)
from api import EduCoderAPI, API_SERVER

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import track
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    def track(iterable, description=""):
        return iterable


def _init_api():
    token = load_session()
    if not token:
        click.echo("[-] 未登录。请先运行 'educoder login' 登录。", err=True)
        sys.exit(1)
    return EduCoderAPI(session_token=token)


def _print_json(data):
    if HAS_RICH:
        from rich import print as rprint
        rprint(data)
    else:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _print_table(title, columns, rows):
    if HAS_RICH:
        console = Console()
        table = Table(title=title)
        styles = ["cyan", "green", "yellow", "magenta", "blue", "red"]
        for i, col in enumerate(columns):
            table.add_column(col, style=styles[i % len(styles)])
        for row in rows:
            table.add_row(*[str(c) for c in row])
        console.print(table)
    else:
        if title:
            click.echo(f"\n=== {title} ===")
        for row in rows:
            click.echo(f"  {' | '.join(str(c) for c in row)}")


def _status_icon(status):
    """Return a human-readable status indicator."""
    passed = {"passed", "completed", "done", "100", 100, "百分百"}
    failed = {"failed", "error", "0", 0}
    if status in passed:
        return "[green]✓[/green]" if HAS_RICH else "✓"
    elif status in failed:
        return "[red]✗[/red]" if HAS_RICH else "✗"
    return "[yellow]…[/yellow]" if HAS_RICH else "…"


# ======== CLI Group ========

@click.group()
@click.version_option(version="1.0.0")
def main():
    """EduCoder CLI - 头歌平台命令行自动化工具。

    \b
    基本流程:
      1. educoder login              登录（首次需输入账号密码）
      2. educoder classrooms         查看我的课堂
      3. educoder shixuns <课堂ID>    查看实训
      4. educoder unfinished <课堂ID> 查看未完成
      5. educoder auto <课堂ID>       自动解答提交
    """
    pass


# ======== Auth ========

@main.command()
@click.option("--cookie", "-c", default=None, help="直接使用 _educoder_session cookie")
def login(cookie):
    """登录头歌平台。首次需要账号密码，后续自动使用保存的会话。

    \b
    示例:
      educoder login                    交互式账号密码登录
      educoder login --cookie "xxxxx"   使用浏览器 cookie
    """
    if cookie:
        login_with_cookie(cookie)
        return

    # Check existing session
    token = load_session()
    if token and not os.environ.get("EDUCODER_FORCE_LOGIN"):
        click.echo("[*] 发现已保存的会话，正在验证...")
        valid, info = validate_session(token)
        if valid:
            user_data = info.get("user") or info.get("data") or {}
            name = (user_data.get("name") or user_data.get("real_name")
                    or user_data.get("nickname") or "Unknown")
            click.echo(f"[+] 会话有效，当前用户: {name}")
            click.echo("[*] 如需重新登录: EDUCODER_FORCE_LOGIN=1 educoder login")
            return
        else:
            click.echo("[*] 会话已过期，需要重新登录")
            clear_session()

    interactive_login()


@main.command()
def logout():
    """清除已保存的登录会话。"""
    clear_session()


@main.command()
def whoami():
    """查看当前登录用户信息。"""
    api = _init_api()
    result = api.get_user_info()
    if result.get("_status") == 401 or result.get("status") == 401:
        click.echo("[-] 会话已过期，请重新登录: educoder login")
        sys.exit(1)

    if HAS_RICH:
        console = Console()
        user = result.get("user") or result.get("data") or result
        lines = []
        for k, v in user.items():
            if isinstance(v, (str, int, float, bool)) and v:
                lines.append(f"[bold]{k}[/bold]: {v}")
        console.print(Panel("\n".join(lines), title="用户信息"))
    else:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))


# ======== Classrooms ========

@main.command()
@click.option("--page", "-p", default=1, type=int)
@click.option("--per-page", "-n", default=50, type=int)
@click.option("--search", "-s", default=None)
@click.option("--all", "-a", "all_pages", is_flag=True)
def classrooms(page, per_page, search, all_pages):
    """列出我的课堂。

    \b
    示例:
      educoder classrooms
      educoder classrooms --all
      educoder classrooms --search Python
    """
    api = _init_api()

    if all_pages:
        courses = api.get_all_classrooms()
    else:
        result = api.get_classrooms(page=page, per_page=per_page, keyword=search)
        courses = (result.get("courses") or result.get("data")
                   or result.get("course_list") or [])

    if not courses:
        click.echo("[-] 没有找到课堂。")
        return

    rows = []
    for c in courses:
        rows.append([
            c.get("id", ""),
            str(c.get("name") or c.get("course_name", ""))[:50],
            str(c.get("teacher") or c.get("teacher_name", ""))[:15],
            str(c.get("status") or ""),
        ])
    _print_table("我的课堂", ["ID", "名称", "教师", "状态"], rows)
    click.echo(f"\n共 {len(courses)} 个课堂")


@main.command()
@click.argument("course_id")
def classroom(course_id):
    """查看课堂详情。"""
    api = _init_api()
    _print_json(api.get_course_detail(course_id))


@main.command()
@click.argument("course_id")
def stages(course_id):
    """列出课堂的阶段（章节）。"""
    api = _init_api()
    result = api.get_course_stages(course_id)
    stages_list = result.get("stages") or result.get("data") or []
    rows = [[s.get("id", ""), str(s.get("name", ""))[:60], s.get("position", "")]
            for s in stages_list]
    _print_table(f"课堂 {course_id} 的阶段", ["ID", "名称", "位置"], rows)


# ======== Shixuns ========

@main.command()
@click.argument("course_id")
@click.option("--stage", "-s", "stage_id", default=None, type=int)
@click.option("--all", "-a", "all_stages", is_flag=True)
def shixuns(course_id, stage_id, all_stages):
    """列出课堂中的实验/实训。"""
    api = _init_api()

    if all_stages:
        shixuns_list = api.get_all_shixuns_in_course(course_id)
    else:
        result = api.get_shixuns(course_id, stage_id=stage_id)
        shixuns_list = result.get("shixuns") or result.get("data") or []

    if not shixuns_list:
        click.echo("[-] 没有找到实训。")
        return

    rows = []
    for s in shixuns_list:
        rows.append([
            s.get("id", ""),
            str(s.get("name") or s.get("title", ""))[:55],
            str(s.get("shixun_type") or s.get("type", ""))[:12],
            str(s.get("_stage_name") or s.get("stage_name", ""))[:18],
        ])
    _print_table("实训列表", ["ID", "名称", "类型", "阶段"], rows)
    click.echo(f"\n共 {len(shixuns_list)} 个实训")


@main.command()
@click.argument("shixun_id")
def info(shixun_id):
    """查看实训详情。"""
    api = _init_api()
    _print_json(api.get_shixun_detail(shixun_id))


# ======== Exercises ========

@main.command()
@click.argument("shixun_id")
def exercises(shixun_id):
    """列出实训中的所有习题。"""
    api = _init_api()
    result = api.get_exercises(shixun_id)
    exercises_list = result.get("exercises") or result.get("data") or []

    if not exercises_list:
        tasks_r = api._get("/api/tasks/", params={"shixun_id": shixun_id})
        exercises_list = tasks_r.get("tasks") or tasks_r.get("data") or []

    if not exercises_list:
        click.echo("[-] 没有找到习题。")
        return

    rows = [[e.get("id", ""),
             str(e.get("name") or e.get("title", ""))[:55],
             str(e.get("exercise_type") or e.get("type", ""))[:15]]
            for e in exercises_list]
    _print_table(f"实训 {shixun_id} 的习题", ["ID", "标题", "类型"], rows)
    click.echo(f"\n共 {len(exercises_list)} 个习题")


@main.command()
@click.argument("exercise_id")
def exercise(exercise_id):
    """查看习题详情（题目内容、答案提示等）。"""
    api = _init_api()
    _print_json(api.get_exercise_detail(exercise_id))


# ======== Solution / Submit ========

@main.command()
@click.argument("exercise_id")
@click.option("--output", "-o", default=None)
def solution(exercise_id, output):
    """尝试提取习题的解答/答案。

    会从习题详情的多个字段中尝试提取正确答案。

    \b
    示例:
      educoder solution 12345
      educoder solution 12345 --output answer.py
    """
    api = _init_api()
    detail = api.get_exercise_detail(exercise_id)

    # Also try to get exercise question answers
    ex_data = detail.get("exercise") or detail.get("data") or detail
    qid = (ex_data.get("question_id")
           or detail.get("question_id")
           or exercise_id)

    answer = api._extract_answer({}, detail)

    if not answer:
        # Try exercise_answers endpoint
        try:
            ans_result = api.get_exercise_answers(qid)
            answer = (ans_result.get("data") or ans_result.get("answers")
                      or ans_result.get("answer"))
        except Exception:
            pass

    if answer:
        click.echo("=" * 60)
        click.echo("[+] 找到解答:")
        click.echo("-" * 60)
        click.echo(answer if isinstance(answer, str)
                   else json.dumps(answer, indent=2, ensure_ascii=False))
        click.echo("=" * 60)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                content = (answer if isinstance(answer, str)
                           else json.dumps(answer, indent=2, ensure_ascii=False))
                f.write(content)
            click.echo(f"[+] 已保存到 {output}")
    else:
        click.echo("[*] 未能自动提取解答。完整习题数据：")
        _print_json(detail)


@main.command()
@click.argument("exercise_id")
@click.argument("answer", required=False, default=None)
@click.option("--file", "-f", "answer_file", default=None)
@click.option("--code", "-c", default=None)
@click.option("--json-file", "-j", "json_file", default=None)
def submit(exercise_id, answer, answer_file, code, json_file):
    """提交习题答案。

    \b
    示例:
      educoder submit 12345 "print('hello')"
      educoder submit 12345 --file solution.py
      educoder submit 12345 --code "答案内容"
      educoder submit 12345 --json-file answer.json
    """
    api = _init_api()
    answer_content = answer

    if code:
        answer_content = code
    elif answer_file:
        if os.path.exists(answer_file):
            with open(answer_file, "r", encoding="utf-8") as f:
                answer_content = f.read()
        else:
            click.echo(f"[-] 文件不存在: {answer_file}")
            sys.exit(1)
    elif json_file:
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                answer_content = json.load(f)
        else:
            click.echo(f"[-] 文件不存在: {json_file}")
            sys.exit(1)

    if not answer_content:
        click.echo("[-] 请提供答案内容。")
        sys.exit(1)

    # Find category_id from exercise detail
    detail = api.get_exercise_detail(exercise_id)
    category_id = (detail.get("category_id")
                   or detail.get("exercise", {}).get("category_id")
                   or detail.get("data", {}).get("category_id")
                   or exercise_id)

    click.echo(f"[*] 提交习题 {exercise_id} (category={category_id}) ...")

    # Start + commit
    start_r = api.start_exercise(category_id)
    click.echo(f"[*] 开始: status={start_r.get('status')}")

    commit_r = api.commit_exercise(category_id, answer_content)
    click.echo(f"[*] 提交: status={commit_r.get('status')}")

    time.sleep(1)

    # Check result
    try:
        check_r = api.get_exercise_result(category_id)
        click.echo(f"[*] 结果: {json.dumps(check_r, indent=2, ensure_ascii=False)[:500]}")
    except Exception:
        pass

    click.echo("\n[+] 提交完成。请用 'educoder check {0}' 验证。".format(exercise_id))


@main.command()
@click.argument("exercise_id")
def check(exercise_id):
    """检查习题完成状态。

    \b
    示例:
      educoder check 12345
    """
    api = _init_api()

    detail = api.get_exercise_detail(exercise_id)
    category_id = (detail.get("category_id")
                   or detail.get("exercise", {}).get("category_id")
                   or exercise_id)

    result = api.get_exercise_result(category_id)
    code_check = api.get_code_check(exercise_id)

    if HAS_RICH:
        console = Console()
        console.print(Panel(
            f"Exercise: {exercise_id}\n"
            f"Result: {json.dumps(result, indent=2, ensure_ascii=False)[:300]}\n"
            f"Code Check: {json.dumps(code_check, indent=2, ensure_ascii=False)[:300]}",
            title="Exercise Status"
        ))
    else:
        click.echo(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
        click.echo(f"Code Check: {json.dumps(code_check, indent=2, ensure_ascii=False)[:500]}")


# ======== Unfinished ========

@main.command()
@click.argument("course_id")
@click.option("--output", "-o", default=None, help="导出未完成列表到JSON文件")
def unfinished(course_id, output):
    """列出课堂中所有未完成的实验/习题。

    \b
    示例:
      educoder unfinished 12345
      educoder unfinished 12345 --output pending.json
    """
    api = _init_api()
    click.echo(f"[*] 正在扫描课堂 {course_id} 中的未完成实验...")

    shixuns = api.get_all_shixuns_in_course(course_id)
    if not shixuns:
        click.echo("[-] 该课堂没有实训。")
        return

    all_unfinished = []

    for s in track(shixuns, description="扫描实训中..."):
        sid = s.get("id")
        if not sid:
            continue

        user_ex = api.get_user_exercises(sid)
        exercises_list = user_ex.get("exercises") or user_ex.get("data") or []

        # If no user exercises, get standard exercises
        if not exercises_list:
            ex_r = api.get_exercises(sid)
            exercises_list = ex_r.get("exercises") or ex_r.get("data") or []

        for ex in exercises_list:
            eid = ex.get("id") or ex.get("exercise_id")
            status = (ex.get("status") or ex.get("exercise_status")
                      or ex.get("pass_status") or "")

            is_done = str(status).lower() in ("passed", "completed", "done", "100")
            if not is_done:
                info = {
                    "shixun_id": sid,
                    "shixun_name": s.get("name", ""),
                    "stage_name": s.get("_stage_name", ""),
                    "exercise_id": eid,
                    "exercise_name": ex.get("name") or ex.get("title", ""),
                    "exercise_type": ex.get("exercise_type") or ex.get("type", ""),
                    "status": status,
                }
                all_unfinished.append(info)

    if not all_unfinished:
        click.echo("[+] 太棒了，该课堂所有实验都已完成！")
        return

    rows = []
    for u in all_unfinished:
        rows.append([
            u["exercise_id"],
            u["exercise_name"][:40],
            u["exercise_type"][:12],
            _status_icon(u["status"]),
            f"实训: {u['shixun_name'][:20]}",
        ])
    _print_table(f"未完成的实验 (共 {len(all_unfinished)} 个)",
                 ["ID", "名称", "类型", "状态", "所属实训"], rows)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(all_unfinished, f, indent=2, ensure_ascii=False)
        click.echo(f"[+] 未完成列表已导出到 {output}")


# ======== Auto Solve ========

@main.command()
@click.argument("target_id")
@click.option("--yes", "-y", "auto_yes", is_flag=True, help="跳过确认，直接执行")
@click.option("--output", "-o", default=None, help="导出解题报告到JSON文件")
def auto(target_id, auto_yes, output):
    """自动解答并提交目标中的所有未完成实验。

    目标可以是课堂ID（自动处理整个课堂）或实训ID（只处理该实训）。

    \b
    示例:
      educoder auto 12345           自动完成课堂12345中的所有未完成实验
      educoder auto 12345 --yes     跳过确认直接执行
      educoder auto 67890           自动完成实训67890（如果只给实训ID）
    """
    api = _init_api()

    # Determine if target is a course or shixun
    is_course = False
    try:
        course_detail = api.get_course_detail(target_id)
        if course_detail.get("status") == 0 or "name" in course_detail:
            is_course = True
    except Exception:
        pass

    if is_course:
        course_name = (course_detail.get("name")
                       or course_detail.get("data", {}).get("name", ""))
        click.echo(f"[*] 目标: 课堂 [{target_id}] {course_name}")

        unfinished_list = api.get_unfinished_exercises(target_id)
        if not unfinished_list:
            click.echo("[+] 该课堂所有实验都已完成！")
            return

        click.echo(f"[*] 发现 {len(unfinished_list)} 个未完成的实验")

        # Also check shixun-based exercises
        shixuns = api.get_all_shixuns_in_course(target_id)
        click.echo(f"[*] 共有 {len(shixuns)} 个实训需要检查")
    else:
        click.echo(f"[*] 目标: 实训 [{target_id}]")
        shixuns = [{"id": target_id, "name": "目标实训"}]
        unfinished_list = []
        is_course = False

    # Confirmation
    if not auto_yes:
        if is_course:
            click.echo(f"\n将自动处理课堂 [{target_id}] 中所有未完成的实验。")
        else:
            click.echo(f"\n将自动处理实训 [{target_id}] 中的所有实验。")
        click.confirm("确认继续?", abort=True)

    # Process
    all_reports = []

    if is_course:
        for s in track(shixuns, description="处理实训中..."):
            sid = s.get("id")
            if not sid:
                continue
            click.echo(f"\n{'='*50}")
            click.echo(f"[*] 处理实训 [{sid}] {s.get('name', '')}")
            click.echo(f"{'='*50}")

            report = api.auto_solve_shixun(sid)
            all_reports.append(report)

            solved = len(report.get("solved", []))
            failed = len(report.get("failed", []))
            skipped = len(report.get("skipped", []))
            click.echo(f"  已解决: {solved} | 失败: {failed} | 已跳过: {skipped}")

            if solved > 0:
                for item in report["solved"]:
                    click.echo(f"    ✓ [{item['id']}] {item.get('name', '')}")
            if failed > 0:
                for item in report["failed"]:
                    click.echo(f"    ✗ [{item['id']}] {item.get('name', '')}: {item.get('reason', '')}")
    else:
        report = api.auto_solve_shixun(target_id)
        all_reports.append(report)

    # Summary
    total_solved = sum(len(r.get("solved", [])) for r in all_reports)
    total_failed = sum(len(r.get("failed", [])) for r in all_reports)
    total_skipped = sum(len(r.get("skipped", [])) for r in all_reports)

    click.echo(f"\n{'='*50}")
    click.echo(f"[+] 完成！已解决: {total_solved} | 失败: {total_failed} | 跳过: {total_skipped}")
    click.echo(f"{'='*50}")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(all_reports, f, indent=2, ensure_ascii=False)
        click.echo(f"[+] 报告已保存到 {output}")


@main.command()
@click.argument("shixun_id")
def solve(shixun_id):
    """自动解答单个实训中的所有习题。

    \b
    示例:
      educoder solve 12345
    """
    api = _init_api()
    click.echo(f"[*] 正在自动解答实训 [{shixun_id}] ...")
    report = api.auto_solve_shixun(shixun_id)

    click.echo(f"\n已解决: {len(report.get('solved', []))}")
    for item in report.get("solved", []):
        click.echo(f"  ✓ [{item['id']}] {item.get('name', '')}")

    click.echo(f"\n失败: {len(report.get('failed', []))}")
    for item in report.get("failed", []):
        click.echo(f"  ✗ [{item['id']}] {item.get('name', '')}: {item.get('reason', '')}")

    click.echo(f"\n跳过: {len(report.get('skipped', []))}")
    if output := click.prompt("是否保存详细报告? (输入路径或按回车跳过)", default="", show_default=False):
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        click.echo(f"[+] 报告已保存到 {output}")


# ======== Environment ========

@main.command()
@click.argument("shixun_id")
def env(shixun_id):
    """获取实训的开发环境信息。"""
    api = _init_api()
    result = api.get_shixun_environment(shixun_id)
    _print_json(result)


@main.command()
@click.argument("shixun_id")
def jupyter(shixun_id):
    """获取实训的 Jupyter 链接。"""
    api = _init_api()
    result = api.get_jupyter_new(shixun_id)
    _print_json(result)


@main.command()
@click.argument("shixun_id")
def challenges(shixun_id):
    """查看实训的编程挑战。"""
    api = _init_api()
    result = api.get_shixun_challenges(shixun_id)
    challenges_list = result.get("challenges") or result.get("data") or []
    if challenges_list:
        rows = [[c.get("id", ""), str(c.get("name", ""))[:55],
                 c.get("difficulty", ""), c.get("score", "")]
                for c in challenges_list]
        _print_table(f"实训 {shixun_id} 的挑战", ["ID", "名称", "难度", "分数"], rows)
        click.echo(f"\n共 {len(challenges_list)} 个挑战")
    else:
        _print_json(result)


# ======== Raw API ========

@main.command()
@click.argument("path")
@click.option("--method", "-m", default="GET",
              type=click.Choice(["GET", "POST", "PUT", "DELETE"]))
@click.option("--data", "-d", default=None, help="请求数据 (JSON)")
@click.option("--form", "-f", "form_data", default=None, help="表单数据 (key=value&...)")
def raw(path, method, data, form_data):
    """直接调用 API 接口（高级用法）。

    \b
    示例:
      educoder raw /api/users/get_user_info.json
      educoder raw /api/exercises/123/code_check.json --method POST
    """
    api = _init_api()
    kwargs = {}
    if data:
        try:
            kwargs["json"] = json.loads(data)
        except json.JSONDecodeError:
            kwargs["form"] = data
    if form_data:
        kwargs["form"] = form_data

    result = api.raw(method, path, **kwargs)
    _print_json(result)


# ======== Export ========

@main.command()
@click.argument("course_id")
@click.option("--output", "-o", default="course_data.json")
def export(course_id, output):
    """导出课堂的完整数据（阶段、实训、习题及答案）。

    \b
    示例:
      educoder export 12345
      educoder export 12345 --output my_course.json
    """
    api = _init_api()

    click.echo(f"[*] 正在导出课堂 {course_id} ...")
    course_info = api.get_course_detail(course_id)
    shixuns = api.get_all_shixuns_in_course(course_id)

    export_data = {"course": course_info, "shixuns": []}

    for s in track(shixuns, description="导出实训中..."):
        sid = s.get("id")
        shixun_data = {"info": s, "exercises": []}
        if sid:
            ex_r = api.get_exercises(sid)
            for ex in (ex_r.get("exercises") or ex_r.get("data") or []):
                ex_id = ex.get("id")
                if ex_id:
                    shixun_data["exercises"].append({
                        "summary": ex,
                        "detail": api.get_exercise_detail(ex_id),
                    })
        export_data["shixuns"].append(shixun_data)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    click.echo(f"[+] 已导出到 {output}")


if __name__ == "__main__":
    main()
