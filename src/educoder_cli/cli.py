"""EduCoder CLI - 头歌平台命令行工具。"""

import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated, Any, ClassVar, NoReturn

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from educoder_cli import __version__
from educoder_cli.client import AmbiguousSelectionError, EduCoderClient
from educoder_cli.credentials import StoredCredentials, load_credentials, save_credentials
from educoder_cli.errors import EduCoderAPIError
from educoder_cli.models import Course, HomeworkCommon, LoginResult, TaskDetail, TestSet

app = typer.Typer(no_args_is_help=True, help="Educoder / 头歌 command line client.")
console = Console()
err_console = Console(stderr=True)

# ---- Options ----

ZzudOption = Annotated[str | None, typer.Option("--zzud", envvar="EDUCODER_ZZUD")]
AutologinOption = Annotated[str | None, typer.Option("--autologin", envvar="EDUCODER_AUTOLOGIN")]
SessionOption = Annotated[str | None, typer.Option("--session", envvar="EDUCODER_SESSION")]
JsonOption = Annotated[bool, typer.Option("--json", help="Output JSON.")]
CourseOption = Annotated[str, typer.Option("--course", help="Course ID, identifier, or name fragment.")]
HomeworkOption = Annotated[str, typer.Option("--homework", help="Homework ID or name fragment.")]
LoginOption = Annotated[str, typer.Option("--login", help="Educoder username, phone, or email.")]
PasswordOption = Annotated[str, typer.Option("--password", prompt=True, hide_input=True, help="Educoder password.")]


# ---- Helpers ----

_HTML_TAG = __import__("re").compile(r"</?[A-Za-z][^>]*>")


class _HTMLToText(HTMLParser):
    _BLOCK: ClassVar[set[str]] = {"blockquote", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ol", "p", "pre", "tr", "ul"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "li":
            self._parts.append("\n- ")
        elif tag.lower() in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts).strip()


def _require_credentials(zzud, autologin, session) -> tuple[str, str, str]:
    if not zzud or not autologin or not session:
        try:
            stored = load_credentials()
        except ValueError as exc:
            _print_error(exc)
            raise typer.Exit(1)
        if stored is not None:
            zzud = zzud or stored.zzud
            autologin = autologin or stored.autologin
            session = session or stored.session

    missing = []
    if not zzud:
        missing.append("EDUCODER_ZZUD")
    if not session:
        missing.append("EDUCODER_SESSION")
    if missing:
        err_console.print("[red]Missing credentials:[/red] " + ", ".join(missing))
        err_console.print("Run [bold]educoder login[/bold] or set credential env vars/options.")
        raise typer.Exit(2)
    return zzud, autologin, session


def _print_json(data: Any) -> None:
    console.print_json(data=data)


def _print_error(exc: Exception) -> None:
    err_console.print(f"[red]{escape(str(exc))}[/red]")


def _handle_cli_error(exc: EduCoderAPIError | ValueError) -> NoReturn:
    _print_error(exc)
    raise typer.Exit(1) from exc


def _select_course_and_homework(client: EduCoderClient, course: str, homework: str) -> tuple[Course, HomeworkCommon]:
    return client.select_course(course), client.select_homework(homework)


def _format_status(status: list[str]) -> str:
    return "、".join(status) if status else ""


def _format_progress(h: HomeworkCommon) -> str:
    return f"{h.finished_challenge_count}/{h.challenge_count}"


def _game_status(value: int) -> str:
    return {0: "未开始", 1: "评测中", 2: "通过", 3: "未通过"}.get(value, str(value))


def _truncate(value: str | None, limit: int = 600) -> str:
    if value is None:
        return ""
    return value[:limit] + "…" if len(value) > limit else value


def _format_problem_text(value: str) -> str:
    normalized = value.strip()
    if _HTML_TAG.search(normalized):
        parser = _HTMLToText()
        parser.feed(normalized)
        parser.close()
        normalized = parser.get_text() or normalized
    return "\n".join(l for l in normalized.splitlines() if l.strip().casefold() != "[toc]").strip()


def _render_task_detail(task: TaskDetail) -> None:
    table = Table(title="Task")
    table.add_column("Field"); table.add_column("Value")
    table.add_row("Homework", escape(task.homework_common_name))
    table.add_row("Challenge", escape(task.challenge.subject))
    table.add_row("Path", escape(task.challenge.clean_path))
    table.add_row("Status", _game_status(task.game.status))
    table.add_row("Score", str(task.game.final_score))
    console.print(table)
    formatted = _format_problem_text(task.challenge.task_pass)
    if formatted:
        console.print(Panel(Markdown(_truncate(formatted, 4000)), title="Task Description"))
    if task.test_sets:
        ts_table = Table(title="Test Sets")
        ts_table.add_column("#", justify="right")
        ts_table.add_column("Result")
        ts_table.add_column("Expected")
        ts_table.add_column("Actual")
        for i, ts in enumerate(task.test_sets, 1):
            ts_table.add_row(str(i), "pass" if ts.result else "fail" if ts.result is not None else "",
                             escape(_truncate(ts.output, 120)), escape(_truncate(ts.actual_output, 120)))
        console.print(ts_table)


# ---- Commands ----

@app.command()
def version() -> None:
    """Show version."""
    console.print(f"educoder-cli {__version__}")


@app.command()
def login(account: LoginOption, password: PasswordOption, json_output: JsonOption = False) -> None:
    """Log in and persist credentials."""
    try:
        with EduCoderClient() as client:
            result = client.login(account, password)
        cred_path = save_credentials(StoredCredentials.from_login_result(result))
    except (EduCoderAPIError, ValueError) as exc:
        _handle_cli_error(exc)

    if json_output:
        _print_json({"user": {"user_id": result.user_id, "login": result.login, "name": result.name,
                     "identity": result.identity, "school": result.school, "grade": result.grade},
                     "saved": True, "credentials_path": str(cred_path)})
    else:
        console.print(f"[green]Logged in as {escape(result.name or result.login or result.user_id)}.[/green]")


@app.command()
def status(zzud: ZzudOption = None, autologin: AutologinOption = None, session: SessionOption = None,
           json_output: JsonOption = False) -> None:
    """Check if credentials are usable."""
    auth = _require_credentials(zzud, autologin, session)
    try:
        with EduCoderClient(*auth) as client:
            courses = client.get_courses(page=1, limit=1)
    except EduCoderAPIError as exc:
        _handle_cli_error(exc)
    if json_output:
        _print_json({"authenticated": True, "courses_checked": len(courses)})
    else:
        console.print("[green]Authenticated.[/green]")


@app.command()
def courses(zzud: ZzudOption = None, autologin: AutologinOption = None, session: SessionOption = None,
            page: Annotated[int, typer.Option("--page", min=1)] = 1,
            limit: Annotated[int, typer.Option("--limit", min=1)] = 20,
            json_output: JsonOption = False) -> None:
    """List courses."""
    auth = _require_credentials(zzud, autologin, session)
    try:
        with EduCoderClient(*auth) as client:
            course_list = client.get_courses(page=page, limit=limit)
    except EduCoderAPIError as exc:
        _handle_cli_error(exc)

    if json_output:
        _print_json([{"id": c.id, "name": c.name, "identifier": c.identifier, "school": c.school,
                       "tasks_count": c.tasks_count} for c in course_list])
    else:
        table = Table(title="Courses")
        table.add_column("ID", justify="right"); table.add_column("Name")
        table.add_column("Identifier"); table.add_column("Tasks", justify="right")
        for c in course_list:
            table.add_row(str(c.id), escape(c.name), escape(c.identifier), str(c.tasks_count))
        console.print(table)


@app.command()
def homeworks(course: CourseOption, zzud: ZzudOption = None, autologin: AutologinOption = None,
              session: SessionOption = None, json_output: JsonOption = False) -> None:
    """List homeworks (experiments) for a course."""
    auth = _require_credentials(zzud, autologin, session)
    try:
        with EduCoderClient(*auth) as client:
            selected = client.select_course(course)
            hw_list = client.get_homeworks()
    except (EduCoderAPIError, ValueError) as exc:
        _handle_cli_error(exc)

    if json_output:
        _print_json({"course": {"id": selected.id, "name": selected.name, "identifier": selected.identifier},
                     "homeworks": [{"homework_id": h.homework_id, "name": h.name,
                                    "challenge_count": h.challenge_count,
                                    "finished_challenge_count": h.finished_challenge_count,
                                    "shixun_finished_status": h.shixun_finished_status,
                                    "status": h.status, "end_time": h.end_time} for h in hw_list]})
    else:
        table = Table(title=f"Homeworks - {selected.name}")
        table.add_column("ID", justify="right"); table.add_column("Name")
        table.add_column("Progress"); table.add_column("Status"); table.add_column("End")
        for h in hw_list:
            table.add_row(str(h.homework_id), escape(h.name), _format_progress(h),
                          escape(_format_status(h.status)), escape(h.end_time))
        console.print(table)


@app.command(name="task")
def task_command(course: CourseOption, homework: HomeworkOption, zzud: ZzudOption = None,
                 autologin: AutologinOption = None, session: SessionOption = None,
                 json_output: JsonOption = False) -> None:
    """Show current task detail for a homework."""
    auth = _require_credentials(zzud, autologin, session)
    try:
        with EduCoderClient(*auth) as client:
            selected_course, selected_homework = _select_course_and_homework(client, course, homework)
            detail = client.get_current_context()
    except (EduCoderAPIError, ValueError) as exc:
        _handle_cli_error(exc)

    if json_output:
        _print_json({"course": selected_course.identifier, "homework": selected_homework.homework_id,
                     "task": {"challenge": detail.challenge.subject, "path": detail.challenge.clean_path,
                              "status": _game_status(detail.game.status), "score": detail.game.final_score}})
    else:
        _render_task_detail(detail)


@app.command()
def code(course: CourseOption, homework: HomeworkOption, zzud: ZzudOption = None,
         autologin: AutologinOption = None, session: SessionOption = None,
         code_path: Annotated[str | None, typer.Option("--path")] = None,
         output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
         force: Annotated[bool, typer.Option("--force")] = False,
         json_output: JsonOption = False) -> None:
    """Read remote answer code."""
    auth = _require_credentials(zzud, autologin, session)
    try:
        with EduCoderClient(*auth) as client:
            _select_course_and_homework(client, course, homework)
            detail = client.get_current_context()
            remote_path = code_path or detail.challenge.clean_path
            content = client.get_answer_code(code_path=remote_path)
        if output is not None:
            if output.exists() and not force:
                raise ValueError(f"输出文件已存在: {output}，使用 --force 覆盖")
            output.write_text(content, encoding="utf-8")
    except (EduCoderAPIError, ValueError) as exc:
        _handle_cli_error(exc)

    if json_output:
        _print_json({"path": remote_path, "output": str(output) if output else None,
                     "content": content if not output else None, "written": output is not None})
    elif output is None:
        sys.stdout.write(content)
    else:
        console.print(f"Wrote {escape(str(output))}")


@app.command()
def submit(course: CourseOption, homework: HomeworkOption,
           file: Annotated[str, typer.Option("--file", "-f", help="Local code file, or '-' for stdin.")],
           zzud: ZzudOption = None, autologin: AutologinOption = None, session: SessionOption = None,
           no_wait: Annotated[bool, typer.Option("--no-wait")] = False,
           timeout: Annotated[int, typer.Option("--timeout", min=1)] = 30,
           poll_interval: Annotated[float, typer.Option("--poll-interval", min=0.1)] = 2.0,
           json_output: JsonOption = False) -> None:
    """Submit local code and wait for evaluation."""
    auth = _require_credentials(zzud, autologin, session)
    try:
        source = sys.stdin.read() if file == "-" else Path(file).read_text(encoding="utf-8")
        with EduCoderClient(*auth) as client:
            _select_course_and_homework(client, course, homework)
            result = client.submit(source, wait=not no_wait, poll_interval=poll_interval, timeout=timeout)
    except (EduCoderAPIError, ValueError) as exc:
        _handle_cli_error(exc)

    passed = result.get("passed")
    if json_output:
        _print_json({"passed": passed, "test_sets": [
            {"result": ts.result, "output": ts.output, "actual_output": ts.actual_output}
            for ts in (result.get("test_sets") or [])]})
    else:
        if passed is None:
            console.print("[green]Submitted (no wait).[/green]")
        elif passed:
            console.print("[green]Passed![/green]")
        else:
            console.print("[red]Failed.[/red]")
    if passed is False:
        raise typer.Exit(1)
