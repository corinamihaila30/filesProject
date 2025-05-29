import socket, os, threading
from shared.protocol import parse_message
from client.file_watcher import ClientWatcher

class SyncClient:
    def __init__(self, host, port, local_dir):
        self.host = host
        self.port = port
        self.local_dir = local_dir

    def start(self):
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print("[CLIENT] Connected to server")

        threading.Thread(target=self.listen, daemon=True).start()
        watcher = ClientWatcher(self.local_dir, self.socket)
        watcher.run()

    def listen(self):
        with self.socket:
            for line in self.socket.makefile():
                msg = parse_message(line.strip())
                full_path = os.path.join(self.local_dir, msg["path"])
                if msg["action"] in ["CREATE", "MODIFY"]:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'w') as f:
                        f.write(msg["content"])
                elif msg["action"] == "DELETE":
                    if os.path.exists(full_path):
                        os.remove(full_path)

if __name__ == "__main__":
    SyncClient("127.0.0.1", 5001, "./client_local").start()