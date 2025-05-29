from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import hashlib
from shared.protocol import create_message

class ClientWatcher(FileSystemEventHandler):
    def __init__(self, path, socket):
        self.path = path
        self.socket = socket
        self.ignore_next = set()
        self.last_hashes = {}

    def _should_ignore(self, rel):
        return (
            rel.endswith("~")
            or os.path.basename(rel).startswith(".")
            or ".tmp" in rel
            or rel.endswith(".swp")
            or rel.endswith(".lock")
        )

    def _compute_hash(self, content):
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def on_modified(self, event):
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self.path)
            if self._should_ignore(rel):
                return

            try:
                with open(event.src_path, 'r') as f:
                    new_content = f.read()

                new_hash = self._compute_hash(new_content)
                if self.last_hashes.get(rel) == new_hash:
                    return

                msg = create_message("MODIFY", rel, new_content)
                self.socket.sendall((msg + '\n').encode())
                self.last_hashes[rel] = new_hash

            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[ClientWatcher] Error on modified: {e}")

    def on_created(self, event):
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self.path)
            if self._should_ignore(rel):
                return

            try:
                if os.path.getsize(event.src_path) == 0:
                    return

                with open(event.src_path, 'r') as f:
                    new_content = f.read()

                new_hash = self._compute_hash(new_content)
                msg = create_message("CREATE", rel, new_content)
                self.socket.sendall((msg + '\n').encode())
                self.last_hashes[rel] = new_hash

            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[ClientWatcher] Error on created: {e}")

    def on_deleted(self, event):
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self.path)
            if self._should_ignore(rel):
                return

            msg = create_message("DELETE", rel)
            self.socket.sendall((msg + '\n').encode())
            self.last_hashes.pop(rel, None)

    def mark_as_synced(self, rel_path):
        try:
            abs_path = os.path.join(self.path, rel_path)
            if os.path.exists(abs_path):
                with open(abs_path, 'r') as f:
                    content = f.read()
                    self.last_hashes[rel_path] = self._compute_hash(content)
        except Exception as e:
            print(f"[ClientWatcher] Error caching synced hash: {e}")

    def run(self):
        observer = Observer()
        observer.schedule(self, self.path, recursive=True)
        observer.start()
        observer.join()