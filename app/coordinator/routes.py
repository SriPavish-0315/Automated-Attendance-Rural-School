import io
from datetime import datetime
from datetime import date as date_cls
from flask import Blueprint, render_template, request, session, Response
from app.db import get_db
from app.decorators import role_required

coordinator_bp = Blueprint(
    "coordinator", __name__, url_prefix="/coordinator"
)


def format_marked_time(value):
    if not value:
        return "-"
    try:
        raw_value = str(value)
        if " " in raw_value and ":" in raw_value:
            raw_value = raw_value.replace(" ", "T", 1)
        dt = datetime.fromisoformat(raw_value)
    except ValueError:
        return str(value)

    hour = dt.hour
    suffix = "am" if hour < 12 else "pm"
    display_hour = hour % 12 or 12
    return f"{display_hour}.{dt.strftime('%M')}.{dt.second} {suffix}"


def build_attendance_excel_rows(records):
    return [
        [
            record.get("full_name", ""),
            record.get("roll_number", ""),
            record.get("status") or "Not marked",
            record.get("formatted_time") or "-",
            record.get("remarks") or "-",
        ]
        for record in records
    ]


def create_attendance_excel(records):
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl is not installed")

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Attendance"
    headers = ["Student Name", "Roll Number", "Status", "Marked Time", "Remarks"]
    sheet.append(headers)
    for row in build_attendance_excel_rows(records):
        sheet.append(row)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


@coordinator_bp.route("/dashboard")
@role_required("Coordinator")
def dashboard():
    db = get_db()
    my_sections = db.execute(
        """SELECT sec.section_id, c.grade_name, sec.section_name, t.full_name AS teacher_name,
                  (SELECT COUNT(*) FROM students st WHERE st.section_id=sec.section_id AND st.status='Active') AS student_count,
                  (SELECT COUNT(*) FROM attendance a WHERE a.section_id=sec.section_id AND a.attendance_date=date('now')) AS marked_today,
                  (SELECT COUNT(*) FROM attendance a WHERE a.section_id=sec.section_id AND a.attendance_date=date('now') AND a.status='Present') AS present_today,
                  (SELECT COUNT(*) FROM attendance a WHERE a.section_id=sec.section_id AND a.attendance_date=date('now') AND a.status='Absent') AS absent_today,
                  (SELECT COUNT(*) FROM attendance a WHERE a.section_id=sec.section_id AND a.attendance_date=date('now') AND a.status!='Present' AND a.status!='Absent') AS other_today
           FROM sections sec
           JOIN classes c ON c.class_id = sec.class_id
           LEFT JOIN users t ON t.user_id = sec.teacher_id
           WHERE sec.coordinator_id = ?
           ORDER BY c.grade_name, sec.section_name""",
        (session["user_id"],),
    ).fetchall()
    notifications = db.execute(
        "SELECT notification_id, message, created_at FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (session["user_id"],),
    ).fetchall()
    return render_template("coordinator/dashboard.html", sections=my_sections, notifications=notifications)


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

    date = request.args.get("date") or date_cls.today().isoformat()
    date_clause = "= date(?)"
    params = (date,)

    records = db.execute(
        f"""SELECT s.full_name, s.roll_number, a.status, a.remarks, a.created_at
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.student_id AND a.attendance_date {date_clause}
            WHERE s.section_id = ? AND s.status='Active'
            ORDER BY s.roll_number""",
        params + (section_id,),
    ).fetchall()

    formatted_records = [
        {
            **dict(record),
            "formatted_time": format_marked_time(record["created_at"]),
        }
        for record in records
    ]

    return render_template("coordinator/section_detail.html", section=section, records=formatted_records, date=date)


@coordinator_bp.route("/section/<int:section_id>/export")
@role_required("Coordinator")
def export_section_attendance(section_id):
    db = get_db()
    section = db.execute(
        "SELECT sec.section_id, c.grade_name, sec.section_name FROM sections sec JOIN classes c ON c.class_id=sec.class_id WHERE sec.section_id=? AND sec.coordinator_id=?",
        (section_id, session["user_id"]),
    ).fetchone()
    if section is None:
        return "Not authorized for this section.", 403

    date = request.args.get("date") or date_cls.today().isoformat()
    date_clause = "= date(?)"
    params = (date,)

    records = db.execute(
        f"""SELECT s.full_name, s.roll_number, a.status, a.remarks, a.created_at
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.student_id AND a.attendance_date {date_clause}
            WHERE s.section_id = ? AND s.status='Active'
            ORDER BY s.roll_number""",
        params + (section_id,),
    ).fetchall()

    formatted_records = [
        {
            **dict(record),
            "formatted_time": format_marked_time(record["created_at"]),
        }
        for record in records
    ]

    try:
        excel_file = create_attendance_excel(formatted_records)
    except RuntimeError as exc:
        return str(exc), 500

    file_name = f"attendance_{section['grade_name']}_{section['section_name']}_{date}.xlsx"
    return Response(
        excel_file.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )
