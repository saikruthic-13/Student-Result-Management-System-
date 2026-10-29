import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "result_management.db")

MAX_INTERNAL = 40
MAX_EXTERNAL = 60
PASS_MARK = 40

GRADE_TABLE = [
    (90, "O", 10),
    (80, "A+", 9),
    (70, "A", 8),
    (60, "B+", 7),
    (50, "B", 6),
    (40, "C", 5),
    (0, "F", 0),
]
