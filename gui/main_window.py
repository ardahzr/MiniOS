import PySimpleGUI as sg
from gui.apps.file_explorer import FileExplorerApp
from gui.apps.terminal import TerminalApp
from gui.apps.game_app import GameApp

class MainWindow:
    def __init__(self):
        sg.theme('DarkBlue3')
        layout = [
            [sg.Text('Mini OS Simulation', font=('Any', 16))],
            [sg.Button('File Explorer'), sg.Button('Terminal'), sg.Button('Game'), sg.Button('Exit')]
        ]
        self.window = sg.Window('Desktop', layout, finalize=True)

    def run(self):
        while True:
            event, values = self.window.read()
            if event in (sg.WIN_CLOSED, 'Exit'):
                break
            elif event == 'File Explorer':
                FileExplorerApp().run()
            elif event == 'Terminal':
                TerminalApp().run()
            elif event == 'Game':
                GameApp().run()
        self.window.close()