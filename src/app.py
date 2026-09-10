"""Mergington High School activities API."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API", description="API for extracurricular activities")
DATABASE_PATH = Path(os.getenv("ACTIVITIES_DB", Path(__file__).with_name("activities.db")))
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "development-only-change-me").encode()
EMAIL_PATTERN = re.compile(r"^[^@\s]+@mergington\.edu$", re.IGNORECASE)
TOKEN_LIFETIME_SECONDS = 60 * 60 * 8

INITIAL_ACTIVITIES = {
    "Chess Club": ("Learn strategies and compete in chess tournaments", "Fridays, 3:30 PM - 5:00 PM", 12),
    "Programming Class": ("Learn programming fundamentals and build software projects", "Tuesdays and Thursdays, 3:30 PM - 4:30 PM", 20),
    "Gym Class": ("Physical education and sports activities", "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM", 30),
    "Soccer Team": ("Join the school soccer team and compete in matches", "Tuesdays and Thursdays, 4:00 PM - 5:30 PM", 22),
    "Basketball Team": ("Practice and play basketball with the school team", "Wednesdays and Fridays, 3:30 PM - 5:00 PM", 15),
    "Art Club": ("Explore your creativity through painting and drawing", "Thursdays, 3:30 PM - 5:00 PM", 15),
    "Drama Club": ("Act, direct, and produce plays and performances", "Mondays and Wednesdays, 4:00 PM - 5:30 PM", 20),
    "Math Club": ("Solve challenging problems and participate in math competitions", "Tuesdays, 3:30 PM - 4:30 PM", 10),
    "Debate Team": ("Develop public speaking and argumentation skills", "Fridays, 4:00 PM - 5:30 PM", 12),
}
INITIAL_PARTICIPANTS = {
    "Chess Club": ["michael@mergington.edu", "daniel@mergington.edu"],
    "Programming Class": ["emma@mergington.edu", "sophia@mergington.edu"],
    "Gym Class": ["john@mergington.edu", "olivia@mergington.edu"],
    "Soccer Team": ["liam@mergington.edu", "noah@mergington.edu"],
    "Basketball Team": ["ava@mergington.edu", "mia@mergington.edu"],
    "Art Club": ["amelia@mergington.edu", "harper@mergington.edu"],
    "Drama Club": ["ella@mergington.edu", "scarlett@mergington.edu"],
    "Math Club": ["james@mergington.edu", "benjamin@mergington.edu"],
    "Debate Team": ["charlotte@mergington.edu", "henry@mergington.edu"],
}


def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def initialize_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('student', 'provider', 'admin'))
            );
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY, description TEXT NOT NULL,
                schedule TEXT NOT NULL, max_participants INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollments (
                activity_name TEXT NOT NULL REFERENCES activities(name) ON DELETE CASCADE,
                student_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (activity_name, student_email)
            );
        """)
        if connection.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO activities VALUES (?, ?, ?, ?)",
                [(name, *details) for name, details in INITIAL_ACTIVITIES.items()],
            )
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO users VALUES (?, ?, ?)",
                [("student@mergington.edu", hash_password("student"), "student"),
                 ("provider@mergington.edu", hash_password("provider"), "provider"),
                 ("admin@mergington.edu", hash_password("admin"), "admin")],
            )
        for email in {email for participants in INITIAL_PARTICIPANTS.values() for email in participants}:
            connection.execute(
                "INSERT OR IGNORE INTO users VALUES (?, ?, 'student')",
                (email, hash_password("student")),
            )
        if connection.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO enrollments(activity_name, student_email) VALUES (?, ?)",
                [(activity, email) for activity, participants in INITIAL_PARTICIPANTS.items() for email in participants],
            )


class LoginRequest(BaseModel):
    email: str
    password: str


def validate_email(email: str) -> str:
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise HTTPException(400, "A valid @mergington.edu email address is required")
    return normalized_email


def issue_token(email: str, role: str) -> str:
    payload = {"email": email, "role": role, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(TOKEN_SECRET, encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in before performing this action")
    try:
        encoded, signature = authorization[7:].split(".", 1)
        expected = hmac.new(TOKEN_SECRET, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < time.time():
            raise ValueError
        return {"email": validate_email(payload["email"]), "role": payload["role"]}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(401, "Invalid or expired authentication token")


initialize_database()
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(credentials: LoginRequest):
    email = validate_email(credentials.email)
    with connect() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not secrets.compare_digest(user["password_hash"], hash_password(credentials.password)):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": issue_token(email, user["role"]), "token_type": "bearer", "role": user["role"]}


@app.get("/me")
def get_current_user(user: Annotated[dict, Depends(current_user)]):
    return user


@app.get("/activities")
def get_activities():
    with connect() as connection:
        rows = connection.execute("""
            SELECT a.name, a.description, a.schedule, a.max_participants,
                   COUNT(e.student_email) AS participant_count
            FROM activities a LEFT JOIN enrollments e ON e.activity_name = a.name
            GROUP BY a.name ORDER BY a.name
        """).fetchall()
    return {row["name"]: {
        "description": row["description"], "schedule": row["schedule"],
        "max_participants": row["max_participants"],
        "available_spaces": row["max_participants"] - row["participant_count"],
    } for row in rows}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, user: Annotated[dict, Depends(current_user)]):
    email = validate_email(email)
    if user["role"] == "student" and user["email"] != email:
        raise HTTPException(403, "Students can only sign themselves up")
    with connect() as connection:
        activity = connection.execute("SELECT max_participants FROM activities WHERE name = ?", (activity_name,)).fetchone()
        if not activity:
            raise HTTPException(404, "Activity not found")
        count = connection.execute("SELECT COUNT(*) FROM enrollments WHERE activity_name = ?", (activity_name,)).fetchone()[0]
        if count >= activity["max_participants"]:
            raise HTTPException(409, "Activity is full")
        if not connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(404, "Student account not found")
        try:
            connection.execute("INSERT INTO enrollments(activity_name, student_email) VALUES (?, ?)", (activity_name, email))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Student is already signed up")
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, user: Annotated[dict, Depends(current_user)]):
    email = validate_email(email)
    if user["role"] == "student" and user["email"] != email:
        raise HTTPException(403, "Students can only unregister themselves")
    with connect() as connection:
        result = connection.execute("DELETE FROM enrollments WHERE activity_name = ? AND student_email = ?", (activity_name, email))
        if result.rowcount == 0:
            raise HTTPException(400, "Student is not signed up for this activity")
    return {"message": f"Unregistered {email} from {activity_name}"}
