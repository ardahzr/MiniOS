import os
import PySimpleGUI as sg
from PIL import Image # Import Pillow
import io # For BytesIO

from gui.apps.file_explorer import FileExplorerApp
from gui.apps.terminal import TerminalApp
from gui.apps.game_app import GameApp
from gui.apps.memory_visualizer_app import MemoryVisualizerApp # Import the new app

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
icon_folder_path = os.path.join(BASEDIR, 'resources', 'folder.png')
icon_terminal_path = os.path.join(BASEDIR, 'resources', 'terminal.png')
icon_game_path = os.path.join(BASEDIR, 'resources', 'game.png')
icon_exit_path = os.path.join(BASEDIR, 'resources', 'exit.png')

# Helper function to create a button, falling back if image is not found
def create_button_with_icon(text, image_path, key=None, pad=(10,10), icon_size=(48, 48)):
    fallback_button_size = (14, 2)
    if os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            img.thumbnail(icon_size, Image.Resampling.LANCZOS) # Resize image, maintaining aspect ratio
            with io.BytesIO() as bio:
                img.save(bio, format="PNG")
                image_bytes = bio.getvalue()
            # When using image_data, the 'text' parameter becomes a tooltip.
            # Button size will be determined by the image.
            # Making button background transparent and removing border for icon-like feel.
            return sg.Button(tooltip=text, image_data=image_bytes, key=key or text, pad=pad,
                             button_color=(sg.theme_background_color(), sg.theme_background_color()),
                             border_width=0)
        except Exception as e:
            print(f"Warning: Could not load or resize icon {image_path} with Pillow: {e}. Using text-only button for '{text}'.")
            return sg.Button(text, key=key or text, pad=pad, size=fallback_button_size)
    else:
        print(f"Warning: Icon not found at {image_path}. Using text-only button for '{text}'.")
        return sg.Button(text, key=key or text, pad=pad, size=fallback_button_size)

class MainWindow:
    def __init__(self):
        sg.theme('DarkBlue3')

        common_icon_size = (64, 64)

        button_file_explorer = create_button_with_icon('File Explorer', icon_folder_path, icon_size=common_icon_size)
        button_terminal = create_button_with_icon('Terminal', icon_terminal_path, icon_size=common_icon_size)
        button_game = create_button_with_icon('Game', icon_game_path, icon_size=common_icon_size)
        button_memory = sg.Button('Memory Viz', key='Memory Visualizer', size=(14,2), pad=(10,10)) # Text button for now
        button_exit = create_button_with_icon('Exit', icon_exit_path, key='Exit', icon_size=common_icon_size)

        layout = [
            [sg.Text('Mini OS Simulation', font=('Any', 20), justification='center', expand_x=True)],
            [
                button_file_explorer,
                button_terminal,
                button_game,
                button_memory, # Add the new button
                button_exit
            ]
        ]
        self.window = sg.Window('Desktop', layout, finalize=True, element_justification='c', background_color='#1a2332')

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
            elif event == 'Memory Visualizer': # Add event handler for the new app
                MemoryVisualizerApp().run()
        self.window.close()