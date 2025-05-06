
# memory.py
from collections import defaultdict, deque

# Memoria temporanea per ogni utente (ultimi n scambi)
USER_MEMORY = defaultdict(lambda: deque(maxlen=10))

def add_to_memory(user_id, role, content):
    USER_MEMORY[user_id].append({"role": role, "content": content})

def get_memory(user_id):
    return list(USER_MEMORY[user_id])

def reset_memory(user_id):
    USER_MEMORY[user_id].clear()
