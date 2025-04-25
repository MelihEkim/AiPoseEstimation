import json
from datetime import datetime

def log_session(name, reps):
    data = {
        "exercise": name,
        "reps": reps,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open("sessions.json", "r") as f:
            sessions = json.load(f)
    except FileNotFoundError:
        sessions = []

    sessions.append(data)

    with open("sessions.json", "w") as f:
        json.dump(sessions, f, indent=4)
