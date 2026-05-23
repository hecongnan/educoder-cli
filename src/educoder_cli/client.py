import base64
import json
import time
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Self

import httpx

from educoder_cli.errors import (
    EduCoderAPIError,
    EvaluationTimeoutError,
    SessionExpiredError,
    SignatureError,
)
from educoder_cli.models import Course, HomeworkCommon, LoginResult, TaskDetail
from educoder_cli.signature import gen_signature

JsonObject = dict[str, Any]
SelectionCandidate = Course | HomeworkCommon


class AmbiguousSelectionError(ValueError):
    def __init__(self, target: str, query: str | int, candidates: list[SelectionCandidate]) -> None:
        self.target = target
        self.query = query
        self.candidates = candidates
        super().__init__(f"{target} 匹配到多个结果: {query}")


def _coerce_selector(value: str | int) -> str | int:
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return value


def _single_match(
    target: str, query: str | int, candidates: Sequence[SelectionCandidate]
) -> SelectionCandidate | None:
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise AmbiguousSelectionError(target, query, list(candidates))
    return None


class EduCoderClient:
    BASE = "https://data.educoder.net/api"

    def __init__(
        self,
        zzud: str = "",
        cookie_autologin: str = "",
        cookie_session: str = "",
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.zzud = zzud
        self.cookie_autologin = cookie_autologin
        self.cookie_session = cookie_session
        self.cookie = self._format_cookie(cookie_autologin, cookie_session)
        self.pc_auth = cookie_session
        self._client = http_client or httpx.Client(timeout=30, verify=False)
        self._owns_client = http_client is None

        self.course_identifier: str | None = None
        self.homework_common_id: int | None = None
        self.shixun_identifier: str | None = None
        self.myshixun_identifier: str | None = None
        self.game_identifier: str | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @staticmethod
    def _format_cookie(cookie_autologin: str, cookie_session: str) -> str:
        values = []
        if cookie_autologin:
            values.append(f"autologin_trustie={cookie_autologin}")
        if cookie_session:
            values.append(f"_educoder_session={cookie_session}")
        return "; ".join(values)

    def _headers(self, method: str, *, pc_auth: str | None = None, include_cookie: bool = True) -> dict[str, str]:
        ts, sig = gen_signature(method)
        headers = {
            "X-EDU-Type": "pc",
            "X-EDU-Timestamp": str(ts),
            "X-EDU-Signature": sig,
            "Pc-Authorization": self.pc_auth if pc_auth is None else pc_auth,
            "Accept": "application/json",
        }
        if include_cookie and self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    def _request_with_response(
        self, method: str, endpoint: str, *,
        json_data: JsonObject | None = None,
        headers: dict[str, str] | None = None,
        pc_auth: str | None = None,
        include_cookie: bool = True,
    ) -> tuple[JsonObject, httpx.Response]:
        url = f"{self.BASE}{endpoint}"
        req_headers = self._headers(method, pc_auth=pc_auth, include_cookie=include_cookie)
        if headers:
            req_headers.update(headers)
        try:
            if json_data is not None:
                req_headers["Content-Type"] = "application/json; charset=utf-8"
                resp = self._client.request(method, url, headers=req_headers, json=json_data)
            else:
                resp = self._client.request(method, url, headers=req_headers)
        except httpx.HTTPError as exc:
            raise EduCoderAPIError("网络请求失败，请稍后重试") from exc

        if resp.status_code == 401:
            raise SessionExpiredError("Cookie 已过期，请重新从浏览器获取", status_code=401)

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise EduCoderAPIError(f"非 JSON 响应: {resp.text[:300]}") from exc

        if not isinstance(data, dict):
            raise EduCoderAPIError("JSON 响应不是对象")
        if data.get("status") == -102:
            raise SignatureError("签名验证失败，请检查 AK/SK 或时间戳")
        return data, resp

    def _request(self, method: str, endpoint: str, *, json_data: JsonObject | None = None) -> JsonObject:
        data, _resp = self._request_with_response(method, endpoint, json_data=json_data)
        return data

    def _get(self, endpoint: str) -> JsonObject:
        return self._request("GET", endpoint)

    def _post(self, endpoint: str, json_data: JsonObject) -> JsonObject:
        return self._request("POST", endpoint, json_data=json_data)

    # ---- Login ----

    def login(self, login: str, password: str, *, autologin: bool = True) -> LoginResult:
        data, resp = self._request_with_response(
            "POST", "/accounts/login.json",
            json_data={
                "login": login, "password": password,
                "autologin": autologin, "tl": None, "source": None,
            },
            headers={
                "Origin": "https://www.educoder.net",
                "Referer": "https://www.educoder.net/login",
            },
            pc_auth="null",
            include_cookie=False,
        )

        status = data.get("status")
        if status == -3:
            raise EduCoderAPIError("用户名或密码错误")
        if status == -4:
            raise EduCoderAPIError("登录失败：账号需要绑定手机号或邮箱")
        if status == -5:
            raise EduCoderAPIError(f"登录失败: {data.get('message', '未知错误')}")
        if isinstance(status, int) and status < 0:
            raise EduCoderAPIError(f"登录失败 (status={status}): {data.get('message', '未知错误')}")

        session = resp.cookies.get("_educoder_session") or self._client.cookies.get("_educoder_session", "")
        cookie_autologin = resp.cookies.get("autologin_trustie") or self._client.cookies.get("autologin_trustie", "")
        if not session:
            raise EduCoderAPIError("登录失败：响应中缺少 _educoder_session")
        if not cookie_autologin:
            raise EduCoderAPIError("登录失败：响应中缺少 autologin_trustie")

        result = LoginResult.from_dict(data, fallback_zzud=login, autologin=cookie_autologin, session=session)
        self.zzud = result.zzud
        self.cookie_autologin = result.autologin
        self.cookie_session = result.session
        self.cookie = self._format_cookie(result.autologin, result.session)
        self.pc_auth = result.session
        return result

    # ---- Courses ----

    def get_courses(self, page: int = 1, limit: int = 20) -> list[Course]:
        data = self._get(f"/courses.json?page={page}&limit={limit}&order=mine&search=&zzud={self.zzud}")
        return [Course.from_dict(c) for c in data.get("courses", [])]

    def select_course(self, name_or_id: str | int) -> Course:
        selector = _coerce_selector(name_or_id)
        selector_text = str(name_or_id)
        courses = self.get_courses()

        if isinstance(selector, int):
            match = _single_match("课堂", name_or_id, [c for c in courses if c.id == selector])
            if isinstance(match, Course):
                self.course_identifier = match.identifier
                return match

        for matcher in [
            lambda c: c.identifier == selector_text,
            lambda c: c.name == selector_text,
            lambda c: selector_text in c.name,
        ]:
            match = _single_match("课堂", name_or_id, [c for c in courses if matcher(c)])
            if isinstance(match, Course):
                self.course_identifier = match.identifier
                return match
        raise ValueError(f"未找到匹配的课堂: {name_or_id}")

    # ---- Homeworks ----

    def get_homeworks(self, course_identifier: str | None = None) -> list[HomeworkCommon]:
        cid = course_identifier or self.course_identifier
        if not cid:
            raise ValueError("请先指定 course_identifier")
        data = self._get(
            f"/courses/{cid}/homework_commons.json"
            f"?limit=50&status=0&id={cid}&type=4&order=0&zzud={self.zzud}"
        )
        return [HomeworkCommon.from_dict(h) for h in data.get("homeworks", [])]

    def select_homework(self, identifier: int | str, *, course_identifier: str | None = None) -> HomeworkCommon:
        selector = _coerce_selector(identifier)
        selector_text = str(identifier)
        if course_identifier is not None:
            self.course_identifier = course_identifier
        homeworks = self.get_homeworks()
        target: HomeworkCommon | None = None

        if isinstance(selector, int):
            match = _single_match("实验", identifier, [h for h in homeworks if h.homework_id == selector])
            if isinstance(match, HomeworkCommon):
                target = match

        if target is None and isinstance(identifier, str):
            for matcher in [
                lambda h: h.name == selector_text,
                lambda h: selector_text in h.name,
            ]:
                match = _single_match("实验", identifier, [h for h in homeworks if matcher(h)])
                if isinstance(match, HomeworkCommon):
                    target = match
                    break

        if target is None:
            raise ValueError(f"未找到匹配的实验: {identifier}")

        self.homework_common_id = target.homework_id
        self.shixun_identifier = target.shixun_identifier
        self.myshixun_identifier = target.myshixun_identifier
        self.game_identifier = None
        self._resolve_game_identifier()
        return target

    # ---- Task Detail ----

    def get_myshixun(self, myshixun_identifier: str | None = None) -> JsonObject:
        mid = myshixun_identifier or self.myshixun_identifier
        if not mid:
            raise ValueError("请先指定 myshixun_identifier")
        return self._get(f"/myshixuns/{mid}.json?zzud={self.zzud}")

    def get_shixun_exec(self, shixun_identifier: str | None = None, homework_common_id: int | None = None) -> JsonObject:
        sid = shixun_identifier or self.shixun_identifier
        hw_id = homework_common_id or self.homework_common_id
        if not sid or not hw_id:
            raise ValueError("请先指定 shixun_identifier 和 homework_common_id")
        return self._get(f"/shixuns/{sid}/shixun_exec.json?homework_common_id={hw_id}&zzud={self.zzud}")

    def get_task_detail(self, game_identifier: str | None = None, homework_common_id: int | None = None) -> TaskDetail:
        gid = game_identifier or self.game_identifier
        hw_id = homework_common_id or self.homework_common_id
        if not gid or not hw_id:
            raise ValueError("请先指定 game_identifier 和 homework_common_id")
        data = self._get(f"/tasks/{gid}.json?homework_common_id={hw_id}&zzud={self.zzud}")
        return TaskDetail.from_dict(data)

    def _resolve_game_identifier(self) -> None:
        if self.game_identifier:
            return
        if self.myshixun_identifier:
            data = self.get_myshixun()
            self.game_identifier = str(data.get("game_identifier") or "")
        if not self.game_identifier and self.shixun_identifier and self.homework_common_id:
            data = self.get_shixun_exec()
            self.game_identifier = str(data.get("game_identifier") or "")

    def get_current_context(self) -> TaskDetail:
        self._resolve_game_identifier()
        if not self.game_identifier:
            raise ValueError("无法获取 game_identifier，该实验可能尚未开始。请先在 Web 页面打开该实验。")
        return self.get_task_detail()

    # ---- Code Operations ----

    def get_answer_code(self, code_path: str | None = None, game_identifier: str | None = None,
                        homework_common_id: int | None = None) -> str:
        gid = game_identifier or self.game_identifier
        hw_id = homework_common_id or self.homework_common_id
        path = code_path
        if not gid or not path or not hw_id:
            raise ValueError("请先指定 game_identifier, code_path, homework_common_id")
        path = path.rstrip("；;")
        data = self._get(
            f"/tasks/{gid}/rep_content.json?path={path}&homework_common_id={hw_id}&exercise_id=&zzud={self.zzud}"
        )
        content_data = data.get("content", {})
        content = content_data.get("content", "") if isinstance(content_data, dict) else ""
        return base64.b64decode(content).decode("utf-8") if content else ""

    def save_code(self, code: str, *, code_path: str | None = None, game_id: int | None = None,
                  challenge_id: int | None = None, user_id: int | None = None,
                  homework_common_id: int | None = None) -> JsonObject:
        path = code_path
        gid = game_id
        cid = challenge_id
        uid = user_id
        hw_id = homework_common_id or self.homework_common_id
        mid = self.myshixun_identifier
        if not path or gid is None or cid is None or uid is None or hw_id is None or not mid:
            raise ValueError("缺少必要参数，请先调用 select_homework 加载上下文")
        path = path.rstrip("；;")
        body: JsonObject = {
            "path": path, "evaluate": 1, "content": code,
            "game_id": gid, "tab_type": 1, "homework_common_id": hw_id,
            "extras": {
                "challenge_id": cid, "homework_common_id": hw_id,
                "currentUserId": uid, "exercise_id": "", "question_id": "",
                "subject_id": "", "competition_entry_id": "",
            },
        }
        return self._post(f"/myshixuns/{mid}/update_file.json?zzud={self.zzud}", body)

    def game_build(self, sec_key: str, commit_id: str, *, shixun_environment_id: int | None = None,
                   challenge_id: int | None = None, user_id: int | None = None,
                   homework_common_id: int | None = None, game_identifier: str | None = None) -> JsonObject:
        gid = game_identifier or self.game_identifier
        sid = shixun_environment_id
        cid = challenge_id
        uid = user_id
        hw_id = homework_common_id or self.homework_common_id
        if not gid or sid is None or cid is None or uid is None or hw_id is None:
            raise ValueError("缺少必要参数")
        body: JsonObject = {
            "sec_key": sec_key, "resubmit": "", "first": 1, "content_modified": 0,
            "shixun_environment_id": sid, "tab_type": 1,
            "extras": {
                "challenge_id": cid, "commitID": commit_id,
                "homework_common_id": hw_id, "currentUserId": uid,
                "exercise_id": "", "question_id": "", "subject_id": "", "competition_entry_id": "",
            },
        }
        return self._post(f"/tasks/{gid}/game_build.json?zzud={self.zzud}", body)

    # ---- Submit ----

    def submit(self, code: str, *, wait: bool = True, poll_interval: float = 2.0, timeout: int = 30) -> JsonObject:
        task = self.get_current_context()
        save_resp = self.save_code(
            code, code_path=task.challenge.clean_path, game_id=task.game.id,
            challenge_id=task.challenge.id, user_id=task.user.user_id,
            homework_common_id=task.homework_common_id,
        )
        content_data = save_resp.get("content", {})
        commit_id = content_data.get("commitID", "") if isinstance(content_data, dict) else ""
        sec_key = save_resp.get("sec_key", "")
        if not commit_id:
            raise EduCoderAPIError("保存代码失败: 未获取到 commitID")
        env_id = task.shixun_environments[0].shixun_environment_id if task.shixun_environments else 0
        self.game_build(
            sec_key, commit_id, shixun_environment_id=env_id,
            challenge_id=task.challenge.id, user_id=task.user.user_id,
            homework_common_id=task.homework_common_id,
        )
        if not wait:
            return {"task_detail": task, "passed": None, "test_sets": []}
        return self._poll_result(poll_interval, timeout)

    def _poll_result(self, interval: float = 2.0, timeout: int = 30) -> JsonObject:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(interval)
            result = self.get_task_detail()
            status = result.game.status
            if status == 2:
                return {"task_detail": result, "passed": True, "test_sets": result.test_sets}
            if status == 3:
                return {"task_detail": result, "passed": False, "test_sets": result.test_sets}
        raise EvaluationTimeoutError(f"评测未在 {timeout}s 内完成")

    def submit_all_levels(self, code: str) -> list[JsonObject]:
        results = []
        self.get_current_context()
        while True:
            result = self.submit(code)
            results.append(result)
            if not result["passed"]:
                break
            detail = result["task_detail"]
            if not detail.next_game:
                break
            self.game_identifier = detail.next_game
        return results
