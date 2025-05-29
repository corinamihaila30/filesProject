from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from shared.protocol import create_message

class ServerWatcher(FileSystemEventHandler):
    def __init__(self, path, server):
        self.path = path
        self.server = server

    def on_modified(self, event):
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self.path)
            with open(event.src_path, 'r') as f:
                msg = create_message("MODIFY", rel, f.read())
                self.server.broadcast(msg)

    def on_created(self, event):
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self.path)
            with open(event.src_path, 'r') as f:
                msg = create_message("CREATE", rel, f.read())
                self.server.broadcast(msg)

    def on_deleted(self, event):
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self.path)
            msg = create_message("DELETE", rel)
            self.server.broadcast(msg)

    def run(self):
        observer = Observer()
        observer.schedule(self, self.path, recursive=True)
        observer.start()
        observer.join()