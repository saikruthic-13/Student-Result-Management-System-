"""Embedded graphical analysis using the application's current database records."""
from collections import Counter, defaultdict
from tkinter import ttk


def build_graphs(parent, records):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    for child in parent.winfo_children():
        child.destroy()
    if not records:
        ttk.Label(parent, text="No result records yet. Enter marks and generate results to see graphs.").pack(pady=30)
        return

    notebook = ttk.Notebook(parent)
    notebook.pack(fill="both", expand=True)
    by_subject, by_student, by_semester = defaultdict(list), defaultdict(list), defaultdict(list)
    grades = Counter()
    statuses = Counter()
    totals = []
    for r in records:
        mark = float(r['total_marks'])
        by_subject[r['subject_name']].append(mark)
        by_student[f"{r['name']} (ID {r['student_id']})"].append(mark)
        by_semester[r['semester_no']].append(mark)
        grades[str(r['grade'])] += 1
        statuses[str(r['status']).upper()] += 1
        totals.append(mark)

    def chart_tab(title, draw):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=title)
        fig = Figure(figsize=(9, 5), dpi=100, constrained_layout=True)
        ax = fig.add_subplot(111)
        draw(ax)
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return canvas

    def averages(d):
        return [(k, sum(v)/len(v)) for k, v in d.items()]

    def subject_chart(ax):
        data = sorted(averages(by_subject), key=lambda x: x[1], reverse=True)
        ax.barh([x[0] for x in data][::-1], [x[1] for x in data][::-1], color='#3285bd')
        ax.set_xlim(0, 105)
        ax.set_xlabel('Average marks / 100')
        ax.set_title('Subject-wise Average Marks')
        ax.grid(axis='x', alpha=.2)

    def student_chart(ax):
        data = sorted(averages(by_student), key=lambda x: x[1], reverse=True)[:10]
        ax.barh([x[0] for x in data][::-1], [x[1] for x in data][::-1], color='#40a58b')
        ax.set_xlim(0, 105)
        ax.set_xlabel('Average marks / 100')
        ax.set_title('Top 10 Students by Average Marks')
        ax.grid(axis='x', alpha=.2)

    def semester_chart(ax):
        data = sorted(averages(by_semester))
        ax.plot([x[0] for x in data], [x[1] for x in data], marker='o', linewidth=2, color='#7356ae')
        ax.set_ylim(0, 105)
        ax.set_xticks([x[0] for x in data])
        ax.set_xlabel('Semester')
        ax.set_ylabel('Average marks / 100')
        ax.set_title('Semester-wise Performance')
        ax.grid(alpha=.25)

    def grade_chart(ax):
        order = ['O', 'A+', 'A', 'B+', 'B', 'C', 'F']
        labels = [g for g in order if grades[g]] + [g for g in grades if g not in order]
        ax.bar(labels, [grades[g] for g in labels], color='#efad4e')
        ax.set_title('Grade Distribution')
        ax.set_ylabel('Number of result records')
        ax.grid(axis='y', alpha=.2)

    def pass_fail_chart(ax):
        labels = [s for s in ('PASS', 'FAIL') if statuses[s]]
        labels += [s for s in statuses if s not in labels]
        ax.pie([statuses[s] for s in labels], labels=labels, autopct='%1.1f%%',
               startangle=90, colors=['#42a87a', '#d86161', '#e2ac52'][:len(labels)])
        ax.set_title('Pass / Fail Distribution (Result Records)')

    canvases = [chart_tab(title, fn) for title, fn in [
        ('Subjects', subject_chart), ('Students', student_chart),
        ('Semesters', semester_chart), ('Grades', grade_chart),
        ('Pass / Fail', pass_fail_chart)
    ]]
    parent._chart_canvases = canvases
