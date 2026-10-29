import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager
from models import User, require
from ui_helpers import guarded

class StudentResultApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.root = tk.Tk()
        self.root.title("Smart Student Result & Academic Performance Management System")
        self.root.geometry("1120x720")
        self.user = None
        self.show_login()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear()
        box = ttk.LabelFrame(self.root, text="Login", padding=25)
        box.place(relx=0.5, rely=0.4, anchor="center")
        ttk.Label(
            box, text="Smart Student Result Management System",
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=12)
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        ttk.Label(box, text="Username").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        username_entry = ttk.Entry(box, textvariable=self.username_var, width=28)
        username_entry.grid(row=1, column=1)
        ttk.Label(box, text="Password").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(box, textvariable=self.password_var, show="*", width=28).grid(row=2, column=1)
        ttk.Button(box, text="Login", command=self.do_login).grid(row=3, column=0, columnspan=2, pady=12)
        self.root.bind("<Return>", lambda _event: self.do_login())
        username_entry.focus()

    @guarded
    def do_login(self):
        if self.user is not None:
            return
        require(self.username_var.get(), "Username")
        require(self.password_var.get(), "Password")
        self.user = User.login(self.db, self.username_var.get().strip(), self.password_var.get())
        self.show_main()

    def show_main(self):
        self.clear()
        header = ttk.Frame(self.root, padding=6)
        header.pack(fill="x")
        ttk.Label(
            header, text=f"Welcome, {self.user.name} ({self.user.ROLE.title()})",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")
        ttk.Button(header, text="Logout", command=self.logout).pack(side="right")
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)
        for title, frame in self.user.build_tabs(notebook, self.db):
            notebook.add(frame, text=title)
        notebook.bind("<<NotebookTabChanged>>", lambda _event: self.refresh_tab(notebook))

    def refresh_tab(self, notebook):
        selected = notebook.select()
        if not selected:
            return
        frame = self.root.nametowidget(selected)
        if hasattr(frame, "refresh"):
            frame.refresh()

    def logout(self):
        self.user = None
        self.show_login()

    def close(self):
        try:
            self.db.close()
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()
