# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teachers can register and unregister students after logging in
- Students can browse activities and participant lists without an account

## Teacher accounts

Teacher credentials are stored in `src/teachers.json`; only password hashes are saved. Create or update an account with:

```sh
python -m src.manage_teachers teacher-username
```

The command prompts for a password twice and requires at least 12 characters. Keep `teachers.json` private; it is ignored by Git.

Set a stable session-signing secret before starting the app. Without it, a temporary secret is generated and teacher sessions end whenever the server restarts:

```sh
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

When serving over HTTPS, also set `COOKIE_SECURE=true`. The signed teacher session cookie is HttpOnly, SameSite=Lax, and expires after one hour.

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application from the repository root:

   ```
   uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/me`                                                        | Check the current teacher session                                   |
| POST   | `/auth/login`                                                      | Log in with a teacher username and password                         |
| POST   | `/auth/logout`                                                     | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only student registration                                   |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only student removal                                      |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
