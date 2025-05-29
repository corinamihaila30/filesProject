import socket, threading, os
from server.file_watcher import ServerWatcher
from server.client_handler import ClientHandler

class SyncServer:
    def __init__(self, host, port, shared_dir):
        self.host = host
        self.port = port
        self.shared_dir = shared_dir
        self.clients = []
        self.lock = threading.Lock()

    def broadcast(self, message, sender=None):
        with self.lock:
            for client in self.clients:
                if client != sender:
                    client.send(message)

    def start(self):
        if not os.path.exists(self.shared_dir):
            os.makedirs(self.shared_dir)

        watcher = ServerWatcher(self.shared_dir, self)
        threading.Thread(target=watcher.run, daemon=True).start()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"[SERVER] Listening on {self.host}:{self.port}")

            while True:
                client_socket, addr = s.accept()
                print(f"[SERVER] Client connected: {addr}")
                handler = ClientHandler(client_socket, self, self.shared_dir)
                with self.lock:
                    self.clients.append(handler)
                threading.Thread(target=handler.handle).start()

if __name__ == "__main__":
    SyncServer("127.0.0.1", 5001, "./server_shared").start()