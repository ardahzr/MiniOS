import PySimpleGUI as sg
from os_core.filesystem import FileSystem
import sys
import io

class TerminalApp:
    def __init__(self):
        self.fs = FileSystem()
        self.fs.load()
        self.cwd = '/'
        self.username = 'user'
        self.hostname = 'miniOS'
        self.history = []
        self.history_idx = -1
        layout = [
            [sg.Multiline(size=(80, 24), key='-OUT-', font='Consolas 11', autoscroll=True, write_only=True, disabled=True, background_color='black', text_color='white')],
            [sg.Input(key='-IN-', font='Consolas 11', do_not_clear=False, focus=True, background_color='black', text_color='white')],
            [sg.Button('Enter'), sg.Button('Close')]
        ]
        self.window = sg.Window('Terminal', layout, modal=True, finalize=True, return_keyboard_events=True)
        self.window['-IN-'].set_focus()

        # Enter tuşuna basıldığında özel bir olay tetiklemek için Tkinter bind kullan
        self.window['-IN-'].Widget.bind('<Return>', lambda event: self.window.write_event_value('-IN-_ReturnKeyPressed-', self.window['-IN-'].get()))

        self._print_prompt()

    def _prompt(self):
        return f"{self.username}@{self.hostname}:{self.cwd}$ "

    def _print(self, msg, end='\n'):
        self.window['-OUT-'].update(msg + end, append=True)

    def _print_prompt(self):
        self._print(self._prompt(), end='')

    def run(self):
        while True:
            event, values = self.window.read()
            # print(f"DEBUG: Event='{event}', Values='{values}'") # Hata ayıklama için bırakılabilir veya kaldırılabilir
            if event in (sg.WIN_CLOSED, 'Close'):
                self.fs.save()
                break
            elif event == 'Enter' or event == '-IN-_ReturnKeyPressed-':
                cmd = ""
                if event == '-IN-_ReturnKeyPressed-':
                    cmd = values[event]
                elif values is not None and '-IN-' in values:
                    cmd = values['-IN-']

                if cmd is None: cmd = ""

                if cmd.strip() == '':
                    self._print('')
                    self._print_prompt()
                    continue
                self.history.append(cmd)
                self.history_idx = len(self.history)
                self._print(cmd)
                self.window['-IN-'].update('')
                self._handle_command(cmd)
                self._print_prompt()
            elif event == '-IN-':
                pass
            elif event == '__TIMEOUT__':
                pass
            elif event.startswith('Up:'):
                if self.history and self.history_idx > 0:
                    self.history_idx -= 1
                    self.window['-IN-'].update(self.history[self.history_idx])
            elif event.startswith('Down:'):
                if self.history and self.history_idx < len(self.history) - 1:
                    self.history_idx += 1
                    self.window['-IN-'].update(self.history[self.history_idx])
                elif self.history_idx == len(self.history) -1 :
                    self.window['-IN-'].update('')
                    self.history_idx = len(self.history)


        self.window.close()

    def _handle_command(self, cmd):
        parts = cmd.strip().split()
        if not parts:
            return
        if parts[0] == 'ls':
            try:
                files = self.fs.list_dir(self.cwd)
                self._print('\n'.join(files))
            except Exception as e:
                self._print(f'Error: {e}')
        elif parts[0] == 'cd':
            if len(parts) > 1:
                new_path = parts[1]
                if not new_path.startswith('/'):
                    if self.cwd == '/':
                        new_path = '/' + new_path.lstrip('/')
                    else:
                        new_path = self.cwd.rstrip('/') + '/' + new_path.lstrip('/')

                if new_path.endswith('/..'):
                    path_parts = new_path.rstrip('/..').split('/')
                    if len(path_parts) > 1:
                        new_path = '/'.join(path_parts[:-1]) or '/'
                    else:
                        new_path = '/'
                elif '/../' in new_path:
                    # Bu kısım daha karmaşık path normalizasyonu gerektirebilir
                    pass


                try:
                    self.fs.list_dir(new_path) # Dizin varlığını kontrol eder
                    self.cwd = new_path if new_path.startswith('/') else '/'
                    if not self.cwd.endswith('/') and self.cwd != '/':
                        self.cwd += '/'
                    if '//' in self.cwd:
                        self.cwd = self.cwd.replace('//', '/')
                    if self.cwd != '/' and self.cwd.endswith('/'):
                         self.cwd = self.cwd.rstrip('/')


                except Exception as e:
                    self._print(f'Error: {e}')
        elif parts[0] == 'pwd':
            self._print(self.cwd)
        elif parts[0] == 'mkdir' and len(parts) > 1:
            try:
                path = parts[1] if parts[1].startswith('/') else (self.cwd.rstrip('/') + '/' + parts[1] if self.cwd != '/' else '/' + parts[1])
                self.fs.mkdir(path)
                self._print(f"Directory '{path}' created.")
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'touch' and len(parts) > 1:
            try:
                path = parts[1] if parts[1].startswith('/') else (self.cwd.rstrip('/') + '/' + parts[1] if self.cwd != '/' else '/' + parts[1])
                self.fs.create_file(path, content=b'')
                self._print(f"File '{path}' created.")
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'cat' and len(parts) > 1:
            try:
                path = parts[1] if parts[1].startswith('/') else (self.cwd.rstrip('/') + '/' + parts[1] if self.cwd != '/' else '/' + parts[1])
                
                # Dosyayı okurken şifre çözme işlemini yapma (decrypt_if_able=False)
                # read_file şimdi (content_bytes, is_encrypted_originally) döndürüyor
                content_bytes, is_encrypted_originally = self.fs.read_file(path, decrypt_if_able=False)

                if is_encrypted_originally:
                    self._print(f"--- Encrypted Content of '{parts[1]}' ---")
                    self._print(content_bytes.decode('utf-8', errors='replace'))
                    self._print(f"--- End of Encrypted Content ---")
                else:
                    self._print(content_bytes.decode('utf-8', errors='ignore'))
            except FileNotFoundError:
                self._print(f"Error: File not found '{path}'")
            except ValueError as e: 
                self._print(f"Error: {e}")
            except Exception as e:
                self._print(f"Error reading file: {e}")
        elif parts[0] == 'echo' and '>' in parts:
            try:
                idx = parts.index('>')
                text_parts = parts[1:idx]
                if not text_parts:
                    text = ""
                else:
                    text = ' '.join(text_parts)

                filename = parts[idx+1]
                if not filename:
                    self._print("Error: No filename specified after >")
                    return

                path = filename if filename.startswith('/') else (self.cwd.rstrip('/') + '/' + filename if self.cwd != '/' else '/' + filename)
                self.fs.write_file(path, text.encode('utf-8'))
                self._print(f"Wrote to {path}")
            except ValueError:
                self._print("Error: Invalid echo command. Usage: echo [text] > filename")
            except IndexError:
                self._print("Error: No filename specified after >")
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'run' and len(parts) > 1 and parts[1].endswith('.py'):
            path = parts[1] if parts[1].startswith('/') else (self.cwd.rstrip('/') + '/' + parts[1] if self.cwd != '/' else '/' + parts[1])
            try:
                # Dosya içeriğini oku, şifreliyse şifresini çözerek al
                content_bytes, _ = self.fs.read_file(path, decrypt_if_able=True)
                code = content_bytes.decode('utf-8')
                
                old_stdout = sys.stdout
                redirected_output = io.StringIO()
                sys.stdout = redirected_output
                try:
                    exec(code, {'__name__': '__main__', 'fs': self.fs, 'cwd': self.cwd})
                except Exception as e:
                    print(f"Runtime error in {parts[1]}: {e}", file=sys.stderr) # Hataları stderr'e yazdır
                finally:
                    sys.stdout = old_stdout # stdout'u geri yükle
                
                output_val = redirected_output.getvalue()
                if output_val:
                    self._print(output_val)
            except FileNotFoundError:
                self._print(f"Error: File not found '{path}'")
            except Exception as e:
                self._print(f"Error running script: {e}")

        elif parts[0] == 'help':
            self._print(
                "Available commands:\n"
                "  ls                - List directory contents\n"
                "  cd <directory>    - Change current directory (use '..' for parent)\n"
                "  pwd               - Print working directory\n"
                "  mkdir <directory> - Create a new directory\n"
                "  touch <file>      - Create a new empty file\n"
                "  cat <file>        - Display file content (shows raw if encrypted)\n"
                "  echo [text] > <file> - Write text to a file (overwrite)\n"
                "  run <file.py>     - Execute a Python script from the filesystem (decrypts if needed)\n"
                "  help              - Show this help message\n"
                "  Up/Down Arrows    - Navigate command history"
            )
        else:
            self._print(f"Unknown command: {parts[0]}. Type 'help' for available commands.")
