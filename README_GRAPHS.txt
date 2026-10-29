SMART STUDENT RESULT MANAGEMENT SYSTEM + GRAPHICAL ANALYSIS

FILES
- main.py and the supporting .py files: original student result management application
- result_management.db: database copy supplied with the project
- analysis_graphs.py: separate graphical analysis window (Matplotlib)

SETUP
1. Open this folder in VS Code.
2. Install Matplotlib once:
       python -m pip install matplotlib

RUN THE MAIN APPLICATION
       python main.py

RUN THE GRAPHICAL ANALYSIS
       python analysis_graphs.py

The graph program reads result_management.db in this folder and does not modify it.
It displays average marks by subject, average marks by student, grade distribution,
and pass/fail plus verification summary.

NOTE
This folder contains a copy of the database uploaded in this conversation. Keep a backup
before changing or replacing database files. If you add new marks through the main app,
close/reopen the graph program to see the updated figures.
