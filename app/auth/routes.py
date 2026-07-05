from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from app.db import get_db, log_audit

auth_bp = Blueprint("auth", __name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def normalize_username(username):
    return (username or "").strip().lower()


def verify_password(password_hash, password, assigned_password=None):
    if not password:
        return False
    if password_hash and check_password_hash(password_hash, password):
        return True
    if assigned_password and password == assigned_password:
        return True
    return False


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        normalized_username = normalize_username(username)
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        db = get_db()
        user = db.execute(
            """SELECT u.*, r.role_name FROM users u
               JOIN roles r ON r.role_id = u.role_id
               WHERE lower(u.username) = ?""",
            (normalized_username,),
        ).fetchone()

        if user is None:
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html")

        if user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > datetime.now():
            flash("Account temporarily locked due to too many failed attempts. Try again later.", "error")
            return render_template("auth/login.html")

        if user["status"] != "Active":
            flash("This account is not active. Contact the administrator.", "error")
            return render_template("auth/login.html")

        if not verify_password(user["password_hash"], password, user["assigned_password"]):
            attempts = user["failed_attempts"] + 1
            locked_until = None
            if attempts >= MAX_FAILED_ATTEMPTS:
                locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            db.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE user_id = ?",
                (attempts, locked_until, user["user_id"]),
            )
            db.commit()
            log_audit(db, user["user_id"], "LOGIN_FAILED", f"attempt {attempts}", request.remote_addr)
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html")

        if user["password_hash"] and check_password_hash(user["password_hash"], password):
            password_verified = True
        else:
            password_verified = False

        if not password_verified:
            db.execute(
                "UPDATE users SET password_hash = ? WHERE user_id = ?",
                (generate_password_hash(password), user["user_id"]),
            )

        # Success
        db.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
            (user["user_id"],),
        )
        db.execute(
            "INSERT INTO login_history (user_id, ip_address, status) VALUES (?, ?, 'Success')",
            (user["user_id"], request.remote_addr),
        )
        db.commit()
        log_audit(db, user["user_id"], "LOGIN_SUCCESS", None, request.remote_addr)

        session.clear()
        session["user_id"] = user["user_id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role_name"]
        session.permanent = remember  # remember-me extends cookie lifetime (7 days, set in config)

        flash(f"Welcome, {user['full_name']}!", "success")
        return redirect(url_for("index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    if "user_id" in session:
        db = get_db()
        log_audit(db, session["user_id"], "LOGOUT", None, request.remote_addr)
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
