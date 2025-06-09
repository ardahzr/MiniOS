import PySimpleGUI as sg
from os_core.filesystem import FileSystem, File, Directory
import os

class FileExplorerApp:
    def __init__(self):
        self.fs = FileSystem()
        self.fs.load()
        self.current_path = '/'
        self.layout = [
            [sg.Text('File Explorer')],
            [sg.Text('Current Path:'), sg.Text(self.current_path, key='-CURPATH-', size=(40,1))],
            [sg.Listbox(values=self._get_entries(self.current_path), size=(60, 15), key='-FILELIST-', enable_events=True)],
            [
                sg.Button('Up'), sg.Button('New Folder'), sg.Button('New File'),
                sg.Button('Write File'), sg.Button('Encrypt'), sg.Button('Decrypt'), sg.Button('Delete'),
                sg.Button('Refresh'), sg.Button('Close')
            ]
        ]
        self.window = sg.Window('File Explorer', self.layout, finalize=True)

    def show_window(self):
        return sg.Window('File Explorer', self.layout, finalize=True)

    def _get_current_directory_object(self):
        """Resolves self.current_path to a Directory object."""
        if self.current_path == '/':
            return self.fs.root
        
        parent_dir, dir_name = self.fs._resolve(self.current_path)
        if dir_name in parent_dir.entries and isinstance(parent_dir.entries[dir_name], Directory):
            return parent_dir.entries[dir_name]
        else:
            sg.popup_error(f"Error: Current path '{self.current_path}' is not a valid directory. Resetting to root.")
            self.current_path = '/'
            self.window['-CURPATH-'].update(self.current_path)
            return self.fs.root

    def _get_entries(self, current_dir_path):
        entries = []
        try:
            target_dir_obj = self._get_current_directory_object()
        except Exception as e:
            sg.popup_error(f"Error accessing directory '{current_dir_path}': {e}. Displaying empty list.")
            if self.current_path != '/':
                self.current_path = '/'
                self.window['-CURPATH-'].update(self.current_path)
                return self._get_entries('/')
            return []


        for entry_name, entry_obj in target_dir_obj.entries.items():
            if isinstance(entry_obj, Directory):
                entries.append(f'[DIR] {entry_name}')
            elif isinstance(entry_obj, File):
                if entry_obj.encrypted:
                    entries.append(f'[FILE-E] {entry_name}')
                else:
                    entries.append(f'[FILE] {entry_name}')
        return sorted(entries)

    def _get_selected_item_details(self, values):
        if not values['-FILELIST-']:
            return None, None, None # full_path, entry_name_only, entry_obj

        selected_display_name = values['-FILELIST-'][0]
        
        entry_name_only = ""
        if selected_display_name.startswith('[DIR] '):
            entry_name_only = selected_display_name[len('[DIR] '):]
        elif selected_display_name.startswith('[FILE-E] '):
            entry_name_only = selected_display_name[len('[FILE-E] '):]
        elif selected_display_name.startswith('[FILE] '):
            entry_name_only = selected_display_name[len('[FILE] '):]
        else:
            sg.popup_error("Unknown item format in list.")
            return None, None, None

        if self.current_path == '/':
            full_path = '/' + entry_name_only
        else:
            full_path = self.current_path.rstrip('/') + '/' + entry_name_only
        
        parent_dir_obj, item_name_in_parent = self.fs._resolve(full_path)
        
        if item_name_in_parent not in parent_dir_obj.entries:
            sg.popup_error(f"Error: Entry '{entry_name_only}' not found at '{full_path}'. List might be outdated. Please refresh.")
            return None, None, None
            
        entry_obj = parent_dir_obj.entries[item_name_in_parent]
        return full_path, entry_name_only, entry_obj

    def handle_event(self, event, values):
        if event in (sg.WIN_CLOSED, 'Close'):
            return 'close'

        if event == 'Refresh':
            self.window['-FILELIST-'].update(self._get_entries(self.current_path))
            self.window['-CURPATH-'].update(self.current_path)

        elif event == 'Up':
            if self.current_path != '/':
                self.current_path = os.path.dirname(self.current_path.rstrip('/'))
                if not self.current_path:
                    self.current_path = '/'
                self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                self.window['-CURPATH-'].update(self.current_path)

        elif event == '-FILELIST-':
            full_path, entry_name_only, entry_obj = self._get_selected_item_details(values)
            if entry_obj is None:
                return
            if isinstance(entry_obj, Directory):
                self.current_path = full_path
                self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                self.window['-CURPATH-'].update(self.current_path)
            elif isinstance(entry_obj, File):
                # Dosya içeriğini göster
                if entry_obj.encrypted:
                    content, _ = self.fs.read_file(full_path, decrypt_if_able=False)
                    content = content.decode('utf-8', errors='replace') if isinstance(content, bytes) else content
                    sg.popup_scrolled(content, title=f"Encrypted File: {entry_name_only}")
                else:
                    content = entry_obj.read()
                    content = content.decode('utf-8', errors='replace') if isinstance(content, bytes) else content
                    if content is None:
                        sg.popup_error(f"Error reading file: {entry_name_only}")
                    else:
                        sg.popup_scrolled(content, title=entry_name_only)

    
        elif event == 'New Folder':
            folder_name = sg.popup_get_text("New folder name:")
            if folder_name:
                dir_obj = self._get_current_directory_object()
                if folder_name in dir_obj.entries:
                    sg.popup_error("A file or folder with that name already exists.")
                else:
                    dir_obj.entries[folder_name] = Directory(folder_name)
                    self.fs.save()
                    self.window['-FILELIST-'].update(self._get_entries(self.current_path))

        elif event == 'New File':
            file_name = sg.popup_get_text("New file name:")
            if file_name:
                dir_obj = self._get_current_directory_object()
                if file_name in dir_obj.entries:
                    sg.popup_error("A file or folder with that name already exists.")
                else:
                    dir_obj.entries[file_name] = File(file_name, "")
                    self.fs.save()
                    self.window['-FILELIST-'].update(self._get_entries(self.current_path))

        elif event == 'Delete':
            full_path, entry_name_only, entry_obj = self._get_selected_item_details(values)
            if entry_obj is None:
                sg.popup_error("No file or folder selected.")
                return
            confirm = sg.popup_yes_no(f"Delete '{entry_name_only}'?")
            if confirm == 'Yes':
                parent_dir_obj, item_name_in_parent = self.fs._resolve(full_path)
                del parent_dir_obj.entries[item_name_in_parent]
                self.fs.save()
                self.window['-FILELIST-'].update(self._get_entries(self.current_path))

        elif event == 'Encrypt':
            full_path, entry_name_only, entry_obj = self._get_selected_item_details(values)
            if isinstance(entry_obj, File) and not entry_obj.encrypted:
                password = sg.popup_get_text("Enter password to encrypt:")
                if password:
                    entry_obj.encrypt(password)
                    self.fs.save()
                    self.window['-FILELIST-'].update(self._get_entries(self.current_path))
            else:
                sg.popup_error("Select a non-encrypted file to encrypt.")

        elif event == 'Decrypt':
            full_path, entry_name_only, entry_obj = self._get_selected_item_details(values)
            if isinstance(entry_obj, File) and entry_obj.encrypted:
                password = sg.popup_get_text("Enter password to decrypt:")
                if password:
                    try:
                        entry_obj.decrypt(password)
                        self.fs.save()
                        self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                    except Exception as e:
                        sg.popup_error(f"Decryption failed: {e}")
            else:
                sg.popup_error("Select an encrypted file to decrypt.")

        elif event == 'Write File':
            full_path, entry_name_only, entry_obj = self._get_selected_item_details(values)
            if isinstance(entry_obj, File):
                # Show current content (if not encrypted)
                if entry_obj.encrypted:
                    sg.popup_error("Cannot write to encrypted file. Decrypt it first.")
                    return
                current_content = entry_obj.read()
                if isinstance(current_content, bytes):
                    try:
                        current_content = current_content.decode('utf-8', errors='replace')
                    except Exception:
                        current_content = str(current_content)
                new_content = sg.popup_get_text(f"Edit file: {entry_name_only}", default_text=current_content)
                if new_content is not None:
                    entry_obj.write(new_content.encode())
                    self.fs.save()
                    self.window['-FILELIST-'].update(self._get_entries(self.current_path))
            else:
                sg.popup_error("Select a file to write.")

        return None

