import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import ValidationError
from models import require, to_number, Marks, Result, Semester
from analytics import Analytics
from ui_helpers import FormFrame, button_row, make_tree, fill_tree, make_text, set_text, selected_values, guarded

class SemestersFrame(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=8)
        self.db = db
        self.form = FormFrame(self, "Add Semester", [("Semester No", "number"), ("Academic Year", "year")])
        self.form.pack(fill="x")
        button_row(self, [("Add", self.add), ("Delete Selected", self.remove)]).pack(fill="x", pady=6)
        frame, self.tree = make_tree(self, ["ID", "Semester No", "Academic Year"])
        frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        rows = self.db.fetch("SELECT semester_id, semester_no, academic_year FROM semesters ORDER BY semester_no")
        fill_tree(self.tree, [tuple(row.values()) for row in rows])

    @guarded
    def add(self):
        number = to_number(self.form.get("number"), "Semester number", int)
        if not 1 <= number <= 12:
            raise ValidationError("Semester number must be between 1 and 12.")
        require(self.form.get("year"), "Academic year")
        self.db.insert("semesters", {"semester_no": number, "academic_year": self.form.get("year")})
        self.form.clear()
        self.refresh()

    @guarded
    def remove(self):
        self.db.delete("semesters", "semester_id", selected_values(self.tree)[0])
        self.refresh()

class SubjectsFrame(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=8)
        self.db = db
        self.form = FormFrame(self, "Add Subject", [
            ("Subject Name", "name"), ("Credits", "credits"), ("Semester", "semester", [])
        ])
        self.form.pack(fill="x")
        button_row(self, [("Add", self.add), ("Delete Selected", self.remove)]).pack(fill="x", pady=6)
        frame, self.tree = make_tree(self, ["ID", "Subject", "Credits", "Semester"])
        frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        semesters = self.db.fetch("SELECT semester_no FROM semesters ORDER BY semester_no")
        self.form.set_options("semester", [str(row["semester_no"]) for row in semesters])
        rows = self.db.fetch(
            "SELECT sub.subject_id, sub.subject_name, sub.credits, sem.semester_no "
            "FROM subjects sub JOIN semesters sem ON sem.semester_id=sub.semester_id "
            "ORDER BY sem.semester_no, sub.subject_name"
        )
        fill_tree(self.tree, [tuple(row.values()) for row in rows])

    @guarded
    def add(self):
        require(self.form.get("name"), "Subject name")
        credits = to_number(self.form.get("credits"), "Credits", int)
        if not 1 <= credits <= 10:
            raise ValidationError("Credits must be between 1 and 10.")
        require(self.form.get("semester"), "Semester")
        semester = self.db.fetch("SELECT semester_id FROM semesters WHERE semester_no=?", (int(self.form.get("semester")),))
        if not semester:
            raise ValidationError("Select a valid semester.")
        self.db.insert("subjects", {
            "subject_name": self.form.get("name"),
            "credits": credits,
            "semester_id": semester[0]["semester_id"]
        })
        self.form.clear()
        self.refresh()

    @guarded
    def remove(self):
        if messagebox.askyesno("Confirm", "Deleting a subject also deletes its marks. Continue?"):
            self.db.delete("subjects", "subject_id", selected_values(self.tree)[0])
            self.refresh()

class MarksFrame(ttk.Frame):
    def __init__(self, parent, db, faculty_id=None):
        super().__init__(parent, padding=8)
        self.db, self.faculty_id = db, faculty_id
        self.records = []
        self.student_semesters = {}
        self.form = FormFrame(self, "Marks Entry / Update (Internal max 40, External max 60)", [
            ("Student", "student", []), ("Subject", "subject", []),
            ("Internal Marks", "internal"), ("External Marks", "external")
        ])
        self.form.pack(fill="x")
        self.form.widgets["student"].bind("<<ComboboxSelected>>", lambda _event: self.load_subjects())
        button_row(self, [("Save / Update", self.save), ("Delete Selected", self.remove), ("Clear", self.form.clear)]).pack(fill="x", pady=6)
        self.search = tk.StringVar()
        frame_bar = ttk.Frame(self)
        frame_bar.pack(fill="x")
        ttk.Label(frame_bar, text="Search:").pack(side="left")
        entry = ttk.Entry(frame_bar, textvariable=self.search, width=25)
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda _event: self.show())
        columns = ["ID", "Student", "Subject", "Sem", "Internal", "External", "Total", "Grade", "Status", "Verified"]
        frame, self.tree = make_tree(self, columns, [45, 130, 140, 45, 65, 65, 60, 55, 65, 65])
        frame.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self.pick_row())
        self.refresh()

    def refresh(self):
        students = self.db.fetch(
            "SELECT s.student_id, s.semester_id, u.name, sem.semester_no FROM students s "
            "JOIN users u ON u.user_id=s.user_id JOIN semesters sem ON sem.semester_id=s.semester_id "
            "ORDER BY u.name"
        )
        self.student_semesters = {row["student_id"]: row["semester_id"] for row in students}
        self.form.set_options("student", [
            f"{row['student_id']} - {row['name']} (Sem {row['semester_no']})" for row in students
        ])
        self.records = Analytics.records(self.db)
        self.show()

    def show(self):
        query = self.search.get().strip().lower()
        rows = [r for r in self.records if query in r["name"].lower() or query in r["subject_name"].lower()]
        fill_tree(self.tree, [
            (r["marks_id"], r["name"], r["subject_name"], r["semester_no"], r["internal_marks"],
             r["external_marks"], r["total_marks"], r["grade"], r["status"], "Yes" if r["verified"] else "No")
            for r in rows
        ])

    def selected_id(self, key):
        value = self.form.get(key)
        require(value, key.title())
        return int(value.split(" - ")[0])

    def load_subjects(self):
        student_id = self.selected_id("student")
        semester_id = self.student_semesters.get(student_id)
        if semester_id is None:
            return
        subjects = Semester(semester_id).get_subjects(self.db)
        self.form.set_options("subject", [subject.label for subject in subjects])
        self.form.set("subject", "")

    @guarded
    def pick_row(self):
        selected = self.tree.selection()
        if not selected:
            return
        marks_id = self.tree.item(selected[0])["values"][0]
        record = next((r for r in self.records if r["marks_id"] == marks_id), None)
        if not record:
            return
        for option in self.form.widgets["student"]["values"]:
            if option.startswith(f"{record['student_id']} - "):
                self.form.set("student", option)
                break
        self.load_subjects()
        self.form.set("subject", f"{record['subject_id']} - {record['subject_name']}")
        self.form.set("internal", str(record["internal_marks"]))
        self.form.set("external", str(record["external_marks"]))

    @guarded
    def save(self):
        student_id = self.selected_id("student")
        subject_id = self.selected_id("subject")
        marks = Marks(self.form.get("internal"), self.form.get("external"))
        total = marks.calculate_total()
        grade, point, status = Result.evaluate(total)
        mark_data = {
            "internal_marks": marks.internal,
            "external_marks": marks.external,
            "total_marks": total,
            "faculty_id": self.faculty_id
        }
        existing = self.db.fetch("SELECT marks_id FROM marks WHERE student_id=? AND subject_id=?", (student_id, subject_id))
        result_data = {"grade": grade, "grade_point": point, "status": status, "verified": 0}
        if existing:
            marks_id = existing[0]["marks_id"]
            self.db.update("marks", mark_data, "marks_id", marks_id)
            self.db.update("results", result_data, "marks_id", marks_id)
        else:
            marks_id = self.db.insert("marks", {"student_id": student_id, "subject_id": subject_id, **mark_data})
            self.db.insert("results", {"marks_id": marks_id, **result_data})
        messagebox.showinfo("Saved", f"Total: {total:.1f} | Grade: {grade} | {status}")
        self.refresh()

    @guarded
    def remove(self):
        self.db.delete("marks", "marks_id", selected_values(self.tree)[0])
        self.refresh()

class ResultsFrame(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=8)
        self.db = db
        button_row(self, [
            ("Verify All Pending", self.verify), ("Export CSV", self.export),
            ("Backup Database", self.backup), ("Refresh", self.refresh)
        ]).pack(fill="x", pady=6)
        columns = ["Marks ID", "Student", "Subject", "Sem", "Total", "Grade", "GP", "Status", "Verified"]
        frame, self.tree = make_tree(self, columns, [70, 140, 150, 45, 65, 55, 45, 60, 65], height=18)
        frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        records = Analytics.records(self.db)
        fill_tree(self.tree, [
            (r["marks_id"], r["name"], r["subject_name"], r["semester_no"], r["total_marks"],
             r["grade"], r["grade_point"], r["status"], "Yes" if r["verified"] else "No")
            for r in records
        ])

    @guarded
    def verify(self):
        self.db.execute("UPDATE results SET verified=1 WHERE verified=0")
        messagebox.showinfo("Verified", "All pending results are verified.")
        self.refresh()

    @guarded
    def export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Marks ID", "Student", "Subject", "Semester", "Total", "Grade", "GP", "Status", "Verified"])
                writer.writerows(self.tree.item(item)["values"] for item in self.tree.get_children())
            messagebox.showinfo("Exported", "CSV report saved.")

    @guarded
    def backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite database", "*.db")])
        if path:
            self.db.backup(path)
            messagebox.showinfo("Backup", "Database backup created.")

class AnalysisFrame(ttk.Frame):
    TYPES = ["Student-wise", "Subject-wise", "Semester-wise", "Class-wise", "Grade distribution"]

    def __init__(self, parent, db):
        super().__init__(parent, padding=8)
        self.db = db
        self.form = FormFrame(self, "Performance Analysis", [
            ("Analysis Type", "type", self.TYPES), ("Student", "student", [])
        ])
        self.form.set("type", "Class-wise")
        self.form.pack(fill="x")
        button_row(self, [("Generate", self.generate), ("Save Report", self.save)]).pack(fill="x", pady=6)
        self.views = ttk.Notebook(self)
        self.views.pack(fill="both", expand=True)
        report_tab = ttk.Frame(self.views)
        self.graph_tab = ttk.Frame(self.views)
        self.views.add(report_tab, text="Text Report")
        self.views.add(self.graph_tab, text="Graphical Representation")
        frame, self.output = make_text(report_tab, 22)
        frame.pack(fill="both", expand=True)
        ttk.Button(self.graph_tab, text="Refresh Graphs", command=self.refresh_graphs).pack(anchor="e", padx=8, pady=4)
        self.chart_area = ttk.Frame(self.graph_tab)
        self.chart_area.pack(fill="both", expand=True)
        self.views.bind("<<NotebookTabChanged>>", self.on_view_changed)
        self.refresh()

    def refresh(self):
        students = self.db.fetch(
            "SELECT s.student_id, u.name FROM students s JOIN users u ON u.user_id=s.user_id ORDER BY u.name"
        )
        self.form.set_options("student", [f"{r['student_id']} - {r['name']}" for r in students])

    def on_view_changed(self, _event=None):
        if self.views.select() == str(self.graph_tab):
            self.refresh_graphs()

    def refresh_graphs(self):
        try:
            from embedded_charts import build_graphs
            build_graphs(self.chart_area, Analytics.records(self.db))
        except ImportError as error:
            messagebox.showerror("Missing dependency", f"Install matplotlib using: python -m pip install matplotlib\n\n{error}")
        except Exception as error:
            messagebox.showerror("Graph error", str(error))

    @guarded
    def generate(self):
        kind = self.form.get("type")
        records = Analytics.records(self.db)
        if kind == "Student-wise":
            require(self.form.get("student"), "Student")
            student_id = int(self.form.get("student").split(" - ")[0])
            output = Analytics.student_report(Analytics.records(self.db, student_id=student_id))
        else:
            reports = {
                "Subject-wise": Analytics.subject_report,
                "Semester-wise": Analytics.semester_report,
                "Class-wise": Analytics.class_report,
                "Grade distribution": Analytics.grade_report
            }
            output = reports[kind](records)
        set_text(self.output, output)

    @guarded
    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.output.get("1.0", "end"))
            messagebox.showinfo("Saved", "Analysis report saved.")

class StudentResultFrame(ttk.Frame):
    def __init__(self, parent, db, student_id):
        super().__init__(parent, padding=8)
        self.db, self.student_id = db, student_id
        ttk.Label(self, text="Only verified results are shown.").pack(anchor="w")
        columns = ["Sem", "Subject", "Credits", "Internal", "External", "Total", "Grade", "GP", "Status"]
        frame, self.tree = make_tree(self, columns, [45, 160, 55, 65, 65, 60, 55, 45, 60], height=9)
        frame.pack(fill="x", pady=6)
        text_frame, self.output = make_text(self, 14)
        text_frame.pack(fill="both", expand=True)
        button_row(self, [("Refresh", self.refresh)]).pack(pady=4)
        self.refresh()

    def refresh(self):
        records = Analytics.records(self.db, self.student_id, verified_only=True)
        fill_tree(self.tree, [
            (r["semester_no"], r["subject_name"], r["credits"], r["internal_marks"],
             r["external_marks"], r["total_marks"], r["grade"], r["grade_point"], r["status"])
            for r in records
        ])
        set_text(self.output, "MY PERFORMANCE\n" + "=" * 40 + "\n" + Analytics.student_report(records))
