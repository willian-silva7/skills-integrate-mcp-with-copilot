# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities with a school-domain email
- View remaining activity capacity without exposing participant emails
- Sign in with role-protected student, provider, or administrator accounts
- Persist activities and enrollments in SQLite

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Exchange an email and password for a bearer token                  |
| GET    | `/me`                                                              | Get the authenticated user and role                                |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister the signed-in student                                  |

Protected requests must include the bearer token returned by `/auth/login`.
Students can only manage their own enrollments; providers and administrators
can manage enrollments for other students.

For local development, the seeded accounts are `student@mergington.edu` with
password `student`, `provider@mergington.edu` with password `provider`, and
`admin@mergington.edu` with password `admin`. Set `ACTIVITIES_DB` to choose a
different SQLite file and `TOKEN_SECRET` to configure token signing.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - Private list of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

The public activities response includes `available_spaces`, but never returns
the private participant list. Activities, users, and enrollments are stored in
SQLite and survive server restarts.
