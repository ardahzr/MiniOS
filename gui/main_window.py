import os
import PySimpleGUI as sg
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

from gui.apps.file_explorer import FileExplorerApp
from gui.apps.terminal import TerminalApp
from gui.apps.game_app import GameApp
from gui.apps.memory_visualizer_app import MemoryVisualizerApp
from gui.apps.gemini_chat_app import GeminiChatApp
from gui.apps.process_manager_visualizer_app import ProcessManagerVisualizerApp # Add this line

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
icon_folder_path = os.path.join(BASEDIR, 'resources', 'folder.png')
icon_terminal_path = os.path.join(BASEDIR, 'resources', 'terminal.png')
icon_game_path = os.path.join(BASEDIR, 'resources', 'game.png')
icon_exit_path = os.path.join(BASEDIR, 'resources', 'exit.png')
icon_memoryVis_path = os.path.join(BASEDIR, 'resources', 'memory_vis.png')
icon_start_path = os.path.join(BASEDIR, 'resources', 'start.png')
wallpaper_path = os.path.join(BASEDIR, 'resources', 'wallpaper.png')
icon_ai_path = os.path.join(BASEDIR, 'resources', 'gemini.png')
icon_scheduler_vis_path = os.path.join(BASEDIR, 'resources', 'scheduler_vis.png') # Add this line

class MainWindow:
    DESKTOP_ICON_SIZE = (48, 48)
    DESKTOP_ICON_TEXT_FONT = ('Arial', 9)
    DESKTOP_ICON_TEXT_COLOR = 'white'
    DESKTOP_ICON_VERTICAL_SPACING = 80
    DESKTOP_ICON_HORIZONTAL_PADDING = 20
    DESKTOP_ICON_TOP_PADDING = 20

    def __init__(self):
        sg.theme('DarkBlue3')

        self.taskbar_bg = "#30528a"
        self.start_menu_bg = '#1565c0'
        self.button_color = ('white', self.start_menu_bg)

        self.desktop_icon_configs = [
            {'key': 'File Explorer', 'text': 'File Explorer', 'image_path': icon_folder_path},
            {'key': 'Terminal', 'text': 'Terminal', 'image_path': icon_terminal_path},
            {'key': 'Game', 'text': 'Game', 'image_path': icon_game_path},
            {'key': 'Memory', 'text': 'Memory', 'image_path': icon_memoryVis_path},
            {'key': 'AIChat', 'text': 'AI Chat', 'image_path': icon_ai_path},
            {'key': 'SchedulerVisualizer', 'text': 'Scheduler', 'image_path': icon_scheduler_vis_path}, # Add this line
        ]
        self.clickable_icon_areas = {}

        start_icon_height_config = 40 
        taskbar_button_padding = 8
        self.taskbar_height = start_icon_height_config + taskbar_button_padding 

        window_width, window_height = 1440, 810
        self.desktop_graph_width = window_width
        self.desktop_graph_height = window_height - self.taskbar_height

        desktop_layout = [[
            sg.Graph(
                canvas_size=(self.desktop_graph_width, self.desktop_graph_height),
                graph_bottom_left=(0, self.desktop_graph_height),
                graph_top_right=(self.desktop_graph_width, 0),
                key='-DESKTOP_GRAPH-',
                enable_events=True,
                pad=(0,0),
                background_color='lightgrey'
            )
        ]]

        start_icon_width, start_icon_height = 40, 40
        start_icon = None
        if os.path.exists(icon_start_path):
            try:
                img = Image.open(icon_start_path)
                img.thumbnail((start_icon_width, start_icon_height), Image.Resampling.LANCZOS)
                with io.BytesIO() as bio:
                    img.save(bio, format="PNG")
                    start_icon = bio.getvalue()
            except Exception as e:
                print(f"ERROR DEBUG: Could not load or process start icon {icon_start_path}: {e}")
        
        button_text_content = ''
        current_image_data = start_icon
        if start_icon is None:
            button_text_content = 'ERR'
            current_image_data = None

        button_pixel_width = start_icon_width + 8
        button_pixel_height = start_icon_height + 8
        clock_font_size_approx_pixels = 20

        taskbar_layout = [[
            sg.Button(button_text_content,
                      image_data=current_image_data,
                      key='START',
                      button_color=(self.taskbar_bg, self.taskbar_bg),
                      border_width=0,
                      pad=((10, 20), (0,0)),
                      ),
            sg.Push(),
            sg.Text('', key='CLOCK',
                    font=('Arial', 16),
                    pad=(10, (button_pixel_height - clock_font_size_approx_pixels) // 2 if button_pixel_height > clock_font_size_approx_pixels else 3),
                    background_color=self.taskbar_bg,
                    text_color='white')
        ]]

        layout = [
            [sg.Column(desktop_layout, pad=(0,0), expand_x=True, expand_y=True)],
            [sg.Column(taskbar_layout, background_color=self.taskbar_bg, pad=(0,0), expand_x=True)]
        ]

        self.window = sg.Window(
            'Desktop',
            layout,
            finalize=True,
            resizable=True,
            size=(window_width, window_height),
            margins=(0,0),
            element_justification='c'
        )

        self.desktop_graph = self.window['-DESKTOP_GRAPH-']
        self._draw_wallpaper()
        self._draw_desktop_icons_on_graph()
        
        self.update_clock()

    def _get_icon_image_bytes(self, image_path, size):
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                with io.BytesIO() as bio:
                    img.save(bio, format="PNG")
                    return bio.getvalue()
            except Exception as e:
                print(f"Warning: Could not load icon {image_path}: {e}")
        return None

    def _draw_wallpaper(self):
        if os.path.exists(wallpaper_path):
            try:
                img = Image.open(wallpaper_path)
                img = img.resize((self.desktop_graph_width, self.desktop_graph_height), Image.Resampling.LANCZOS)
                with io.BytesIO() as bio:
                    img.save(bio, format="PNG")
                    image_bytes = bio.getvalue()
                
                self.desktop_graph.draw_image(data=image_bytes, location=(0,0))
            except Exception as e:
                print(f"Error drawing wallpaper: {e}")
        else:
            print(f"Wallpaper image not found: {wallpaper_path}")


    def _draw_desktop_icons_on_graph(self):
        self.clickable_icon_areas.clear()
        current_x = self.DESKTOP_ICON_HORIZONTAL_PADDING
        current_y = self.DESKTOP_ICON_TOP_PADDING
        approx_font_pixel_height = 12
        approx_half_font_height = approx_font_pixel_height // 2

        for i, icon_config in enumerate(self.desktop_icon_configs):
            image_bytes = self._get_icon_image_bytes(icon_config['image_path'], self.DESKTOP_ICON_SIZE)
            
            icon_w, icon_h = self.DESKTOP_ICON_SIZE
            
            img_x, img_y = current_x, current_y

            if image_bytes:
                self.desktop_graph.draw_image(data=image_bytes, location=(img_x, img_y))
            else:
                self.desktop_graph.draw_rectangle((img_x, img_y), (img_x + icon_w, img_y + icon_h), line_color='red')
                self.desktop_graph.draw_text("?", location=(img_x + icon_w/2, img_y + icon_h/2), color='red', font=('Arial', 20))

            text_content = icon_config['text']
            text_area_height_approx = 20 
            
            text_x_center = img_x + icon_w / 2
            text_y_anchor_top = img_y + icon_h + 5

            text_draw_location_y = text_y_anchor_top + approx_half_font_height

            self.desktop_graph.draw_text(
                text_content,
                location=(text_x_center, text_draw_location_y),
                font=self.DESKTOP_ICON_TEXT_FONT,
                color=self.DESKTOP_ICON_TEXT_COLOR
            )

            clickable_x1 = img_x
            clickable_y1 = img_y 
            clickable_x2 = img_x + icon_w
            clickable_y2 = text_y_anchor_top + text_area_height_approx 
            
            self.clickable_icon_areas[icon_config['key']] = (clickable_x1, clickable_y1, clickable_x2, clickable_y2)

            current_y += self.DESKTOP_ICON_VERTICAL_SPACING


    def update_clock(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.window['CLOCK'].update(current_time)
        

    @staticmethod
    def _safe_icon_button(text, icon_path, key):
        if os.path.exists(icon_path) and icon_path.lower().endswith(('.png', '.gif')):
            return sg.Button(text, image_filename=icon_path, image_size=(32,32), pad=(5,5), key=key)
        else:
            return sg.Button(text, pad=(5,5), key=key)

    def _show_start_menu(self):
        layout = [
            [sg.Text("Start Menu", font=("Arial", 14, "bold"))],
            [self._safe_icon_button("File Explorer", icon_folder_path, "File Explorer")],
            [self._safe_icon_button("Terminal", icon_terminal_path, "Terminal")],
            [self._safe_icon_button("Game", icon_game_path, "Game")],
            [self._safe_icon_button("Memory", icon_memoryVis_path, "Memory")],
            [self._safe_icon_button("AI Chat", icon_ai_path, "AIChat")],
            [sg.Button("Close", pad=(5,10))]
        ]
        window = sg.Window("Start Menu", layout, modal=True, finalize=True, keep_on_top=True)
        event, _ = window.read()
        window.close()
        if event in ("File Explorer", "Terminal", "Game", "Memory", "AIChat"):
            return event
        return None

    def run(self):
        open_windows = {'Desktop': (self.window, self)}
        app_classes = {
            'File Explorer': FileExplorerApp,
            'Terminal': TerminalApp,
            'Game': GameApp,
            'Memory': MemoryVisualizerApp,
            'AIChat': GeminiChatApp,
            'SchedulerVisualizer': ProcessManagerVisualizerApp
        }
        GAME_TICK_INTERVAL = 200  

        while True:
            window_that_had_event, event, values = sg.read_all_windows(timeout=GAME_TICK_INTERVAL)
            self.update_clock()

            if event == sg.WIN_CLOSED and window_that_had_event == self.window:
                break 
            if window_that_had_event is None and event != sg.TIMEOUT_EVENT: 
                 break

 
            if event == sg.TIMEOUT_EVENT:
                if 'Game' in open_windows:
                    game_window, game_instance = open_windows['Game']
                    if game_window and hasattr(game_instance, 'handle_event'):
                        game_instance.handle_event("TIMER_TICK", None)
            

            elif window_that_had_event is not None:
                current_app_key = None
                current_app_instance = None
                current_win_ref = None

                for key_iter, (win_iter, app_instance_iter) in open_windows.items():
                    if win_iter == window_that_had_event:
                        current_app_key = key_iter
                        current_app_instance = app_instance_iter
                        current_win_ref = win_iter
                        break
                
                if current_app_key == 'Desktop':
                    if event == sg.WIN_CLOSED:
                        return 
                    if event == 'START':
                        start_menu_layout = [
                            [sg.Button('File Explorer', size=(20,1), button_color=self.button_color, key='File Explorer')],
                            [sg.Button('Terminal', size=(20,1), button_color=self.button_color, key='Terminal')],
                            [sg.Button('Game', size=(20,1), button_color=self.button_color, key='Game')],
                            [sg.Button('Memory', size=(20,1), button_color=self.button_color, key='Memory')],
                            [sg.Button('AI Chat', size=(20,1), button_color=self.button_color, key='AIChat')],
                            [sg.Button('Scheduler Visualizer', size=(20,1), button_color=self.button_color, key='SchedulerVisualizer')], 
                            [sg.HorizontalSeparator(color='#1976d2')],
                            [sg.Button('Exit', size=(20,1), button_color=self.button_color, key='Exit')]
                        ]
                        
                        start_button_widget = self.window['START'].Widget
                        start_menu_x = start_button_widget.winfo_rootx()
                        taskbar_y_abs = self.window.CurrentLocation()[1] + self.desktop_graph_height
                        
                        num_items = len(start_menu_layout)
                        button_height_approx = 30 
                        menu_height_approx = num_items * button_height_approx

                        start_menu_y = taskbar_y_abs - menu_height_approx 

                        start_menu = sg.Window(
                            'Start Menu', 
                            start_menu_layout, 
                            location=(start_menu_x, start_menu_y),
                            no_titlebar=True, 
                            keep_on_top=True, 
                            finalize=True, 
                            background_color=self.start_menu_bg,
                            grab_anywhere=False
                        )
                        
                        menu_choice, _ = start_menu.read(timeout=10000)
                        start_menu.close()
                        
                        if menu_choice:
                            if menu_choice == 'Exit':
                                return 
                           
                            event = menu_choice 

                    elif event == '-DESKTOP_GRAPH-':
                        click_coords = values['-DESKTOP_GRAPH-']
                        if click_coords:
                            cx, cy = click_coords
                            for icon_key, (x1, y1, x2, y2) in self.clickable_icon_areas.items():
                                if x1 <= cx <= x2 and y1 <= cy <= y2:
                                    event = icon_key 
                                    break
                    
                    
                    if event in app_classes and event not in open_windows:
                        app_instance_new = app_classes[event]()
                        app_window_new = getattr(app_instance_new, 'window', None)
                        if app_window_new is not None:
                            open_windows[event] = (app_window_new, app_instance_new)
                        else:
                            print(f"Warning: App {event} window could not be created.")
                
                elif current_app_instance is not None: 
                    result = current_app_instance.handle_event(event, values)
                    if result == 'close' or event == sg.WIN_CLOSED:
                        current_win_ref.close()
                        if current_app_key in open_windows:
                            del open_windows[current_app_key]
        
       
        for _key, (win_to_close, _app_instance_to_close) in open_windows.items():
            try:
                win_to_close.close()
            except Exception as e:
                print(f"Error closing window on exit: {e}")
