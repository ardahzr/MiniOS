import PySimpleGUI as sg
import google.generativeai as genai

API_KEY = "AIzaSyDKrJSlhL9zt2oZdlvMCAKzKIWg9KfqpAA" # REPLACE WITH YOUR ACTUAL API KEY

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    sg.popup_error(f"Failed to configure Gemini API: {e}\nPlease check your API key and internet connection.", title="API Configuration Error")

class GeminiChatApp:
    def __init__(self):
        self.model = None
        try:
            # Using a modern, efficient model
            self.model = genai.GenerativeModel('gemini-2.0-flash') 
        except Exception as e:
            sg.popup_error(f"Failed to initialize Gemini Model: {e}", title="Model Initialization Error")

        self.title_font = ('Helvetica', 16, 'bold')
        self.chat_font = ('Helvetica', 11)
        self.input_font = ('Helvetica', 10)

        self.user_text_color = 'blue' 
        self.gemini_text_color = '#006400' # Dark green for Gemini
        self.system_text_color = 'grey'
        self.default_text_color = 'black' 
        
        chat_display_elem = sg.Multiline(
            "", 
            size=(80, 20), 
            key='-CHAT_HISTORY-', 
            autoscroll=True, 
            disabled=True, 
            write_only=True,
            background_color='#f0f0f0', 
            text_color=self.default_text_color, 
            font=self.chat_font,
            pad=((5,5),(5,5))
        )

        layout = [
            [sg.Text('Gemini AI Chat', font=self.title_font, justification='center', expand_x=True, pad=((0,0),(10,15)))],
            [chat_display_elem],
            [sg.HorizontalSeparator(pad=((0,0),(5,10)))],
            [
                sg.Input(
                    key='-USER_INPUT-', 
                    font=self.input_font,
                    expand_x=True, # Make input field expand
                    do_not_clear=False, 
                    focus=True, 
                    pad=((5,5),(5,5))
                ),
                sg.Button('Send', key='-SEND-', font=self.input_font, size=(8,1), pad=((0,5),(5,5)), bind_return_key=True)
            ],
            [sg.Push(), sg.Button('Close', font=self.input_font, size=(8,1), pad=((5,5),(15,5)))] 
        ]
        
        self.window = sg.Window(
            'AI Chat', 
            layout, 
            finalize=True, 
            element_justification='left'
        )
        self._append_to_history("Welcome to AI Chat. Type your message and press Send or Enter.", speaker_prefix="System:")

    def _append_to_history(self, message_content, speaker_prefix):
        text_color_to_use = self.default_text_color
        if speaker_prefix == "You:":
            text_color_to_use = self.user_text_color
        elif speaker_prefix == "Gemini:":
            text_color_to_use = self.gemini_text_color
        elif speaker_prefix == "System:":
            text_color_to_use = self.system_text_color

        if speaker_prefix:
            self.window['-CHAT_HISTORY-'].print(f"{speaker_prefix} {message_content.strip()}", font=self.chat_font, text_color=text_color_to_use)
        else: 
            self.window['-CHAT_HISTORY-'].print(message_content.strip(), font=self.chat_font, text_color=text_color_to_use)
        
        # Adds a blank line for spacing, with default text color
        self.window['-CHAT_HISTORY-'].print("", font=self.chat_font, text_color=self.default_text_color) 

    def handle_event(self, event, values):
        if event in (sg.WIN_CLOSED, 'Close'):
            return 'close'

        if event == '-SEND-':
            user_input = values['-USER_INPUT-'].strip()
            if not user_input:
                return
            if not self.model:
                self._append_to_history("Gemini model is not available. Cannot send message.", speaker_prefix="System:")
                self.window['-USER_INPUT-'].update('')
                return
            self._append_to_history(user_input, speaker_prefix="You:")
            self.window['-USER_INPUT-'].update('')
            try:
                self.window.refresh()
                response = self.model.generate_content(user_input)
                if response and response.text:
                    self._append_to_history(response.text, speaker_prefix="Gemini:")
                elif response and response.prompt_feedback:
                    self._append_to_history(f"No content generated. Feedback: {response.prompt_feedback}", speaker_prefix="Gemini:")
                else:
                    self._append_to_history("Received an empty response or an error occurred.", speaker_prefix="Gemini:")
            except Exception as e:
                error_message = f"Error communicating with Gemini API: {e}"
                self._append_to_history(error_message, speaker_prefix="System:")
        return None

    def run(self):
        while True:
            event, values = self.window.read()

            result = self.handle_event(event, values)
            if result == 'close':
                break
        
        self.window.close()

if __name__ == '__main__':
    if API_KEY == "YOUR_API_KEY_HERE" or not API_KEY or "AIzaSyDKrJSlhL9zt2oZdlvMCAKzKIWg9KfqpAA" == API_KEY :
         sg.popup_error("Please set your actual Gemini API_KEY in the script to run this test.", title="API Key Missing/Default")
    else:
        app = GeminiChatApp()
        app.run()