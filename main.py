import PySimpleGUI as sg
from gui.main_window import MainWindow

if __name__ == '__main__':
    main_win = MainWindow()
    main_win.run()      # ← use run() instead of show()

