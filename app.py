import functools
import os
import re
import sqlite3

from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import generate_user_id, get_db, init_db, seed_db

app = Flask(__name__)

# SECRET_KEY signs the session cookie. Set a real, random value via the
# SECRET_KEY environment variable in any non-local environment — this
# fallback is for local development only and is NOT safe for production.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key-change-me")

with app.app_context():
    init_db()
    seed_db()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def format_member_since(created_at):
    dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%B %d, %Y")


def get_transactions(conn, user_id):
    """Return this user's expenses, most recent date first."""
    query = (
        "SELECT id, amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC, id DESC"
    )
    return conn.execute(query, (user_id,)).fetchall()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
@app.route("/<user_id>")
def landing(user_id=None):
    if user_id is None:
        if session.get("user_id"):
            return redirect(url_for("landing", user_id=session["user_id"]))
        return render_template("landing.html")

    if session.get("user_id") != user_id:
        return redirect(url_for("login"))

    conn = get_db()
    try:
        transactions = get_transactions(conn, user_id)
        stats = get_summary_stats(conn, user_id)
        categories = get_category_breakdown(conn, user_id)
    finally:
        conn.close()

    return render_template(
        "dashboard.html",
        transactions=transactions, stats=stats, categories=categories,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing", user_id=session["user_id"]))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name:
        return render_template("register.html", error="Name is required.")
    if not email:
        return render_template("register.html", error="Email is required.")
    if not password:
        return render_template("register.html", error="Password is required.")
    if not confirm_password:
        return render_template("register.html", error="Confirm password is required.")
    if not EMAIL_RE.match(email):
        return render_template("register.html", error="Enter a valid email address.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(email) = ?", (email,)
        ).fetchone()
        if existing:
            return render_template("register.html", error="An account with that email already exists.")

        password_hash = generate_password_hash(password)
        user_id = generate_user_id()
        try:
            conn.execute(
                "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, name, email, password_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="An account with that email already exists.")
    finally:
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing", user_id=session["user_id"]))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Invalid email or password.")

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE LOWER(email) = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("landing", user_id=user["id"]))


def get_summary_stats(conn, user_id):
    """Return {'total': float, 'count': int} for this user's expenses."""
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return {"total": row["total"], "count": row["count"]}


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


def get_category_breakdown(conn, user_id):
    """Return per-category totals for this user, highest spend first."""
    query = """
        SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses
        WHERE user_id = ? GROUP BY category ORDER BY total DESC
    """
    return conn.execute(query, (user_id,)).fetchall()


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        member_since = format_member_since(user["created_at"])

        if request.method == "GET":
            return render_template(
                "profile.html",
                name=user["name"], email=user["email"], member_since=member_since,
            )

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not name:
            return render_template("profile.html", name=name, email=email,
                                    member_since=member_since, info_error="Name is required.")
        if not email:
            return render_template("profile.html", name=name, email=email,
                                    member_since=member_since, info_error="Email is required.")
        if not EMAIL_RE.match(email):
            return render_template("profile.html", name=name, email=email,
                                    member_since=member_since, info_error="Enter a valid email address.")

        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(email) = ? AND id != ?",
            (email, session["user_id"]),
        ).fetchone()
        if existing:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    info_error="An account with that email already exists.")

        try:
            conn.execute("UPDATE users SET name = ?, email = ? WHERE id = ?",
                         (name, email, session["user_id"]))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    info_error="An account with that email already exists.")

        session["user_name"] = name
        return render_template("profile.html", name=name, email=email, member_since=member_since,
                                info_success="Your details have been updated.")
    finally:
        conn.close()


@app.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, email, password_hash, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
        name, email = user["name"], user["email"]
        member_since = format_member_since(user["created_at"])

        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_new_password = request.form.get("confirm_new_password", "")

        if not current_password:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    password_error="Current password is required.")
        if not check_password_hash(user["password_hash"], current_password):
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    password_error="Current password is incorrect.")
        if not new_password:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    password_error="New password is required.")
        if not confirm_new_password:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    password_error="Confirm new password is required.")
        if len(new_password) < 8:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    password_error="Password must be at least 8 characters.")
        if new_password != confirm_new_password:
            return render_template("profile.html", name=name, email=email, member_since=member_since,
                                    password_error="Passwords do not match.")

        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (generate_password_hash(new_password), session["user_id"]))
        conn.commit()

        return render_template("profile.html", name=name, email=email, member_since=member_since,
                                password_success="Your password has been updated.")
    finally:
        conn.close()


@app.route("/expenses/add")
@login_required
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
@login_required
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
@login_required
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
