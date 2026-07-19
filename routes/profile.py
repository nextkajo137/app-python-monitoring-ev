from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import db_conn, login_required
from werkzeug.security import generate_password_hash, check_password_hash

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    conn = db_conn()
    cur = conn.cursor()
    
    user_id = session.get("user_id")
    
    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
        
        if not check_password_hash(user["password_hash"], current_password):
            flash("Password saat ini salah.", "error")
            conn.close()
            return redirect(url_for("index", tab="profile"))
            
        # Check username uniqueness if changed
        if new_username and new_username != user["username"]:
            cur.execute("SELECT id FROM users WHERE username = ? AND id != ?", (new_username, user_id))
            if cur.fetchone():
                flash("Username sudah digunakan orang lain.", "error")
                conn.close()
                return redirect(url_for("index", tab="profile"))
            
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user_id))
            session["username"] = new_username
            flash("Username berhasil diupdate.", "success")
            
        # Update password if provided
        if new_password:
            if new_password != confirm_password:
                flash("Konfirmasi password baru tidak cocok.", "error")
                conn.close()
                return redirect(url_for("index", tab="profile"))
                
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), user_id))
            flash("Password berhasil diupdate.", "success")
            
        conn.commit()
        conn.close()
        return redirect(url_for("index", tab="profile"))
        
    cur.execute("SELECT username, role, last_login_at FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    
    return render_template("users/profile.html", user=user)
