"""
头歌实验全自动提交脚本 v3
=======================

基于 educoder-cli 包，自动从 API 获取凭证和代码模板。
用法: python educoder_auto.py [--dry-run] [--course GXV5CTWD]
"""

import json
import sys
import time
from pathlib import Path

# Use educoder-cli package
sys.path.insert(0, str(Path(__file__).resolve().parent / "educoder-cli" / "src"))
from educoder_cli.client import EduCoderClient
from educoder_cli.credentials import load_credentials
from educoder_cli.errors import EvaluationTimeoutError

DEFAULT_COURSE = "GXV5CTWD"

# 未完成实验的答案（按 challenge_id 精确匹配）
ANSWERS = {
    # 12-2 授权及回收权限 — 授予某表上的所有权限
    3863627: (
        "CREATE USER IF NOT EXISTS 'user1'@'localhost' IDENTIFIED BY '123';\n"
        "CREATE USER IF NOT EXISTS 'user2'@'%' IDENTIFIED BY '123';\n"
        "GRANT ALL PRIVILEGES ON teachingdb.student TO 'user1'@'localhost' WITH GRANT OPTION;\n"
        "GRANT ALL PRIVILEGES ON teachingdb.student TO 'user2'@'%';"
    ),
    # 7-2 视图 — 向信息系学生的视图中插入数据
    3863567: "INSERT INTO v_information VALUES ('98001', '王立红', '信息', '02');",
    # 7-1 索引 — 创建全文索引
    3863547: (
        "CREATE FULLTEXT INDEX ft_remarks ON student(remarks);\n"
        "SHOW INDEX FROM student;\n"
        "SELECT sname FROM student WHERE MATCH(remarks) AGAINST('学生干部');"
    ),
}

# 不需要 "use teachingdb;" 前缀的实验（用户/角色管理类）
NO_DB_PREFIX = {3635201, 3635199, 3635196}


def wrap_sql(sql, hw_id=None):
    """根据实验类型决定是否加 use teachingdb 前缀"""
    if hw_id in NO_DB_PREFIX:
        prefix = ""
    elif sql.strip().lower().startswith("use "):
        prefix = ""
    else:
        prefix = "use teachingdb;\n"
    return (
        prefix
        + "/****请在此编写代码，操作完毕之后点击评测******/\n\n"
        + "/**********Begin**********/\n"
        + sql
        + "\n/**********End**********/"
    )


def auto_complete_homework(client, hw_id, course):
    """自动完成一个实验的所有未通过关卡"""
    print(f"\n{'='*60}")

    try:
        hw = client.select_homework(hw_id, course_identifier=course)
    except Exception as e:
        print(f"  SKIP: {e}")
        return 0, 0

    print(f"  {hw.name} ({hw_id})")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    while client.game_identifier:
        task = client.get_task_detail()
        ch_name = task.challenge.subject
        ch_id = task.challenge.id

        # 已通过，跳过
        if task.game.status == 2:
            print(f"  [{ch_name}] 已通过，跳过")
            passed += 1
            if not task.next_game:
                break
            client.game_identifier = task.next_game
            continue

        # 查找答案（按 challenge_id 精确匹配）
        sql = ANSWERS.get(ch_id)
        if sql is None:
            # 尝试从代码模板获取（如果模板里已经有答案）
            try:
                template = client.get_answer_code(code_path=task.challenge.clean_path)
                # 提取 Begin/End 之间的代码
                import re
                m = re.search(r"/\*+Begin\*+/\s*\n(.*?)\n\s*/\*+End\*+/", template, re.DOTALL)
                if m:
                    candidate = m.group(1).strip()
                    if candidate and len(candidate) > 5:
                        sql = candidate
                        print(f"  [{ch_name}] 使用模板代码")
            except Exception:
                pass

        if sql is None:
            print(f"  [{ch_name}] 无答案 (challenge_id={ch_id})")
            failed += 1
            if not task.next_game:
                break
            client.game_identifier = task.next_game
            continue

        code = wrap_sql(sql, hw_id)
        print(f"  [{ch_name}] 提交中...")
        print(f"    SQL: {sql[:120]}")

        try:
            result = client.submit(code, timeout=90)
            if result["passed"]:
                print(f"    PASS!")
                passed += 1
            else:
                print(f"    FAIL")
                for ts in result.get("test_sets", []):
                    if ts.result is False:
                        print(f"    预期: {str(ts.output)[:100] if ts.output else '(空)'}")
                        print(f"    实际: {str(ts.actual_output)[:100] if ts.actual_output else '(空)'}")
                failed += 1
        except EvaluationTimeoutError:
            task2 = client.get_task_detail()
            if task2.test_sets and any(ts.result is not None for ts in task2.test_sets):
                if all(ts.result for ts in task2.test_sets if ts.result is not None):
                    print(f"    PASS (超时后检测到通过)")
                    passed += 1
                else:
                    print(f"    FAIL (超时)")
                    failed += 1
            else:
                print(f"    TIMEOUT")
                failed += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            failed += 1

        time.sleep(2)
        if not task.next_game:
            break
        client.game_identifier = task.next_game

    print(f"  结果: {passed}通过 {failed}失败")
    return passed, failed


def main():
    dry_run = "--dry-run" in sys.argv

    # 从保存的凭证文件加载
    try:
        cred = load_credentials()
    except Exception as e:
        print(f"无法加载凭证: {e}")
        print("请先运行: python -m educoder_cli login")
        return

    course = DEFAULT_COURSE
    for arg in sys.argv:
        if arg.startswith("--course"):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                course = sys.argv[idx + 1]

    client = EduCoderClient(*cred.as_tuple())

    print("=" * 60)
    print("EduCoder Auto Submit v3")
    print(f"Course: {course}")
    print("=" * 60)

    # 显示实验状态
    print("\n实验状态:")
    client.course_identifier = course
    try:
        homeworks = client.get_homeworks()
    except Exception as e:
        print(f"获取实验列表失败: {e}")
        client.close()
        return

    for h in homeworks:
        pct = f"{h.finished_challenge_count}/{h.challenge_count}"
        done = h.finished_challenge_count >= h.challenge_count
        mark = "DONE" if done else "TODO"
        print(f"  [{mark}] {h.name} ({pct})")

    if dry_run:
        client.close()
        return

    total_pass = 0
    total_fail = 0

    # 只处理有未完成关卡的实验
    incomplete_hw_ids = {
        h.homework_id for h in homeworks
        if h.finished_challenge_count < h.challenge_count
    }

    # 获取所有未完成的 challenge_id
    print("\n扫描未完成关卡...")
    for hw_id in sorted(incomplete_hw_ids):
        try:
            client.select_homework(hw_id, course_identifier=course)
            while client.game_identifier:
                task = client.get_task_detail()
                if task.game.status != 2:
                    print(f"  需完成: {task.challenge.subject} (id={task.challenge.id})")
                if not task.next_game:
                    break
                client.game_identifier = task.next_game
        except Exception as e:
            print(f"  扫描 {hw_id} 出错: {e}")

    # 开始自动提交
    for hw_id in sorted(incomplete_hw_ids):
        p, f = auto_complete_homework(client, hw_id, course)
        total_pass += p
        total_fail += f

    print(f"\n{'='*60}")
    print(f"总计: {total_pass} 通过, {total_fail} 失败")
    print(f"{'='*60}")

    client.close()


if __name__ == "__main__":
    main()
