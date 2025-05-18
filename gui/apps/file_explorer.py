import PySimpleGUI as sg
from os_core.filesystem import FileSystem, File, Directory

class FileExplorerApp:
    def __init__(self):
        self.fs = FileSystem()
        self.fs.load()
        self.current_path = '/'
        self.layout = [
            [sg.Text('File Explorer')],
            [sg.Text('Current Path:'), sg.Text(self.current_path, key='-CURPATH-')],
            [sg.Listbox(values=self._get_entries(self.current_path), size=(40, 15), key='-FILELIST-', enable_events=True)],
            [sg.Button('Up'), sg.Button('New Folder'), sg.Button('New File'), sg.Button('Refresh'), sg.Button('Close')]
        ]
        self.window = sg.Window('File Explorer', self.layout, modal=True)

    def _get_entries(self, path):
        # Hem dosya hem klasörleri göster, türünü belirt
        entries = []
        dir_obj, name = self.fs._resolve(path)
        if name:
            dir_obj = dir_obj.entries[name]
        for entry_name, entry in dir_obj.entries.items():
            if isinstance(entry, Directory):
                entries.append(f'[DIR] {entry_name}')
            elif isinstance(entry, File):
                entries.append(f'[FILE] {entry_name}')
        return entries

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
                        sg.popup_error(f'Error: {e}')
            elif event == 'New File':
                file_name = sg.popup_get_text('File name (ör: dosya.txt):')
                if file_name:
                    new_path = self.current_path.rstrip('/') + '/' + file_name if self.current_path != '/' else '/' + file_name
                    try:
                        self.fs.create_file(new_path, content=b'')
                        self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                    except Exception as e:
                        sg.popup_error(f'Error: {e}')
            elif event == '-FILELIST-':
                selected = values['-FILELIST-']
                if selected:
                    entry = selected[0]
                    entry_name = entry.split(' ', 1)[1]
                    dir_obj, name = self.fs._resolve(self.current_path)
                    if name:
                        dir_obj = dir_obj.entries[name]
                    entry_obj = dir_obj.entries[entry_name]
                    if isinstance(entry_obj, Directory):
                        # Klasöre gir
                        self.current_path = self.current_path.rstrip('/') + '/' + entry_name if self.current_path != '/' else '/' + entry_name
                        self.window['-CURPATH-'].update(self.current_path)
                        self.window['-FILELIST-'].update(self._get_entries(self.current_path))
                    elif isinstance(entry_obj, File):
                        # Dosya ise içeriğini göster ve düzenle
                        try:
                            content = entry_obj.read().decode('utf-8', errors='ignore')
                        except Exception:
                            content = '[BINARY DATA]'
                        # Düzenleme penceresi
                        layout = [
                            [sg.Multiline(content, size=(60, 20), key='-EDIT-')],
                            [sg.Button('Kaydet'), sg.Button('Kapat')]
                        ]
                        edit_win = sg.Window(entry_name, layout, modal=True)
                        while True:
                            e_event, e_values = edit_win.read()
                            if e_event in (sg.WIN_CLOSED, 'Kapat'):
                                break
                            elif e_event == 'Kaydet':
                                new_content = e_values['-EDIT-'].encode('utf-8')
                                try:
                                    self.fs.write_file(self.current_path.rstrip('/') + '/' + entry_name if self.current_path != '/' else '/' + entry_name, new_content)
                                    sg.popup('Kaydedildi!')
                                except Exception as ex:
                                    sg.popup_error(f'Hata: {ex}')
                        edit_win.close()
        self.fs.save()
        self.window.close()