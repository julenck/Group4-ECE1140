import json, os, time
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler 

class JSONFileWatcher(FileSystemEventHandler): 
    def __init__(self,path,callback): 
        self.path = os.path.abspath(path)
        self.callback = callback
        self.last_data = None
        self.last_mtime = 0
        self.load_json() 

    def load_json(self, retries=5, delay=0.2):
        for _ in range(retries): 
            try: 
                if not os.path.exists(self.path):
                    raise FileNotFoundError(self.path)
                if os.path.getsize(self.path) == 0:
                    raise ValueError("File is Empty")
                with open(self.path, "r") as f: 
                    data = json.load(f)
                self.last_data = data
                return data 
            except (json.JSONDecodeError,ValueError):
                time.sleep(delay)
        return None 
    
    def on_modified(self,event): 
        if os.path.abspath(event.src_path) == self.path: 
            mtime = os.path.getmtime(self.path)
            if mtime != self.last_mtime: 
                new_data = self.load_json()
                if new_data is not None: 
                    self.last_mtime = mtime
                    self.callback(new_data)
    


