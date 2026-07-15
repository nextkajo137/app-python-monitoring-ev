from flask import Blueprint, request, jsonify
from datetime import datetime
from models.charging import (
    get_charging_by_id, create_charging, update_charging, delete_charging
)

charging_bp = Blueprint('charging', __name__, url_prefix='/charging')


def parse_datetime_local(value):
    if not value:
        return None
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def compute_duration(started_at, ended_at):
    if not started_at or not ended_at:
        return None
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        s = datetime.strptime(started_at, fmt)
        e = datetime.strptime(ended_at, fmt)
        diff = int((e - s).total_seconds() // 60)
        return max(diff, 0)
    except Exception:
        return None


@charging_bp.route('/item/<int:charging_id>')
def get_item(charging_id):
    item = get_charging_by_id(charging_id)
    if item is None:
        return jsonify({"ok": False, "error": "Data tidak ditemukan"}), 404
    if item['source'] != 'manual':
        return jsonify({"ok": False, "error": "Data otomatis tidak bisa diedit"}), 403
    return jsonify({"ok": True, "item": dict(item)})


@charging_bp.route('/add', methods=['POST'])
def add_charging():
    payload = request.get_json(silent=True) or {}

    started_at = parse_datetime_local(payload.get('started_at'))
    ended_at = parse_datetime_local(payload.get('ended_at'))

    if not started_at:
        return jsonify({"ok": False, "error": "Waktu mulai wajib diisi"}), 400

    form_data = {
        'started_at': started_at,
        'ended_at': ended_at,
        'duration_min': compute_duration(started_at, ended_at),
        'energy_kwh': float(payload.get('energy_kwh') or 0),
        'cost_rp': float(payload.get('cost_rp') or 0),
        'status': payload.get('status', 'completed')
    }
    create_charging(form_data)
    return jsonify({"ok": True, "message": "Data charging manual berhasil ditambahkan"})


@charging_bp.route('/edit/<int:charging_id>', methods=['POST'])
def edit_charging(charging_id):
    item = get_charging_by_id(charging_id)
    if item is None:
        return jsonify({"ok": False, "error": "Data tidak ditemukan"}), 404
    if item['source'] != 'manual':
        return jsonify({"ok": False, "error": "Data otomatis tidak bisa diedit"}), 403

    payload = request.get_json(silent=True) or {}
    started_at = parse_datetime_local(payload.get('started_at'))
    ended_at = parse_datetime_local(payload.get('ended_at'))

    if not started_at:
        return jsonify({"ok": False, "error": "Waktu mulai wajib diisi"}), 400

    form_data = {
        'started_at': started_at,
        'ended_at': ended_at,
        'duration_min': compute_duration(started_at, ended_at),
        'energy_kwh': float(payload.get('energy_kwh') or 0),
        'cost_rp': float(payload.get('cost_rp') or 0),
        'status': payload.get('status', 'completed')
    }
    ok = update_charging(charging_id, form_data)
    if not ok:
        return jsonify({"ok": False, "error": "Gagal memperbarui data"}), 400
    return jsonify({"ok": True, "message": "Data charging berhasil diperbarui"})


@charging_bp.route('/delete/<int:charging_id>', methods=['POST'])
def delete_charging_route(charging_id):
    item = get_charging_by_id(charging_id)
    if item is None:
        return jsonify({"ok": False, "error": "Data tidak ditemukan"}), 404
    if item['source'] != 'manual':
        return jsonify({"ok": False, "error": "Data otomatis tidak bisa dihapus"}), 403
    delete_charging(charging_id)
    return jsonify({"ok": True})