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
                sg.Button('Encrypt'), sg.Button('Decrypt'), sg.Button('Delete'),
                sg.Button('Refresh'), sg.Button('Close')
            ]
        ]
        self.window = sg.Window('File Explorer', self.layout, modal=True, finalize=True)

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

    def run(self):
        while True:
            event, values = self.window.read()
            if event in (sg.WIN_CLOSED, 'Close'):
                break
            
            elif event == 'Refresh':
                self.window['-FILELIST-'].update(self._get_entries(self.current_path))
            
            elif event == 'Up':
                if self.current_path != '/':
                    self.current_path = '/'.join(self.current_path.rstrip('/').split('/')[:-1]) or '/'
                    self.window['-CURPATH-'].update(self.current_path)
                    self.window['-FILELIST-'].update(self._get_entries(self.current_path))
            
            elif event == 'New Folder':
                folder_name = sg.popup_get_text('Folder name:')
                if folder_name:
                    new_path = self.current_path.rstrip('/') + '/' + folder_name if self.current_path != '/' else '/' + folder_name
                    try:
                        self.fs.mkdir(new_path)
                        self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                    except Exception as e:
                        sg.popup_error(f'Error creating folder: {e}')
            
            elif event == 'New File':
                file_name = sg.popup_get_text('File name (e.g., doc.txt):')
                if file_name:
                    encrypt_choice = sg.popup_yes_no('Encrypt this file?')
                    is_encrypted = (encrypt_choice == 'Yes')
                    
                    new_path = self.current_path.rstrip('/') + '/' + file_name if self.current_path != '/' else '/' + file_name
                    try:
                        self.fs.create_file(new_path, content=b'', encrypted=is_encrypted)
                        self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                    except Exception as e:
                        sg.popup_error(f'Error creating file: {e}')
            
            elif event == 'Encrypt':
                full_path, entry_name, entry_obj = self._get_selected_item_details(values)
                if not entry_obj:
                    sg.popup_error("Please select an item first.")
                    continue

                if isinstance(entry_obj, File):
                    if entry_obj.encrypted:
                        sg.popup_ok("File is already encrypted.")
                    else:
                        confirm = sg.popup_yes_no(f"Are you sure you want to encrypt '{entry_name}'?\nThis will re-encrypt the file with a new key.")
                        if confirm == 'Yes':
                            try:
                                content = entry_obj.read() 
                                self.fs.delete_file(full_path) 
                                self.fs.create_file(full_path, content=content, encrypted=True) 
                                self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                                sg.popup_ok(f"File '{entry_name}' encrypted.")
                            except Exception as e:
                                sg.popup_error(f"Error encrypting file: {e}")
                else:
                    sg.popup_error("Only files can be encrypted. Please select a file.")

            elif event == 'Decrypt':
                full_path, entry_name, entry_obj = self._get_selected_item_details(values)
                if not entry_obj:
                    sg.popup_error("Please select an item first.")
                    continue

                if isinstance(entry_obj, File):
                    if not entry_obj.encrypted:
                        sg.popup_ok("File is not encrypted.")
                    else:
                        confirm = sg.popup_yes_no(f"Are you sure you want to decrypt '{entry_name}'?")
                        if confirm == 'Yes':
                            try:
                                content = entry_obj.read() 
                                self.fs.delete_file(full_path) 
                                self.fs.create_file(full_path, content=content, encrypted=False) 
                                self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                                sg.popup_ok(f"File '{entry_name}' decrypted.")
                            except Exception as e:
                                sg.popup_error(f"Error decrypting file: {e}")
                else:
                    sg.popup_error("Only files can be decrypted. Please select a file.")
            
            elif event == 'Delete':
                full_path, entry_name, entry_obj = self._get_selected_item_details(values)
                if not entry_obj:
                    sg.popup_error("Please select an item to delete.")
                    continue

                confirm_msg = f"Are you sure you want to delete '{entry_name}'?"
                if isinstance(entry_obj, Directory) and entry_obj.entries:
                    confirm_msg += "\nWARNING: Directory is not empty. Deleting it will remove all its contents."
                
                confirm = sg.popup_yes_no(confirm_msg)
                if confirm == 'Yes':
                    try:
                        if isinstance(entry_obj, Directory):
                            if entry_obj.entries:
                                sg.popup_error("Cannot delete non-empty directory with current rmdir. Implement recursive delete or empty it first.")
                            else:
                                self.fs.rmdir(full_path)
                        elif isinstance(entry_obj, File):
                            self.fs.delete_file(full_path)
                        
                        self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                        sg.popup_ok(f"'{entry_name}' deleted.")
                    except OSError as e: 
                         sg.popup_error(f"Error deleting: {e}. Directory might not be empty.")
                    except Exception as e:
                        sg.popup_error(f"Error deleting '{entry_name}': {e}")


            elif event == '-FILELIST-':
                if not values['-FILELIST-']: 
                    continue
                selected_display_name = values['-FILELIST-'][0]
                
                entry_name_only = ""
                is_dir = False
                if selected_display_name.startswith('[DIR] '):
                    entry_name_only = selected_display_name[len('[DIR] '):]
                    is_dir = True
                elif selected_display_name.startswith('[FILE-E] '):
                    entry_name_only = selected_display_name[len('[FILE-E] '):]
                elif selected_display_name.startswith('[FILE] '):
                    entry_name_only = selected_display_name[len('[FILE] '):]
                else:
                    continue 

                if self.current_path == '/':
                    full_item_path = '/' + entry_name_only
                else:
                    full_item_path = self.current_path.rstrip('/') + '/' + entry_name_only

                parent_dir_obj, item_name_in_parent = self.fs._resolve(full_item_path)
                if item_name_in_parent not in parent_dir_obj.entries:
                    sg.popup_error(f"Error: '{entry_name_only}' not found. Please refresh.")
                    continue
                
                entry_obj = parent_dir_obj.entries[item_name_in_parent]

                if is_dir:
                    self.current_path = full_item_path
                    self.window['-CURPATH-'].update(self.current_path)
                    self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                elif isinstance(entry_obj, File):
                    try:
                        content = entry_obj.read().decode('utf-8', errors='ignore')
                    except Exception: 
                        content = '[Encrypted or Binary Data - Cannot display directly]'
                        if entry_obj.encrypted:
                             try:
                                 content = entry_obj.read().decode('utf-8', errors='replace') 
                             except Exception:
                                 content = '[Encrypted Data - Error decoding]'
                        else: 
                            content = '[Binary Data]'


                    edit_layout = [
                        [sg.Text(f"Editing: {entry_name_only}{' (Encrypted)' if entry_obj.encrypted else ''}")],
                        [sg.Multiline(content, size=(60, 20), key='-EDIT-')],
                        [sg.Button('Kaydet'), sg.Button('Kapat')]
                    ]
                    edit_win = sg.Window(f"Edit {entry_name_only}", edit_layout, modal=True, finalize=True)
                    while True:
                        e_event, e_values = edit_win.read()
                        if e_event in (sg.WIN_CLOSED, 'Kapat'):
                            break
                        elif e_event == 'Kaydet':
                            new_content = e_values['-EDIT-'].encode('utf-8')
                            try:
                                self.fs.write_file(full_item_path, new_content)
                                sg.popup('Kaydedildi!')
                            except Exception as ex:
                                sg.popup_error(f'Hata: {ex}')
                    edit_win.close()
        
        self.fs.save()
        self.window.close()