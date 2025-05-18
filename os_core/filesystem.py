import os
from cryptography.fernet import Fernet, InvalidToken
import time
import pickle

class File:
    def __init__(self, name, content=b'', encrypted=False, key=None):
        self.name = name
        self.timestamp = time.time()
        self.encrypted = encrypted
        self.key = key if key else (Fernet.generate_key() if encrypted else None)
        self.content = content # content şifreliyse şifreli, değilse ham olarak saklanmalı
        if encrypted and content: # Eğer başlangıçta şifreli içerik verildiyse ve bu içerik plaintext ise şifrele
             # Bu kısım create_file veya write_file içinde ele alınmalı.
             # __init__ doğrudan şifrelenmiş content almalı veya boş olmalı.
             # Şimdilik, content'in zaten doğru formatta (şifreliyse şifreli) geldiğini varsayalım.
             pass
        self.size = len(self.content)


    def read(self, decrypt_if_able=True):
        if self.encrypted:
            if decrypt_if_able:
                if not self.key:
                    raise ValueError("File is marked as encrypted but no key is available.")
                try:
                    f = Fernet(self.key)
                    return f.decrypt(self.content)
                except InvalidToken:
                    raise ValueError("Decryption failed. Invalid token or key.")
                except Exception as e:
                    raise ValueError(f"Decryption failed: {e}")
            else:
                return self.content # Ham, şifreli içeriği döndür
        return self.content

    def write(self, data_bytes, encrypt_override=None):
        """Writes data to the file, encrypting if necessary."""
        should_encrypt = self.encrypted if encrypt_override is None else encrypt_override

        if should_encrypt:
            if not self.key:
                self.key = Fernet.generate_key()
            f = Fernet(self.key)
            self.content = f.encrypt(data_bytes)
            self.encrypted = True
        else:
            self.content = data_bytes
            self.encrypted = False
            self.key = None
        
        self.size = len(self.content)
        self.timestamp = time.time()


class Directory:
    def __init__(self, name):
        self.name = name
        self.entries = {} # name: File or Directory object
        self.timestamp = time.time()

class FileSystem:
    def __init__(self, state_file='fs_state.pkl'):
        self.root = Directory('/')
        self.state_file = state_file

    def _resolve(self, path_str):
        if not path_str.startswith('/'):
            raise ValueError("Path must be absolute (start with '/')")
        if path_str == '/':
            return self.root, None 

        parts = path_str.strip('/').split('/')
        current_dir = self.root
        for i, part in enumerate(parts[:-1]):
            if part not in current_dir.entries or not isinstance(current_dir.entries[part], Directory):
                raise FileNotFoundError(f"Path component not found or not a directory: {part}")
            current_dir = current_dir.entries[part]
        
        entry_name = parts[-1]
        return current_dir, entry_name


    def read_file(self, path, decrypt_if_able=True):
        parent_dir, filename = self._resolve(path)
        if filename in parent_dir.entries and isinstance(parent_dir.entries[filename], File):
            file_obj = parent_dir.entries[filename]
            content = file_obj.read(decrypt_if_able=decrypt_if_able)
            return content, file_obj.encrypted # İçeriği ve orijinal şifreleme durumunu döndür
        raise FileNotFoundError(f"File not found: {path}")

    def write_file(self, path, data_bytes):
        parent_dir, filename = self._resolve(path)
        if filename not in parent_dir.entries or not isinstance(parent_dir.entries[filename], File):
            raise FileNotFoundError(f"File not found: {path}. Use create_file first.")

        file_obj = parent_dir.entries[filename]
        file_obj.write(data_bytes)

    def create_file(self, path, content=b'', encrypted=False):
        parent_dir, filename = self._resolve(path)
        if filename in parent_dir.entries:
            raise FileExistsError(f"File or directory already exists: {path}")
        
        new_file = File(filename, encrypted=encrypted)
        new_file.write(content) 
        parent_dir.entries[filename] = new_file

    def mkdir(self, path):
        parent_dir, dirname = self._resolve(path)
        if dirname in parent_dir.entries:
            raise FileExistsError(f"File or directory already exists: {path}")
        parent_dir.entries[dirname] = Directory(dirname)

    def list_dir(self, path):
        target_dir_obj = self.root
        if path != '/':
            parent_dir, dirname = self._resolve(path)
            if dirname not in parent_dir.entries or not isinstance(parent_dir.entries[dirname], Directory):
                raise FileNotFoundError(f"Directory not found: {path}")
            target_dir_obj = parent_dir.entries[dirname]
        
        return list(target_dir_obj.entries.keys())


    def delete_file(self, path):
        parent_dir, filename = self._resolve(path)
        if filename in parent_dir.entries and isinstance(parent_dir.entries[filename], File):
            del parent_dir.entries[filename]
        else:
            raise FileNotFoundError(f"File not found or not a file: {path}")

    def rmdir(self, path):
        parent_dir, dirname = self._resolve(path)
        if dirname in parent_dir.entries and isinstance(parent_dir.entries[dirname], Directory):
            if parent_dir.entries[dirname].entries:
                raise OSError("Directory not empty")
            del parent_dir.entries[dirname]
        else:
            raise FileNotFoundError(f"Directory not found or not a directory: {path}")


    def save(self):
        with open(self.state_file, 'wb') as f:
            pickle.dump(self.root, f)

    def load(self):
        try:
            with open(self.state_file, 'rb') as f:
                self.root = pickle.load(f)
        except FileNotFoundError:
            self.root = Directory('/')
        except Exception as e:
            print(f"Error loading filesystem state: {e}. Starting with a new filesystem.")
            self.root = Directory('/')