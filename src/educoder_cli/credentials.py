import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from educoder_cli.models import LoginResult

APP_DIR_NAME = "educoder-cli"
CREDENTIALS_FILE_NAME = "credentials.json"


@dataclass(frozen=True)
class StoredCredentials:
    zzud: str
    autologin: str
    session: str

    @classmethod
    def from_login_result(cls, result: LoginResult) -> Self:
        return cls(
            zzud=result.zzud,
            autologin=result.autologin,
            session=result.session,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        credentials = cls(
            zzud=str(data.get("zzud") or ""),
            autologin=str(data.get("autologin") or ""),
            session=str(data.get("session") or ""),
        )
        if not credentials.zzud or not credentials.session:
            raise ValueError("保存的登录状态不完整，请重新运行 educoder login")
        return credentials

    def to_dict(self) -> dict[str, str]:
        return {"zzud": self.zzud, "autologin": self.autologin, "session": self.session}

    def as_tuple(self) -> tuple[str, str, str]:
        return self.zzud, self.autologin, self.session


def default_credentials_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME / CREDENTIALS_FILE_NAME
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME / CREDENTIALS_FILE_NAME
    return Path.home() / ".config" / APP_DIR_NAME / CREDENTIALS_FILE_NAME


def load_credentials(path: Path | None = None) -> StoredCredentials | None:
    credentials_path = path or default_credentials_path()
    if not credentials_path.exists():
        return None
    try:
        raw_data = json.loads(credentials_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("无法读取保存的登录状态，请重新运行 educoder login") from exc
    if not isinstance(raw_data, dict):
        raise ValueError("保存的登录状态格式无效，请重新运行 educoder login")
    return StoredCredentials.from_dict(raw_data)


def save_credentials(credentials: StoredCredentials, path: Path | None = None) -> Path:
    credentials_path = path or default_credentials_path()
    data = json.dumps(credentials.to_dict(), ensure_ascii=False, indent=2) + "\n"
    try:
        credentials_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError:
        pass
    credentials_path.write_text(data, encoding="utf-8")
    return credentials_path
