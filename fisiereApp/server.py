# server.py
import os
import socket
import threading
import json

HOST = '127.0.0.1'
PORT = 9000
SERVER_DIR = './server_data'

def scan_directory(base_path):
    file_map = {}
    for root, _, files in os.walk(base_path):
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), base_path)
            with open(os.path.join(root, f), 'rb') as file:
                file_map[rel_path] = file.read().decode('utf-8', errors='ignore')
    return file_map

def apply_change(base_path, change):
    path = os.path.join(base_path, change['path'])
    if change['op'] in ('create', 'modify'):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(change['content'])
    elif change['op'] == 'delete' and os.path.exists(path):
        os.remove(path)
    elif change['op'] == 'rename':
        old_path = os.path.join(base_path, change['old_path'])
        os.rename(old_path, path)

class SyncServer:
    def __init__(self):
        self.clients = []
        self.lock = threading.Lock()

    def start(self):
        os.makedirs(SERVER_DIR, exist_ok=True)
        threading.Thread(target=self.run_server, daemon=True).start()
        print("Server running on", HOST, PORT)
        while True:
            pass  # keep main thread alive

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            while True:
                conn, _ = s.accept()
                with self.lock:
                    self.clients.append(conn)
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def broadcast(self, msg, sender):
        with self.lock:
            for c in list(self.clients):
                if c != sender:
                    try:
                        c.sendall((json.dumps(msg) + "\n").encode())
                    except:
                        self.clients.remove(c)

    def handle_client(self, conn):
        try:
            initial_data = scan_directory(SERVER_DIR)
            conn.sendall((json.dumps({'op': 'sync', 'files': initial_data}) + "\n").encode())
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                for line in data.decode().splitlines():
                    change = json.loads(line)
                    apply_change(SERVER_DIR, change)
                    self.broadcast(change, conn)
        finally:
            with self.lock:
                if conn in self.clients:
                    self.clients.remove(conn)
            conn.close()

if __name__ == "__main__":
    SyncServer().start()
