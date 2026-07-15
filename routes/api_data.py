from flask import Blueprint, render_template
import requests

api_data_bp = Blueprint('api_data', __name__)
NODE_RED_BASE = "http://127.0.0.1:1880/api/charger"

@api_data_bp.route('/data-api')
def data_api_page():
    live_data, history_data, summary_data, error = {}, [], {}, None
    try:
        r = requests.get(f"{NODE_RED_BASE}/live", timeout=5)
        live_data = r.json() if r.status_code == 200 else {}
    except Exception as e:
        error = str(e)
    try:
        r = requests.get(f"{NODE_RED_BASE}/history", timeout=5)
        history_data = r.json() if r.status_code == 200 else []
    except Exception:
        pass
    try:
        r = requests.get(f"{NODE_RED_BASE}/summary", timeout=5)
        summary_data = r.json() if r.status_code == 200 else {}
    except Exception:
        pass

    return render_template('api_data.html', live_data=live_data,
                            history_data=history_data, summary_data=summary_data, error=error)