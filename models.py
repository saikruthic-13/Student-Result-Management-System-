from functools import reduce
from config import MAX_INTERNAL, MAX_EXTERNAL, PASS_MARK, GRADE_TABLE
from database import AuthError, ValidationError, hash_password

def require(value, label):
    if value is None or not str(value).strip():
        raise ValidationError(f"{label} is required.")

def to_number(value, label, cast=float):
    try:
        return cast(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} must be a valid number.")

def validate_contact(email, phone):
    if email and ("@" not in email or "." not in email):
        raise ValidationError("Enter a valid email address.")
    if phone and not (phone.isdigit() and len(phone) == 10):
        raise ValidationError("Phone must be exactly 10 digits.")

class Subject:
    def __init__(self, subject_id, name, credits):
        self.subject_id, self.name, self.credits = subject_id, name, credits

    @property
    def label(self):
        return f"{self.subject_id} - {self.name}"

class Semester:
    def __init__(self, semester_id):
        self.semester_id = semester_id

    def get_subjects(self, db):
        rows = db.fetch(
            "SELECT subject_id, subject_name, credits FROM subjects "
            "WHERE semester_id=? ORDER BY subject_name",
            (self.semester_id,)
        )
        return [Subject(r["subject_id"], r["subject_name"], r["credits"]) for r in rows]

class Marks:
    def __init__(self, internal, external):
        self.internal = to_number(internal, "Internal marks")
        self.external = to_number(external, "External marks")
        if not 0 <= self.internal <= MAX_INTERNAL:
            raise ValidationError(f"Internal marks must be between 0 and {MAX_INTERNAL}.")
        if not 0 <= self.external <= MAX_EXTERNAL:
            raise ValidationError(f"External marks must be between 0 and {MAX_EXTERNAL}.")

    def calculate_total(self):
        return self.internal + self.external

class Result:
    @staticmethod
    def evaluate(total):
        for minimum, grade, point in GRADE_TABLE:
            if total >= minimum:
                return grade, point, "PASS" if total >= PASS_MARK else "FAIL"
        return "F", 0, "FAIL"

    @staticmethod
    def calculate_sgpa(pairs):
        total_credits = reduce(lambda acc, pair: acc + pair[1], pairs, 0)
        if not total_credits:
            return 0.0
        weighted = reduce(lambda acc, pair: acc + pair[0] * pair[1], pairs, 0)
        return round(weighted / total_credits, 2)

    calculate_cgpa = calculate_sgpa

class User:
    ROLE = ""
    TABLE = ""
    ID_COL = ""

    def __init__(self, user_id, name, username, profile_id):
        self._user_id = user_id
        self.__name = name
        self.__username = username
        self._profile_id = profile_id

    @property
    def name(self):
        return self.__name

    @property
    def username(self):
        return self.__username

    @staticmethod
    def login(db, username, password):
        rows = db.fetch("SELECT * FROM users WHERE username=?", (username,))
        if not rows or rows[0]["password"] != hash_password(password):
            raise AuthError("Invalid username or password.")
        row = rows[0]
        cls = ROLE_CLASSES[row["role"]]
        profile = db.fetch(
            f"SELECT {cls.ID_COL} FROM {cls.TABLE} WHERE user_id=?",
            (row["user_id"],)
        )
        if not profile:
            raise AuthError("User profile is missing. Contact the administrator.")
        return cls(row["user_id"], row["name"], row["username"], profile[0][cls.ID_COL])

    def build_tabs(self, notebook, db):
        raise NotImplementedError

class Admin(User):
    ROLE, TABLE, ID_COL = "admin", "admins", "admin_id"

    def build_tabs(self, notebook, db):
        from people_frames import StudentsFrame, FacultyFrame
        from academic_frames import SemestersFrame, SubjectsFrame, MarksFrame, ResultsFrame, AnalysisFrame
        return [
            ("Students", StudentsFrame(notebook, db)),
            ("Faculty", FacultyFrame(notebook, db)),
            ("Semesters", SemestersFrame(notebook, db)),
            ("Subjects", SubjectsFrame(notebook, db)),
            ("Marks", MarksFrame(notebook, db)),
            ("Results", ResultsFrame(notebook, db)),
            ("Analysis", AnalysisFrame(notebook, db)),
        ]

class Faculty(User):
    ROLE, TABLE, ID_COL = "faculty", "faculty", "faculty_id"

    def build_tabs(self, notebook, db):
        from academic_frames import MarksFrame, AnalysisFrame
        return [
            ("Marks Entry", MarksFrame(notebook, db, self._profile_id)),
            ("Analysis", AnalysisFrame(notebook, db)),
        ]

class Student(User):
    ROLE, TABLE, ID_COL = "student", "students", "student_id"

    def build_tabs(self, notebook, db):
        from academic_frames import StudentResultFrame
        return [("My Results", StudentResultFrame(notebook, db, self._profile_id))]

ROLE_CLASSES = {"admin": Admin, "faculty": Faculty, "student": Student}
