import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from database import (
    init_db,
    get_all_students,
    get_student_by_id,
    add_student,
    update_student,
    delete_student,
    get_marks_by_student,
    get_mark_by_id,
    add_mark,
    update_mark,
    delete_mark,
    calculate_result,
)

# Load environment variables from the .env file
load_dotenv()

# Create the Flask application instance
app = Flask(__name__)

# Load the secret key from .env (Flask uses this to sign session cookies)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key')

# Read admin password from .env
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')


# ---------------------------------------------------------------------------
# Helper: protect routes that require admin login
# ---------------------------------------------------------------------------

def admin_required(f):
    """
    Decorator that redirects unauthenticated users to the login page.
    Add @admin_required above any route you want to protect.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """
    Public home page — shows the student ID search form.
    No login required.
    """
    return render_template('index.html')


@app.route('/result')
def student_result():
    """
    Public result page — no login required.

    Reads the student_id from the query string: /result?student_id=STU001
    The search form on index.html submits here via GET.

    Steps:
    1. Read student_id from request.args (query string).
    2. Look up the student in the database.
    3. If not found, render the same page with a not-found message.
    4. If found, fetch their marks and calculate the result.
    5. Render student_result.html with all the data.
    """
    # Read the student_id typed into the search box.
    # .strip() removes any accidental leading/trailing spaces.
    student_id = request.args.get('student_id', '').strip()

    # If someone visits /result with no ID, send them back to the home page.
    if not student_id:
        return redirect(url_for('index'))

    # Look up the student
    student = get_student_by_id(student_id)

    if student is None:
        # Student ID does not exist — render a friendly not-found message.
        # We pass student_id back so the template can show what was searched.
        return render_template(
            'student_result.html',
            student=None,
            searched_id=student_id,
            marks=[],
            result=None,
        )

    # Student found — fetch marks and calculate result
    marks  = get_marks_by_student(student_id)
    result = calculate_result(marks)   # returns None if marks list is empty

    return render_template(
        'student_result.html',
        student=student,
        marks=marks,
        result=result,
        searched_id=None,
    )


# ---------------------------------------------------------------------------
# Admin auth routes
# ---------------------------------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    GET  -- show the login form
    POST -- validate the password and create a session on success
    """
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        entered_password = request.form.get('password', '')
        if entered_password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Logged in successfully. Welcome, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect password. Please try again.', 'danger')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Clears the admin session and redirects to the login page."""
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """
    Shows a table of all students.
    Fetches every row from the students table and passes it to the template.
    """
    students = get_all_students()
    return render_template('dashboard.html', students=students)


# ---------------------------------------------------------------------------
# Add student
# ---------------------------------------------------------------------------

@app.route('/admin/add-student', methods=['GET', 'POST'])
@admin_required
def admin_add_student():
    """
    GET  -- show the blank Add Student form
    POST -- validate input, attempt to insert into DB, handle duplicate ID error
    """
    if request.method == 'POST':
        # Read every field from the submitted form
        student_id = request.form.get('student_id', '').strip()
        name       = request.form.get('name', '').strip()
        class_name = request.form.get('class_name', '').strip()
        section    = request.form.get('section', '').strip()

        # Basic server-side validation -- all fields are required
        if not all([student_id, name, class_name, section]):
            flash('All fields are required.', 'danger')
            # Pass form_data back so the template can re-fill what the admin typed
            return render_template('add_student.html', form_data=request.form)

        try:
            add_student(student_id, name, class_name, section)
            flash(f'Student "{name}" (ID: {student_id}) added successfully.', 'success')
            return redirect(url_for('admin_dashboard'))

        except sqlite3.IntegrityError:
            # Raised when student_id already exists (UNIQUE constraint violation)
            flash(
                f'Student ID "{student_id}" already exists. '
                'Please use a different ID.',
                'danger'
            )
            # Re-render the form keeping the values the admin already typed
            return render_template('add_student.html', form_data=request.form)

    # GET request -- show empty form
    return render_template('add_student.html', form_data=None)


# ---------------------------------------------------------------------------
# Edit student
# ---------------------------------------------------------------------------

@app.route('/admin/edit-student/<student_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_student(student_id):
    """
    GET  -- show the Edit form pre-filled with current student data
    POST -- validate input and update the record in the DB

    <student_id> in the URL is captured as the function parameter.
    Example URL: /admin/edit-student/STU001
    """
    # Fetch the student first -- if not found, redirect with an error
    student = get_student_by_id(student_id)
    if student is None:
        flash(f'Student ID "{student_id}" not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        class_name = request.form.get('class_name', '').strip()
        section    = request.form.get('section', '').strip()

        # Basic server-side validation
        if not all([name, class_name, section]):
            flash('All fields are required.', 'danger')
            return render_template('edit_student.html', student=student)

        update_student(student_id, name, class_name, section)
        flash(f'Student "{name}" updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    # GET -- show pre-filled form
    return render_template('edit_student.html', student=student)


# ---------------------------------------------------------------------------
# Delete student
# ---------------------------------------------------------------------------

@app.route('/admin/delete-student/<student_id>', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    """
    POST only -- deletes the student and all their marks.

    Only accepts POST (not GET) so a student cannot be deleted just by
    visiting a URL. The delete confirmation modal in dashboard.html
    submits a POST form to this route.
    """
    student = get_student_by_id(student_id)
    if student is None:
        flash(f'Student ID "{student_id}" not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    student_name = student['name']
    delete_student(student_id)
    flash(f'Student "{student_name}" (ID: {student_id}) deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


# ---------------------------------------------------------------------------
# Marks management
# ---------------------------------------------------------------------------

def _validate_mark_fields(subject, marks_obtained_raw, max_marks_raw):
    """
    Shared validation used by both add-mark and edit-mark routes.
    Returns (marks_obtained, max_marks, error_message).
    If validation passes, error_message is None.
    If validation fails, marks_obtained and max_marks are None.
    """
    subject = subject.strip()

    # Subject name must not be empty
    if not subject:
        return None, None, 'Subject name is required.'

    # marks_obtained must be a whole number
    try:
        marks_obtained = int(marks_obtained_raw)
    except (ValueError, TypeError):
        return None, None, 'Marks obtained must be a whole number.'

    # max_marks must be a whole number
    try:
        max_marks = int(max_marks_raw)
    except (ValueError, TypeError):
        return None, None, 'Max marks must be a whole number.'

    # max_marks must be positive
    if max_marks <= 0:
        return None, None, 'Max marks must be greater than 0.'

    # marks_obtained cannot be negative
    if marks_obtained < 0:
        return None, None, 'Marks obtained cannot be negative.'

    # marks_obtained cannot exceed max_marks
    if marks_obtained > max_marks:
        return None, None, (
            f'Marks obtained ({marks_obtained}) cannot be greater than '
            f'max marks ({max_marks}).'
        )

    return marks_obtained, max_marks, None


@app.route('/admin/marks/<student_id>')
@admin_required
def admin_manage_marks(student_id):
    """
    GET -- shows the manage marks page for a student.
    Optionally pre-fills the edit form when ?edit=<mark_id> is in the URL.
    Example: /admin/marks/STU001?edit=3
    """
    student = get_student_by_id(student_id)
    if student is None:
        flash(f'Student ID "{student_id}" not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    marks = get_marks_by_student(student_id)

    # Calculate result summary from the marks list.
    # calculate_result() returns None when marks is empty — the template
    # handles that case by showing a "no marks yet" message.
    result = calculate_result(marks)

    # Check if the admin clicked Edit on a specific mark row.
    # request.args reads query parameters from the URL (?edit=3).
    edit_mark = None
    edit_id = request.args.get('edit')
    if edit_id:
        try:
            edit_mark = get_mark_by_id(int(edit_id))
        except (ValueError, TypeError):
            pass  # Invalid ?edit value — just show the normal add form

    return render_template(
        'manage_marks.html',
        student=student,
        marks=marks,
        edit_mark=edit_mark,
        result=result,
    )


@app.route('/admin/marks/<student_id>/add', methods=['POST'])
@admin_required
def admin_add_mark(student_id):
    """
    POST -- validates and inserts one new subject-mark row for the student.
    On validation failure, redirects back to the marks page with a flash error.
    """
    student = get_student_by_id(student_id)
    if student is None:
        flash(f'Student ID "{student_id}" not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    subject          = request.form.get('subject', '')
    marks_obtained_r = request.form.get('marks_obtained', '')
    max_marks_r      = request.form.get('max_marks', '100')

    marks_obtained, max_marks, error = _validate_mark_fields(
        subject, marks_obtained_r, max_marks_r
    )

    if error:
        flash(error, 'danger')
        return redirect(url_for('admin_manage_marks', student_id=student_id))

    add_mark(student_id, subject.strip(), marks_obtained, max_marks)
    flash(f'Marks for "{subject.strip()}" added successfully.', 'success')
    return redirect(url_for('admin_manage_marks', student_id=student_id))


@app.route('/admin/marks/<student_id>/edit/<int:mark_id>', methods=['POST'])
@admin_required
def admin_edit_mark(student_id, mark_id):
    """
    POST -- validates and updates an existing mark row.
    <int:mark_id> tells Flask to convert the URL segment to an integer automatically.
    """
    # Verify the student exists
    student = get_student_by_id(student_id)
    if student is None:
        flash(f'Student ID "{student_id}" not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Verify the mark row exists
    mark = get_mark_by_id(mark_id)
    if mark is None:
        flash('Mark record not found.', 'danger')
        return redirect(url_for('admin_manage_marks', student_id=student_id))

    subject          = request.form.get('subject', '')
    marks_obtained_r = request.form.get('marks_obtained', '')
    max_marks_r      = request.form.get('max_marks', '100')

    marks_obtained, max_marks, error = _validate_mark_fields(
        subject, marks_obtained_r, max_marks_r
    )

    if error:
        flash(error, 'danger')
        # Redirect back with ?edit= so the form re-opens in edit mode
        return redirect(url_for(
            'admin_manage_marks', student_id=student_id, edit=mark_id
        ))

    update_mark(mark_id, subject.strip(), marks_obtained, max_marks)
    flash(f'Marks for "{subject.strip()}" updated successfully.', 'success')
    return redirect(url_for('admin_manage_marks', student_id=student_id))


@app.route('/admin/marks/<student_id>/delete/<int:mark_id>', methods=['POST'])
@admin_required
def admin_delete_mark(student_id, mark_id):
    """
    POST only -- deletes a single mark row by its primary key.
    POST-only prevents accidental deletion by visiting a URL directly.
    """
    mark = get_mark_by_id(mark_id)
    if mark is None:
        flash('Mark record not found.', 'danger')
        return redirect(url_for('admin_manage_marks', student_id=student_id))

    subject = mark['subject']
    delete_mark(mark_id)
    flash(f'Marks for "{subject}" deleted successfully.', 'success')
    return redirect(url_for('admin_manage_marks', student_id=student_id))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # Initialise the database tables when the app starts
    init_db()
    app.run(debug=True)
