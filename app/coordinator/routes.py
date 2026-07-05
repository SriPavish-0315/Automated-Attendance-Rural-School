from flask import Blueprint, render_template, request, session
from app.db import get_db
from app.decorators import role_required

coordinator_bp = Blueprint(
    "coordinator", __name__, url_prefix="/coordinator"
)


@coordinator_bp.route("/dashboard")
@role_required("Coordinator")
def dashboard():
    db = get_db()
    my_sections = db.execute(
        """SELECT sec.section_id, c.grade_name, sec.section_name, t.full_name AS teacher_name,
                  (SELECT COUNT(*) FROM students st WHERE st.section_id=sec.section_id AND st.status='Active') AS student_count,
                  (SELECT COUNT(*) FROM attendance a WHERE a.section_id=sec.section_id AND a.attendance_date=date('now')) AS marked_today
           FROM sections sec
           JOIN classes c ON c.class_id = sec.class_id
           LEFT JOIN users t ON t.user_id = sec.teacher_id
           WHERE sec.coordinator_id = ?
           ORDER BY c.grade_name, sec.section_name""",
        (session["user_id"],),
    ).fetchall()
    return render_template("coordinator/dashboard.html", sections=my_sections)


@coordinator_bp.route("/section/<int:section_id>")
@role_required("Coordinator")
def section_detail(section_id):
    db = get_db()
    section = db.execute(
        """SELECT sec.*, c.grade_name, t.full_name AS teacher_name FROM sections sec
           JOIN classes c ON c.class_id=sec.class_id
           LEFT JOIN users t ON t.user_id = sec.teacher_id
           WHERE sec.section_id=? AND sec.coordinator_id=?""",
        (section_id, session["user_id"]),
    ).fetchone()
    if section is None:
        return "Not authorized for this section.", 403

    date = request.args.get("date")
    date_clause = "= date(?)" if date else "= date('now')"
    params = (date,) if date else ()

    records = db.execute(
        f"""SELECT s.full_name, s.roll_number, a.status, a.remarks
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.student_id AND a.attendance_date {date_clause}
            WHERE s.section_id = ? AND s.status='Active'
            ORDER BY s.roll_number""",
        params + (section_id,),
    ).fetchall()

    return render_template("coordinator/section_detail.html", section=section, records=records, date=date)
