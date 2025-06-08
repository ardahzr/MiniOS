import PySimpleGUI as sg
import re
import sys
import webbrowser
import subprocess
import tempfile
import urllib.parse
import time

try:
    from yt_dlp import YoutubeDL
    ydl_available = True
except ImportError:
    ydl_available = False

try:
    import vlc
except ImportError:
    vlc = None

class YouTubeApp:
    def __init__(self):
        sg.theme('DarkBlue3')
        self.title_font = ('Helvetica', 17, 'bold')
        self.label_font = ('Helvetica', 13, 'bold')
        self.input_font = ('Helvetica', 13, 'bold')
        self.button_font = ('Helvetica', 13, 'bold')
        self.status_font = ('Helvetica', 12, 'bold italic')
        self.default_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.status_text_key = '-STATUS_TEXT-'

        self.vlc_instance = None
        self.media_player = None
        self.video_player_ready = False
        self.current_loaded_url = None

        libraries_available = vlc is not None and ydl_available

        icon_search = '🔍'
        icon_pause = '⏸️'

        if not libraries_available:
            error_message = "Required libraries not found:\n"
            if not ydl_available:
                error_message += "- 'yt-dlp' (Install: pip install yt-dlp)\n"
            if vlc is None:
                error_message += "- 'python-vlc' (Install: pip install python-vlc)\n"
                error_message += "  And make sure VLC Media Player is installed on your system.\n"
            error_message += "In-app video playback will not be available."

            layout_top = [
                [sg.Text('MiniOS YouTube Player', font=self.title_font, justification='center', expand_x=True, pad=((0,0),(10,10)), text_color='#E53935')],
                [
                    sg.Input(key='-URL_OR_ID-', expand_x=True, font=self.input_font, size=(30,1), default_text="Search or URL"),
                    sg.Button(f'{icon_search} Open', font=self.button_font, key='-OPEN_EXTERNALLY-', button_color=('white', '#1976D2')),
                ],
                [sg.Text(error_message, font=self.label_font, text_color='red')]
            ]
            layout_video = []
            window_title = 'YouTube Player (Missing Libraries)'
            initial_size = (500, 180)
        else:
            try:
                self.vlc_instance = vlc.Instance('--no-video-title-show', '--quiet', '--avcodec-hw=none')
                self.media_player = self.vlc_instance.media_player_new()
            except Exception as e:
                libraries_available = False
                error_message = f"VLC could not be started: {e}\nMake sure VLC Media Player is properly installed.\nIn-app video playback will not be available."
                layout_top = [
                    [sg.Text('MiniOS YouTube Player', font=self.title_font, justification='center', expand_x=True, pad=((0,0),(10,10)), text_color='#E53935')],
                    [
                        sg.Input(key='-URL_OR_ID-', expand_x=True, font=self.input_font, size=(30,1), default_text="Search or URL"),
                        sg.Button(f'{icon_search} Open', font=self.button_font, key='-OPEN_EXTERNALLY-', button_color=('white', '#1976D2')),
                    ],
                    [sg.Text(error_message, font=self.label_font, text_color='red')]
                ]
                layout_video = []
                window_title = 'YouTube Player (VLC Error)'
                initial_size = (500, 180)

            if libraries_available:
                layout_top = [
                    [sg.Text('MiniOS YouTube Player', 
                             font=('Helvetica', 20, 'bold'), 
                             justification='center', 
                             expand_x=True, 
                             pad=((0,0),(10,10)), 
                             text_color='#FF1744')],
                    [
                        sg.Input(key='-URL_OR_ID-', expand_x=True, font=self.input_font, size=(40,1), default_text="Search or URL"),
                        sg.Button(f'{icon_search} Play', font=self.button_font, key='-PLAY-', button_color=('white', '#388E3C')),
                        sg.Button(f'{icon_pause} Pause', font=self.button_font, key='-PAUSE_RESUME-', button_color=('white', '#FBC02D')),
                    ],
                    [sg.Text("", font=self.status_font, text_color='#FFD600', key=self.status_text_key, expand_x=True, pad=((0,0),(5,10)))]
                ]
                layout_video = [[sg.Image(key='-VIDEO_OUTPUT-', background_color='black', size=(700, 393))]]
                window_title = 'MiniOS YouTube Player'
                initial_size = (700, 540)

        layout = layout_top + layout_video
        self.window = sg.Window(window_title, layout, finalize=True, resizable=False, size=initial_size, element_justification='left', background_color='#1B263B')

        if libraries_available and self.media_player and layout_video:
            try:
                video_widget = self.window['-VIDEO_OUTPUT-'].Widget
                video_widget_id = video_widget.winfo_id()

                if sys.platform.startswith('linux'):
                    self.media_player.set_xwindow(video_widget_id)
                elif sys.platform.startswith('win'):
                    self.media_player.set_hwnd(video_widget_id)
                elif sys.platform.startswith('darwin'):
                    sg.popup_notify("Video embedding may be unstable on macOS.", title="macOS Warning")
                    self.video_player_ready = False
                else:
                    self.video_player_ready = True

                if not sys.platform.startswith('darwin'):
                    self.video_player_ready = True

            except Exception as e:
                sg.popup_error(f"Error setting up video output: {e}", title="VLC Setup Error")
                self.video_player_ready = False

        if not libraries_available:
            self.video_player_ready = False

        # Auto-play Rickroll on startup
        if self.video_player_ready:
            self.window[self.status_text_key].update("Starting: Rick Astley - Never Gonna Give You Up...")
            self._play_video(self.default_url)

    def _is_valid_youtube_url(self, url):
        youtube_regex = (
            r'(https?://)?(www\.)?'
            r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})')
        match = re.match(youtube_regex, url)
        return match is not None

    def _is_valid_youtube_id(self, video_id):
        return re.match(r'^[a-zA-Z0-9_-]{11}$', video_id) is not None

    def _construct_youtube_url(self, input_value):
        if not input_value: return None
        if self._is_valid_youtube_url(input_value):
            if not input_value.startswith(('http://', 'https://')):
                return 'https://' + input_value
            return input_value
        elif self._is_valid_youtube_id(input_value):
            return f'https://www.youtube.com/watch?v={input_value}'
        return None

    def _search_youtube(self, search_query):
        self.window[self.status_text_key].update(f"Searching '{search_query}', please wait...")
        self.window.refresh()
        if ydl_available:
            try:
                search_opts = {
                    'default_search': 'ytsearch1:',
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'skip_download': True,
                    'extract_flat': 'in_playlist',
                    'forcejson': True,
                }
                with YoutubeDL(search_opts) as ydl:
                    result = ydl.extract_info(search_query, download=False)
                    if result and 'entries' in result and result['entries']:
                        video_id = result['entries'][0].get('id')
                        if video_id:
                            found_url = f"https://www.youtube.com/watch?v={video_id}"
                            self.window[self.status_text_key].update("Result found, playing...")
                            return found_url
            except Exception as e:
                self.window[self.status_text_key].update(f"Search error: {e}")
        self.window[self.status_text_key].update("Search failed, opening in browser.")
        encoded_search = urllib.parse.quote(search_query)
        return f"https://www.youtube.com/results?search_query={encoded_search}"

    def _get_video_stream_url(self, youtube_url):
        self.window[self.status_text_key].update("Getting video stream URL...")
        self.window.refresh()
        if ydl_available:
            try:
                ydl_opts = {
                    'format': 'best[height<=720][ext=mp4]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'skip_download': True,
                    'nocheckcertificate': True,
                    'retries': 3,
                    'socket_timeout': 15,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_url, download=False)
                    if 'url' in info:
                        stream_url = info['url']
                        return stream_url
                    if 'formats' in info:
                        for f in reversed(info['formats']):
                            if (f.get('vcodec') != 'none' and f.get('acodec') != 'none' and
                                'url' in f and f.get('ext') == 'mp4'):
                                return f['url']
                        for f in reversed(info['formats']):
                            if (f.get('vcodec') != 'none' and 'url' in f and f.get('ext') == 'mp4'):
                                return f['url']
                        for f in reversed(info['formats']):
                            if 'url' in f:
                                return f['url']
            except Exception as e:
                self.window[self.status_text_key].update(f"Stream extraction error: {e}")
        return None

    def _play_video(self, youtube_url):
        self.window[self.status_text_key].update("Loading video, please wait...")
        self.window.refresh()
        if self.media_player.is_playing():
            self.media_player.stop()
        stream_url = self._get_video_stream_url(youtube_url)
        if stream_url:
            media = self.vlc_instance.media_new(stream_url)
            media.add_option(':network-caching=5000')
            media.add_option(':sout-keep')
            self.media_player.set_media(media)
            self.media_player.play()
            self.current_loaded_url = youtube_url
            self.window[self.status_text_key].update("Video is playing.")
            self.window['-PAUSE_RESUME-'].update(text='⏸️ Pause', button_color=('white', '#FBC02D'))
        else:
            self.window[self.status_text_key].update("Could not get video stream, opening in browser.")
            webbrowser.open(youtube_url)
            sg.popup_notify("Video could not be played, opening in browser.", title="Playback Error")

    def handle_event(self, event, values):
        if event in (sg.WIN_CLOSED, 'Close'):
            if self.media_player and self.media_player.is_playing():
                self.media_player.stop()
            if hasattr(self, 'media_player') and self.media_player:
                self.media_player.release()
                self.media_player = None
            if hasattr(self, 'vlc_instance') and self.vlc_instance:
                self.vlc_instance.release()
                self.vlc_instance = None
            return 'close'

        if not self.video_player_ready:
            if event == '-PLAY-' or event == '-OPEN_EXTERNALLY-':
                input_value = values['-URL_OR_ID-']
                url_to_open = self._construct_youtube_url(input_value)
                if not url_to_open:
                    encoded_search = urllib.parse.quote(input_value)
                    url_to_open = f"https://www.youtube.com/results?search_query={encoded_search}"
                if url_to_open:
                    webbrowser.open(url_to_open)
                else:
                    sg.popup_error("Invalid input. Please enter a YouTube URL, Video ID, or search term.", title="Invalid Input")
            return None

        if event == '-PLAY-':
            input_value = values['-URL_OR_ID-']
            if not input_value:
                sg.popup_error("Please enter a URL, Video ID, or search term.", title="Input Required")
                return
            self.window[self.status_text_key].update("Searching, please wait...")
            self.window.refresh()
            youtube_url = self._construct_youtube_url(input_value)
            if not youtube_url:
                youtube_url = self._search_youtube(input_value)
                if not youtube_url or "results?search_query=" in youtube_url:
                    if youtube_url: webbrowser.open(youtube_url)
                    self.window[self.status_text_key].update("No results found.")
                    return
            self._play_video(youtube_url)

        elif event == '-PAUSE_RESUME-':
            if self.media_player and self.current_loaded_url:
                state = self.media_player.get_state()
                if state == vlc.State.Playing:
                    self.media_player.pause()
                    self.window['-PAUSE_RESUME-'].update(text='▶️ Resume', button_color=('white', '#388E3C'))
                    self.window[self.status_text_key].update("Video paused.")
                elif state in (vlc.State.Paused, vlc.State.Stopped):
                    self.media_player.play()
                    self.window['-PAUSE_RESUME-'].update(text='⏸️ Pause', button_color=('white', '#FBC02D'))
                    self.window[self.status_text_key].update("Video is playing.")
            else:
                self.window[self.status_text_key].update("No active video to pause/resume.")

        return None