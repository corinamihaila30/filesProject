# client.py
import os
import socket
import threading
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

HOST = '127.0.0.1'
PORT = 9000
CLIENT_DIR = sys.argv[1] if len(sys.argv) > 1 else './client_data'

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, base_path, send_func):
        super().__init__()
        self.base_path = base_path
        self.send_func = send_func

    def dispatch(self, event):
        if event.is_directory:
            return
        rel_path = os.path.relpath(event.src_path, self.base_path)
        if event.event_type in ('created', 'modified'):
            try:
                with open(event.src_path, 'r', errors='ignore') as f:
                    content = f.read()
                self.send_func({'op': 'modify', 'path': rel_path, 'content': content})
            except Exception as e:
                print(f"Read error: {e}")
        elif event.event_type == 'deleted':
            self.send_func({'op': 'delete', 'path': rel_path})
        elif event.event_type == 'moved':
            dest_rel = os.path.relpath(event.dest_path, self.base_path)
            self.send_func({'op': 'rename', 'old_path': rel_path, 'path': dest_rel})

class SyncClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = threading.Lock()

    def start(self):
        os.makedirs(CLIENT_DIR, exist_ok=True)
        self.sock.connect((HOST, PORT))
        threading.Thread(target=self.listen_server, daemon=True).start()

        handler = FileChangeHandler(CLIENT_DIR, self.send_change)
        observer = Observer()
        observer.schedule(handler, CLIENT_DIR, recursive=True)
        observer.start()
        print("Client connected and listening...")

        while True:
            time.sleep(1)

    def listen_server(self):
        buffer = ""
        while True:
            data = self.sock.recv(4096)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                change = json.loads(line)
                if change['op'] == 'sync':
                    self.sync_initial(change['files'])
                else:
                    self.apply_change(CLIENT_DIR, change)

    def send_change(self, change):
        with self.lock:
            try:
                self.sock.sendall((json.dumps(change) + "\n").encode())
            except Exception as e:
                print(f"Send error: {e}")

    def sync_initial(self, file_map):
        for path, content in file_map.items():
            full_path = os.path.join(CLIENT_DIR, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)

    def apply_change(self, base_path, change):
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

if __name__ == "__main__":
    SyncClient().start()
