import os
import pickle
from cryptography.fernet import Fernet
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID

class File:
    def __init__(self, name, content=b'', encrypted=False, key=None, owner='user', permissions=0o644):
        self.name = name
        self.encrypted = encrypted
        self._key = key or (Fernet.generate_key() if encrypted else None)
        self._fernet = Fernet(self._key) if encrypted else None
        self._data = self._fernet.encrypt(content) if encrypted else content
        self.owner = owner
        self.permissions = permissions  # rw-r--r--
        self.metadata = {}

    def read(self):
        return self._fernet.decrypt(self._data) if self.encrypted else self._data

    def write(self, data):
        self._data = self._fernet.encrypt(data) if self.encrypted else data

class Directory:
    def __init__(self, name, owner='user', permissions=0o755):
        self.name = name
        self.entries = {}  # name: File or Directory
        self.owner = owner
        self.permissions = permissions  # rwxr-xr-x

class FileSystem:
    SAVE_PATH = 'fs_state.pkl'

    def __init__(self):
        self.root = Directory('/')
        self.cwd = self.root  # current working directory (not used in this example)
        self.schema = Schema(path=ID(stored=True, unique=True), content=TEXT)
        os.makedirs('indexdir', exist_ok=True)
        self.index = create_in('indexdir', self.schema)

    def _split_path(self, path):
        # Returns list of path components, e.g. /a/b/c.txt -> ['a','b','c.txt']
        return [p for p in path.strip('/').split('/') if p]

    def _resolve(self, path):
        # Returns (parent_dir, entry_name)
        parts = self._split_path(path)
        if not parts:
            return self.root, ''
        curr = self.root
        for p in parts[:-1]:
            if p not in curr.entries or not isinstance(curr.entries[p], Directory):
                raise FileNotFoundError(f"Directory '{p}' not found in path '{path}'")
            curr = curr.entries[p]
        return curr, parts[-1]

    def list_dir(self, path='/'):
        dir_obj, name = self._resolve(path)
        if name:
            if name in dir_obj.entries and isinstance(dir_obj.entries[name], Directory):
                return list(dir_obj.entries[name].entries.keys())
            else:
                raise NotADirectoryError(path)
        return list(dir_obj.entries.keys())

    def mkdir(self, path, owner='user', permissions=0o755):
        parent, name = self._resolve(path)
        if name in parent.entries:
            raise FileExistsError(f"Directory '{name}' already exists")
        parent.entries[name] = Directory(name, owner, permissions)

    def rmdir(self, path):
        parent, name = self._resolve(path)
        if name not in parent.entries or not isinstance(parent.entries[name], Directory):
            raise FileNotFoundError(f"Directory '{name}' not found")
        if parent.entries[name].entries:
            raise OSError("Directory not empty")
        del parent.entries[name]

    def create_file(self, path, content=b'', encrypted=False, owner='user', permissions=0o644):
        parent, name = self._resolve(path)
        if name in parent.entries:
            raise FileExistsError(f"File '{name}' already exists")
        key = Fernet.generate_key() if encrypted else None
        file = File(name, content, encrypted, key, owner, permissions)
        parent.entries[name] = file
        # Index content
        writer = self.index.writer()
        writer.add_document(path=path, content=file.read().decode('utf-8', errors='ignore'))
        writer.commit()

    def read_file(self, path):
        parent, name = self._resolve(path)
        file = parent.entries.get(name)
        if isinstance(file, File):
            return file.read()
        raise FileNotFoundError(path)

    def write_file(self, path, data):
        parent, name = self._resolve(path)
        file = parent.entries.get(name)
        if isinstance(file, File):
            file.write(data)
            # Re-index
            writer = self.index.writer()
            writer.update_document(path=path, content=file.read().decode('utf-8', errors='ignore'))
            writer.commit()
        else:
            raise FileNotFoundError(path)

    def delete_file(self, path):
        parent, name = self._resolve(path)
        if name in parent.entries and isinstance(parent.entries[name], File):
            del parent.entries[name]
            # Delete from index
            writer = self.index.writer()
            writer.delete_by_term('path', path)
            writer.commit()
        else:
            raise FileNotFoundError(path)

    def move(self, src_path, dst_path):
        src_parent, src_name = self._resolve(src_path)
        dst_parent, dst_name = self._resolve(dst_path)
        if src_name not in src_parent.entries:
            raise FileNotFoundError(src_path)
        if dst_name in dst_parent.entries:
            raise FileExistsError(dst_path)
        dst_parent.entries[dst_name] = src_parent.entries.pop(src_name)
        # Update index path
        writer = self.index.writer()
        writer.update_document(path=dst_path, content=dst_parent.entries[dst_name].read().decode('utf-8', errors='ignore'))
        writer.delete_by_term('path', src_path)
        writer.commit()

    def chmod(self, path, permissions):
        parent, name = self._resolve(path)
        entry = parent.entries.get(name)
        if entry:
            entry.permissions = permissions
        else:
            raise FileNotFoundError(path)

    def search(self, query_str):
        from whoosh.qparser import QueryParser
        qp = QueryParser('content', schema=self.schema)
        q = qp.parse(query_str)
        with self.index.searcher() as s:
            results = s.search(q)
            return [hit['path'] for hit in results]

    def save(self):
        with open(self.SAVE_PATH, 'wb') as f:
            pickle.dump(self.root, f)

    def load(self):
        try:
            with open(self.SAVE_PATH, 'rb') as f:
                self.root = pickle.load(f)
        except FileNotFoundError:
            self.root = Directory('/')