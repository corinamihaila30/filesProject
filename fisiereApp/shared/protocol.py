import json

def create_message(action, path, content=None):
    return json.dumps({"action": action, "path": path, "content": content})

def parse_message(message):
    return json.loads(message)