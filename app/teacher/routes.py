from datetime import date as date_cls
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import get_db, log_audit
from app.decorators import role_required

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

VALID_STATUSES = {"Present", "Absent", "Half-Day", "Late", "Medical Leave", "Official Leave"}


@teacher_bp.route("/dashboard")
@role_required("Teacher")
def dashboard():
    db = get_db()
    sections = db.execute(
        """SELECT sec.section_id, c.grade_name, sec.section_name,
                  (SELECT COUNT(*) FROM students st WHERE st.section_id=sec.section_id AND st.status='Active') AS student_count,
                  (SELECT COUNT(*) FROM attendance a WHERE a.section_id=sec.section_id AND a.attendance_date=date('now')) AS marked_today
           FROM sections sec JOIN classes c ON c.class_id = sec.class_id
           WHERE sec.teacher_id = ? AND sec.section_id IS NOT NULL""",
        (session["user_id"],),
    ).fetchall()
    return render_template("teacher/dashboard.html", sections=sections, today=date_cls.today().isoformat())


@teacher_bp.route("/attendance/<int:section_id>", methods=["GET", "POST"])
@role_required("Teacher")
def mark_attendance(section_id):
    db = get_db()
    section = db.execute(
        """SELECT sec.*, c.grade_name FROM sections sec JOIN classes c ON c.class_id=sec.class_id
           WHERE sec.section_id=? AND sec.teacher_id=?""",
        (section_id, session["user_id"]),
    ).fetchone()
    if section is None:
        return "Not authorized for this section.", 403

    attendance_date = request.args.get("date") or date_cls.today().isoformat()

    if request.method == "POST":
        attendance_date = request.form["attendance_date"]
        students_ids = request.form.getlist("student_id")
        try:
            for sid in students_ids:
                status = request.form.get(f"status_{sid}")
                remarks = request.form.get(f"remarks_{sid}", "").strip()
                if status not in VALID_STATUSES:
                    continue
                # FIX #1 benefit: WAL mode lets this loop of writes proceed
                # smoothly even if another teacher is submitting at the same time.
                db.execute(
                    """INSERT INTO attendance (student_id, section_id, marked_by, attendance_date, status, remarks)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(student_id, attendance_date)
                       DO UPDATE SET status=excluded.status, remarks=excluded.remarks, marked_by=excluded.marked_by""",
                    (sid, section_id, session["user_id"], attendance_date, status, remarks),
                )
            db.commit()
            log_audit(
                db, session["user_id"], "ATTENDANCE_MARKED",
                f"section {section_id} on {attendance_date}", request.remote_addr,
            )
            flash(f"Attendance saved for {attendance_date}.", "success")
            return redirect(url_for("teacher.mark_attendance", section_id=section_id, date=attendance_date))
        except Exception as e:
            flash(f"Error saving attendance: {e}", "error")

    students = db.execute(
        """SELECT s.student_id, s.full_name, s.roll_number, a.status, a.remarks
           FROM students s
           LEFT JOIN attendance a ON a.student_id = s.student_id AND a.attendance_date = ?
           WHERE s.section_id = ? AND s.status='Active'
           ORDER BY s.roll_number""",
        (attendance_date, section_id),
    ).fetchall()

    return render_template(
        "teacher/mark_attendance.html",
        section=section,
        students=students,
        attendance_date=attendance_date,
        statuses=sorted(VALID_STATUSES),
    )


@teacher_bp.route("/history/<int:section_id>")
@role_required("Teacher")
def history(section_id):
    db = get_db()
    section = db.execute(
        "SELECT sec.*, c.grade_name FROM sections sec JOIN classes c ON c.class_id=sec.class_id WHERE sec.section_id=? AND sec.teacher_id=?",
        (section_id, session["user_id"]),
    ).fetchone()
    if section is None:
        return "Not authorized for this section.", 403

    rows = db.execute(
        """SELECT attendance_date,
                  SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present,
                  SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) AS absent,
                  COUNT(*) AS total
           FROM attendance WHERE section_id=?
           GROUP BY attendance_date ORDER BY attendance_date DESC LIMIT 30""",
        (section_id,),
    ).fetchall()
    return render_template("teacher/history.html", section=section, rows=rows)
