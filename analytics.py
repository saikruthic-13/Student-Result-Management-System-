from collections import Counter
from models import Result
from config import GRADE_TABLE

class Analytics:
    BASE = """
    SELECT m.marks_id, s.student_id, u.name, sub.subject_id, sub.subject_name,
           sub.credits, sem.semester_no, m.internal_marks, m.external_marks,
           m.total_marks, r.grade, r.grade_point, r.status, r.verified
    FROM marks m
    JOIN results r ON r.marks_id=m.marks_id
    JOIN students s ON s.student_id=m.student_id
    JOIN users u ON u.user_id=s.user_id
    JOIN subjects sub ON sub.subject_id=m.subject_id
    JOIN semesters sem ON sem.semester_id=sub.semester_id
    """

    @staticmethod
    def records(db, student_id=None, verified_only=False):
        conditions, params = [], []
        if student_id is not None:
            conditions.append("s.student_id=?")
            params.append(student_id)
        if verified_only:
            conditions.append("r.verified=1")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return db.fetch(
            Analytics.BASE + where +
            " ORDER BY u.name, sem.semester_no, sub.subject_name",
            tuple(params)
        )

    @staticmethod
    def student_report(records):
        if not records:
            return "No results available yet."
        lines = ["Subject                     Sem   Total  Grade   GP  Status"]
        for r in records:
            lines.append(
                f"{r['subject_name']:<27} {r['semester_no']:>3} "
                f"{r['total_marks']:>7.1f} {r['grade']:>6} "
                f"{r['grade_point']:>4.0f}  {r['status']}"
            )
        semesters = sorted({r["semester_no"] for r in records})
        for sem in semesters:
            pairs = [(r["grade_point"], r["credits"]) for r in records if r["semester_no"] == sem]
            lines.append(f"Semester {sem} SGPA: {Result.calculate_sgpa(pairs)}")
        lines.append("Overall CGPA: " + str(Result.calculate_cgpa(
            [(r["grade_point"], r["credits"]) for r in records]
        )))
        ranked = sorted(records, key=lambda r: r["total_marks"], reverse=True)
        lines.append("Strong subjects: " + ", ".join(r["subject_name"] for r in ranked[:2]))
        weak = [r["subject_name"] for r in records if r["total_marks"] < 50]
        lines.append("Weak subjects: " + (", ".join(weak) if weak else "None"))
        return "\n".join(lines)

    @staticmethod
    def class_report(records):
        if not records:
            return "No data available."
        groups = {}
        for r in records:
            groups.setdefault(r["student_id"], []).append(r)
        rows = []
        for group in groups.values():
            cgpa = Result.calculate_cgpa([(x["grade_point"], x["credits"]) for x in group])
            failed = any(x["status"] == "FAIL" for x in group)
            rows.append((group[0]["name"], cgpa, failed))
        average = sum(r["total_marks"] for r in records) / len(records)
        lines = [
            "CLASS-WISE ANALYSIS", "=" * 40,
            f"Students analysed: {len(rows)}",
            f"Class average: {average:.2f} marks",
            f"Students with no fail: {sum(not row[2] for row in rows)}",
            "", "Top performers:"
        ]
        for i, (name, cgpa, _) in enumerate(sorted(rows, key=lambda x: x[1], reverse=True)[:3], 1):
            lines.append(f"{i}. {name} (CGPA {cgpa})")
        lines.append("\nNeed improvement:")
        needing = [row for row in rows if row[1] < 5 or row[2]]
        lines.extend([f"- {name} (CGPA {cgpa})" for name, cgpa, _ in needing] or ["None"])
        return "\n".join(lines)

    @staticmethod
    def subject_report(records):
        if not records:
            return "No data available."
        groups = {}
        for r in records:
            groups.setdefault(r["subject_name"], []).append(r)
        lines = ["SUBJECT-WISE ANALYSIS", "=" * 40]
        weak = []
        for name, group in sorted(groups.items()):
            passed = sum(r["status"] == "PASS" for r in group)
            average = sum(r["total_marks"] for r in group) / len(group)
            percentage = 100 * passed / len(group)
            if percentage < 60:
                weak.append(name)
            grades = Counter(r["grade"] for r in group)
            lines.append(
                f"{name}: average {average:.1f}, pass {passed}, fail {len(group)-passed}, "
                f"pass rate {percentage:.0f}%"
            )
            lines.append("  Grades: " + ", ".join(f"{g}={n}" for g, n in sorted(grades.items())))
        lines.append("Weak subjects (pass rate below 60%): " + (", ".join(weak) if weak else "None"))
        return "\n".join(lines)

    @staticmethod
    def semester_report(records):
        if not records:
            return "No data available."
        lines = ["SEMESTER-WISE ANALYSIS", "=" * 40]
        previous = None
        for sem in sorted({r["semester_no"] for r in records}):
            group = [r for r in records if r["semester_no"] == sem]
            student_ids = {r["student_id"] for r in group}
            sgpas = []
            for sid in student_ids:
                pairs = [(r["grade_point"], r["credits"]) for r in group if r["student_id"] == sid]
                sgpas.append(Result.calculate_sgpa(pairs))
            average = sum(sgpas) / len(sgpas) if sgpas else 0
            pass_rate = 100 * sum(r["status"] == "PASS" for r in group) / len(group)
            trend = "" if previous is None else (" (up)" if average > previous else " (down)" if average < previous else " (same)")
            lines.append(f"Semester {sem}: average SGPA {average:.2f}; subject pass rate {pass_rate:.0f}%{trend}")
            previous = average
        return "\n".join(lines)

    @staticmethod
    def grade_report(records):
        if not records:
            return "No data available."
        distribution = Counter(r["grade"] for r in records)
        lines = ["GRADE DISTRIBUTION", "=" * 40]
        for _, grade, _ in GRADE_TABLE:
            if distribution[grade]:
                lines.append(f"{grade:<3} {'#' * distribution[grade]} {distribution[grade]}")
        passed = sum(r["status"] == "PASS" for r in records)
        lines.append(f"Pass: {passed}; Fail: {len(records)-passed}; Pass rate: {100*passed/len(records):.1f}%")
        return "\n".join(lines)
