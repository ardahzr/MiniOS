import PySimpleGUI as sg
import datetime
import socket
import threading
import re

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432

class ChatApp:
    PREDEFINED_COLORS = ['#E6194B', '#3CB44B', '#4363D8', '#F58231', '#911EB4', '#46F0F0', '#FABEBE', '#008080', '#E6BEFF', '#AA6E28']
    USER_COLORS_CACHE = {}
    NEXT_COLOR_INDEX = 0
    OWN_MESSAGE_COLOR = '#007bff'
    SYSTEM_MESSAGE_COLOR = '#6c757d'
    DEFAULT_TEXT_COLOR = '#212529'

    def __init__(self):
        self.username = None
        self.window = None
        self.client_socket = None
        self.receive_thread = None
        self.running = False

        self._prompt_for_username()

        if not self.username:
            return

        if not self._connect_to_server():
            sg.popup_error(f"Could not connect to the chat server at {SERVER_HOST}:{SERVER_PORT}.\nPlease ensure the server is running.", title="Connection Error")
            return

        self.running = True
        chat_font = ("Helvetica", 11)
        input_font = ("Helvetica", 10)
        button_font = ("Helvetica", 10)

        layout = [
            [sg.Text(f"MiniOS Network Chat - User: {self.username}", font=("Helvetica", 16), justification='center', expand_x=True, key='-CHAT_TITLE-')],
            [sg.Multiline(
                "",
                size=(70, 20),
                key='-CHAT_HISTORY-',
                autoscroll=True,
                disabled=True,
                font=chat_font,
                text_color=ChatApp.DEFAULT_TEXT_COLOR,
                background_color='#f8f9fa',
                pad=((5,5),(5,10)),
                write_only=True
            )],
            [
                sg.Input(key='-MESSAGE_INPUT-', expand_x=True, focus=True, font=input_font, pad=((5,5),(0,5))),
                sg.Button('Send', bind_return_key=True, font=button_font, pad=((0,5),(0,5)))
            ],
            [sg.Push(), sg.Button('Close', font=button_font, pad=((5,5),(10,5)))]
        ]
        self.window = sg.Window(f'Network Chat - {self.username}', layout, finalize=True, element_justification='center')
        
        self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
        self.receive_thread.start()

    def _prompt_for_username(self):
        name = sg.popup_get_text("Enter your username for the chat:", title="Username Entry", default_text="User")
        if name and name.strip():
            self.username = name.strip()
        else:
            self.username = None

    def _connect_to_server(self):
        if not self.username:
            return False
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((SERVER_HOST, SERVER_PORT))
            self.client_socket.sendall(f"USERNAME:{self.username}".encode('utf-8'))
            return True
        except socket.error as e:
            print(f"[CHATAPP {self.username}] Connection error: {e}")
            self.client_socket = None
            return False
        except Exception as e:
            print(f"[CHATAPP {self.username}] Unexpected error during connection: {e}")
            self.client_socket = None
            return False

    def _get_user_color(self, username_from_message):
        if username_from_message == self.username:
            return ChatApp.OWN_MESSAGE_COLOR
        if username_from_message.lower() == "system":
            return ChatApp.SYSTEM_MESSAGE_COLOR
        
        if username_from_message not in ChatApp.USER_COLORS_CACHE:
            color = ChatApp.PREDEFINED_COLORS[ChatApp.NEXT_COLOR_INDEX % len(ChatApp.PREDEFINED_COLORS)]
            ChatApp.USER_COLORS_CACHE[username_from_message] = color
            ChatApp.NEXT_COLOR_INDEX = (ChatApp.NEXT_COLOR_INDEX + 1) % len(ChatApp.PREDEFINED_COLORS)
        return ChatApp.USER_COLORS_CACHE[username_from_message]

    def _receive_messages(self):
        while self.running and self.client_socket:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    if self.window:
                         self.window.write_event_value('-NETWORK_MESSAGE_RECEIVED-', message)
                else:
                    if self.window:
                        self.window.write_event_value('-SERVER_DISCONNECTED-', "Server closed the connection.")
                    break
            except socket.error:
                if self.running and self.window:
                     self.window.write_event_value('-SERVER_DISCONNECTED-', "Connection to server lost.")
                break
            except Exception as e:
                print(f"[CHATAPP {self.username}] Error receiving message: {e}")
                if self.running and self.window:
                    self.window.write_event_value('-SERVER_DISCONNECTED-', f"Error: {e}")
                break
        print(f"[CHATAPP {self.username}] Receive thread stopped.")

    def _append_message_to_history(self, full_message_string):
        if not self.window: return

        match = re.match(r"\[(.*?)\]\s(.*?):\s(.*)", full_message_string.strip())
        sender = "Unknown"
        
        if match:
            sender = match.group(2)
        elif full_message_string.strip().lower().startswith("[system]:"):
            parts = full_message_string.strip().split(":", 1)
            if len(parts) > 0 and parts[0].lower() == "[system]":
                sender = "System"

        user_color = self._get_user_color(sender)
        
        self.window['-CHAT_HISTORY-'].print(full_message_string.strip(), text_color=user_color, font=("Helvetica", 11))
        self.window['-CHAT_HISTORY-'].print("", font=("Helvetica", 1))

        if hasattr(self.window['-CHAT_HISTORY-'].Widget, 'yview_moveto'):
            self.window['-CHAT_HISTORY-'].Widget.yview_moveto(1.0)

    def handle_event(self, event, values):
        if not self.window:
            self._shutdown_client()
            return 'close'

        if event in (sg.WIN_CLOSED, 'Close'):
            self._shutdown_client()
            return 'close'

        if event == 'Send':
            message_text = values['-MESSAGE_INPUT-'].strip()
            if message_text and self.client_socket:
                try:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    formatted_own_message = f"[{timestamp}] {self.username}: {message_text}"
                    self._append_message_to_history(formatted_own_message)
                    
                    self.client_socket.sendall(message_text.encode('utf-8'))
                    self.window['-MESSAGE_INPUT-'].update('')
                except socket.error as e:
                    self._append_message_to_history(f"[System]: Error sending message: {e}")
                except Exception as e:
                    self._append_message_to_history(f"[System]: Unexpected error sending message: {e}")
        
        elif event == '-NETWORK_MESSAGE_RECEIVED-':
            if values and isinstance(values.get(event), str):
                self._append_message_to_history(values[event])
        
        elif event == '-SERVER_DISCONNECTED-':
            disconnect_msg = "[System]: Disconnected from server."
            if values and isinstance(values.get(event), str) and values[event]:
                disconnect_msg = f"[System]: {values[event]}"
            self._append_message_to_history(disconnect_msg)
            if self.window:
                self.window['Send'].update(disabled=True)
                self.window['-MESSAGE_INPUT-'].update(disabled=True)
            self._shutdown_client(keep_socket_for_check=True)

        return None

    def _shutdown_client(self, keep_socket_for_check=False):
        self.running = False
        if self.client_socket and not keep_socket_for_check:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except socket.error:
                pass
            except Exception as e:
                print(f"[CHATAPP {self.username}] Error during socket shutdown: {e}")
            finally:
                self.client_socket = None
        
        print(f"[CHATAPP {self.username}] Client shutdown initiated.")