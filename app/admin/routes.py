from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from app.db import get_db, log_audit
from app.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def update_staff_account(db, user_id, payload):
    role_row = db.execute("SELECT role_id FROM roles WHERE role_name=?", (payload.get("role"),)).fetchone()
    if role_row is None:
        raise ValueError("Invalid role")

    updates = [
        "username = ?",
        "full_name = ?",
        "email = ?",
        "phone = ?",
        "role_id = ?",
    ]
    values = [
        payload.get("username", "").strip(),
        payload.get("full_name", "").strip(),
        payload.get("email", "").strip(),
        payload.get("phone", "").strip(),
        role_row["role_id"],
    ]

    if payload.get("password"):
        updates.append("assigned_password = ?")
        values.append(payload.get("password"))

    values.append(user_id)
    db.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id=?", values)


def update_staff_section_assignment(db, user_id, role_name, section_id):
    if not user_id:
        return

    if role_name == "Teacher":
        column_name = "teacher_id"
    elif role_name == "Coordinator":
        column_name = "coordinator_id"
    else:
        return

    if section_id is None:
        db.execute(f"UPDATE sections SET {column_name}=NULL WHERE {column_name}=?", (user_id,))
        return

    db.execute(
        f"UPDATE sections SET {column_name}=NULL WHERE {column_name}=? AND section_id != ?",
        (user_id, section_id),
    )
    db.execute(f"UPDATE sections SET {column_name}=? WHERE section_id=?", (user_id, section_id))


@admin_bp.route("/dashboard")
@role_required("Administrator")
def dashboard():
    db = get_db()
    total_students = db.execute("SELECT COUNT(*) c FROM students WHERE status='Active'").fetchone()["c"]
    total_teachers = db.execute(
        "SELECT COUNT(*) c FROM users u JOIN roles r ON r.role_id=u.role_id WHERE r.role_name='Teacher' AND u.status='Active'"
    ).fetchone()["c"]
    total_coordinators = db.execute(
        "SELECT COUNT(*) c FROM users u JOIN roles r ON r.role_id=u.role_id WHERE r.role_name='Coordinator' AND u.status='Active'"
    ).fetchone()["c"]
    total_classes = db.execute("SELECT COUNT(*) c FROM sections").fetchone()["c"]
    today_attendance = db.execute(
        "SELECT COUNT(*) c FROM attendance WHERE attendance_date = date('now')"
    ).fetchone()["c"]
    recent_logs = db.execute(
        """SELECT a.*, u.full_name FROM audit_log a LEFT JOIN users u ON u.user_id = a.user_id
           ORDER BY a.created_at DESC LIMIT 10"""
    ).fetchall()

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        total_coordinators=total_coordinators,
        total_classes=total_classes,
        today_attendance=today_attendance,
        recent_logs=recent_logs,
    )


# ---------------------------------------------------------------- Students
@admin_bp.route("/students")
@role_required("Administrator")
def students():
    db = get_db()
    rows = db.execute(
        """SELECT s.*, c.grade_name, sec.section_name,
                  t.full_name AS teacher_name
           FROM students s
           JOIN sections sec ON sec.section_id = s.section_id
           JOIN classes c ON c.class_id = sec.class_id
           LEFT JOIN users t ON t.user_id = sec.teacher_id
           ORDER BY s.full_name"""
    ).fetchall()
    return render_template("admin/students.html", students=rows)


@admin_bp.route("/students/add", methods=["GET", "POST"])
@role_required("Administrator")
def add_student():
    db = get_db()
    sections = db.execute(
        """SELECT sec.section_id, c.grade_name, sec.section_name FROM sections sec
           JOIN classes c ON c.class_id = sec.class_id"""
    ).fetchall()

    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO students (admission_no, full_name, roll_number, section_id,
                   parent_name, parent_contact, status) VALUES (?, ?, ?, ?, ?, ?, 'Active')""",
                (
                    request.form["admission_no"].strip(),
                    request.form["full_name"].strip(),
                    request.form["roll_number"].strip(),
                    request.form["section_id"],
                    request.form.get("parent_name", "").strip(),
                    request.form.get("parent_contact", "").strip(),
                ),
            )
            db.commit()
            log_audit(db, session["user_id"], "STUDENT_ADDED", request.form["full_name"], request.remote_addr)
            flash("Student added successfully.", "success")
            return redirect(url_for("admin.students"))
        except Exception as e:
            flash(f"Error adding student: {e}", "error")

    return render_template("admin/student_form.html", sections=sections)


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@role_required("Administrator")
def edit_student(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_id=? AND status='Active'", (student_id,)).fetchone()
    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("admin.students"))

    sections = db.execute(
        """SELECT sec.section_id, c.grade_name, sec.section_name FROM sections sec
           JOIN classes c ON c.class_id = sec.class_id"""
    ).fetchall()

    if request.method == "POST":
        try:
            db.execute(
                """UPDATE students SET admission_no=?, full_name=?, roll_number=?, section_id=?,
                   parent_name=?, parent_contact=? WHERE student_id=?""",
                (
                    request.form["admission_no"].strip(),
                    request.form["full_name"].strip(),
                    request.form["roll_number"].strip(),
                    request.form["section_id"],
                    request.form.get("parent_name", "").strip(),
                    request.form.get("parent_contact", "").strip(),
                    student_id,
                ),
            )
            db.commit()
            log_audit(db, session["user_id"], "STUDENT_UPDATED", request.form["full_name"], request.remote_addr)
            flash("Student updated successfully.", "success")
            return redirect(url_for("admin.students"))
        except Exception as e:
            flash(f"Error updating student: {e}", "error")

    return render_template("admin/student_form.html", sections=sections, student=student)


@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@role_required("Administrator")
def delete_student(student_id):
    db = get_db()
    db.execute("UPDATE students SET status='Deleted' WHERE student_id=?", (student_id,))
    db.commit()
    log_audit(db, session["user_id"], "STUDENT_DELETED", str(student_id), request.remote_addr)
    flash("Student removed.", "info")
    return redirect(url_for("admin.students"))


# ---------------------------------------------------------------- Staff (Teachers/Coordinators)
@admin_bp.route("/staff")
@role_required("Administrator")
def staff():
    db = get_db()
    rows = db.execute(
        """
        SELECT u.user_id, u.username, u.assigned_password, u.full_name, u.email, u.phone, u.status,
               r.role_name,
               GROUP_CONCAT(c.grade_name || ' - ' || sec.section_name, ', ') AS assigned_class
        FROM users u
        JOIN roles r ON r.role_id = u.role_id
        LEFT JOIN sections sec ON (
            (r.role_name = 'Teacher' AND sec.teacher_id = u.user_id) OR
            (r.role_name = 'Coordinator' AND sec.coordinator_id = u.user_id)
        )
        LEFT JOIN classes c ON c.class_id = sec.class_id
        WHERE r.role_name IN ('Teacher','Coordinator') AND u.status = 'Active'
        GROUP BY u.user_id, u.username, u.assigned_password, u.full_name, u.email, u.phone, u.status, r.role_name
        ORDER BY u.full_name
        """
    ).fetchall()
    teachers = [row for row in rows if row["role_name"] == "Teacher"]
    coordinators = [row for row in rows if row["role_name"] == "Coordinator"]
    return render_template("admin/staff.html", teachers=teachers, coordinators=coordinators)


@admin_bp.route("/staff/add", methods=["GET", "POST"])
@role_required("Administrator")
def add_staff():
    db = get_db()
    if request.method == "POST":
        role_name = request.form["role"]
        role_row = db.execute("SELECT role_id FROM roles WHERE role_name=?", (role_name,)).fetchone()
        password = request.form["password"]
        try:
            db.execute(
                """INSERT INTO users (username, password_hash, assigned_password, full_name, email, phone, role_id, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')""",
                (
                    request.form["username"].strip(),
                    generate_password_hash(password),
                    password,
                    request.form["full_name"].strip(),
                    request.form.get("email", "").strip(),
                    request.form.get("phone", "").strip(),
                    role_row["role_id"],
                ),
            )
            db.commit()
            log_audit(db, session["user_id"], "STAFF_ADDED", request.form["full_name"], request.remote_addr)
            flash("Staff account created.", "success")
            return redirect(url_for("admin.staff"))
        except Exception as e:
            flash(f"Error creating staff account: {e}", "error")

    return render_template("admin/staff_form.html")


@admin_bp.route("/staff/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("Administrator")
def edit_staff(user_id):
    db = get_db()
    staff_user = db.execute(
        "SELECT u.*, r.role_name FROM users u JOIN roles r ON r.role_id = u.role_id WHERE u.user_id=?",
        (user_id,),
    ).fetchone()
    if staff_user is None:
        flash("Staff member not found.", "error")
        return redirect(url_for("admin.staff"))

    if request.method == "POST":
        try:
            update_staff_account(db, user_id, request.form)
            db.commit()
            log_audit(db, session["user_id"], "STAFF_UPDATED", request.form.get("full_name", staff_user["full_name"]), request.remote_addr)
            flash("Staff details updated.", "success")
            return redirect(url_for("admin.staff"))
        except Exception as e:
            flash(f"Error updating staff: {e}", "error")

    return render_template("admin/staff_form.html", staff=staff_user)


@admin_bp.route("/staff/<int:user_id>/deactivate", methods=["POST"])
@role_required("Administrator")
def deactivate_staff(user_id):
    db = get_db()
    db.execute("UPDATE users SET status='Inactive' WHERE user_id=?", (user_id,))
    db.commit()
    log_audit(db, session["user_id"], "STAFF_DEACTIVATED", str(user_id), request.remote_addr)
    flash("Staff account deactivated.", "info")
    return redirect(url_for("admin.staff"))


# ---------------------------------------------------------------- Classes & Sections
@admin_bp.route("/classes")
@role_required("Administrator")
def classes():
    db = get_db()
    rows = db.execute(
        """SELECT sec.section_id, c.grade_name, sec.section_name, t.full_name AS teacher_name,
                  co.full_name AS coordinator_name,
                  (SELECT COUNT(*) FROM students st WHERE st.section_id = sec.section_id AND st.status='Active') AS student_count
           FROM sections sec
           JOIN classes c ON c.class_id = sec.class_id
           LEFT JOIN users t ON t.user_id = sec.teacher_id
           LEFT JOIN users co ON co.user_id = sec.coordinator_id
           ORDER BY c.grade_name, sec.section_name"""
    ).fetchall()
    return render_template("admin/classes.html", sections=rows)


@admin_bp.route("/classes/add", methods=["GET", "POST"])
@role_required("Administrator")
def add_class():
    db = get_db()
    teachers = db.execute(
        "SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id WHERE r.role_name='Teacher' AND u.status='Active'"
    ).fetchall()
    coordinators = db.execute(
        "SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id WHERE r.role_name='Coordinator' AND u.status='Active'"
    ).fetchall()

    if request.method == "POST":
        grade_name = request.form["grade_name"].strip()
        row = db.execute("SELECT class_id FROM classes WHERE grade_name=?", (grade_name,)).fetchone()
        class_id = row["class_id"] if row else db.execute(
            "INSERT INTO classes (grade_name) VALUES (?)", (grade_name,)
        ).lastrowid

        section_id = db.execute(
            "INSERT INTO sections (class_id, section_name, teacher_id, coordinator_id) VALUES (?, ?, ?, ?)",
            (
                class_id,
                request.form["section_name"].strip(),
                request.form.get("teacher_id") or None,
                request.form.get("coordinator_id") or None,
            ),
        ).lastrowid
        if request.form.get("teacher_id"):
            update_staff_section_assignment(db, int(request.form["teacher_id"]), "Teacher", section_id)
        if request.form.get("coordinator_id"):
            update_staff_section_assignment(db, int(request.form["coordinator_id"]), "Coordinator", section_id)
        db.commit()
        log_audit(db, session["user_id"], "CLASS_ADDED", f"{grade_name} {request.form['section_name']}", request.remote_addr)
        flash("Class/section added.", "success")
        return redirect(url_for("admin.classes"))

    return render_template("admin/class_form.html", teachers=teachers, coordinators=coordinators)


@admin_bp.route("/classes/<int:section_id>/edit", methods=["GET", "POST"])
@role_required("Administrator")
def edit_class(section_id):
    db = get_db()
    section = db.execute(
        "SELECT sec.section_id, sec.class_id, sec.section_name, sec.teacher_id, sec.coordinator_id, c.grade_name FROM sections sec JOIN classes c ON c.class_id = sec.class_id WHERE sec.section_id=?",
        (section_id,),
    ).fetchone()
    if section is None:
        flash("Class/section not found.", "error")
        return redirect(url_for("admin.classes"))

    teachers = db.execute(
        "SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id WHERE r.role_name='Teacher' AND u.status='Active'"
    ).fetchall()
    coordinators = db.execute(
        "SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id WHERE r.role_name='Coordinator' AND u.status='Active'"
    ).fetchall()

    if request.method == "POST":
        grade_name = request.form["grade_name"].strip()
        class_row = db.execute("SELECT class_id FROM classes WHERE grade_name=?", (grade_name,)).fetchone()
        class_id = class_row["class_id"] if class_row else db.execute(
            "INSERT INTO classes (grade_name) VALUES (?)", (grade_name,)
        ).lastrowid

        teacher_id = request.form.get("teacher_id") or None
        coordinator_id = request.form.get("coordinator_id") or None

        db.execute(
            "UPDATE sections SET class_id=?, section_name=?, teacher_id=?, coordinator_id=? WHERE section_id=?",
            (
                class_id,
                request.form["section_name"].strip(),
                teacher_id,
                coordinator_id,
                section_id,
            ),
        )

        if section["class_id"] != class_id:
            db.execute("UPDATE classes SET grade_name=? WHERE class_id=?", (grade_name, class_id))

        if section["teacher_id"] != teacher_id:
            update_staff_section_assignment(db, section["teacher_id"], "Teacher", None)
            if teacher_id:
                update_staff_section_assignment(db, int(teacher_id), "Teacher", section_id)

        if section["coordinator_id"] != coordinator_id:
            update_staff_section_assignment(db, section["coordinator_id"], "Coordinator", None)
            if coordinator_id:
                update_staff_section_assignment(db, int(coordinator_id), "Coordinator", section_id)

        db.commit()
        log_audit(db, session["user_id"], "CLASS_UPDATED", f"{grade_name} {request.form['section_name']}", request.remote_addr)
        flash("Class/section updated.", "success")
        return redirect(url_for("admin.classes"))

    return render_template("admin/class_form.html", teachers=teachers, coordinators=coordinators, section=section)


@admin_bp.route("/classes/<int:section_id>/delete", methods=["POST"])
@role_required("Administrator")
def delete_class(section_id):
    db = get_db()
    section = db.execute("SELECT class_id FROM sections WHERE section_id=?", (section_id,)).fetchone()
    if section is None:
        flash("Class/section not found.", "error")
        return redirect(url_for("admin.classes"))

    db.execute("DELETE FROM attendance WHERE section_id=?", (section_id,))
    db.execute("DELETE FROM students WHERE section_id=?", (section_id,))
    db.execute("DELETE FROM sections WHERE section_id=?", (section_id,))

    class_id = section["class_id"]
    remaining_sections = db.execute("SELECT COUNT(*) c FROM sections WHERE class_id=?", (class_id,)).fetchone()["c"]
    if remaining_sections == 0:
        db.execute("DELETE FROM classes WHERE class_id=?", (class_id,))

    db.commit()
    log_audit(db, session["user_id"], "CLASS_DELETED", str(section_id), request.remote_addr)
    flash("Class/section removed.", "info")
    return redirect(url_for("admin.classes"))
