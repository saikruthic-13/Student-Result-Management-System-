"""
Graphical Analysis for Smart Student Result & Academic Performance Management System

Requirements:
    pip install matplotlib

Usage:
    1. Save this file in the same folder as result_management.db
    2. Run: python analysis_graphs.py

The program reads the existing SQLite database and displays graphical reports.
It does not change your database.
"""

import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def find_database():
    """Find the project's database beside this Python file."""
    folder = os.path.dirname(os.path.abspath(__file__))
    possible_names = [
        "result_management.db",
        "result_management(4).db",
    ]
    for name in possible_names:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path

    # If the database has another name or is in another folder, ask the user.
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select the Student Result SQLite database",
        filetypes=[("SQLite database", "*.db"), ("All files", "*.*")]
    )
    root.destroy()
    return path


def load_data(db_path):
    """Read result data by joining the project's existing tables."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        query = """
            SELECT
                s.student_id,
                u.name AS student_name,
                sub.subject_name,
                sub.credits,
                sem.semester_no,
                m.internal_marks,
                m.external_marks,
                m.total_marks,
                r.grade,
                r.grade_point,
                r.status,
                r.verified
            FROM marks m
            JOIN results r ON r.marks_id = m.marks_id
            JOIN students s ON s.student_id = m.student_id
            JOIN users u ON u.user_id = s.user_id
            JOIN subjects sub ON sub.subject_id = m.subject_id
            JOIN semesters sem ON sem.semester_id = sub.semester_id
            ORDER BY u.name, sem.semester_no, sub.subject_name
        """
        return [dict(row) for row in connection.execute(query).fetchall()]
    finally:
        connection.close()


def show_graphs(db_path, records):
    """Display four graphical views of academic performance."""
    if not records:
        messagebox.showinfo(
            "No data",
            "There are no marks/results in this database yet. Add marks first."
        )
        return

    names = sorted({r["student_name"] for r in records})
    subjects = sorted({r["subject_name"] for r in records})

    # Average marks for each subject, using the records available.
    subject_averages = []
    for subject in subjects:
        values = [r["total_marks"] for r in records if r["subject_name"] == subject]
        subject_averages.append(sum(values) / len(values))

    # Average marks for each student, using the student's available records.
    student_averages = []
    for name in names:
        values = [r["total_marks"] for r in records if r["student_name"] == name]
        student_averages.append(sum(values) / len(values))

    grade_counts = {}
    for record in records:
        grade = record["grade"]
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    pass_count = sum(r["status"].upper() == "PASS" for r in records)
    fail_count = sum(r["status"].upper() == "FAIL" for r in records)
    verified_count = sum(bool(r["verified"]) for r in records)
    pending_count = len(records) - verified_count
    class_average = sum(r["total_marks"] for r in records) / len(records)

    window = tk.Tk()
    window.title("Student Result - Graphical Analysis")
    window.geometry("1200x850")
    window.minsize(900, 650)

    heading = tk.Label(
        window,
        text="SMART STUDENT RESULT & ACADEMIC PERFORMANCE ANALYSIS",
        font=("Segoe UI", 14, "bold"),
        pady=8
    )
    heading.pack()

    summary = (
        f"Records: {len(records)}    |    Class average: {class_average:.2f}/100"
        f"    |    Pass: {pass_count}    |    Fail: {fail_count}"
        f"    |    Verified: {verified_count}    |    Pending: {pending_count}"
    )
    tk.Label(window, text=summary, font=("Segoe UI", 10), pady=4).pack()

    figure = Figure(figsize=(12, 7.5), dpi=100, constrained_layout=True)

    # Graph 1: average marks by subject.
    ax1 = figure.add_subplot(221)
    bars = ax1.bar(subjects, subject_averages)
    ax1.set_title("Average Marks by Subject")
    ax1.set_ylabel("Average marks out of 100")
    ax1.set_ylim(0, 100)
    ax1.tick_params(axis="x", rotation=20)
    ax1.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, subject_averages):
        ax1.text(bar.get_x() + bar.get_width() / 2, value + 1,
                 f"{value:.1f}", ha="center", va="bottom", fontsize=8)

    # Graph 2: average marks by student.
    ax2 = figure.add_subplot(222)
    bars = ax2.bar(names, student_averages)
    ax2.set_title("Average Marks by Student")
    ax2.set_ylabel("Average marks out of 100")
    ax2.set_ylim(0, 100)
    ax2.tick_params(axis="x", rotation=20)
    ax2.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, student_averages):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + 1,
                 f"{value:.1f}", ha="center", va="bottom", fontsize=8)

    # Graph 3: grade distribution.
    ax3 = figure.add_subplot(223)
    grade_order = ["O", "A+", "A", "B+", "B", "C", "F"]
    grades = [g for g in grade_order if grade_counts.get(g, 0) > 0]
    counts = [grade_counts[g] for g in grades]
    if grades:
        ax3.bar(grades, counts)
    ax3.set_title("Grade Distribution")
    ax3.set_xlabel("Grade")
    ax3.set_ylabel("Number of result records")
    ax3.grid(axis="y", alpha=0.25)
    for index, value in enumerate(counts):
        ax3.text(index, value + 0.03, str(value), ha="center", fontsize=9)

    # Graph 4: pass/fail and verification status.
    ax4 = figure.add_subplot(224)
    labels = ["Pass", "Fail", "Verified", "Pending"]
    values = [pass_count, fail_count, verified_count, pending_count]
    bars = ax4.bar(labels, values)
    ax4.set_title("Pass/Fail and Verification Summary")
    ax4.set_ylabel("Number of result records")
    ax4.grid(axis="y", alpha=0.25)
    ax4.tick_params(axis="x", rotation=15)
    for bar, value in zip(bars, values):
        ax4.text(bar.get_x() + bar.get_width() / 2, value + 0.03,
                 str(value), ha="center", fontsize=9)

    canvas = FigureCanvasTkAgg(figure, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    footer = tk.Label(
        window,
        text=f"Database: {db_path}    |    Charts are based on records currently stored in the database.",
        font=("Segoe UI", 8),
        pady=5
    )
    footer.pack()

    window.mainloop()


def main():
    db_path = find_database()
    if not db_path:
        return

    try:
        records = load_data(db_path)
        show_graphs(db_path, records)
    except sqlite3.Error as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database Error",
            f"Could not read this database:\n{error}\n\n"
            "Please select the SQLite database used by your Student Result Management System."
        )
        root.destroy()


if __name__ == "__main__":
    main()
