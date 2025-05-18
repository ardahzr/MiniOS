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
        self.window = sg.Window('Terminal', layout, modal=True, finalize=True)
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
            if event in (sg.WIN_CLOSED, 'Close'):
                self.fs.save()
                break
            elif event == 'Enter':
                cmd = values['-IN-']
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
            elif event.startswith('Up'):
                if self.history and self.history_idx > 0:
                    self.history_idx -= 1
                    self.window['-IN-'].update(self.history[self.history_idx])
            elif event.startswith('Down'):
                if self.history and self.history_idx < len(self.history) - 1:
                    self.history_idx += 1
                    self.window['-IN-'].update(self.history[self.history_idx])
                else:
                    self.window['-IN-'].update('')

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
                    new_path = self.cwd.rstrip('/') + '/' + new_path if self.cwd != '/' else '/' + new_path
                try:
                    self.fs.list_dir(new_path)
                    self.cwd = new_path
                except Exception as e:
                    self._print(f'Error: {e}')
            self._print(self.cwd)
        elif parts[0] == 'pwd':
            self._print(self.cwd)
        elif parts[0] == 'mkdir' and len(parts) > 1:
            try:
                path = parts[1] if parts[1].startswith('/') else self.cwd.rstrip('/') + '/' + parts[1]
                self.fs.mkdir(path)
                self._print(f"Directory '{path}' created.")
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'touch' and len(parts) > 1:
            try:
                path = parts[1] if parts[1].startswith('/') else self.cwd.rstrip('/') + '/' + parts[1]
                self.fs.create_file(path, content=b'')
                self._print(f"File '{path}' created.")
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'cat' and len(parts) > 1:
            try:
                path = parts[1] if parts[1].startswith('/') else self.cwd.rstrip('/') + '/' + parts[1]
                content = self.fs.read_file(path)
                self._print(content.decode('utf-8', errors='ignore'))
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'echo' and '>' in parts:
            idx = parts.index('>')
            text = ' '.join(parts[1:idx])
            filename = parts[idx+1]
            path = filename if filename.startswith('/') else self.cwd.rstrip('/') + '/' + filename
            try:
                self.fs.write_file(path, text.encode('utf-8'))
                self._print(f"Wrote to {path}")
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'run' and len(parts) > 1 and parts[1].endswith('.py'):
            path = parts[1] if parts[1].startswith('/') else self.cwd.rstrip('/') + '/' + parts[1]
            try:
                code = self.fs.read_file(path).decode('utf-8')
                old_stdout = sys.stdout
                sys.stdout = mystdout = io.StringIO()
                try:
                    exec(code, {})
                except Exception as e:
                    print(f"Runtime error: {e}")
                sys.stdout = old_stdout
                self._print(mystdout.getvalue())
            except Exception as e:
                self._print(f"Error: {e}")
        elif parts[0] == 'help':
            self._print(
                "ls, cd <dir>, pwd, mkdir <dir>, touch <file>, cat <file>, echo <text> > <file>, run <file.py>, help"
            )
        else:
            self._print(f"Unknown command: {cmd}")