import os
import sqlite3
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "ev_charger.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_charging():
    conn = get_db()
    rows = conn.execute("SELECT * FROM charging_history ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def get_charging_by_id(charging_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM charging_history WHERE id = ?", (charging_id,)).fetchone()
    conn.close()
    return row

def create_charging(data):
    cycle_id = f"MAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    conn = get_db()
    conn.execute("""
        INSERT INTO charging_history
        (cycle_id, started_at, ended_at, duration_min, energy_kwh, cost_rp, status, source, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?)
    """, (
        cycle_id, data['started_at'], data.get('ended_at'),
        data.get('duration_min'), data['energy_kwh'], data['cost_rp'], data['status'],
        data.get('user_id')
    ))
    conn.commit()
    conn.close()

def update_charging(charging_id, data):
    conn = get_db()
    # guard: hanya boleh update kalau source = manual
    row = conn.execute("SELECT source FROM charging_history WHERE id = ?", (charging_id,)).fetchone()
    if row is None or row["source"] != "manual":
        conn.close()
        return False

    conn.execute("""
        UPDATE charging_history SET
            started_at = ?, ended_at = ?, duration_min = ?,
            energy_kwh = ?, cost_rp = ?, status = ?
        WHERE id = ? AND source = 'manual'
    """, (
        data['started_at'], data.get('ended_at'),
        data.get('duration_min'), data['energy_kwh'], data['cost_rp'],
        data['status'], charging_id
    ))
    conn.commit()
    conn.close()
    return True

def delete_charging(charging_id):
    conn = get_db()
    row = conn.execute("SELECT source FROM charging_history WHERE id = ?", (charging_id,)).fetchone()
    if row is None or row["source"] != "manual":
        conn.close()
        return False

    conn.execute("DELETE FROM charging_history WHERE id = ? AND source = 'manual'", (charging_id,))
    conn.commit()
    conn.close()
    return True