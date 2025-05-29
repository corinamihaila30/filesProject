import os
from shared.protocol import parse_message

class ClientHandler:
    def __init__(self, socket, server, base_path):
        self.socket = socket
        self.server = server
        self.base_path = base_path

    def send(self, message):
        try:
            self.socket.sendall((message + '\n').encode())
        except:
            pass

    def handle(self):
        with self.socket:
            try:
                for line in self.socket.makefile():
                    msg = parse_message(line.strip())
                    full_path = os.path.join(self.base_path, msg["path"])

                    if msg["action"] in ["CREATE", "MODIFY"]:
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        with open(full_path, 'w') as f:
                            f.write(msg["content"])
                    elif msg["action"] == "DELETE":
                        if os.path.exists(full_path):
                            os.remove(full_path)

                    self.server.broadcast(line.strip(), sender=self)
            except Exception as e:
                print(f"[SERVER] Client handler error: {e}")