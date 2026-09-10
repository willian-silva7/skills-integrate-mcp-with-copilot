# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities with a school-domain email
- View remaining activity capacity without exposing participant emails

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
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister the signed-in student                                  |

Signup and unregister requests must include the `X-User-Email` header. The
header must match the student's email for student actions. Administrators may
use `X-User-Role: admin` for participant management until full authentication
and role-based access control are added.

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
the private participant list. All data is stored in memory, which means data
will be reset when the server restarts.
