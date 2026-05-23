"""Authentication module for EduCoder platform.

Key details:
- API server: https://data.educoder.net
- Auth: Pc-Authorization header = _educoder_session cookie value
- Signature: MD5(base64(timestamp_seconds))
- Timestamp must be within server tolerance (±~60s), retry on -102
"""

import os
import sys
import json
import time
import hashlib
import base64
import requests
from pathlib import Path

DEFAULT_SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session.json")
API_SERVER = "https://data.educoder.net"
WEB_SERVER = "https://www.educoder.net"


def make_signature():
    """Generate X-EDU-Timestamp and X-EDU-Signature."""
    ts = str(int(time.time()))
    b64_ts = base64.b64encode(ts.encode()).decode()
    sig = hashlib.md5(b64_ts.encode()).hexdigest()
    return ts, sig


def get_api_headers(session_token=None):
    """Build standard API request headers with fresh signature."""
    ts, sig = make_signature()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ),
        "X-EDU-Type": "pc",
        "X-EDU-Timestamp": ts,
        "X-EDU-Signature": sig,
        "Origin": WEB_SERVER,
        "Referer": f"{WEB_SERVER}/",
    }
    if session_token:
        headers["Pc-Authorization"] = session_token
    return headers


def login_with_password(login_name, password, max_retries=3):
    """Login using username/email and password.

    Returns (session_token, user_data) on success, or (None, error_msg).
    Auto-retries on timestamp mismatch (-102).
    """
    session = requests.Session()

    for attempt in range(max_retries):
        # Fresh signature for each attempt (timestamp must be within server tolerance)
        ts, sig = make_signature()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
            "X-EDU-Type": "pc",
            "X-EDU-Timestamp": ts,
            "X-EDU-Signature": sig,
            "Origin": WEB_SERVER,
            "Referer": f"{WEB_SERVER}/",
        }

        try:
            resp = session.post(
                f"{API_SERVER}/api/accounts/login.json",
                json={
                    "login": login_name,
                    "password": password,
                    "remember_me": True,
                },
                headers=headers,
                timeout=15,
            )

            if resp.status_code != 200:
                continue

            data = resp.json() if resp.headers.get("content-type", "").startswith(
                "application/json") else {}

            status = data.get("status")
            if status == -102:
                # Timestamp mismatch — retry with fresh time
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None, f"时间戳不匹配。请检查系统时间是否正确。(status={status})"

            if status == 0:
                # Success — extract session token
                token = None

                # 1. Check Set-Cookie header
                set_cookie = resp.headers.get("Set-Cookie", "")
                if "_educoder_session" in set_cookie:
                    import re
                    m = re.search(r'_educoder_session=([^;]+)', set_cookie)
                    if m:
                        token = m.group(1)

                # 2. Check response cookies
                if not token:
                    for cookie in session.cookies:
                        if "educoder_session" in cookie.name:
                            token = cookie.value

                # 3. Check response body
                if not token:
                    token = (data.get("token")
                             or data.get("authentication_token")
                             or data.get("_educoder_session")
                             or data.get("data", {}).get("token")
                             or data.get("data", {}).get("authentication_token"))

                if token:
                    return token, data

                # If no token found but status is success, maybe the session set a cookie we missed
                # Try to get all cookies from the session
                all_cookies = "; ".join(
                    f"{c.name}={c.value}" for c in session.cookies)
                return None, f"登录成功但未获取到会话token。Cookies: {all_cookies[:200] if all_cookies else 'none'}"

            elif status == -3:
                return None, "用户名或密码错误"
            elif status == -4:
                return None, f"账号已被锁定或禁用 (status={status})"
            elif status == -1:
                return None, f"请求参数错误 (status={status})"
            else:
                message = data.get("message", "")
                return None, f"登录失败 (status={status}): {message}"

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None, f"网络错误: {e}"
        except ValueError as e:
            return None, f"响应解析错误: {e}"

    return None, "超过最大重试次数"


def validate_session(session_token):
    """Validate a saved session token against the user info API."""
    headers = get_api_headers(session_token)

    try:
        resp = requests.get(
            f"{API_SERVER}/api/users/get_user_info.json",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == 0:
                return True, data
            return False, f"status={data.get('status')}: {data.get('message', '')}"
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.RequestException as e:
        return False, str(e)


def save_session(session_token):
    """Save session token to file."""
    with open(DEFAULT_SESSION_FILE, "w") as f:
        json.dump({
            "session_token": session_token,
            "saved_at": int(time.time()),
            "api_server": API_SERVER,
        }, f, indent=2)
    print(f"[+] 会话已保存到 {DEFAULT_SESSION_FILE}")


def load_session():
    """Load saved session token."""
    if os.path.exists(DEFAULT_SESSION_FILE):
        try:
            with open(DEFAULT_SESSION_FILE) as f:
                data = json.load(f)
                return data.get("session_token")
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def clear_session():
    """Remove saved session."""
    if os.path.exists(DEFAULT_SESSION_FILE):
        os.remove(DEFAULT_SESSION_FILE)
        print(f"[+] 已清除会话 ({DEFAULT_SESSION_FILE})")


def interactive_login():
    """Prompt user for credentials and log in."""
    print("\n=== EduCoder / 头歌平台 登录 ===\n")

    login_name = input("请输入账号 (手机号/邮箱/用户名): ").strip()
    if not login_name:
        print("[-] 账号不能为空")
        sys.exit(1)

    import getpass
    password = getpass.getpass("请输入密码: ").strip()
    if not password:
        print("[-] 密码不能为空")
        sys.exit(1)

    print("\n[*] 正在登录...")

    token, info = login_with_password(login_name, password)

    if token:
        print("[+] 登录成功!")
        save_session(token)

        # Show user info
        print("[*] 验证会话...")
        valid, user_info = validate_session(token)
        if valid:
            user_data = (user_info.get("user")
                         or user_info.get("data")
                         or user_info)
            name = (user_data.get("name")
                    or user_data.get("nickname")
                    or user_data.get("real_name")
                    or login_name)
            email = user_data.get("email") or user_data.get("phone") or ""
            school = user_data.get("school") or user_data.get("school_name") or ""
            print(f"[+] 当前用户: {name}")
            if email:
                print(f"[+] 联系方式: {email}")
            if school:
                print(f"[+] 学校: {school}")
        else:
            print(f"[*] 验证信息: {str(user_info)[:200]}")
        return token
    else:
        print(f"[-] 登录失败: {info}")
        print("\n[*] 请检查:")
        print("  1. 账号密码是否正确")
        print("  2. 系统时间是否准确（误差需在 60 秒以内）")
        print("  3. 网络连接是否正常")
        print("  4. 如持续失败，可在浏览器登录后使用 'educoder login --cookie <value>'")
        sys.exit(1)


def login_with_cookie(cookie_value):
    """Use a manually provided _educoder_session cookie."""
    token = cookie_value.strip()
    print("[*] 验证 Cookie...")
    valid, info = validate_session(token)
    if valid:
        save_session(token)
        user_data = info.get("user") or info.get("data") or {}
        name = user_data.get("name") or user_data.get("real_name") or "Unknown"
        print(f"[+] 登录成功! 当前用户: {name}")
        return token
    else:
        print(f"[!] Cookie 验证返回: {info}")
        print("[*] 仍然保存了 cookie，可尝试 'educoder whoami' 测试")
        save_session(token)
        return token
