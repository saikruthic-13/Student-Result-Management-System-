""
Intrusion Detection Using Log Hashing  (GUI + SQLite version)
E1CSA311 - Micro Project
 
Features
--------
* Logs are stored in a SQLite database (logs.db)
* Every log is chained to the previous one with SHA-256 (blockchain-style)
* Verify integrity  -> detects modified logs / broken hash links
* Detect intrusions -> flags IPs with repeated failed logins
* Simulate tampering -> modifies a log directly in the DB to test detection
* Tkinter GUI (no extra libraries needed)
"""
 
import hashlib
import json
import sqlite3
import tkinter as tk
from collections import Counter
from datetime import datetime
from tkinter import ttk, messagebox
 
DB_FILE = "logs.db"
GENESIS_HASH = "0" * 64
 
 
# ----------------------------------------------------------------------
# Backend: database + hashing logic
# ----------------------------------------------------------------------
class LogDatabase:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()
 
    def _create_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT NOT NULL,
                event         TEXT NOT NULL,
                username      TEXT NOT NULL,
                ip            TEXT NOT NULL,
                details       TEXT,
                previous_hash TEXT NOT NULL,
                hash          TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
 
    @staticmethod
    def compute_hash(timestamp, event, username, ip, details, previous_hash):
        data = json.dumps(
            {
                "timestamp": timestamp,
                "event": event,
                "username": username,
                "ip": ip,
                "details": details,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(data.encode()).hexdigest()
 
    def last_hash(self):
        row = self.conn.execute(
            "SELECT hash FROM logs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["hash"] if row else GENESIS_HASH
 
    def add_log(self, event, username, ip, details):
        timestamp = datetime.now().isoformat()
        prev = self.last_hash()
        h = self.compute_hash(timestamp, event, username, ip, details, prev)
        self.conn.execute(
            "INSERT INTO logs (timestamp, event, username, ip, details,"
            " previous_hash, hash) VALUES (?,?,?,?,?,?,?)",
            (timestamp, event, username, ip, details, prev, h),
        )
        self.conn.commit()
 
    def get_logs(self):
        return self.conn.execute("SELECT * FROM logs ORDER BY id").fetchall()
 
    def verify(self):
        """Return (is_valid, {log_id: [problems]})."""
        problems = {}
        expected_prev = GENESIS_HASH
        for row in self.get_logs():
            issues = []
            if row["previous_hash"] != expected_prev:
                issues.append("Broken hash link")
            calc = self.compute_hash(
                row["timestamp"], row["event"], row["username"],
                row["ip"], row["details"], row["previous_hash"],
            )
            if calc != row["hash"]:
                issues.append("Log content modified")
            if issues:
                problems[row["id"]] = issues
            expected_prev = row["hash"]
        return (len(problems) == 0), problems
 
    def detect_intrusions(self, threshold=3):
        rows = self.conn.execute(
            "SELECT ip FROM logs WHERE event = 'failed_login'"
        ).fetchall()
        counts = Counter(r["ip"] for r in rows)
        return {ip: c for ip, c in counts.items() if c >= threshold}
 
    def tamper(self, log_id, new_details="Unauthorized modification"):
        """Edit a record WITHOUT updating its hash (simulates an attacker)."""
        self.conn.execute(
            "UPDATE logs SET details = ? WHERE id = ?", (new_details, log_id)
        )
        self.conn.commit()
 
    def clear(self):
        self.conn.execute("DELETE FROM logs")
        self.conn.execute("DELETE FROM sqlite_sequence WHERE name='logs'")
        self.conn.commit()
 
    def load_sample_data(self):
        samples = [
            ("login_success", "alice", "192.168.1.10", "Login successful"),
            ("file_access", "alice", "192.168.1.10", "Opened a file"),
            ("failed_login", "admin", "10.0.0.5", "Wrong password"),
            ("failed_login", "admin", "10.0.0.5", "Wrong password"),
            ("failed_login", "admin", "10.0.0.5", "Wrong password"),
        ]
        for s in samples:
            self.add_log(*s)
 
 
# ----------------------------------------------------------------------
# Frontend: Tkinter GUI
# ----------------------------------------------------------------------
class App(tk.Tk):
    EVENTS = ["login_success", "failed_login", "file_access",
              "file_delete", "logout", "privilege_change"]
 
    def __init__(self):
        super().__init__()
        self.title("Intrusion Detection Using Log Hashing")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.db = LogDatabase()
 
        self._build_form()
        self._build_buttons()
        self._build_table()
        self._build_console()
        self._build_status()
        self.refresh_table()
 
    # ---------- layout ----------
    def _build_form(self):
        frame = ttk.LabelFrame(self, text="Add New Log", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))
 
        ttk.Label(frame, text="Event").grid(row=0, column=0, sticky="w")
        self.event_var = tk.StringVar(value=self.EVENTS[0])
        ttk.Combobox(frame, textvariable=self.event_var, values=self.EVENTS,
                     width=18).grid(row=1, column=0, padx=(0, 8))
 
        ttk.Label(frame, text="Username").grid(row=0, column=1, sticky="w")
        self.user_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.user_var, width=16).grid(
            row=1, column=1, padx=(0, 8))
 
        ttk.Label(frame, text="IP Address").grid(row=0, column=2, sticky="w")
        self.ip_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ip_var, width=16).grid(
            row=1, column=2, padx=(0, 8))
 
        ttk.Label(frame, text="Details").grid(row=0, column=3, sticky="w")
        self.details_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.details_var, width=34).grid(
            row=1, column=3, padx=(0, 8))
 
        ttk.Button(frame, text="Add Log", command=self.on_add).grid(
            row=1, column=4, padx=4)
 
    def _build_buttons(self):
        frame = ttk.Frame(self, padding=(10, 5))
        frame.pack(fill="x")
 
        ttk.Button(frame, text="Verify Integrity",
                   command=self.on_verify).pack(side="left", padx=3)
        ttk.Button(frame, text="Detect Intrusions",
                   command=self.on_detect).pack(side="left", padx=3)
 
        ttk.Label(frame, text="Threshold:").pack(side="left", padx=(10, 2))
        self.threshold_var = tk.IntVar(value=3)
        ttk.Spinbox(frame, from_=1, to=20, width=4,
                    textvariable=self.threshold_var).pack(side="left")
 
        ttk.Button(frame, text="Simulate Tampering (selected)",
                   command=self.on_tamper).pack(side="left", padx=(20, 3))
        ttk.Button(frame, text="Load Sample Data",
                   command=self.on_sample).pack(side="left", padx=3)
        ttk.Button(frame, text="Clear All Logs",
                   command=self.on_clear).pack(side="left", padx=3)
 
    def _build_table(self):
        frame = ttk.LabelFrame(self, text="Log Records (double-click a row for details)",
                               padding=5)
        frame.pack(fill="both", expand=True, padx=10, pady=5)
 
        cols = ("id", "timestamp", "event", "username", "ip", "details", "hash")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        widths = {"id": 40, "timestamp": 175, "event": 110, "username": 90,
                  "ip": 110, "details": 200, "hash": 330}
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=widths[c], anchor="w")
 
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
 
        self.tree.tag_configure("ok", background="#e6f4ea")
        self.tree.tag_configure("bad", background="#fbd5d5", foreground="#a00000")
        self.tree.bind("<Double-1>", self.on_row_details)
 
    def _build_console(self):
        frame = ttk.LabelFrame(self, text="Analysis Output", padding=5)
        frame.pack(fill="both", expand=False, padx=10, pady=5)
        self.console = tk.Text(frame, height=9, state="disabled",
                               font=("Consolas", 10), wrap="word")
        self.console.pack(fill="both", expand=True)
        self.console.tag_configure("alert", foreground="#c00000")
        self.console.tag_configure("good", foreground="#1b7f3b")
        self.console.tag_configure("info", foreground="#222222")
 
    def _build_status(self):
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, relief="sunken",
                  anchor="w").pack(fill="x", side="bottom")
 
    # ---------- helpers ----------
    def log_out(self, text, tag="info"):
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n", tag)
        self.console.see("end")
        self.console.configure(state="disabled")
 
    def refresh_table(self, problems=None):
        problems = problems or {}
        self.tree.delete(*self.tree.get_children())
        rows = self.db.get_logs()
        for r in rows:
            tag = "bad" if r["id"] in problems else "ok"
            self.tree.insert(
                "", "end", iid=str(r["id"]), tags=(tag,),
                values=(r["id"], r["timestamp"], r["event"], r["username"],
                        r["ip"], r["details"], r["hash"]),
            )
        self.status.set(f"  Total logs: {len(rows)}   |   Database: {DB_FILE}")
 
    # ---------- actions ----------
    def on_add(self):
        user, ip = self.user_var.get().strip(), self.ip_var.get().strip()
        if not user or not ip:
            messagebox.showwarning("Missing data", "Username and IP are required.")
            return
        self.db.add_log(self.event_var.get(), user, ip,
                        self.details_var.get().strip())
        self.details_var.set("")
        self.refresh_table()
        self.log_out(f"Log added: {self.event_var.get()} | {user} | {ip}")
 
    def on_verify(self):
        valid, problems = self.db.verify()
        self.refresh_table(problems)
        self.log_out("--- Integrity Verification ---")
        if valid:
            self.log_out("INTEGRITY VERIFIED: All logs are valid.", "good")
        else:
            for log_id, issues in problems.items():
                self.log_out(f"ALERT: Log {log_id}: {', '.join(issues)}", "alert")
            self.log_out("INTEGRITY FAILURE: Tampering detected!", "alert")
 
    def on_detect(self):
        self.log_out("--- Intrusion Detection ---")
        found = self.db.detect_intrusions(self.threshold_var.get())
        if not found:
            self.log_out("No suspicious IP addresses found.", "good")
            return
        for ip, count in found.items():
            self.log_out(
                f"INTRUSION ALERT! Suspicious IP: {ip} | Failed login attempts: {count}",
                "alert",
            )
        messagebox.showwarning(
            "Intrusion Alert",
            "Suspicious IP(s): " + ", ".join(found.keys()),
        )
 
    def on_tamper(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a log", "Select a log row to tamper with.")
            return
        log_id = int(sel[0])
        self.db.tamper(log_id)
        self.refresh_table()
        self.log_out(f"Log {log_id} modified directly in the database (test).",
                     "alert")
        self.log_out("Click 'Verify Integrity' to detect the change.")
 
    def on_sample(self):
        self.db.load_sample_data()
        self.refresh_table()
        self.log_out("Sample data loaded.")
 
    def on_clear(self):
        if messagebox.askyesno("Confirm", "Delete ALL logs from the database?"):
            self.db.clear()
            self.refresh_table()
            self.log_out("All logs cleared.")
 
    def on_row_details(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        row = self.db.conn.execute(
            "SELECT * FROM logs WHERE id = ?", (int(sel[0]),)
        ).fetchone()
        text = (
            f"Log ID:        {row['id']}\n"
            f"Timestamp:     {row['timestamp']}\n"
            f"Event:         {row['event']}\n"
            f"User:          {row['username']}\n"
            f"IP:            {row['ip']}\n"
            f"Details:       {row['details']}\n\n"
            f"Previous Hash: {row['previous_hash']}\n"
            f"Current Hash:  {row['hash']}"
        )
        messagebox.showinfo(f"Log {row['id']} Details", text)
 
 
if __name__ == "__main__":
    App().mainloop()
 