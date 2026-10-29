import tkinter as tk
from tkinter import ttk, messagebox
from database import ValidationError
from models import require, validate_contact, hash_password
from ui_helpers import FormFrame, button_row, make_tree, fill_tree, selected_values, guarded

class PeopleFrame(ttk.Frame):
    ROLE, TABLE, ID_COL, HAS_SEMESTER = "", "", "", False

    def __init__(self, parent, db):
        super().__init__(parent, padding=8)
        self.db = db
        fields = [
            ("Full Name", "name"), ("Username", "username"),
            ("Password", "password", None, "*"), ("Department", "department")
        ]
        if self.HAS_SEMESTER:
            fields.append(("Semester", "semester", []))
        fields.extend([("Email", "email"), ("Phone", "phone")])
        self.form = FormFrame(self, f"Add {self.ROLE.title()}", fields)
        self.form.pack(fill="x")
        bar = button_row(self, [("Add", self.add), ("Delete Selected", self.remove), ("Refresh", self.refresh)])
        bar.pack(fill="x", pady=6)
        self.search = tk.StringVar()
        ttk.Label(bar, text=" Search:").pack(side="left")
        entry = ttk.Entry(bar, textvariable=self.search, width=22)
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda _event: self.refresh())
        columns = ["ID", "Name", "Username", "Department"]
        if self.HAS_SEMESTER:
            columns.append("Semester")
        columns.extend(["Email", "Phone"])
        frame, self.tree = make_tree(self, columns)
        frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        if self.HAS_SEMESTER:
            semesters = self.db.fetch("SELECT semester_no FROM semesters ORDER BY semester_no")
            self.form.set_options("semester", [str(row["semester_no"]) for row in semesters])
        search = f"%{self.search.get().strip()}%"
        semester_select = "sem.semester_no AS semester_no," if self.HAS_SEMESTER else ""
        semester_join = "JOIN semesters sem ON sem.semester_id=t.semester_id" if self.HAS_SEMESTER else ""
        rows = self.db.fetch(
            f"SELECT t.{self.ID_COL} AS id, u.name, u.username, t.department, "
            f"{semester_select} t.email, t.phone FROM {self.TABLE} t "
            f"JOIN users u ON u.user_id=t.user_id {semester_join} "
            f"WHERE u.name LIKE ? OR u.username LIKE ? OR t.department LIKE ? "
            f"ORDER BY t.{self.ID_COL}",
            (search, search, search)
        )
        fill_tree(self.tree, [tuple(row.values()) for row in rows])

    @guarded
    def add(self):
        form = self.form
        for key, label in [("name", "Name"), ("username", "Username"), ("password", "Password"), ("department", "Department")]:
            require(form.get(key), label)
        if len(form.get("password")) < 4:
            raise ValidationError("Password must contain at least 4 characters.")
        validate_contact(form.get("email"), form.get("phone"))
        profile = {
            "department": form.get("department"),
            "email": form.get("email"),
            "phone": form.get("phone")
        }
        if self.HAS_SEMESTER:
            require(form.get("semester"), "Semester")
            found = self.db.fetch("SELECT semester_id FROM semesters WHERE semester_no=?", (int(form.get("semester")),))
            if not found:
                raise ValidationError("Select a valid semester.")
            profile["semester_id"] = found[0]["semester_id"]
        user_id = self.db.insert("users", {
            "name": form.get("name"),
            "username": form.get("username"),
            "password": hash_password(form.get("password")),
            "role": self.ROLE
        })
        try:
            self.db.insert(self.TABLE, {"user_id": user_id, **profile})
        except Exception:
            self.db.delete("users", "user_id", user_id)
            raise
        form.clear()
        self.refresh()
        messagebox.showinfo("Saved", f"{self.ROLE.title()} added successfully.")

    @guarded
    def remove(self):
        person_id = selected_values(self.tree)[0]
        if not messagebox.askyesno("Confirm", f"Delete this {self.ROLE} and related records?"):
            return
        self.db.execute(
            f"DELETE FROM users WHERE user_id=(SELECT user_id FROM {self.TABLE} WHERE {self.ID_COL}=?)",
            (person_id,)
        )
        self.refresh()

class StudentsFrame(PeopleFrame):
    ROLE, TABLE, ID_COL, HAS_SEMESTER = "student", "students", "student_id", True

class FacultyFrame(PeopleFrame):
    ROLE, TABLE, ID_COL, HAS_SEMESTER = "faculty", "faculty", "faculty_id", False
