from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Self


def _string_or_empty(value: Any) -> str:
    return "" if value is None else str(value)


@dataclass
class LoginResult:
    user_id: str = ""
    login: str = ""
    name: str = ""
    identity: str = ""
    school: str = ""
    grade: str = ""
    zzud: str = ""
    autologin: str = ""
    session: str = ""

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, fallback_zzud: str, autologin: str, session: str
    ) -> Self:
        login = _string_or_empty(data.get("login"))
        return cls(
            user_id=_string_or_empty(data.get("user_id")),
            login=login,
            name=_string_or_empty(data.get("name")),
            identity=_string_or_empty(data.get("identity")),
            school=_string_or_empty(data.get("school")),
            grade=_string_or_empty(data.get("grade")),
            zzud=login or fallback_zzud,
            autologin=autologin,
            session=session,
        )


@dataclass
class Course:
    id: int
    name: str
    identifier: str
    school: str = ""
    creator: str = ""
    tasks_count: int = 0
    course_members_count: int = 0
    is_end: bool = False
    is_accessible: bool = True

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            identifier=data.get("identifier", ""),
            school=data.get("school", ""),
            creator=data.get("creator", ""),
            tasks_count=data.get("tasks_count", 0),
            course_members_count=data.get("course_members_count", 0),
            is_end=data.get("is_end", False),
            is_accessible=data.get("is_accessible", True),
        )


@dataclass
class HomeworkCommon:
    homework_id: int
    name: str
    shixun_identifier: str
    myshixun_identifier: str | None
    status: list[str] = field(default_factory=list)
    time_status: int = 0
    challenge_count: int = 0
    finished_challenge_count: int = 0
    checked_challenge_count: int = 0
    shixun_finished_status: int = 0
    publish_time: str = ""
    end_time: str = ""
    upper_category_name: str = ""
    author: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            homework_id=data.get("homework_id", 0),
            name=data.get("name", ""),
            shixun_identifier=data.get("shixun_identifier", ""),
            myshixun_identifier=data.get("myshixun_identifier"),
            status=data.get("status", []),
            time_status=data.get("time_status", 0),
            challenge_count=data.get("challenge_count", 0),
            finished_challenge_count=data.get("finished_challenge_count", 0),
            checked_challenge_count=data.get("checked_challenge_count", 0),
            shixun_finished_status=data.get("shixun_finished_status", 0),
            publish_time=data.get("publish_time", ""),
            end_time=data.get("end_time", ""),
            upper_category_name=data.get("upper_category_name", ""),
            author=data.get("author", ""),
        )


@dataclass
class Challenge:
    id: int
    subject: str = ""
    position: int = 0
    score: int = 0
    path: str = ""
    difficulty: int = 0
    task_pass: str = ""
    exec_time: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            id=data["id"],
            subject=data.get("subject", ""),
            position=data.get("position", 0),
            score=data.get("score", 0),
            path=data.get("path", ""),
            difficulty=data.get("difficulty", 0),
            task_pass=data.get("task_pass", ""),
            exec_time=data.get("exec_time", 0),
        )

    @property
    def clean_path(self) -> str:
        return self.path.rstrip("；;")


@dataclass
class TestSet:
    result: bool | None = None
    output: str | None = ""
    actual_output: str | None = ""
    compile_success: int | None = None
    is_public: bool = False
    ts_time: float | None = None
    ts_mem: float | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            result=data.get("result"),
            output=data.get("output"),
            actual_output=data.get("actual_output"),
            compile_success=data.get("compile_success"),
            is_public=data.get("is_public", False),
            ts_time=data.get("ts_time"),
            ts_mem=data.get("ts_mem"),
        )


@dataclass
class ShixunEnvironment:
    shixun_environment_id: int
    name: str = ""
    tab_type: int = 1
    resource_type: int = 1

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            shixun_environment_id=data.get("shixun_environment_id", 0),
            name=data.get("name", ""),
            tab_type=data.get("tab_type", 1),
            resource_type=data.get("resource_type", 1),
        )


@dataclass
class Game:
    id: int
    identifier: str = ""
    user_id: int = 0
    status: int = 0
    final_score: float = 0.0
    challenge_id: int = 0
    myshixun_id: int = 0
    accuracy: float = 0.0
    cost_time: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            id=data["id"],
            identifier=data.get("identifier", ""),
            user_id=data.get("user_id", 0),
            status=data.get("status", 0),
            final_score=data.get("final_score", 0.0),
            challenge_id=data.get("challenge_id", 0),
            myshixun_id=data.get("myshixun_id", 0),
            accuracy=data.get("accuracy", 0.0),
            cost_time=data.get("cost_time", 0),
        )


@dataclass
class User:
    user_id: int
    login: str = ""
    name: str = ""
    identity: int = 6

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            user_id=data.get("user_id", 0),
            login=data.get("login", ""),
            name=data.get("name", ""),
            identity=data.get("identity", 6),
        )


@dataclass
class TaskDetail:
    game: Game = field(default_factory=lambda: Game(id=0))
    challenge: Challenge = field(default_factory=lambda: Challenge(id=0))
    user: User = field(default_factory=lambda: User(user_id=0))
    test_sets: list[TestSet] = field(default_factory=list)
    shixun_environments: list[ShixunEnvironment] = field(default_factory=list)
    homework_common_id: int = 0
    homework_common_name: str = ""
    sec_key: str = ""
    prev_game: str | None = None
    next_game: str | None = None
    last_compile_output: str = ""
    game_count: int = 0
    time_limit: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        game = Game.from_dict(data["game"]) if data.get("game") else Game(id=0)
        challenge = (
            Challenge.from_dict(data["challenge"]) if data.get("challenge") else Challenge(id=0)
        )
        user = User.from_dict(data["user"]) if data.get("user") else User(user_id=0)
        test_sets = [TestSet.from_dict(ts) for ts in data.get("test_sets", [])]
        environments = [
            ShixunEnvironment.from_dict(env) for env in data.get("shixun_environments", [])
        ]
        return cls(
            game=game,
            challenge=challenge,
            user=user,
            test_sets=test_sets,
            shixun_environments=environments,
            homework_common_id=data.get("homework_common_id", 0),
            homework_common_name=data.get("homework_common_name", ""),
            sec_key=data.get("sec_key", ""),
            prev_game=data.get("prev_game"),
            next_game=data.get("next_game"),
            last_compile_output=data.get("last_compile_output", ""),
            game_count=data.get("game_count", 0),
            time_limit=data.get("time_limit", 0),
        )
