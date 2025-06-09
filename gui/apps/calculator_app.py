import PySimpleGUI as sg
import re

class CalculatorApp:
    def __init__(self):
        button_size = (5, 2)
        btn_font = ('Arial', 16, 'bold')
        layout = [
            [sg.Text(
                '', size=(18, 1), key='-DISPLAY-', justification='right',
                font=('Arial', 32, 'bold'), background_color='#222',
                text_color='#1565c0', pad=((8, 8), (18, 18)), relief='groove', border_width=2
            )],
            [
                sg.Button('C', size=button_size, font=btn_font, button_color=('white', '#d35400')),
                sg.Button('⌫', size=button_size, font=btn_font, button_color=('white', '#7f8c8d')),
                sg.Button('%', size=button_size, font=btn_font, button_color=('white', '#7f8c8d')),
                sg.Button('/', size=button_size, font=btn_font, button_color=('white', '#2980b9'))
            ],
            [
                sg.Button('7', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('8', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('9', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('*', size=button_size, font=btn_font, button_color=('white', '#2980b9'))
            ],
            [
                sg.Button('4', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('5', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('6', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('-', size=button_size, font=btn_font, button_color=('white', '#2980b9'))
            ],
            [
                sg.Button('1', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('2', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('3', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('+', size=button_size, font=btn_font, button_color=('white', '#2980b9'))
            ],
            [
                sg.Button('±', size=button_size, font=btn_font, button_color=('white', '#7f8c8d')),
                sg.Button('0', size=button_size, font=btn_font, button_color=('white', '#34495e')),
                sg.Button('.', size=button_size, font=btn_font, button_color=('white', '#7f8c8d')),
                sg.Button('=', size=button_size, font=btn_font, button_color=('white', '#27ae60'))
            ],
            [sg.Button('Close', size=(23, 1), font=('Arial', 12), button_color=('white', '#c0392b'))]
        ]
        self.window = sg.Window(
            'Calculator', layout, finalize=True, element_justification='center',
            keep_on_top=True, background_color='#222', return_keyboard_events=True
        )
        self.current = ''

    def handle_event(self, event, values):

        key_map = {
            'Escape': 'C', 'BackSpace': '⌫', 'Return': '=', 'equal': '=',
            'plus': '+', 'minus': '-', 'asterisk': '*', 'slash': '/',
            'percent': '%', 'period': '.', 'comma': '.'
        }

        if isinstance(event, str) and ':' in event:
            event = event.split(':')[0]
        if isinstance(event, str) and event.startswith(' '):
            event = event.strip()
        if event in (sg.WIN_CLOSED, 'Close'):
            return 'close'
        if event in key_map:
            event = key_map[event]
   
        if event in ('=', 'Enter', '-IN-_ReturnKeyPressed-'):
            try:
                expression = self.current.replace('%', '/100')
                result = str(eval(expression))
                self.current = result
            except Exception:
                self.current = ''
                self.window['-DISPLAY-'].update('Error')
                return
            self.window['-DISPLAY-'].update(self.current)
            return
        if event in '0123456789':
            self.current += event
        elif event == '.':
            if not self.current or not self.current.split()[-1].replace('.', '', 1).isdigit():
                self.current += '0.'
            elif '.' not in self.current.split()[-1]:
                self.current += '.'
        elif event in '+-*/%':
            if self.current and self.current[-1] in '+-*/%':
                self.current = self.current[:-1] + event
            elif self.current:
                self.current += event
        elif event == 'C':
            self.current = ''
        elif event == '⌫':
            self.current = self.current[:-1]
        elif event == '±':
            numbers = list(re.finditer(r'(\d+\.?\d*)', self.current))
            if numbers:
                last = numbers[-1]
                num = self.current[last.start():last.end()]
                if self.current[last.start()-1:last.start()] == '-':
                    self.current = self.current[:last.start()-1] + self.current[last.start():]
                else:
                    self.current = self.current[:last.start()] + '-' + num + self.current[last.end():]

        self.window['-DISPLAY-'].update(self.current)

    def run(self):
        while True:
            event, values = self.window.read()
            result = self.handle_event(event, values)
            if result == 'close':
                break
        self.window.close()

if __name__ == '__main__':
    app = CalculatorApp()
    app.run()