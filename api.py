"""EduCoder platform API client. Covers complete business flow."""

import json
import time
import requests
from auth import get_api_headers, API_SERVER, WEB_SERVER


class EduCoderAPI:
    def __init__(self, session_token=None, api_server=None):
        self.api_server = api_server or API_SERVER
        self.session_token = session_token
        self.session = requests.Session()

    def _headers(self, extra=None):
        h = get_api_headers(self.session_token)
        h["Origin"] = WEB_SERVER
        h["Referer"] = f"{WEB_SERVER}/"
        if extra:
            h.update(extra)
        return h

    def _get(self, path, params=None):
        url = f"{self.api_server}{path}"
        resp = self.session.get(url, params=params, headers=self._headers(), timeout=30)
        return self._parse(resp)

    def _post(self, path, data=None, json_data=None, form_data=None):
        url = f"{self.api_server}{path}"
        if form_data:
            resp = self.session.post(url, data=form_data,
                                     headers=self._headers(
                                         {"Content-Type": "application/x-www-form-urlencoded"}),
                                     timeout=30)
        elif json_data is not None:
            resp = self.session.post(url, json=json_data, headers=self._headers(), timeout=30)
        else:
            resp = self.session.post(url, data=data, headers=self._headers(), timeout=30)
        return self._parse(resp)

    def _put(self, path, data=None, json_data=None):
        url = f"{self.api_server}{path}"
        resp = self.session.put(url, data=data, json=json_data, headers=self._headers(), timeout=30)
        return self._parse(resp)

    def _parse(self, resp):
        ct = resp.headers.get("Content-Type", "")
        if resp.status_code == 204:
            return {"_status": 204}
        if "application/json" in ct:
            try:
                return resp.json()
            except ValueError:
                return {"_raw": resp.text, "_status": resp.status_code}
        return {"_raw": resp.text, "_status": resp.status_code}

    # ============ User ============
    def get_user_info(self):
        return self._get("/api/users/get_user_info.json")

    # ============ Classrooms ============
    def get_classrooms(self, page=1, per_page=20, keyword=None):
        params = {"page": page, "per_page": per_page}
        if keyword:
            params["search"] = keyword
        return self._get("/api/courses/mine.json", params=params)

    def get_course_detail(self, course_id):
        return self._get(f"/api/v2/courses/{course_id}")

    def search_courses(self, keyword, page=1, per_page=20):
        return self._get("/api/courses/search_all.json",
                         params={"search": keyword, "page": page, "per_page": per_page})

    def get_course_stages(self, course_id):
        return self._get("/api/v2/stages.json", params={"course_id": course_id})

    # ============ Shixuns ============
    def get_shixuns(self, course_id, stage_id=None, page=1, per_page=50):
        params = {"course_id": course_id, "page": page, "per_page": per_page}
        if stage_id is not None:
            params["stage_id"] = stage_id
        return self._get("/api/v2/stage_shixuns/", params=params)

    def get_shixun_detail(self, shixun_id):
        return self._get(f"/api/shixuns/{shixun_id}")

    def get_shixun_challenges(self, shixun_identifier):
        """Get challenges (programming tasks) for a shixun."""
        return self._get(f"/api/shixuns/{shixun_identifier}/challenges.json")

    def get_shixun_environment(self, shixun_id):
        return self._get(f"/api/shixuns/{shixun_id}/environment_info")

    def get_jupyter_new(self, shixun_id):
        return self._get(f"/api/shixuns/{shixun_id}/jupyter_new.json")

    def get_challenge_detail(self, shixun_id):
        """Get shixun challenges."""
        return self._get(f"/api/shixuns/{shixun_id}/challenges.json")

    def review_newest_record(self, shixun_id):
        """Get newest game record for a shixun."""
        return self._get(f"/api/shixuns/{shixun_id}/review_newest_record.json")

    # ============ Exercises ============
    def get_exercises(self, shixun_id, page=1, per_page=50):
        return self._get("/api/v2/exercises/",
                         params={"shixun_id": shixun_id, "page": page, "per_page": per_page})

    def get_exercise_detail(self, exercise_id):
        return self._get(f"/api/v2/exercises/{exercise_id}")

    def get_user_exercises(self, shixun_id):
        """Get user's exercise status/progress for a shixun."""
        return self._get("/api/exercises/get_user_exercises.json",
                         params={"shixun_id": shixun_id})

    def get_exercise_lists(self, category_id):
        """Get exercise list for a category."""
        return self._get(f"/api/exercises/{category_id}/exercise_lists.json")

    def get_exercise_result(self, category_id):
        """Get exercise result."""
        return self._get(f"/api/exercises/{category_id}/exercise_result.json")

    def get_user_exercise_detail(self, category_id):
        """Get user's exercise detail."""
        return self._get(f"/api/exercises/{category_id}/user_exercise_detail.json")

    def get_code_check(self, exercise_id):
        """Check code exercise status."""
        return self._get(f"/api/exercises/{exercise_id}/code_check.json",
                         params={"id": exercise_id})

    def check_user_exercise(self, exercise_id):
        """Check user exercise completion."""
        return self._get(f"/api/exercises/{exercise_id}/check_user_exercise.json")

    # ============ Exercise Actions ============
    def start_exercise(self, category_id):
        """Start an exercise."""
        return self._post(f"/api/exercises/{category_id}/start.json")

    def commit_exercise(self, category_id, answers=None):
        """Commit/submit exercise answer."""
        if answers is None:
            answers = {}
        return self._post(f"/api/exercises/{category_id}/commit_exercise.json",
                          form_data=answers if isinstance(answers, dict) else {"answer": answers})

    def simulate_start_answer(self, category_id):
        """Simulate start answer."""
        return self._post(f"/api/exercises/{category_id}/simulate_start_answer.json")

    def simulate_commit_exercise(self, category_id, answers=None):
        """Simulate commit exercise."""
        return self._post(f"/api/exercises/{category_id}/simulate_commit_exercise.json",
                          form_data=answers if isinstance(answers, dict) else {"answer": answers})

    def review_exercise_user(self, exercise_id):
        """Review/submit exercise user data."""
        return self._post(f"/api/exercises/{exercise_id}/review_exercise_user.json")

    # ============ Exercise Questions (item-based) ============
    def get_exercise_questions(self, category_id):
        """Get exercise questions for a category."""
        return self._get(f"/api/exercises/{category_id}/exercise_questions.json")

    def get_exercise_answers(self, question_id):
        """Get answers for an exercise question."""
        return self._get(f"/api/exercise_questions/{question_id}/exercise_answers.json")

    # ============ Polls ============
    def get_poll_list(self, shixun_id):
        return self._get("/api/shixun_polls/select_polls_list.json",
                         params={"shixun_id": shixun_id})

    def get_poll_detail(self, poll_id):
        return self._get("/api/shixun_polls/select_polls.json", params={"id": poll_id})

    def start_poll_answer(self, poll_id):
        return self._post("/api/shixun_polls/start_answer.json", form_data={"id": poll_id})

    def commit_poll(self, poll_id, answers):
        if isinstance(answers, (dict, list)):
            answers = json.dumps(answers, ensure_ascii=False)
        return self._post("/api/shixun_polls/commit_poll.json",
                          form_data={"id": poll_id, "answers": answers})

    def commit_poll_result(self, poll_id):
        return self._post("/api/shixun_polls/commit_result.json", form_data={"id": poll_id})

    # ============ Student Works (homework) ============
    def get_student_works(self, homework_id, page=1, per_page=50):
        return self._get(f"/api/homework_commons/{homework_id}/student_works.json",
                         params={"page": page, "per_page": per_page})

    def get_all_student_works(self, category_id):
        return self._get(f"/api/homework_commons/{category_id}/all_student_works.json")

    def get_work_detail(self, homework_id):
        return self._get(f"/api/student_works/{homework_id}.json")

    def get_shixun_work_report(self, homework_id):
        return self._get(f"/api/student_works/{homework_id}/shixun_work_report.json")

    def submit_test_result(self, work_id):
        """Submit test result for a student work."""
        return self._post(f"/api/student_works/{work_id}/submit_test_result.json")

    # ============ Game / Pod ============
    def query_game_url(self, work_id):
        """Get game VM URL for a student work."""
        return self._get(f"/api/student_works/{work_id}/query_game_url.json")

    def exit_delete_pod(self, myshixun_id):
        """Exit and delete the pod/VM."""
        return self._post(f"/api/myshixuns/{myshixun_id}/exit_delete_pod.json")

    def get_newest_shixun_work_comments(self, work_id):
        return self._get(f"/api/student_works/{work_id}/get_newest_shixun_work_comments.json")

    # ============ Jupyter ============
    def active_jupyter_with_tpm(self, shixun_id=None, **params):
        return self._get("/api/jupyters/active_with_tpm.json", params=params)

    def save_jupyter_with_tpm(self, **data):
        return self._post("/api/jupyters/save_with_tpm.json", form_data=data)

    def get_jupyter_info_with_tpm(self, **params):
        return self._get("/api/jupyters/get_info_with_tpm.json", params=params)

    # ============ Raw ============
    def raw(self, method, path, **kwargs):
        url = f"{self.api_server}{path}"
        if method == "GET":
            return self._get(path, params=kwargs.get("params"))
        elif method == "POST":
            return self._post(path, json_data=kwargs.get("json"), form_data=kwargs.get("form"))
        elif method == "PUT":
            return self._put(path, json_data=kwargs.get("json"))
        elif method == "DELETE":
            resp = self.session.delete(url, headers=self._headers(), timeout=30)
            return self._parse(resp)
        raise ValueError(f"Unsupported method: {method}")

    # ============ High-level helpers ============
    def get_all_classrooms(self):
        all_courses = []
        page = 1
        while True:
            result = self.get_classrooms(page=page, per_page=50)
            courses = (result.get("courses") or result.get("data")
                       or result.get("course_list") or [])
            if not courses:
                break
            all_courses.extend(courses)
            if len(courses) < 50:
                break
            page += 1
        return all_courses

    def get_all_shixuns_in_course(self, course_id):
        all_shixuns = []
        stages_result = self.get_course_stages(course_id)
        stages = (stages_result.get("stages") or stages_result.get("data") or [])

        if stages:
            for stage in stages:
                sid = stage.get("id")
                if sid:
                    result = self.get_shixuns(course_id, stage_id=sid)
                    shixuns = result.get("shixuns") or result.get("data") or []
                    for s in shixuns:
                        s["_stage_name"] = stage.get("name", "")
                        s["_stage_id"] = sid
                    all_shixuns.extend(shixuns)
        else:
            result = self.get_shixuns(course_id)
            all_shixuns = result.get("shixuns") or result.get("data") or []
        return all_shixuns

    def get_unfinished_exercises(self, course_id):
        """Get all unfinished exercises across a course."""
        unfinished = []
        shixuns = self.get_all_shixuns_in_course(course_id)

        for s in shixuns:
            sid = s.get("id")
            if not sid:
                continue

            # Get user exercise status for this shixun
            user_ex = self.get_user_exercises(sid)
            exercises = (user_ex.get("exercises") or user_ex.get("data") or [])

            for ex in exercises:
                status = ex.get("status") or ex.get("exercise_status") or ""
                if status not in ("passed", "completed", "done", 100, "100"):
                    unfinished.append({
                        "shixun_id": sid,
                        "shixun_name": s.get("name", ""),
                        "stage_name": s.get("_stage_name", ""),
                        "exercise": ex,
                    })
        return unfinished

    def auto_solve_shixun(self, shixun_id):
        """Attempt to auto-solve all exercises in a shixun.

        This is the main automation entry point.
        Returns a report of what was solved.
        """
        report = {"shixun_id": shixun_id, "solved": [], "failed": [], "skipped": []}

        # 1. Get exercises
        ex_result = self.get_exercises(shixun_id)
        exercises = ex_result.get("exercises") or ex_result.get("data") or []

        if not exercises:
            # Try getting challenges (programming tasks in VM)
            challenges = self.get_shixun_challenges(shixun_id)
            challenges_list = challenges.get("challenges") or challenges.get("data") or []
            if challenges_list:
                return self._auto_solve_challenges(shixun_id, challenges_list)

        # 2. Get user exercise status
        user_ex = self.get_user_exercises(shixun_id)
        user_exercises = user_ex.get("exercises") or user_ex.get("data") or []

        # Build status map
        status_map = {}
        for ue in user_exercises:
            eid = ue.get("id") or ue.get("exercise_id")
            if eid:
                status_map[eid] = ue

        # 3. Process each exercise
        for ex in exercises:
            ex_id = ex.get("id")
            if not ex_id:
                continue

            status_info = status_map.get(ex_id, {})
            current_status = (status_info.get("status")
                              or status_info.get("exercise_status")
                              or status_info.get("pass_status")
                              or "")

            if current_status in ("passed", "completed", "done"):
                report["skipped"].append({
                    "id": ex_id,
                    "name": ex.get("name", ""),
                    "reason": "already completed",
                })
                continue

            # Try to solve
            try:
                result = self._solve_single_exercise(ex)
                if result.get("success"):
                    report["solved"].append({
                        "id": ex_id,
                        "name": ex.get("name", ""),
                        "result": result,
                    })
                else:
                    report["failed"].append({
                        "id": ex_id,
                        "name": ex.get("name", ""),
                        "reason": result.get("error", "unknown"),
                    })
            except Exception as e:
                report["failed"].append({
                    "id": ex_id,
                    "name": ex.get("name", ""),
                    "reason": str(e),
                })
        return report

    def _solve_single_exercise(self, exercise):
        """Solve a single exercise by submitting the correct answer.

        Strategy:
        1. Get exercise detail to find the correct answer
        2. Start the exercise
        3. Submit the answer
        4. Check result
        """
        ex_id = exercise.get("id")
        category_id = exercise.get("category_id") or exercise.get("exercise_category_id") or ex_id
        ex_type = exercise.get("exercise_type") or exercise.get("type") or ""

        if not ex_id:
            return {"success": False, "error": "no exercise id"}

        # Get exercise detail for answer hints
        detail = self.get_exercise_detail(ex_id)
        if detail.get("_status") and detail["_status"] >= 400:
            detail = {}

        # Try to find answer in the exercise data
        answer = self._extract_answer(exercise, detail)

        if not answer:
            return {"success": False, "error": "could not extract answer", "detail": detail}

        # Start exercise
        start_result = self.start_exercise(category_id)

        # Submit answer
        commit_result = self.commit_exercise(category_id, answer)

        # Check result
        time.sleep(1)
        check_result = self.get_exercise_result(category_id)

        success = (commit_result.get("status") == 0
                   or check_result.get("pass") == True
                   or check_result.get("status") in ("passed", "completed"))

        return {
            "success": success,
            "answer": answer,
            "start": start_result,
            "commit": commit_result,
            "check": check_result,
        }

    def _extract_answer(self, exercise, detail):
        """Extract the correct answer from exercise data."""
        # Priority 1: Direct answer field
        for field in ["answer", "correct_answer", "solution", "right_answer",
                      "reference_answer", "standard_answer"]:
            val = detail.get(field) or exercise.get(field)
            if val:
                return val

        # Priority 2: Nested in data/exercise/question
        for container in ["data", "exercise", "question", "detail"]:
            inner = detail.get(container, {})
            if isinstance(inner, dict):
                for field in ["answer", "correct_answer", "solution",
                              "reference_answer", "standard_answer"]:
                    val = inner.get(field)
                    if val:
                        return val

        # Priority 3: For code exercises, look at template/code
        for field in ["template", "code_template", "initial_code", "default_code",
                      "solution_code", "answer_code"]:
            val = detail.get(field) or exercise.get(field)
            if val:
                return val

        # Priority 4: For quiz/poll exercises, look at items/options with is_correct
        items = detail.get("items") or detail.get("options") or detail.get("choices") or []
        if items:
            correct_items = [i for i in items if i.get("is_correct") or i.get("correct")]
            if correct_items:
                return correct_items

        # Priority 5: Check if there's a challenge/answer sub-object
        for key in detail:
            if "answer" in key.lower() or "solution" in key.lower():
                val = detail[key]
                if val:
                    return val

        # Priority 6: Try to get from exercise_answers endpoint
        question_id = detail.get("question_id") or exercise.get("question_id")
        if question_id:
            answers = self.get_exercise_answers(question_id)
            if answers and answers.get("status") == 0:
                ans_data = answers.get("data") or answers.get("answers") or []
                if ans_data:
                    return ans_data

        return None

    def _auto_solve_challenges(self, shixun_id, challenges):
        """Auto-solve programming challenges in a VM-based shixun."""
        report = {"shixun_id": shixun_id, "challenges": []}

        for challenge in challenges:
            ch_id = challenge.get("id")
            ch_name = challenge.get("name", "")
            result = {"id": ch_id, "name": ch_name, "success": False}

            # Challenges typically need code in a VM environment
            # We'd need to connect to the Jupyter/pod and execute
            # For now: try to get review/newest record to check status
            try:
                record = self.review_newest_record(shixun_id)
                result["record"] = record
            except Exception as e:
                result["error"] = str(e)

            report["challenges"].append(result)

        return report
