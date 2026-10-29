import tkinter as tk
from tkinter import ttk, messagebox
from database import AppError, ValidationError

def guarded(function):
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except AppError as exc:
            messagebox.showerror("Error", str(exc))
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
    wrapper.__name__ = function.__name__
    return wrapper

class FormFrame(ttk.LabelFrame):
    def __init__(self, parent, title, fields):
        super().__init__(parent, text=title, padding=8)
        self.variables, self.widgets = {}, {}
        for index, (label, key, *options_rest) in enumerate(fields):
            options = options_rest[0] if options_rest else None
            show = options_rest[1] if len(options_rest) > 1 else ""
            row, col = index // 2, (index % 2) * 2
            ttk.Label(self, text=label).grid(row=row, column=col, padx=5, pady=3, sticky="e")
            variable = tk.StringVar()
            if options is not None:
                widget = ttk.Combobox(self, textvariable=variable, values=options, state="readonly", width=27)
            else:
                widget = ttk.Entry(self, textvariable=variable, width=29, show=show)
            widget.grid(row=row, column=col+1, padx=5, pady=3, sticky="w")
            self.variables[key], self.widgets[key] = variable, widget

    def get(self, key):
        return self.variables[key].get().strip()

    def set(self, key, value):
        self.variables[key].set(value)

    def set_options(self, key, values):
        self.widgets[key]["values"] = values

    def clear(self):
        for variable in self.variables.values():
            variable.set("")

def button_row(parent, buttons):
    row = ttk.Frame(parent)
    for label, command in buttons:
        ttk.Button(row, text=label, command=command).pack(side="left", padx=4)
    return row

def make_tree(parent, columns, widths=None, height=10):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for i, column in enumerate(columns):
        tree.heading(column, text=column)
        tree.column(column, width=widths[i] if widths else 100, anchor="center")
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return frame, tree

def fill_tree(tree, rows):
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", "end", values=list(row))

def make_text(parent, height=14):
    frame = ttk.Frame(parent)
    widget = tk.Text(frame, height=height, font=("Courier New", 10), state="disabled", wrap="none")
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=widget.yview)
    widget.configure(yscrollcommand=scrollbar.set)
    widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return frame, widget

def set_text(widget, content):
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.config(state="disabled")

def selected_values(tree):
    selection = tree.selection()
    if not selection:
        raise ValidationError("Please select a row first.")
    return tree.item(selection[0])["values"]
