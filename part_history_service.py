from flask import Flask, jsonify, request
import requests
import json
import os
import uuid

app = Flask(__name__)

HISTORY_FILE = "parts_history.json"

AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', "http://localhost:5001")
AUTH_VERIFY_ENDPOINT = f"{AUTH_SERVICE_URL}/verify"

def load_history():
    '''Load parts history file into a dict: { user_id: [ {saved_part}, ... ] }'''
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_history(data):
    '''Persist parts history into a json file'''
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_authenticated_user():
    '''
    Pulls the bearer token from authorization header and ask Auth service to verify it
    '''
    auth_header = request.headers.get('Authorization')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header.split(" ", 1)[1]

    try:
        response = requests.post(
            AUTH_VERIFY_ENDPOINT,
            json={"token": token},
            timeout=5,
        )
    except requests.exceptions.RequestException:
        # Auth service unreachable - failed closed
        return None

    if response.status_code != 200:
        return None

    body = response.json()
    return body.get("user_id")

@app.route('/history', methods=['GET'])
def list_saved_parts():
    '''
    List the logged-in user's saved parts.
    '''
    user_id = get_authenticated_user()
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    history = load_history()
    return jsonify(history.get(user_id, [])), 200

@app.route('/history', methods=['POST'])
def save_part():
    '''
    Save a particular part in the history file for later purchase.
    Expected JSON body with {part_id, name, price, model}
    '''
    user_id = get_authenticated_user()
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"message": "Request body must be JSON"}), 400

    required_fields = ["part_id", "name"]
    missing = [
        field
        for field in required_fields
        if field not in payload
    ]
    if missing:
        return jsonify({"message": f"Missing {', '.join(missing)}"}), 400

    history = load_history()
    user_history = history.setdefault(user_id, [])

    # Avoid saving the same part twice
    already_saved = any(part["part_id"] == payload["part_id"] for part in user_history)
    if already_saved:
        return jsonify({"message": "Part already saved"}), 409

    saved_part = {
        'id': str(uuid.uuid4()),
        'part_id': payload["part_id"],
        'name': payload["name"],
        'price': payload["price"],
        'model': payload["model", ""]
    }
    user_history.append(saved_part)
    save_history(history)

    return jsonify(saved_part), 201

@app.route('/history/<saved_id>', methods=['DELETE'])
def delete_saved_part(saved_id):
    '''Delete a particular part from logged-in user's saved parts by its saved id'''
    user_id = get_authenticated_user()
    if not user_id:
        return jsonify({"message": "Unauthorized"}), 401

    history = load_history()
    user_history = history.get(user_id, [])

    remaining = [
        part
        for part in user_history
        if part['id'] != saved_id
    ]

    if len(remaining) == len(user_history):
        return jsonify({"message": "Saved part not found"}), 404

    history[user_id] = remaining
    save_history(history)

    return jsonify({"message": "Part deleted from history"}), 200

if __name__ == '__main__':
    app.run(port=5003, debug=True)