import sqlite3

# Name of the database file that will be created in the project folder
DATABASE = 'srms.db'

# How long (in seconds) to wait for a locked database before raising an error.
# This gives time for another connection to finish and release the lock.
TIMEOUT = 5


def _connect():
    """
    Internal helper: opens a connection with a timeout and row_factory set.
    Always use this inside a try/finally block so conn.close() is guaranteed.

    timeout=5 means SQLite will wait up to 5 seconds for a lock to clear
    before raising OperationalError, instead of failing immediately.
    """
    conn = sqlite3.connect(DATABASE, timeout=TIMEOUT)
    # Makes rows behave like dictionaries: row['name'] instead of row[0]
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates the database tables if they don't already exist.
    Safe to call every time the app starts — will not overwrite existing data.
    """
    conn = _connect()
    try:
        cursor = conn.cursor()

        # --- Table 1: students ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id  TEXT    NOT NULL UNIQUE,
                name        TEXT    NOT NULL,
                class_name  TEXT    NOT NULL,
                section     TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # --- Table 2: marks ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id      TEXT    NOT NULL,
                subject         TEXT    NOT NULL,
                marks_obtained  INTEGER NOT NULL,
                max_marks       INTEGER NOT NULL DEFAULT 100,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
        ''')

        conn.commit()
        print("Database initialised successfully — srms.db is ready.")
    finally:
        # finally always runs — connection is closed even if an exception occurs
        conn.close()


# ===========================================================================
# Student helper functions
#
# IMPORTANT: Every function uses try/finally to guarantee conn.close() is
# always called, even when an exception is raised mid-function.
#
# Without finally: if an exception fires between _connect() and conn.close(),
# the connection stays open, holds a write lock on srms.db, and every
# subsequent write raises "OperationalError: database is locked".
#
# All SQL uses ? placeholders — never string concatenation — to prevent
# SQL injection.
# ===========================================================================

def get_all_students():
    """
    Returns a list of all students ordered by date added (oldest first).
    """
    conn = _connect()
    try:
        students = conn.execute(
            'SELECT * FROM students ORDER BY created_at ASC'
        ).fetchall()
        return students
    finally:
        conn.close()


def get_student_by_id(student_id):
    """
    Returns a single student row matching the given student_id string.
    Returns None if no student is found.
    """
    conn = _connect()
    try:
        student = conn.execute(
            'SELECT * FROM students WHERE student_id = ?',
            (student_id,)
        ).fetchone()
        return student
    finally:
        conn.close()


def add_student(student_id, name, class_name, section):
    """
    Inserts a new student record.
    Raises sqlite3.IntegrityError if student_id already exists (UNIQUE constraint).
    The caller (app.py) catches this error and shows a friendly message.

    The try/finally here is especially important: without it, the
    IntegrityError raised on a duplicate ID would skip conn.close(),
    leaving the lock held and breaking every subsequent write operation.
    """
    conn = _connect()
    try:
        conn.execute(
            '''INSERT INTO students (student_id, name, class_name, section)
               VALUES (?, ?, ?, ?)''',
            (student_id, name, class_name, section)
        )
        conn.commit()
    finally:
        conn.close()


def update_student(student_id, name, class_name, section):
    """
    Updates name, class, and section for an existing student.
    student_id itself cannot be changed (it is the unique identifier).
    """
    conn = _connect()
    try:
        conn.execute(
            '''UPDATE students
               SET name = ?, class_name = ?, section = ?
               WHERE student_id = ?''',
            (name, class_name, section, student_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_student(student_id):
    """
    Deletes a student and all their marks from the database.
    Marks are deleted first to avoid orphaned records in the marks table.
    Both deletes happen before commit() — if either fails, neither is saved.
    """
    conn = _connect()
    try:
        # Step 1: delete the student's marks first
        conn.execute(
            'DELETE FROM marks WHERE student_id = ?',
            (student_id,)
        )
        # Step 2: delete the student record
        conn.execute(
            'DELETE FROM students WHERE student_id = ?',
            (student_id,)
        )
        conn.commit()
    finally:
        conn.close()


# This block runs only when you execute: python database.py directly
if __name__ == '__main__':
    init_db()


# ===========================================================================
# Marks helper functions
# Same safe pattern as student functions: try/finally guarantees conn.close().
# All SQL uses ? placeholders — no string concatenation.
# ===========================================================================

def get_marks_by_student(student_id):
    """
    Returns all mark rows for a given student, ordered by subject name.
    Each row has: id, student_id, subject, marks_obtained, max_marks.
    """
    conn = _connect()
    try:
        marks = conn.execute(
            '''SELECT * FROM marks
               WHERE student_id = ?
               ORDER BY subject ASC''',
            (student_id,)
        ).fetchall()
        return marks
    finally:
        conn.close()


def get_mark_by_id(mark_id):
    """
    Returns a single mark row by its primary key (id column).
    Returns None if not found.
    Used to verify a mark exists before editing or deleting it.
    """
    conn = _connect()
    try:
        mark = conn.execute(
            'SELECT * FROM marks WHERE id = ?',
            (mark_id,)
        ).fetchone()
        return mark
    finally:
        conn.close()


def add_mark(student_id, subject, marks_obtained, max_marks):
    """
    Inserts one subject-mark row for the given student.
    marks_obtained and max_marks are stored as integers.
    """
    conn = _connect()
    try:
        conn.execute(
            '''INSERT INTO marks (student_id, subject, marks_obtained, max_marks)
               VALUES (?, ?, ?, ?)''',
            (student_id, subject, marks_obtained, max_marks)
        )
        conn.commit()
    finally:
        conn.close()


def update_mark(mark_id, subject, marks_obtained, max_marks):
    """
    Updates subject name, marks obtained, and max marks for a single row.
    Identified by the row's integer primary key (mark_id).
    """
    conn = _connect()
    try:
        conn.execute(
            '''UPDATE marks
               SET subject = ?, marks_obtained = ?, max_marks = ?
               WHERE id = ?''',
            (subject, marks_obtained, max_marks, mark_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_mark(mark_id):
    """
    Deletes a single subject-mark row by its primary key.
    """
    conn = _connect()
    try:
        conn.execute(
            'DELETE FROM marks WHERE id = ?',
            (mark_id,)
        )
        conn.commit()
    finally:
        conn.close()


# ===========================================================================
# Result calculation
#
# Nothing is stored in the database. Every value is computed fresh from the
# marks rows each time this function is called.
# ===========================================================================

def calculate_result(marks):
    """
    Accepts a list of mark rows (as returned by get_marks_by_student).
    Returns a dictionary with the calculated result, or None if marks is empty.

    Returned dictionary keys:
        total_obtained  -- sum of marks_obtained across all subjects
        total_max       -- sum of max_marks across all subjects
        percentage      -- rounded to 2 decimal places
        grade           -- one of A, B, C, D, F
        status          -- 'Pass' or 'Fail'
        failed_subjects -- list of subject names where marks_obtained < 35

    Why return None for empty marks?
    If a student has no subjects yet, there is nothing to calculate.
    The caller (route or template) should show a message like
    "No marks available — add subjects first."
    """
    if not marks:
        # No subjects entered yet — cannot calculate anything meaningful
        return None

    # -----------------------------------------------------------------------
    # Step 1: Add up totals
    # We loop through every subject row and accumulate two running totals.
    # -----------------------------------------------------------------------
    total_obtained = 0   # sum of actual marks scored
    total_max      = 0   # sum of maximum possible marks

    for mark in marks:
        total_obtained += mark['marks_obtained']
        total_max      += mark['max_marks']

    # -----------------------------------------------------------------------
    # Step 2: Calculate percentage
    # Formula: (marks obtained / max possible marks) x 100
    # round(..., 2) keeps it to 2 decimal places, e.g. 73.33
    # We guard against division by zero just in case (total_max should always
    # be > 0 because we validated max_marks > 0 when adding marks).
    # -----------------------------------------------------------------------
    if total_max == 0:
        percentage = 0.0
    else:
        percentage = round((total_obtained / total_max) * 100, 2)

    # -----------------------------------------------------------------------
    # Step 3: Determine grade from percentage
    # Thresholds: A>=90, B>=75, C>=60, D>=45, F<45
    # The order matters — we check from highest to lowest.
    # -----------------------------------------------------------------------
    if percentage >= 90:
        grade = 'A'
    elif percentage >= 75:
        grade = 'B'
    elif percentage >= 60:
        grade = 'C'
    elif percentage >= 45:
        grade = 'D'
    else:
        grade = 'F'

    # -----------------------------------------------------------------------
    # Step 4: Determine pass/fail
    # A student PASSES only if they scored >= 35 in EVERY subject.
    # Even one subject below 35 means the overall result is Fail.
    # This is checked independently from the percentage grade.
    # -----------------------------------------------------------------------
    failed_subjects = [
        mark['subject']
        for mark in marks
        if mark['marks_obtained'] < 35
    ]

    status = 'Fail' if failed_subjects else 'Pass'

    # -----------------------------------------------------------------------
    # Return everything as a dictionary so the template can access each
    # value by name, e.g. result['percentage'], result['grade'], etc.
    # -----------------------------------------------------------------------
    return {
        'total_obtained':  total_obtained,
        'total_max':       total_max,
        'percentage':      percentage,
        'grade':           grade,
        'status':          status,
        'failed_subjects': failed_subjects,
    }
