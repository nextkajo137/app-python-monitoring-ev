from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import db_conn, admin_required

users_bp = Blueprint("users", __name__)

@users_bp.route("/control")
@admin_required
def control():
    conn = db_conn()
    cur = conn.cursor()
    
    role = session.get("role")
    if role == "superadmin":
        cur.execute("SELECT id, username, role, is_approved, is_active, last_login_at FROM users WHERE role IN ('user', 'admin')")
    else:
        cur.execute("SELECT id, username, role, is_approved, is_active, last_login_at FROM users WHERE role = 'user'")
        
    users_list = cur.fetchall()
    conn.close()
    
    return render_template("users/control.html", users=users_list)

@users_bp.route("/approve/<int:user_id>", methods=["POST"])
@admin_required
def approve(user_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    
    if not user:
        conn.close()
        flash("User tidak ditemukan.", "error")
        return redirect(url_for("index", tab="users"))
        
    role = session.get("role")
    if role == "admin" and user["role"] != "user":
        conn.close()
        flash("Admin hanya bisa menyetujui akun user biasa.", "error")
        return redirect(url_for("index", tab="users"))
        
    cur.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("Akun berhasil disetujui.", "success")
    return redirect(url_for("index", tab="users"))

@users_bp.route("/toggle_active/<int:user_id>", methods=["POST"])
@admin_required
def toggle_active(user_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT role, is_active FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    
    if not user:
        conn.close()
        flash("User tidak ditemukan.", "error")
        return redirect(url_for("index", tab="users"))
        
    role = session.get("role")
    if role == "admin" and user["role"] != "user":
        conn.close()
        flash("Admin hanya bisa mengatur akun user biasa.", "error")
        return redirect(url_for("index", tab="users"))
        
    new_status = 0 if user["is_active"] else 1
    cur.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
    conn.commit()
    conn.close()
    
    status_text = "diaktifkan" if new_status else "dinonaktifkan"
    flash(f"Akun berhasil {status_text}.", "success")
    return redirect(url_for("index", tab="users"))

@users_bp.route("/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete(user_id):
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    
    if not user:
        conn.close()
        flash("User tidak ditemukan.", "error")
        return redirect(url_for("index", tab="users"))
        
    role = session.get("role")
    if role == "admin" and user["role"] != "user":
        conn.close()
        flash("Admin hanya bisa menghapus akun user biasa.", "error")
        return redirect(url_for("index", tab="users"))
        
    if user["role"] == "superadmin":
        conn.close()
        flash("Akun superadmin tidak dapat dihapus.", "error")
        return redirect(url_for("index", tab="users"))
        
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("Akun berhasil dihapus.", "success")
    return redirect(url_for("index", tab="users"))
