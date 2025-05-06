
# logger.py
import json
import os
from datetime import datetime

LOG_FILE = "conversations.json"

def log_interaction(user_id, user_msg, bot_reply):
    now = datetime.utcnow().isoformat()
    entry = {
        "timestamp": now,
        "user_id": user_id,
        "user_message": user_msg,
        "bot_reply": bot_reply
    }

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([entry], f, indent=2)
    else:
        with open(LOG_FILE, "r+") as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
