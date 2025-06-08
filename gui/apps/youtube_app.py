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
        self.title_font = ('Helvetica', 16, 'bold')
        self.label_font = ('Helvetica', 11)
        self.input_font = ('Helvetica', 10)
        self.button_font = ('Helvetica', 10)
        self.default_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        self.vlc_instance = None
        self.media_player = None
        self.video_player_ready = False
        self.current_loaded_url = None

        libraries_available = vlc is not None and ydl_available
        
        if not libraries_available:
            error_message = "Gerekli kütüphaneler bulunamadı:\n"
            if not ydl_available:
                error_message += "- 'yt-dlp' (Kurulum: pip install yt-dlp)\n"
            if vlc is None:
                error_message += "- 'python-vlc' (Kurulum: pip install python-vlc)\n"
                error_message += "  VE VLC Media Player'ın sisteminizde kurulu olduğundan emin olun.\n"
            error_message += "Uygulama içi video oynatma kullanılamayacak."
            
            layout_top = [
                [sg.Text('MiniOS YouTube Açıcı', font=self.title_font, justification='center', expand_x=True, pad=((0,0),(10,5)))],
                [
                    sg.Text('URL/Arama:', font=self.label_font),
                    sg.Input(key='-URL_OR_ID-', expand_x=True, font=self.input_font, default_text="Arama terimi veya URL girin"),
                    sg.Button('Tarayıcıda Aç', font=self.button_font, key='-OPEN_EXTERNALLY-'),
                    sg.Push(),
                    sg.Button('Kapat', font=self.button_font, key='Close', pad=((5,5),(5,5)))
                ],
                [sg.Text(error_message, font=self.label_font, text_color='red')]
            ]
            layout_video = []
            window_title = 'YouTube Açıcı (Kütüphaneler Eksik)'
            initial_size = (750, 220)
        else:
            try:
                self.vlc_instance = vlc.Instance('--no-video-title-show', '--quiet', '--avcodec-hw=none')
                self.media_player = self.vlc_instance.media_player_new()
                print("VLC örneği ve media player başarıyla başlatıldı.")
            except Exception as e:
                print(f"VLC başlatılamadı: {e}")
                libraries_available = False
                error_message = f"VLC başlatılamadı: {e}\nLütfen VLC Media Player'ın doğru kurulduğundan emin olun.\nUygulama içi video oynatma kullanılamayacak."
                layout_top = [
                    [sg.Text('MiniOS YouTube Açıcı', font=self.title_font, justification='center', expand_x=True, pad=((0,0),(10,5)))],
                    [
                        sg.Text('URL/Arama:', font=self.label_font),
                        sg.Input(key='-URL_OR_ID-', expand_x=True, font=self.input_font, default_text="Arama terimi veya URL girin"),
                        sg.Button('Tarayıcıda Aç', font=self.button_font, key='-OPEN_EXTERNALLY-'),
                        sg.Push(),
                        sg.Button('Kapat', font=self.button_font, key='Close', pad=((5,5),(5,5)))
                    ],
                    [sg.Text(error_message, font=self.label_font, text_color='red')]
                ]
                layout_video = []
                window_title = 'YouTube Açıcı (VLC Hatası)'
                initial_size = (750, 220)

            if libraries_available:
                layout_top = [
                    [sg.Text('MiniOS YouTube Oynatıcı', font=self.title_font, justification='center', expand_x=True, pad=((0,0),(10,5)))],
                    [
                        sg.Text('URL/Arama:', font=self.label_font),
                        sg.Input(key='-URL_OR_ID-', expand_x=True, font=self.input_font, default_text="Arama terimi veya URL girin"),
                        sg.Button('Ara/Oynat', font=self.button_font, key='-PLAY-'),
                        sg.Button('Duraklat', font=self.button_font, key='-PAUSE_RESUME-'),
                        sg.Push(),
                        sg.Button('Kapat', font=self.button_font, key='Close', pad=((5,5),(5,5)))
                    ],
                    [sg.Text("URL/Video ID girin veya arama yapın.", font=('Helvetica', 9, 'italic'), text_color='gray')]
                ]
                layout_video = [[sg.Image(key='-VIDEO_OUTPUT-', background_color='black', size=(640, 360))]]
                window_title = 'MiniOS YouTube Oynatıcı'
                initial_size = (750, 500)

        layout = layout_top + layout_video
        self.window = sg.Window(window_title, layout, finalize=True, resizable=True, size=initial_size, element_justification='left')

        if libraries_available and self.media_player and layout_video:
            try:
                video_widget = self.window['-VIDEO_OUTPUT-'].Widget
                video_widget_id = video_widget.winfo_id()

                if sys.platform.startswith('linux'):
                    self.media_player.set_xwindow(video_widget_id)
                elif sys.platform.startswith('win'):
                    self.media_player.set_hwnd(video_widget_id)
                elif sys.platform.startswith('darwin'):
                    sg.popup_notify("macOS'ta video yerleştirme kararsız olabilir.", title="macOS Uyarısı")
                    self.video_player_ready = False
                else:
                    self.video_player_ready = True

                if not sys.platform.startswith('darwin'):
                     self.video_player_ready = True
                print(f"Video oynatıcı hazır durumu: {self.video_player_ready}")

            except Exception as e:
                print(f"VLC video çıkışı ayarlama hatası: {e}")
                sg.popup_error(f"Video gösterimi ayarlama hatası: {e}", title="VLC Kurulum Hatası")
                self.video_player_ready = False
        
        if not libraries_available:
            self.video_player_ready = False

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
        print(f"'{search_query}' için yt-dlp ile arama yapılıyor...")
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
                            print(f"Arama sonucu bulundu: {found_url}")
                            return found_url
                    print("yt-dlp aramasında sonuç bulunamadı veya ID alınamadı.")
            except Exception as e:
                print(f"yt-dlp arama hatası: {e}")
        
        print("yt-dlp ile arama başarısız, tarayıcıda arama sayfası açılıyor.")
        encoded_search = urllib.parse.quote(search_query)
        return f"https://www.youtube.com/results?search_query={encoded_search}"
        
    def _get_video_stream_url(self, youtube_url):
        print(f"'{youtube_url}' için stream URL'si alınıyor...")
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
                        print(f"Stream URL (anahtar 'url'): {stream_url[:70]}...")
                        return stream_url
                    
                    if 'formats' in info:
                        for f in reversed(info['formats']):
                            if (f.get('vcodec') != 'none' and f.get('acodec') != 'none' and
                                'url' in f and f.get('ext') == 'mp4'):
                                stream_url = f['url']
                                print(f"Stream URL (progressive mp4 format): {stream_url[:70]}..., Format: {f.get('format_note', f.get('format_id'))}")
                                return stream_url
                        for f in reversed(info['formats']):
                             if (f.get('vcodec') != 'none' and 'url' in f and
                                 f.get('ext') == 'mp4'):
                                stream_url = f['url']
                                print(f"Stream URL (video-only mp4 format): {stream_url[:70]}..., Format: {f.get('format_note', f.get('format_id'))}")
                                return stream_url
                        for f in reversed(info['formats']):
                            if 'url' in f:
                                stream_url = f['url']
                                print(f"Stream URL (herhangi bir format): {stream_url[:70]}..., Format: {f.get('format_note', f.get('format_id'))}")
                                return stream_url
                    print("Stream URL'si formatlardan da alınamadı.")
            except Exception as e:
                print(f"yt-dlp stream çıkarma hatası: {e}")
        return None

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
            print("YouTubeApp kapatılıyor, VLC kaynakları serbest bırakıldı.")
            return 'close'

        if not self.video_player_ready:
            if event == '-PLAY-' or event == '-OPEN_EXTERNALLY-':
                input_value = values['-URL_OR_ID-']
                url_to_open = self._construct_youtube_url(input_value)
                if not url_to_open:
                    print(f"Geçerli URL/ID değil, '{input_value}' için tarayıcıda arama yapılıyor.")
                    encoded_search = urllib.parse.quote(input_value)
                    url_to_open = f"https://www.youtube.com/results?search_query={encoded_search}"
                
                if url_to_open:
                    print(f"Tarayıcıda açılıyor: {url_to_open}")
                    webbrowser.open(url_to_open)
                else:
                    sg.popup_error("Geçersiz giriş. Lütfen bir YouTube URL'si, Video ID'si veya arama terimi girin.", title="Hatalı Giriş")
            return None

        if event == '-PLAY-':
            input_value = values['-URL_OR_ID-']
            if not input_value:
                sg.popup_error("Lütfen bir URL, Video ID'si veya arama terimi girin.", title="Giriş Gerekli")
                return

            youtube_url = self._construct_youtube_url(input_value)

            if not youtube_url:
                sg.popup_notify(f"'{input_value}' için arama yapılıyor...", title="YouTube Arama", display_duration_in_ms=2000)
                youtube_url = self._search_youtube(input_value)
                
                if not youtube_url or "results?search_query=" in youtube_url:
                    sg.popup_notify("Arama sonucu bulunamadı veya tarayıcıda açılacak.", title="Arama Sonucu", display_duration_in_ms=2000)
                    if youtube_url: webbrowser.open(youtube_url)
                    return
            
            print(f"Oynatılacak YouTube URL'si: {youtube_url}")
            
            if self.media_player.is_playing():
                self.media_player.stop()
            
            stream_url = self._get_video_stream_url(youtube_url)
            
            if stream_url:
                print(f"Alınan stream URL: {stream_url[:70]}...")
                media = self.vlc_instance.media_new(stream_url)
                media.add_option(':network-caching=5000')
                media.add_option(':sout-keep')
                self.media_player.set_media(media)
                self.media_player.play()
                
                playback_started = False
                for i in range(10):
                    time.sleep(0.5)
                    current_state = self.media_player.get_state()
                    print(f"VLC durumu ({i+1}/10): {current_state}")
                    if current_state in [vlc.State.Playing, vlc.State.Buffering, vlc.State.Opening]:
                        playback_started = True
                        print("VLC oynatma/tamponlama/açılma başladı.")
                        break
                    if current_state == vlc.State.Error:
                        print("VLC durumu: Hata!")
                        break
                
                if not playback_started or self.media_player.get_state() == vlc.State.Error:
                    error_state = self.media_player.get_state()
                    print(f"VLC oynatma 5 saniye içinde başlamadı veya hata oluştu (Durum: {error_state}). Tarayıcı açılıyor...")
                    self.media_player.stop()
                    webbrowser.open(youtube_url)
                    sg.popup_notify("Video oynatılamadı, tarayıcıda açılıyor.", title="Oynatma Hatası")
            else:
                print("Stream URL alınamadı, tarayıcı açılıyor.")
                webbrowser.open(youtube_url)
                sg.popup_notify("Video stream URL'si alınamadı, tarayıcıda açılıyor.", title="Stream Hatası")
                
        elif event == '-PAUSE_RESUME-':
            if self.media_player and self.current_loaded_url:
                self.media_player.pause() 
                current_state_after_toggle = self.media_player.get_state()
                if current_state_after_toggle == vlc.State.Paused:
                    self.window['-PAUSE_RESUME-'].update(text='Devam Et')
                    print("Video duraklatıldı.")
                elif current_state_after_toggle == vlc.State.Playing:
                    self.window['-PAUSE_RESUME-'].update(text='Duraklat')
                    print("Video devam ettiriliyor.")
            else:
                print("Duraklatılacak/devam ettirilecek aktif bir video yok.")
        
        return None

if __name__ == '__main__':
    libraries_available = vlc is not None and (ydl_available)
    if not libraries_available:
        missing = []
        if not ydl_available:
            missing.append("yt-dlp")
        if vlc is None:
            missing.append("python-vlc")
        print(f"Missing libraries: {', '.join(missing)}. Install them for YouTube playback.")
    else:
        print("Required libraries found. Ensure VLC Media Player is installed system-wide.")

    sg.theme('DarkBlue3') 
    app = YouTubeApp()
    while True:
        event, values = app.window.read(timeout=100) 
        if app.handle_event(event, values) == 'close':
            break
    if app.window and not app.window.was_closed():
        app.window.close()