import sqlite3
import hashlib
from config import DB_FILE

class AppError(Exception):
    """Base application error."""

class ValidationError(AppError):
    """Raised when user input is invalid."""

class AuthError(AppError):
    """Raised when login details are invalid."""

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class DatabaseManager:
    def __init__(self, path=DB_FILE):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        self.seed_initial_data()

    def execute(self, sql, params=()):
        try:
            cursor = self.connection.execute(sql, params)
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                "Duplicate entry or invalid reference. Check the values and try again."
            ) from exc

    def fetch(self, sql, params=()):
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def insert(self, table, data):
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        return self.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(data.values())
        )

    def update(self, table, data, key_column, key_value):
        assignments = ", ".join(f"{column}=?" for column in data)
        return self.execute(
            f"UPDATE {table} SET {assignments} WHERE {key_column}=?",
            (*data.values(), key_value)
        )

    def delete(self, table, key_column, key_value):
        return self.execute(
            f"DELETE FROM {table} WHERE {key_column}=?",
            (key_value,)
        )

    def backup(self, destination):
        target = sqlite3.connect(destination)
        try:
            self.connection.backup(target)
        finally:
            target.close()

    def create_tables(self):
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','faculty','student'))
        );
        CREATE TABLE IF NOT EXISTS semesters(
            semester_id INTEGER PRIMARY KEY AUTOINCREMENT,
            semester_no INTEGER UNIQUE NOT NULL,
            academic_year TEXT
        );
        CREATE TABLE IF NOT EXISTS admins(
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
            email TEXT, phone TEXT, department TEXT
        );
        CREATE TABLE IF NOT EXISTS faculty(
            faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
            department TEXT, email TEXT, phone TEXT
        );
        CREATE TABLE IF NOT EXISTS students(
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
            department TEXT,
            semester_id INTEGER NOT NULL REFERENCES semesters(semester_id),
            email TEXT, phone TEXT
        );
        CREATE TABLE IF NOT EXISTS subjects(
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            credits INTEGER NOT NULL,
            semester_id INTEGER NOT NULL REFERENCES semesters(semester_id),
            UNIQUE(subject_name, semester_id)
        );
        CREATE TABLE IF NOT EXISTS marks(
            marks_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
            faculty_id INTEGER REFERENCES faculty(faculty_id) ON DELETE SET NULL,
            internal_marks REAL NOT NULL,
            external_marks REAL NOT NULL,
            total_marks REAL NOT NULL,
            UNIQUE(student_id, subject_id)
        );
        CREATE TABLE IF NOT EXISTS results(
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            marks_id INTEGER UNIQUE NOT NULL REFERENCES marks(marks_id) ON DELETE CASCADE,
            grade TEXT NOT NULL,
            grade_point REAL NOT NULL,
            status TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0
        );
        """)
        self.connection.commit()

    def seed_initial_data(self):
        if not self.fetch("SELECT semester_id FROM semesters LIMIT 1"):
            for number in range(1, 9):
                self.insert("semesters", {
                    "semester_no": number,
                    "academic_year": "2026-27"
                })
        if not self.fetch("SELECT user_id FROM users WHERE role='admin' LIMIT 1"):
            user_id = self.insert("users", {
                "name": "System Admin",
                "username": "admin",
                "password": hash_password("admin123"),
                "role": "admin"
            })
            self.insert("admins", {"user_id": user_id})

    def close(self):
        self.connection.close()
