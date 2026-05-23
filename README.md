# EduCoder CLI

Head Song (EduCoder / TouGe) platform CLI tool for automating classroom, experiment, and submission workflows.

## Features

- **Classroom Management**: List, search, and inspect classrooms/courses
- **Experiment Management**: List experiments (shixuns), exercises, and tasks
- **Solution Extraction**: Extract exercise solutions and answers
- **Submission Automation**: Submit answers to exercises
- **Browser Cookie Extraction**: Auto-extract authentication from Edge/Chrome
- **Full API Access**: Raw API request support for any endpoint

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/educoder-cli.git
cd educoder-cli
pip install -r requirements.txt
```

Or via pip:

```bash
pip install -e .
```

## Quick Start

### 1. Login / Authentication

```bash
# Auto-extract cookies from Edge/Chrome browser (must be logged in)
educoder login

# Or provide cookie manually
educoder login --cookie "your_cookie_string_here"

# Check login status
educoder whoami
```

### 2. List Classrooms

```bash
# List all enrolled classrooms
educoder classrooms

# List all pages
educoder classrooms --all

# Search classrooms
educoder classrooms --search "Python"
```

### 3. List Experiments

```bash
# List experiments in a classroom
educoder shixuns <classroom_id>

# List experiments in a specific stage
educoder shixuns <classroom_id> --stage <stage_id>

# List stages in a classroom
educoder stages <classroom_id>
```

### 4. Get Exercise Info

```bash
# List exercises in an experiment
educoder exercises <shixun_id>

# Get detailed exercise info
educoder exercise <exercise_id>

# Get solution for an exercise
educoder solution <exercise_id>

# Save solution to file
educoder solution <exercise_id> --output answer.py
```

### 5. Submit Answers

```bash
# Submit a simple answer
educoder submit <exercise_id> "your answer here"

# Submit code from a file
educoder submit <exercise_id> --file solution.py

# Submit inline code
educoder submit <exercise_id> --code "print('hello world')"

# Submit JSON data
educoder submit <exercise_id> --json-file answer.json
```

### 6. Advanced

```bash
# Get environment info for a shixun
educoder env <shixun_id>

# List polls/quizzes
educoder polls <shixun_id>

# Make raw API requests
educoder raw /api/users/get_user_info.json
educoder raw /api/shixuns.json --method POST --data '{"name": "test"}'

# Extract cookies from browser
educoder browser-cookies
```

## API Endpoints Discovered

### Core Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/accounts/login.json` | POST | User login |
| `/api/users/get_user_info.json` | GET | Get current user info |
| `/api/courses/mine.json` | GET | My enrolled courses |
| `/api/v2/courses/` | GET | Courses v2 API |
| `/api/shixuns.json` | GET | Shixun list |
| `/api/shixuns/:id` | GET | Shixun detail |
| `/api/v2/stage_shixuns/` | GET | Stage shixuns |
| `/api/v2/exercises/` | GET | Exercises list |
| `/api/v2/exercises/:id` | GET | Exercise detail |
| `/api/shixun_polls/start_answer.json` | POST | Start answering |
| `/api/shixun_polls/commit_poll.json` | POST | Save answer |
| `/api/shixun_polls/commit_result.json` | POST | Submit result |

## Business Flow

```
Login → Get Classrooms → Get Stages → Get Shixuns → Get Exercises → Get Solutions → Submit
```

1. `educoder login` - Authenticate
2. `educoder classrooms` - List classrooms
3. `educoder stages <id>` - List stages in a classroom
4. `educoder shixuns <id>` - List experiments in a stage
5. `educoder exercises <id>` - List exercises in an experiment
6. `educoder solution <id>` - Get solution for an exercise
7. `educoder submit <id> <answer>` - Submit answer

## File Structure

```
educoder-cli/
├── cli.py          # CLI entry point (Click commands)
├── api.py          # API client (all endpoints)
├── auth.py         # Authentication & cookie extraction
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.8+
- requests, click, rich (optional)
- Edge or Chrome browser (for auto cookie extraction)

## License

MIT
