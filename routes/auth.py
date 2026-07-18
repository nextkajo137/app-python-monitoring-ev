import sqlite3
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os

auth_bp = Blueprint("auth", __name__)

DB_PATH = os.getenv("DB_PATH", "ev_charger.db")

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("auth.login"))
        if session.get("role") not in ["admin", "superadmin"]:
            flash("Anda tidak memiliki akses (Admin only).", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "error")
            return redirect(url_for("auth.login"))
        if session.get("role") != "superadmin":
            flash("Anda tidak memiliki akses (Superadmin only).", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username dan password tidak boleh kosong.", "error")
            return redirect(url_for("auth.login"))

        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            if not user["is_approved"]:
                conn.close()
                flash("Akun Anda belum disetujui. Silakan tunggu konfirmasi Admin.", "error")
                return redirect(url_for("auth.login"))
                
            if not user["is_active"]:
                conn.close()
                flash("Akun Anda telah dinonaktifkan.", "error")
                return redirect(url_for("auth.login"))

            from datetime import datetime
            cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]))
            conn.commit()
            conn.close()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Selamat datang, {username}!", "success")
            return redirect(url_for("index"))
        else:
            conn.close()
            flash("Username atau password salah.", "error")

    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "user") # Biarkan form hidden atau select

        if not username or not password:
            flash("Username dan password tidak boleh kosong.", "error")
            return redirect(url_for("auth.register"))
            
        if password != confirm_password:
            flash("Konfirmasi password tidak cocok.", "error")
            return redirect(url_for("auth.register"))
            
        if role not in ["user", "admin"]:
            role = "user"

        conn = db_conn()
        cur = conn.cursor()
        
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            conn.close()
            flash("Username sudah digunakan. Silakan pilih yang lain.", "error")
            return redirect(url_for("auth.register"))
            
        password_hash = generate_password_hash(password)
        
        try:
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                        (username, password_hash, role))
            conn.commit()
            flash("Registrasi berhasil! Akun Anda sedang menunggu persetujuan.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"Terjadi kesalahan: {e}", "error")
        finally:
            conn.close()

    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Anda berhasil logout.", "success")
    return redirect(url_for("auth.login"))
