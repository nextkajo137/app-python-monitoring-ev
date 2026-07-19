import os
import time
import random
import sqlite3
import requests
import io
import csv

from routes.charging import charging_bp
from routes.api_data import api_data_bp
from routes.auth import auth_bp, login_required
from routes.users import users_bp
from routes.profile import profile_bp
from flask import session

from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv("SECRET_KEY", "monitoring-secrey-ev-charger-key")
TARIFF_RP_PER_KWH = float(os.getenv("TARIFF_RP_PER_KWH", "1444.70"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5000"))
DB_PATH = os.getenv("DB_PATH", "ev_charger.db")
DATA_STALE_SECONDS = int(os.getenv("DATA_STALE_SECONDS", "10"))


# =========================
# HELPER
# =========================

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def rupiah(value: float) -> str:
    return "Rp {:,.0f}".format(value).replace(",", ".")


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_status(value: str) -> str:
    value = str(value or "idle").lower().strip()

    allowed = [
        "charging",
        "idle",
        "paused",
        "completed",
        "error",
        "standby"
    ]

    if value not in allowed:
        return "idle"

    return value


def status_label(status: str) -> str:
    labels = {
        "charging": "Sedang Charging",
        "idle": "Standby",
        "standby": "Standby",
        "paused": "Pause",
        "completed": "Selesai",
        "error": "Gangguan",
    }

    return labels.get(status, "Standby")


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# DATABASE INIT
# =========================

def init_db():
    conn = db_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS live_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            source TEXT,
            status TEXT,
            level_percent REAL,
            charger_power_kw REAL,
            charger_voltage_v REAL,
            pln_voltage_v REAL,
            cycle_energy_kwh REAL,
            cycle_cost_rp REAL,
            total_energy_kwh REAL,
            total_cost_rp REAL,
            cycle_started_at TEXT,
            last_update TEXT,
            last_update_ts REAL,
            user_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS charging_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            started_at TEXT,
            ended_at TEXT,
            duration_min INTEGER,
            energy_kwh REAL,
            cost_rp REAL,
            status TEXT,
            source TEXT DEFAULT 'auto',
            user_id INTEGER
        )
    """)

    cur.execute("SELECT id FROM live_state WHERE id = 1")
    row = cur.fetchone()

    if row is None:
        cur.execute("""
            INSERT INTO live_state (
                id,
                source,
                status,
                level_percent,
                charger_power_kw,
                charger_voltage_v,
                pln_voltage_v,
                cycle_energy_kwh,
                cycle_cost_rp,
                total_energy_kwh,
                total_cost_rp,
                cycle_started_at,
                last_update,
                last_update_ts,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1,
            "init",
            "idle",
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            now_str(),
            now_str(),
            time.time(),
            None
        ))

    cur.execute("PRAGMA table_info(live_state)")
    existing_cols_live = [col[1] for col in cur.fetchall()]
    if "user_id" not in existing_cols_live:
        cur.execute("ALTER TABLE live_state ADD COLUMN user_id INTEGER DEFAULT NULL")

    cur.execute("PRAGMA table_info(charging_history)")
    existing_cols = [col[1] for col in cur.fetchall()]
    if "source" not in existing_cols:
        cur.execute("ALTER TABLE charging_history ADD COLUMN source TEXT DEFAULT 'auto'")
    if "user_id" not in existing_cols:
        cur.execute("ALTER TABLE charging_history ADD COLUMN user_id INTEGER DEFAULT NULL")

    cur.execute("PRAGMA table_info(users)")
    existing_cols_users = [col[1] for col in cur.fetchall()]
    if "is_approved" not in existing_cols_users:
        cur.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 0")
        cur.execute("UPDATE users SET is_approved = 1") # Approve existing users
    if "is_active" not in existing_cols_users:
        cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    if "last_login_at" not in existing_cols_users:
        cur.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")

    # Seed 3 fixed superadmin accounts
    from werkzeug.security import generate_password_hash
    for i in range(1, 4):
        username = f"superadmin{i}"
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, is_approved, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (username, generate_password_hash("superadmin123"), "superadmin", 1, 1))

    # Hapus default admin jika sebelumnya terbuat namun belum dihapus manual (opsional, biarkan saja)
    
    conn.commit()
    conn.close()


init_db()


# =========================
# DATABASE FUNCTION
# =========================

def get_live_state() -> Dict[str, Any]:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM live_state WHERE id = 1")
    row = cur.fetchone()
    conn.close()

    if not row:
        return {}

    data = dict(row)

    cycle_cost = safe_float(data.get("cycle_energy_kwh")) * TARIFF_RP_PER_KWH
    total_cost = safe_float(data.get("total_energy_kwh")) * TARIFF_RP_PER_KWH

    data["cycle_cost_rp"] = round(cycle_cost, 0)
    data["cycle_cost_text"] = rupiah(cycle_cost)

    data["total_cost_rp"] = round(total_cost, 0)
    data["total_cost_text"] = rupiah(total_cost)

    data["status_label"] = status_label(data.get("status"))
    data["tariff_rp_per_kwh"] = TARIFF_RP_PER_KWH
    data["charger_power_w"] = round(safe_float(data.get("charger_power_kw")) * 1000, 0)

    age = time.time() - safe_float(data.get("last_update_ts"), 0)
    data["data_age_seconds"] = round(age, 1)
    data["connection_status"] = "online" if age <= DATA_STALE_SECONDS else "stale"

    return data


def insert_history_if_cycle_finished(old_state: Dict[str, Any], new_status: str, new_level: float):
    old_status = old_state.get("status")
    old_energy = safe_float(old_state.get("cycle_energy_kwh"))
    cycle_started_at = old_state.get("cycle_started_at") or now_str()
    user_id = old_state.get("user_id")

    should_finish = False

    if old_status == "charging" and new_status in ["idle", "completed", "standby"]:
        should_finish = True

    if old_status == "charging" and new_level >= 100:
        should_finish = True
        new_status = "completed"

    if not should_finish:
        return False

    if old_energy <= 0.001:
        return False

    try:
        started_dt = datetime.strptime(cycle_started_at, "%Y-%m-%d %H:%M:%S")
    except Exception:
        started_dt = datetime.now()

    ended_dt = datetime.now()
    duration_min = max(1, int((ended_dt - started_dt).total_seconds() // 60))

    cycle_cost = old_energy * TARIFF_RP_PER_KWH
    cycle_id = f"CHG-{ended_dt.strftime('%Y%m%d-%H%M%S')}"

    conn = db_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO charging_history (
            cycle_id,
            started_at,
            ended_at,
            duration_min,
            energy_kwh,
            cost_rp,
            status,
            user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cycle_id,
        cycle_started_at,
        ended_dt.strftime("%Y-%m-%d %H:%M:%S"),
        duration_min,
        round(old_energy, 4),
        round(cycle_cost, 0),
        "completed",
        user_id
    ))

    # Reset user_id in live_state
    cur.execute("UPDATE live_state SET user_id = NULL WHERE id = 1")

    conn.commit()
    conn.close()

    return True


def update_live_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    old = get_live_state()

    old_status = old.get("status", "idle")
    old_power_kw = safe_float(old.get("charger_power_kw"))
    old_cycle_energy = safe_float(old.get("cycle_energy_kwh"))
    old_total_energy = safe_float(old.get("total_energy_kwh"))
    old_level = safe_float(old.get("level_percent"))
    old_ts = safe_float(old.get("last_update_ts"), time.time())

    now_ts = time.time()
    dt = max(0, min(now_ts - old_ts, 10))

    source = str(payload.get("source", "node-red"))
    new_status = safe_status(payload.get("status", old_status))

    power_kw = safe_float(payload.get("charger_power_kw", payload.get("power_kw", old_power_kw)))
    charger_voltage = safe_float(payload.get("charger_voltage_v", payload.get("charger_voltage", 0)))
    pln_voltage = safe_float(payload.get("pln_voltage_v", payload.get("pln_voltage", 0)))
    level = safe_float(payload.get("level_percent", payload.get("level", old_level)))

    if level < 0:
        level = 0

    if level > 100:
        level = 100

    added_kwh = 0.0

    if new_status == "charging":
        added_kwh = power_kw * (dt / 3600.0)
    else:
        power_kw = 0.0

    new_cycle_energy = old_cycle_energy + added_kwh
    new_total_energy = old_total_energy + added_kwh

    cycle_started_at = old.get("cycle_started_at") or now_str()

    if old_status in ["idle", "standby", "completed"] and new_status == "charging":
        cycle_started_at = now_str()
        new_cycle_energy = 0.0

    finished = insert_history_if_cycle_finished(old, new_status, level)

    if finished:
        new_cycle_energy = 0.0
        power_kw = 0.0
        if level >= 100:
            level = 100
        new_status = "completed"

    new_cycle_cost = new_cycle_energy * TARIFF_RP_PER_KWH
    new_total_cost = new_total_energy * TARIFF_RP_PER_KWH

    user_id = payload.get("user_id", old.get("user_id"))

    conn = db_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE live_state
        SET
            source = ?,
            status = ?,
            level_percent = ?,
            charger_power_kw = ?,
            charger_voltage_v = ?,
            pln_voltage_v = ?,
            cycle_energy_kwh = ?,
            cycle_cost_rp = ?,
            total_energy_kwh = ?,
            total_cost_rp = ?,
            cycle_started_at = ?,
            last_update = ?,
            last_update_ts = ?,
            user_id = ?
        WHERE id = 1
    """, (
        source,
        new_status,
        round(level, 2),
        round(power_kw, 4),
        round(charger_voltage, 2),
        round(pln_voltage, 2),
        round(new_cycle_energy, 6),
        round(new_cycle_cost, 0),
        round(new_total_energy, 6),
        round(new_total_cost, 0),
        cycle_started_at,
        now_str(),
        now_ts,
        user_id
    ))

    conn.commit()
    conn.close()

    return get_live_state()


def get_history_items(role=None, user_id=None) -> List[Dict[str, Any]]:
    live = get_live_state()
    items = []

    if safe_float(live.get("cycle_energy_kwh")) > 0 or live.get("status") == "charging":
        started_at_str = live.get("cycle_started_at", "")
        try:
            started_dt = datetime.strptime(started_at_str, "%Y-%m-%d %H:%M:%S")
            duration_active = max(0, int((time.time() - started_dt.timestamp()) // 60))
        except Exception:
            duration_active = 0

        items.append({
            "id": None,
            "cycle_id": "CHG-ACTIVE",
            "started_at": live.get("cycle_started_at", "-"),
            "ended_at": "Sedang Berjalan",
            "duration_min": duration_active,
            "energy_kwh": round(safe_float(live.get("cycle_energy_kwh")), 4),
            "cost_rp": round(safe_float(live.get("cycle_cost_rp")), 0),
            "status": live.get("status", "idle"),
            "source": "auto"
        })

    conn = db_conn()
    cur = conn.cursor()
    
    if role == "user" and user_id is not None:
        cur.execute("""
            SELECT
                id,
                cycle_id,
                started_at,
                ended_at,
                duration_min,
                energy_kwh,
                cost_rp,
                status,
                source,
                user_id
            FROM charging_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
        """, (user_id,))
    else:
        cur.execute("""
            SELECT
                id,
                cycle_id,
                started_at,
                ended_at,
                duration_min,
                energy_kwh,
                cost_rp,
                status,
                source,
                user_id
            FROM charging_history
            ORDER BY id DESC
            LIMIT 50
        """)
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        items.append(dict(row))

    return items


def get_summary_data() -> Dict[str, Any]:
    live = get_live_state()

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total_cycles FROM charging_history")
    row = cur.fetchone()
    conn.close()

    total_cycles = row["total_cycles"] if row else 0

    return {
        "source": live.get("source", "database"),
        "total_cost_rp": live.get("total_cost_rp", 0),
        "total_cost_text": live.get("total_cost_text", rupiah(0)),
        "total_energy_kwh": round(safe_float(live.get("total_energy_kwh")), 4),
        "tariff_rp_per_kwh": TARIFF_RP_PER_KWH,
        "total_cycles": total_cycles,
        "active_cycle_energy_kwh": round(safe_float(live.get("cycle_energy_kwh")), 4),
        "active_cycle_cost_rp": round(safe_float(live.get("cycle_cost_rp")), 0),
        "active_cycle_cost_text": live.get("cycle_cost_text", rupiah(0)),
        "connection_status": live.get("connection_status", "unknown"),
        "data_age_seconds": live.get("data_age_seconds", 0),
    }


# =========================
# DUMMY SIMULATOR
# =========================

def generate_dummy_payload() -> Dict[str, Any]:
    live = get_live_state()

    level = safe_float(live.get("level_percent"))

    if live.get("status") in ["idle", "standby", "completed"]:
        level = random.uniform(10, 35)

    if level < 80:
        power_kw = random.uniform(6.0, 7.4)
    elif level < 95:
        power_kw = random.uniform(3.0, 5.5)
    else:
        power_kw = random.uniform(0.8, 2.0)

    level += power_kw * 0.035

    if level >= 100:
        level = 100
        status = "completed"
    else:
        status = "charging"

    return {
        "source": "python-dummy",
        "status": status,
        "level_percent": level,
        "charger_power_kw": power_kw,
        "charger_voltage_v": random.uniform(380, 414),
        "pln_voltage_v": random.uniform(217, 231)
    }


# =========================
# ROUTE WEB
# =========================

@app.route("/")
@login_required
def index():
    conn = db_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM users WHERE id = ?", (session.get("user_id"),))
    current_user = cur.fetchone()
    
    users_list = []
    role = session.get("role")
    if role in ["admin", "superadmin"]:
        if role == "superadmin":
            cur.execute("SELECT id, username, role, is_approved, is_active, last_login_at FROM users WHERE role IN ('user', 'admin')")
        else:
            cur.execute("SELECT id, username, role, is_approved, is_active, last_login_at FROM users WHERE role = 'user'")
        users_list = cur.fetchall()
        
    conn.close()

    return render_template(
        "index.html",
        tariff=TARIFF_RP_PER_KWH,
        node_red_url="POST /api/ingest",
        current_user=current_user,
        users_list=users_list
    )


# =========================
# API UNTUK DASHBOARD
# =========================


@app.route("/api/live")
def api_live():
    try:
        # 1. Tarik data realtime dari Node-RED
        response = requests.get("http://127.0.0.1:1880/api/charger/live")

        if response.status_code == 200:
            nr_data = response.json()
            
            # 2. SINKRONISASI: Update data Node-RED ke SQLite biar kWh & History jalan
            db_data = update_live_from_payload(nr_data)
            
            # 3. Gabungin data Node-RED dengan hasil hitungan DB (kWh & Biaya)
            nr_data["cycle_energy_kwh"] = db_data.get("cycle_energy_kwh", 0)
            nr_data["cycle_cost_rp"] = db_data.get("cycle_cost_rp", 0)
            nr_data["cycle_cost_text"] = db_data.get("cycle_cost_text", "Rp 0")
            nr_data["timestamp"] = db_data.get("last_update", now_str())
            
            return jsonify(nr_data)

        return jsonify({
            "error": "Node-RED API gagal"
        }), 500

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/api/history")
@login_required
def api_history():
    role = session.get("role")
    user_id = session.get("user_id")
    return jsonify({
        "source": "sqlite",
        "items": get_history_items(role=role, user_id=user_id)
    })


@app.route("/api/summary")
def api_summary():
    return jsonify(get_summary_data())

@app.route("/api/export/csv")
def api_export_csv():

    selected_date = request.args.get("date")
    role = session.get("role")
    user_id = session.get("user_id")

    conn = db_conn()
    cur = conn.cursor()

    if selected_date:
        if role == "user" and user_id is not None:
            cur.execute("""
                SELECT cycle_id, started_at, ended_at,
                       duration_min, energy_kwh,
                       cost_rp, status
                FROM charging_history
                WHERE started_at LIKE ? AND user_id = ?
                ORDER BY id DESC
            """, (f"{selected_date}%", user_id))
        else:
            cur.execute("""
                SELECT cycle_id, started_at, ended_at,
                       duration_min, energy_kwh,
                       cost_rp, status
                FROM charging_history
                WHERE started_at LIKE ?
                ORDER BY id DESC
            """, (f"{selected_date}%",))

    else:
        if role == "user" and user_id is not None:
            cur.execute("""
                SELECT cycle_id, started_at, ended_at,
                       duration_min, energy_kwh,
                       cost_rp, status
                FROM charging_history
                WHERE user_id = ?
                ORDER BY id DESC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT cycle_id, started_at, ended_at,
                       duration_min, energy_kwh,
                       cost_rp, status
                FROM charging_history
                ORDER BY id DESC
            """)

    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        'ID Siklus',
        'Waktu Mulai',
        'Waktu Selesai',
        'Durasi (Menit)',
        'Energi (kWh)',
        'Biaya (Rp)',
        'Status'
    ])

    for row in rows:
        writer.writerow([
            row['cycle_id'],
            row['started_at'],
            row['ended_at'],
            row['duration_min'],
            row['energy_kwh'],
            row['cost_rp'],
            str(row['status']).upper()
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    filename = "riwayat_charging.csv"

    if selected_date:
        filename = f"riwayat_charging_{selected_date}.csv"

    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename={filename}"

    return response

# =========================
# API INPUT DARI NODE-RED
# =========================

@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    payload = request.get_json(silent=True) or {}

    data = update_live_from_payload(payload)

    return jsonify({
        "ok": True,
        "message": "Data received",
        "data": data
    })


# =========================
# API CONTROL BUTTON
# =========================

@app.route("/api/control", methods=["POST"])
@login_required
def api_control():
    payload = request.get_json(silent=True) or {}
    
    action = payload.get("action")
    if action == "start":
        payload["user_id"] = session.get("user_id")
        # Ensure we set user_id in live_state directly
        update_live_from_payload({"status": "charging", "user_id": session.get("user_id")})

    try:
        response = requests.post(
            "http://127.0.0.1:1880/api/charger/control",
            json=payload
        )

        return jsonify(response.json())

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# =========================
# API DUMMY UNTUK TEST MANUAL
# =========================

@app.route("/api/dummy-push")
def api_dummy_push():
    payload = generate_dummy_payload()
    data = update_live_from_payload(payload)

    return jsonify({
        "ok": True,
        "message": "Dummy data pushed",
        "payload": payload,
        "data": data
    })


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "db_path": DB_PATH,
        "tariff_rp_per_kwh": TARIFF_RP_PER_KWH,
        "time": now_str()
    })


# =========================
# REGISTER BLUEPRINT (auth, charging CRUD, data API publik)
# =========================

app.register_blueprint(auth_bp)
app.register_blueprint(users_bp, url_prefix="/users")
app.register_blueprint(profile_bp, url_prefix="/profile")
app.register_blueprint(charging_bp)
app.register_blueprint(api_data_bp)


# =========================
# ERROR HANDLER
# =========================

@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403

@app.errorhandler(401)
def unauthorized(e):
    return render_template("errors/403.html"), 401


@app.errorhandler(500)
def internal_error(e):
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=True)