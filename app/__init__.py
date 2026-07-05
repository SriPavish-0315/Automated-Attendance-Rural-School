from datetime import timedelta
from flask import Flask
from config import Config
from app.db import close_db, init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(
        minutes=app.config["PERMANENT_SESSION_LIFETIME_MINUTES"]
    )

    init_db(app)
    app.teardown_appcontext(close_db)

    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.coordinator.routes import coordinator_bp
    from app.teacher.routes import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(coordinator_bp)
    app.register_blueprint(teacher_bp)

    from flask import redirect, url_for, session

    @app.route("/")
    def index():
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        role = session.get("role")
        if role == "Administrator":
            return redirect(url_for("admin.dashboard"))
        if role == "Coordinator":
            return redirect(url_for("coordinator.dashboard"))
        return redirect(url_for("teacher.dashboard"))

    @app.errorhandler(403)
    def forbidden(e):
        return "403 Forbidden - you don't have access to this page.", 403

    @app.errorhandler(404)
    def not_found(e):
        return "404 Not Found.", 404

    return app
