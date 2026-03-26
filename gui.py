import customtkinter as ctk
import threading
import os
import gc
import sys
import tkinter.messagebox as messagebox
from main import generate_full_video
from script_gen import CATEGORY_NAMES
from dotenv import load_dotenv, set_key
from PIL import Image
import youtube_uploader
import PIL
from audio_gen import get_edge_tts_voices, get_edge_tts_languages, EDGE_LANGUAGE_NAMES, clone_voice_elevenlabs, clone_voice_dubvoice

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Edge TTS ses verileri (bir kez yukle)
        try:
            self._edge_voices = get_edge_tts_voices()
            self._edge_languages = get_edge_tts_languages()
        except Exception:
            self._edge_voices = {"tr-TR": [{"short": "tr-TR-AhmetNeural", "name": "Ahmet", "gender": "Male", "label": "Ahmet (Erkek)"}, {"short": "tr-TR-EmelNeural", "name": "Emel", "gender": "Female", "label": "Emel (Kadin)"}]}
            self._edge_languages = [("tr-TR", "Turkce"), ("en-US", "Ingilizce (ABD)")]

        # Dil gosterim isimleri -> locale kodu mapping
        self._lang_display_to_locale = {display: locale for locale, display in self._edge_languages}
        self._lang_display_names = [display for _, display in self._edge_languages]

        # Window configuration
        self.title("YTAUTO Video Studio - Ultra Edition")
        self.geometry("1150x800")
        
        # Grid layout (sidebar & main content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Theme & Colors (Premium Cyberpunk Dark)
        ctk.set_appearance_mode("Dark")
        
        # Premium Color Palette
        self.bg_color = "#08090D"         # Amoled Black
        self.sidebar_color = "#0D0E16"    # Deep Navy Sidebar
        self.card_color = "#12141E"       # Midnight Blue Card
        self.accent_color = "#00D2FF"     # Cyber Cyan
        self.accent_purple = "#9D50BB"    # Neon Purple
        self.text_primary = "#FFFFFF"
        self.text_secondary = "#8E9297"
        self.border_color = "#222533"
        self.success_color = "#00F260"
        
        self.configure(fg_color=self.bg_color)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=self.sidebar_color, border_width=1, border_color=self.border_color)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # Load Logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
            if not os.path.exists(logo_path):
                logo_path = r"C:\Users\abidin\.gemini\antigravity\brain\5f8ccae4-ed76-4c61-aa49-54245b18ee75\video_bot_logo_1772565357878.png"
            if os.path.exists(logo_path):
                logo_img = ctk.CTkImage(light_image=Image.open(logo_path), dark_image=Image.open(logo_path), size=(100, 100))
                self.logo_image_label = ctk.CTkLabel(self.sidebar_frame, text="", image=logo_img)
                self.logo_image_label.grid(row=0, column=0, padx=20, pady=(30, 0))
            else:
                raise FileNotFoundError()
        except:
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="YTAUTO", font=ctk.CTkFont(size=24, weight="bold"))
            self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 0))
        
        self.logo_sub_label = ctk.CTkLabel(self.sidebar_frame, text="VIDEO AUTOMATION", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.accent_purple)
        self.logo_sub_label.grid(row=1, column=0, padx=20, pady=(0, 40))

        # Modern Sidebar Buttons
        self.btn_single = ctk.CTkButton(
            self.sidebar_frame, text="   ⚡  Tekil Üretim", command=self.show_single, 
            fg_color="transparent", anchor="w", height=50, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=self.text_secondary,
            hover_color="#1A1C26"
        )
        self.btn_single.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.btn_batch = ctk.CTkButton(
            self.sidebar_frame, text="   📦  Toplu Üretim", command=self.show_batch, 
            fg_color="transparent", anchor="w", height=50, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=self.text_secondary,
            hover_color="#1A1C26"
        )
        self.btn_batch.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.btn_channels = ctk.CTkButton(
            self.sidebar_frame, text="   📺  Kanallar", command=self.show_channels, 
            fg_color="transparent", anchor="w", height=50, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=self.text_secondary,
            hover_color="#1A1C36"
        )
        self.btn_channels.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame, text="   ⚙️  Sistem Ayarları", command=self.show_settings, 
            fg_color="transparent", anchor="w", height=50, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=self.text_secondary,
            hover_color="#1A1C26"
        )
        self.btn_settings.grid(row=5, column=0, padx=15, pady=5, sticky="ew")

        # Sidebar Bottom Status
        self.status_card = ctk.CTkFrame(self.sidebar_frame, fg_color="#12141C", corner_radius=12, height=100)
        self.status_card.grid(row=11, column=0, padx=15, pady=20, sticky="ew")
        
        ctk.CTkLabel(self.status_card, text="SİSTEM DURUMU", font=ctk.CTkFont(size=9, weight="bold"), text_color=self.text_secondary).pack(pady=(12, 5))
        self.sidebar_status_indicator = ctk.CTkLabel(self.status_card, text="● Çevrimiçi", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.success_color)
        self.sidebar_status_indicator.pack(pady=(0, 10))

        # --- Main Content Area ---
        self.main_container = ctk.CTkFrame(self, corner_radius=25, fg_color=self.card_color, border_width=1, border_color=self.border_color)
        self.main_container.grid(row=0, column=1, padx=25, pady=25, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)

        # Initialize the different "views" (frames)
        self.frames = {}
        self.init_single_view()
        self.init_batch_view()
        self.init_channels_view()
        self.init_settings_view()

        # Token klasorunu hazirla
        self.tokens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channel_tokens")
        os.makedirs(self.tokens_dir, exist_ok=True)

        # Show initial view
        self.show_single()
        self.refresh_channels()
        
        self.check_env()

    def init_single_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["single"] = f
        f.grid_columnconfigure(0, weight=1)

        # Header section
        header_frame = ctk.CTkFrame(f, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        
        ctk.CTkLabel(header_frame, text="Video Studio", font=ctk.CTkFont(size=32, weight="bold"), text_color=self.text_primary).pack(side="left", padx=40)
        ctk.CTkLabel(header_frame, text="CREATIVE MODE", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.accent_color, fg_color="#1A3A4A", corner_radius=5, padx=8, pady=2).pack(side="left", padx=(0, 40))

        # Scrollable Form Area
        form_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent", height=500)
        form_scroll.grid(row=1, column=0, padx=20, sticky="nsew")
        form_scroll.grid_columnconfigure(0, weight=1)

        # 1. Konu ve Kategori Grubu
        group1 = ctk.CTkFrame(form_scroll, fg_color="#161824", corner_radius=18, border_width=1, border_color=self.border_color)
        group1.pack(fill="x", padx=20, pady=10)
        group1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group1, text="VİDEO İÇERİĞİ", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_color).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group1, text="Konu / Talimat:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        self.topic_textbox = ctk.CTkTextbox(group1, height=120, fg_color="#0A0B10", border_color=self.border_color, border_width=1, corner_radius=12, font=ctk.CTkFont(size=13))
        self.topic_textbox.grid(row=1, column=1, padx=(0, 25), pady=15, sticky="ew")
        self.topic_textbox.insert("1.0", "Buraya video konusunu veya 2000 kelimelik talimatınızı girebilirsiniz...")


        ctk.CTkLabel(group1, text="Kategori / Dil:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=10, sticky="e")
        cat_row = ctk.CTkFrame(group1, fg_color="transparent")
        cat_row.grid(row=2, column=1, sticky="ew", padx=(0, 25), pady=10)
        cat_row.grid_columnconfigure(0, weight=1)

        self.category_var = ctk.StringVar(value=CATEGORY_NAMES[0])
        self.category_menu = ctk.CTkOptionMenu(cat_row, variable=self.category_var, values=CATEGORY_NAMES, width=220, height=38, fg_color="#1F212E", button_color="#2A2D3A", button_hover_color="#3A3D4E", corner_radius=10)
        self.category_menu.grid(row=0, column=0, sticky="w")

        self.language_var = ctk.StringVar(value="Turkce")
        self.language_menu = ctk.CTkOptionMenu(cat_row, variable=self.language_var, values=self._lang_display_names, width=180, height=38, fg_color="#1F212E", button_color="#2A2D3A", button_hover_color="#3A3D4E", corner_radius=10)
        self.language_menu.grid(row=0, column=1, padx=(10, 0), sticky="w")

        ctk.CTkLabel(group1, text="İçerik Yazarı:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=25, pady=10, sticky="e")
        self.content_provider_var = ctk.StringVar(value="Google Gemini")
        self.content_provider_menu = ctk.CTkOptionMenu(group1, variable=self.content_provider_var, values=["Google Gemini", "Kie.ai (Gemini 3.1 Pro)"], height=38, fg_color="#1F212E", button_color="#2A2D3A", button_hover_color="#3A3D4E", corner_radius=10)
        self.content_provider_menu.grid(row=3, column=1, padx=(0, 25), pady=15, sticky="w")

        # 2. Teknik Ayarlar Grubu
        group2 = ctk.CTkFrame(form_scroll, fg_color="#161824", corner_radius=18, border_width=1, border_color=self.border_color)
        group2.pack(fill="x", padx=20, pady=10)
        group2.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group2, text="TEKNİK AYARLAR", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_color).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group2, text="Kelime / Format:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        f_row = ctk.CTkFrame(group2, fg_color="transparent")
        f_row.grid(row=1, column=1, sticky="ew", padx=(0, 25), pady=10)
        
        self.word_count_entry = ctk.CTkEntry(f_row, width=80, height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.word_count_entry.insert(0, "500")
        self.word_count_entry.pack(side="left")
        
        self.orientation_var = ctk.StringVar(value="Yatay (16:9)")
        self.orientation_menu = ctk.CTkOptionMenu(f_row, variable=self.orientation_var, values=["Yatay (16:9)", "Dikey (9:16 Shorts)"], width=160, height=38, fg_color="#1F212E", corner_radius=10)
        self.orientation_menu.pack(side="left", padx=(15, 0))
        
        self.use_gpu_var = ctk.BooleanVar(value=True)
        self.gpu_checkbox = ctk.CTkCheckBox(f_row, text="RTX 4060 Hızlandırma", variable=self.use_gpu_var, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.success_color, hover_color="#252833", checkmark_color=self.success_color)
        self.gpu_checkbox.pack(side="left", padx=(20, 0))

        ctk.CTkLabel(group2, text="Çıktı Klasörü:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=10, sticky="e")
        out_f = ctk.CTkFrame(group2, fg_color="transparent")
        out_f.grid(row=2, column=1, sticky="ew", padx=(0, 25), pady=10)
        out_f.grid_columnconfigure(0, weight=1)
        self.output_dir_entry = ctk.CTkEntry(out_f, placeholder_text="output/", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.output_dir_entry.grid(row=0, column=0, sticky="ew")
        self.browse_btn = ctk.CTkButton(out_f, text="Seç", width=70, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_output_dir)
        self.browse_btn.grid(row=0, column=1, padx=(10, 0))

        ctk.CTkLabel(group2, text="Video Kaynağı:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=25, pady=10, sticky="e")
        vsrc_row = ctk.CTkFrame(group2, fg_color="transparent")
        vsrc_row.grid(row=3, column=1, sticky="ew", padx=(0, 25), pady=15)
        vsrc_row.grid_columnconfigure(0, weight=1)

        self.video_source_var = ctk.StringVar(value="Pexels (Otomatik İndir)")
        self.video_source_menu = ctk.CTkOptionMenu(
            vsrc_row, variable=self.video_source_var, 
            values=[
                "Pexels (Otomatik İndir)", 
                "Pixabay (Otomatik İndir)",
                "Manuel (Kendi Videolarım)", 
                "AI Görsel Üretimi (PicLumen)", 
                "Leonardo.ai (Fotoğraf)",
                "Leonardo.ai (Video)",
                "Pexels (Görsel/Fotoğraf)", 
                "Pexels (Karma: 5 Video + 5 Fotoğraf)",
                "Pexels + Pixabay (Hibrit Mod)"
            ], 
            height=38, command=self._on_video_source_change, fg_color="#1F212E", corner_radius=10
        )
        self.video_source_menu.grid(row=0, column=0, sticky="ew")

        self.browse_videos_btn = ctk.CTkButton(vsrc_row, text="Video Seç", width=90, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_manual_videos, state="disabled")
        self.browse_videos_btn.grid(row=0, column=1, padx=(10, 0))

        self.manual_video_label = ctk.CTkLabel(vsrc_row, text="Pexels modu aktif", text_color="gray", font=ctk.CTkFont(size=10))
        self.manual_video_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.manual_video_files = []

        # 3. Ses ve Müzik Grubu
        group3 = ctk.CTkFrame(form_scroll, fg_color="#161824", corner_radius=18, border_width=1, border_color=self.border_color)
        group3.pack(fill="x", padx=20, pady=10)
        group3.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group3, text="SES & MÜZİK", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_color).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        # Voice and Subtitle Toggle Row
        toggle_row = ctk.CTkFrame(group3, fg_color="transparent")
        toggle_row.grid(row=1, column=0, columnspan=2, padx=25, pady=5, sticky="w")

        self.enable_voice_var = ctk.BooleanVar(value=True)
        self.voice_checkbox = ctk.CTkCheckBox(toggle_row, text="AI Seslendirme Aktif", variable=self.enable_voice_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_color)
        self.voice_checkbox.pack(side="left", padx=(0, 20))

        self.enable_subtitles_var = ctk.BooleanVar(value=True)
        self.subtitle_checkbox = ctk.CTkCheckBox(toggle_row, text="Altyazılar Aktif", variable=self.enable_subtitles_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_color)
        self.subtitle_checkbox.pack(side="left", padx=(0, 20))
        
        self.subtitle_style_var = ctk.StringVar(value="Standart (Kutu)")
        self.subtitle_style_menu = ctk.CTkOptionMenu(toggle_row, variable=self.subtitle_style_var, values=["Standart (Kutu)", "Dinamik (Shorts)", "Neon Mavi", "Altın Işıltı", "Modern Sade"], width=135, height=32, font=ctk.CTkFont(size=11, weight="bold"), fg_color="#1F212E", corner_radius=8)
        self.subtitle_style_menu.pack(side="left")

        ctk.CTkLabel(group3, text="Ses Motoru:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=10, sticky="e")
        self.tts_provider_var = ctk.StringVar(value="Edge TTS (Ücretsiz)")
        self.tts_provider_menu = ctk.CTkOptionMenu(group3, variable=self.tts_provider_var, values=["Edge TTS (Ücretsiz)", "Spesh Audio", "DubVoice.ai", "OtomasyonLabs", "VoysLity", "ElevenLabs"], height=38, fg_color="#1F212E", corner_radius=10)
        self.tts_provider_menu.grid(row=2, column=1, padx=(0, 25), pady=10, sticky="w")

        ctk.CTkLabel(group3, text="Edge Dil:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=25, pady=10, sticky="e")
        self.edge_lang_var = ctk.StringVar(value="Turkce")
        self.edge_lang_menu = ctk.CTkOptionMenu(group3, variable=self.edge_lang_var, values=self._lang_display_names, width=200, height=38, fg_color="#1F212E", corner_radius=10, command=self._on_edge_lang_change)
        self.edge_lang_menu.grid(row=3, column=1, padx=(0, 25), pady=10, sticky="w")

        ctk.CTkLabel(group3, text="Edge Sesi:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=4, column=0, padx=25, pady=10, sticky="e")
        tr_voices = [v["label"] for v in self._edge_voices.get("tr-TR", [])]
        self.edge_voice_var = ctk.StringVar(value=tr_voices[0] if tr_voices else "Ahmet (Erkek)")
        self.edge_voice_menu = ctk.CTkOptionMenu(group3, variable=self.edge_voice_var, values=tr_voices or ["Ahmet (Erkek)"], width=200, height=38, fg_color="#1F212E", corner_radius=10)
        self.edge_voice_menu.grid(row=4, column=1, padx=(0, 25), pady=10, sticky="w")

        ctk.CTkLabel(group3, text="Müzik:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=5, column=0, padx=25, pady=10, sticky="e")
        m_row = ctk.CTkFrame(group3, fg_color="transparent")
        m_row.grid(row=5, column=1, sticky="ew", padx=(0, 25), pady=10)
        m_row.grid_columnconfigure(0, weight=1)

        self.bgm_entry = ctk.CTkEntry(m_row, placeholder_text="Müzik dosyası seçin...", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.bgm_entry.grid(row=0, column=0, sticky="ew")
        self.browse_bgm_btn = ctk.CTkButton(m_row, text="Gözat", width=70, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_bgm)
        self.browse_bgm_btn.grid(row=0, column=1, padx=(10, 0))

        ctk.CTkLabel(group3, text="Müzik Volüm:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=6, column=0, padx=25, pady=10, sticky="e")
        self.bgm_vol_slider = ctk.CTkSlider(group3, from_=0.0, to=1.0, height=18, button_color=self.accent_color, progress_color=self.accent_color, button_hover_color=self.accent_purple)
        self.bgm_vol_slider.set(0.1)
        self.bgm_vol_slider.grid(row=6, column=1, padx=(0, 25), pady=15, sticky="ew")

        # 4. İçerik Ayarları Grubu
        group4_ui = ctk.CTkFrame(form_scroll, fg_color="#161824", corner_radius=18, border_width=1, border_color=self.border_color)
        group4_ui.pack(fill="x", padx=20, pady=10)
        group4_ui.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group4_ui, text="İÇERİK AYARLARI", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_color).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group4_ui, text="Asset Sayısı:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        self.asset_count_slider = ctk.CTkSlider(group4_ui, from_=1, to=20, number_of_steps=19, height=18, button_color=self.accent_color, progress_color=self.accent_color)
        self.asset_count_slider.set(10)
        self.asset_count_slider.grid(row=1, column=1, padx=(0, 25), pady=15, sticky="ew")
        
        self.asset_count_label = ctk.CTkLabel(group4_ui, text="10", text_color=self.accent_color, font=ctk.CTkFont(size=12, weight="bold"))
        self.asset_count_label.grid(row=1, column=2, padx=15)
        self.asset_count_slider.configure(command=lambda v: self.asset_count_label.configure(text=str(int(v))))

        self.auto_asset_var = ctk.BooleanVar(value=False)
        self.auto_asset_checkbox = ctk.CTkCheckBox(group4_ui, text="Zekâ Modu (Otomatik Sayı Belirle)", variable=self.auto_asset_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_color)
        self.auto_asset_checkbox.grid(row=2, column=1, padx=25, pady=10, sticky="w")

        # 5. YouTube Ayarları Grubu
        group4 = ctk.CTkFrame(form_scroll, fg_color="#181414", corner_radius=18, border_width=1, border_color="#3D1A1A")
        group4.pack(fill="x", padx=20, pady=10)
        group4.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group4, text="YOUTUBE YÜKLEME", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF4B4B").grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        self.enable_youtube_var = ctk.BooleanVar(value=False)
        self.youtube_checkbox = ctk.CTkCheckBox(group4, text="Otomatik Yükle", variable=self.enable_youtube_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color="#FF4B4B")
        self.youtube_checkbox.grid(row=1, column=0, padx=25, pady=15, sticky="w")

        ctk.CTkLabel(group4, text="Kanal Seç:", text_color=self.text_secondary, font=ctk.CTkFont(size=11)).grid(row=1, column=1, padx=(0, 5), sticky="e")
        self.yt_channel_var = ctk.StringVar(value="Varsayılan")
        self.yt_channel_menu = ctk.CTkOptionMenu(group4, variable=self.yt_channel_var, values=["Varsayılan"], width=140, height=30, fg_color="#1F212E", corner_radius=8)
        self.yt_channel_menu.grid(row=1, column=2, padx=(0, 25), pady=15, sticky="w")

        # 5. Video Efektleri Grubu (Single)
        group5 = ctk.CTkFrame(form_scroll, fg_color="#161824", corner_radius=18, border_width=1, border_color=self.border_color)
        group5.pack(fill="x", padx=20, pady=10)
        group5.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group5, text="VİDEO EFEKTLERİ", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_color).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        fx_row = ctk.CTkFrame(group5, fg_color="transparent")
        fx_row.grid(row=1, column=0, columnspan=2, padx=25, pady=15, sticky="w")

        self.enable_darken_var = ctk.BooleanVar(value=False)
        self.darken_checkbox = ctk.CTkCheckBox(fx_row, text="Karanlık", variable=self.enable_darken_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_color)
        self.darken_checkbox.pack(side="left", padx=(0, 20))

        self.enable_fog_var = ctk.BooleanVar(value=False)
        self.fog_checkbox = ctk.CTkCheckBox(fx_row, text="Sis", variable=self.enable_fog_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_color)
        self.fog_checkbox.pack(side="left", padx=(0, 20))

        self.enable_sparks_var = ctk.BooleanVar(value=False)
        self.sparks_checkbox = ctk.CTkCheckBox(fx_row, text="Kıvılcım", variable=self.enable_sparks_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_color)
        self.sparks_checkbox.pack(side="left")

        # Bottom Action Bar
        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.grid(row=2, column=0, pady=25, padx=40, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.generate_btn = ctk.CTkButton(
            action_frame, text="🚀  VİDEOYU OLUŞTURMAYA BAŞLA", 
            height=60, font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.accent_color, hover_color="#00A8CC", text_color="#000000",
            corner_radius=15, border_width=0,
            command=self.start_generation
        )
        self.generate_btn.grid(row=0, column=0, sticky="ew")

        # Logging / Progress Section
        info_frame = ctk.CTkFrame(f, fg_color="#0D0E16", height=180, corner_radius=15, border_width=1, border_color=self.border_color)
        info_frame.grid(row=3, column=0, padx=40, pady=(0, 30), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(info_frame, mode="determinate", progress_color=self.accent_color, height=10, corner_radius=5)
        self.progress_bar.grid(row=0, column=0, padx=25, pady=(20, 5), sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(info_frame, text="Sistem hazıra bekliyor...", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_color)
        self.status_label.grid(row=1, column=0, padx=25, pady=5)

        self.log_box = ctk.CTkTextbox(info_frame, height=90, fg_color="transparent", text_color="#A0A0A0", font=ctk.CTkFont(size=12))
        self.log_box.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.log_box.configure(state="disabled")

    def init_batch_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["batch"] = f
        f.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(f, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(30, 20), sticky="ew")
        ctk.CTkLabel(header_frame, text="Batch Studio", font=ctk.CTkFont(size=32, weight="bold"), text_color=self.text_primary).pack(side="left", padx=40)
        ctk.CTkLabel(header_frame, text="AUTOMATION", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.accent_purple, fg_color="#3A1A4A", corner_radius=5, padx=8, pady=2).pack(side="left", padx=(0, 40))

        # Scrollable
        form_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent", height=500)
        form_scroll.grid(row=1, column=0, padx=20, sticky="nsew")
        form_scroll.grid_columnconfigure(0, weight=1)

        # 1. Liste Grubu
        group1 = ctk.CTkFrame(form_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
        group1.pack(fill="x", padx=20, pady=10)
        group1.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(group1, text="OTOMASYON LİSTESİ", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group1, text="Konu Listesi (.txt):", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        txt_row = ctk.CTkFrame(group1, fg_color="transparent")
        txt_row.grid(row=1, column=1, sticky="ew", padx=(0, 25), pady=15)
        txt_row.grid_columnconfigure(0, weight=1)
        
        self.batch_file_entry = ctk.CTkEntry(txt_row, placeholder_text="Dosya seçin...", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10, state="disabled")
        self.batch_file_entry.grid(row=0, column=0, sticky="ew")
        self.browse_txt_btn = ctk.CTkButton(txt_row, text="Gözat", width=70, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_txt_file)
        self.browse_txt_btn.grid(row=0, column=1, padx=(10, 0))

        # 2. Genel Ayarlar (Batch)
        group2 = ctk.CTkFrame(form_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
        group2.pack(fill="x", padx=20, pady=10)
        group2.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group2, text="GENEL AYARLAR", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group2, text="Kelime / Format:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        bf_row = ctk.CTkFrame(group2, fg_color="transparent")
        bf_row.grid(row=1, column=1, sticky="ew", padx=(0, 25), pady=10)

        self.batch_word_count_entry = ctk.CTkEntry(bf_row, width=80, height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.batch_word_count_entry.insert(0, "500")
        self.batch_word_count_entry.pack(side="left")
        
        self.batch_orientation_var = ctk.StringVar(value="Yatay (16:9)")
        self.batch_orientation_menu = ctk.CTkOptionMenu(bf_row, variable=self.batch_orientation_var, values=["Yatay (16:9)", "Dikey (9:16 Shorts)"], width=160, height=38, fg_color="#1F212E", corner_radius=10)
        self.batch_orientation_menu.pack(side="left", padx=(15, 0))
        
        self.batch_use_gpu_var = ctk.BooleanVar(value=True)
        self.batch_gpu_checkbox = ctk.CTkCheckBox(bf_row, text="RTX 4060 Hızlandırma", variable=self.batch_use_gpu_var, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.success_color, border_width=2, checkmark_color=self.success_color)
        self.batch_gpu_checkbox.pack(side="left", padx=(20, 0))

        ctk.CTkLabel(group2, text="Kategori / Dil:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=10, sticky="e")
        bcat_row = ctk.CTkFrame(group2, fg_color="transparent")
        bcat_row.grid(row=2, column=1, sticky="ew", padx=(0, 25), pady=10)
        bcat_row.grid_columnconfigure(0, weight=1)

        self.batch_category_var = ctk.StringVar(value=CATEGORY_NAMES[0])
        self.batch_category_menu = ctk.CTkOptionMenu(bcat_row, variable=self.batch_category_var, values=CATEGORY_NAMES, width=220, height=38, fg_color="#1F212E", button_color="#2A2D3A", button_hover_color="#3A3D4E", corner_radius=10)
        self.batch_category_menu.grid(row=0, column=0, sticky="w")

        self.batch_language_var = ctk.StringVar(value="Turkce")
        self.batch_language_menu = ctk.CTkOptionMenu(bcat_row, variable=self.batch_language_var, values=self._lang_display_names, width=180, height=38, fg_color="#1F212E", button_color="#2A2D3A", button_hover_color="#3A3D4E", corner_radius=10)
        self.batch_language_menu.grid(row=0, column=1, padx=(10, 0), sticky="w")

        ctk.CTkLabel(group2, text="İçerik Yazarı:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=4, column=0, padx=25, pady=10, sticky="e")
        self.batch_content_provider_var = ctk.StringVar(value="Google Gemini")
        self.batch_content_provider_menu = ctk.CTkOptionMenu(group2, variable=self.batch_content_provider_var, values=["Google Gemini", "Kie.ai (Gemini 3.1 Pro)"], height=38, fg_color="#1F212E", button_color="#2A2D3A", button_hover_color="#3A3D4E", corner_radius=10)
        self.batch_content_provider_menu.grid(row=4, column=1, padx=(0, 25), pady=15, sticky="w")

        ctk.CTkLabel(group2, text="Kaydedilecek Yer:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=25, pady=10, sticky="e")
        bout_f = ctk.CTkFrame(group2, fg_color="transparent")
        bout_f.grid(row=3, column=1, sticky="ew", padx=(0, 25), pady=10)
        bout_f.grid_columnconfigure(0, weight=1)
        self.batch_out_entry = ctk.CTkEntry(bout_f, placeholder_text="output/", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.batch_out_entry.grid(row=0, column=0, sticky="ew")
        self.browse_batch_out_btn = ctk.CTkButton(bout_f, text="Seç", width=70, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_batch_output_dir)
        self.browse_batch_out_btn.grid(row=0, column=1, padx=(10, 0))

        # 3. Video Kaynağı (Batch)
        group3 = ctk.CTkFrame(form_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
        group3.pack(fill="x", padx=20, pady=10)
        group3.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group3, text="VİDEO KAYNAĞI", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group3, text="Kaynağı Seç:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        v_row = ctk.CTkFrame(group3, fg_color="transparent")
        v_row.grid(row=1, column=1, sticky="ew", padx=(0, 25), pady=10)
        v_row.grid_columnconfigure(0, weight=1)

        self.batch_video_source_var = ctk.StringVar(value="Pexels (Otomatik İndir)")
        self.batch_video_source_menu = ctk.CTkOptionMenu(
            v_row, variable=self.batch_video_source_var, 
            values=[
                "Pexels (Otomatik İndir)", 
                "Pixabay (Otomatik İndir)",
                "Manuel (Kendi Videolarım)", 
                "AI Görsel Üretimi (PicLumen)", 
                "Leonardo.ai (Fotoğraf)",
                "Leonardo.ai (Video)",
                "Pexels (Görsel/Fotoğraf)", 
                "Pexels (Karma: 5 Video + 5 Fotoğraf)",
                "Pexels + Pixabay (Hibrit Mod)"
            ], 
            height=38, command=self._on_batch_video_source_change, fg_color="#1F212E", corner_radius=10
        )
        self.batch_video_source_menu.grid(row=0, column=0, sticky="ew")
        
        self.batch_browse_videos_btn = ctk.CTkButton(v_row, text="Video Seç", width=90, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_batch_manual_videos, state="disabled")
        self.batch_browse_videos_btn.grid(row=0, column=1, padx=(10, 0))

        self.batch_manual_video_label = ctk.CTkLabel(group3, text="Pexels modu aktif", text_color="gray", font=ctk.CTkFont(size=10))
        self.batch_manual_video_label.grid(row=2, column=1, padx=25, pady=(0, 15), sticky="w")
        self.batch_manual_video_files = []

        # 4. Ses ve Müzik (Batch)
        group4 = ctk.CTkFrame(form_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
        group4.pack(fill="x", padx=20, pady=10)
        group4.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group4, text="SES & MÜZİK", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        # Voice and Subtitle Toggle Row (Batch)
        batch_toggle_row = ctk.CTkFrame(group4, fg_color="transparent")
        batch_toggle_row.grid(row=1, column=0, columnspan=2, padx=25, pady=5, sticky="w")

        self.batch_enable_voice_var = ctk.BooleanVar(value=True)
        self.batch_voice_checkbox = ctk.CTkCheckBox(batch_toggle_row, text="AI Seslendirme Aktif", variable=self.batch_enable_voice_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_purple)
        self.batch_voice_checkbox.pack(side="left", padx=(0, 20))

        self.batch_enable_subtitles_var = ctk.BooleanVar(value=True)
        self.batch_subtitle_checkbox = ctk.CTkCheckBox(batch_toggle_row, text="Altyazılar Aktif", variable=self.batch_enable_subtitles_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_purple)
        self.batch_subtitle_checkbox.pack(side="left", padx=(0, 20))
        
        self.batch_subtitle_style_var = ctk.StringVar(value="Standart (Kutu)")
        self.batch_subtitle_style_menu = ctk.CTkOptionMenu(batch_toggle_row, variable=self.batch_subtitle_style_var, values=["Standart (Kutu)", "Dinamik (Shorts)", "Neon Mavi", "Altın Işıltı", "Modern Sade"], width=135, height=32, font=ctk.CTkFont(size=11, weight="bold"), fg_color="#1F212E", corner_radius=8)
        self.batch_subtitle_style_menu.pack(side="left")

        ctk.CTkLabel(group4, text="Müzik:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=10, sticky="e")
        bm_row = ctk.CTkFrame(group4, fg_color="transparent")
        bm_row.grid(row=2, column=1, sticky="ew", padx=(0, 25), pady=10)
        bm_row.grid_columnconfigure(0, weight=1)
        
        self.batch_bgm_entry = ctk.CTkEntry(bm_row, placeholder_text="Müzik seçin...", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.batch_bgm_entry.grid(row=0, column=0, sticky="ew")
        self.batch_browse_bgm_btn = ctk.CTkButton(bm_row, text="Gözat", width=70, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_batch_bgm)
        self.batch_browse_bgm_btn.grid(row=0, column=1, padx=(10, 0))

        ctk.CTkLabel(group4, text="Edge Dil:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=25, pady=10, sticky="e")
        self.batch_edge_lang_var = ctk.StringVar(value="Turkce")
        self.batch_edge_lang_menu = ctk.CTkOptionMenu(group4, variable=self.batch_edge_lang_var, values=self._lang_display_names, width=200, height=38, fg_color="#1F212E", corner_radius=10, command=self._on_batch_edge_lang_change)
        self.batch_edge_lang_menu.grid(row=3, column=1, padx=(0, 25), pady=10, sticky="w")

        ctk.CTkLabel(group4, text="Ses Tonu:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=4, column=0, padx=25, pady=10, sticky="e")
        batch_tr_voices = [v["label"] for v in self._edge_voices.get("tr-TR", [])]
        self.batch_edge_voice_var = ctk.StringVar(value=batch_tr_voices[0] if batch_tr_voices else "Ahmet (Erkek)")
        self.batch_edge_voice_menu = ctk.CTkOptionMenu(group4, variable=self.batch_edge_voice_var, values=batch_tr_voices or ["Ahmet (Erkek)"], width=200, height=38, fg_color="#1F212E", corner_radius=10)
        self.batch_edge_voice_menu.grid(row=4, column=1, padx=(0, 25), pady=10, sticky="w")

        ctk.CTkLabel(group4, text="Ses Motoru:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=5, column=0, padx=25, pady=10, sticky="e")
        self.batch_tts_provider_var = ctk.StringVar(value="Edge TTS (Ücretsiz)")
        self.batch_tts_provider_menu = ctk.CTkOptionMenu(group4, variable=self.batch_tts_provider_var, values=["Edge TTS (Ücretsiz)", "Spesh Audio", "DubVoice.ai", "OtomasyonLabs", "VoysLity", "ElevenLabs"], height=38, fg_color="#1F212E", corner_radius=10)
        self.batch_tts_provider_menu.grid(row=5, column=1, padx=(0, 25), pady=10, sticky="w")

        ctk.CTkLabel(group4, text="Müzik Volüm:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=6, column=0, padx=25, pady=10, sticky="e")
        self.batch_bgm_vol_slider = ctk.CTkSlider(group4, from_=0.0, to=1.0, height=18, button_color=self.accent_purple, progress_color=self.accent_purple, button_hover_color=self.accent_color)
        self.batch_bgm_vol_slider.set(0.1)
        self.batch_bgm_vol_slider.grid(row=6, column=1, padx=(0, 25), pady=15, sticky="ew")

        # 5. İçerik Ayarları Grubu (Batch)
        group_b_content = ctk.CTkFrame(form_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
        group_b_content.pack(fill="x", padx=20, pady=10)
        group_b_content.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group_b_content, text="İÇERİK AYARLARI", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        ctk.CTkLabel(group_b_content, text="Asset Sayısı:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        self.batch_asset_count_slider = ctk.CTkSlider(group_b_content, from_=1, to=20, number_of_steps=19, height=18, button_color=self.accent_purple, progress_color=self.accent_purple)
        self.batch_asset_count_slider.set(10)
        self.batch_asset_count_slider.grid(row=1, column=1, padx=(0, 25), pady=15, sticky="ew")
        
        self.batch_asset_count_label = ctk.CTkLabel(group_b_content, text="10", text_color=self.accent_purple, font=ctk.CTkFont(size=12, weight="bold"))
        self.batch_asset_count_label.grid(row=1, column=2, padx=15)
        self.batch_asset_count_slider.configure(command=lambda v: self.batch_asset_count_label.configure(text=str(int(v))))

        self.batch_auto_asset_var = ctk.BooleanVar(value=False)
        self.batch_auto_asset_checkbox = ctk.CTkCheckBox(group_b_content, text="Zekâ Modu (Otomatik Sayı Belirle)", variable=self.batch_auto_asset_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_purple)
        self.batch_auto_asset_checkbox.grid(row=2, column=1, padx=25, pady=10, sticky="w")

        # 6. YouTube Ayarları (Batch)
        group5 = ctk.CTkFrame(form_scroll, fg_color="#181414", corner_radius=18, border_width=1, border_color="#3D1A1A")
        group5.pack(fill="x", padx=20, pady=10)
        group5.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group5, text="YOUTUBE YÜKLEME", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF4B4B").grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        self.batch_enable_youtube_var = ctk.BooleanVar(value=False)
        self.batch_youtube_checkbox = ctk.CTkCheckBox(group5, text="YouTube'a Otomatik Yükle", variable=self.batch_enable_youtube_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color="#FF4B4B")
        self.batch_youtube_checkbox.grid(row=1, column=0, padx=25, pady=15, sticky="w")

        ctk.CTkLabel(group5, text="Kanal Seç:", text_color=self.text_secondary, font=ctk.CTkFont(size=11)).grid(row=1, column=1, padx=(0, 5), sticky="e")
        self.batch_yt_channel_var = ctk.StringVar(value="Varsayılan")
        self.batch_yt_channel_menu = ctk.CTkOptionMenu(group5, variable=self.batch_yt_channel_var, values=["Varsayılan"], width=140, height=30, fg_color="#1F212E", corner_radius=8)
        self.batch_yt_channel_menu.grid(row=1, column=2, padx=(0, 25), pady=15, sticky="w")

        # 6. Video Efektleri Grubu (Batch)
        group6 = ctk.CTkFrame(form_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
        group6.pack(fill="x", padx=20, pady=10)
        group6.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(group6, text="VİDEO EFEKTLERİ", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple).grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        bfx_row = ctk.CTkFrame(group6, fg_color="transparent")
        bfx_row.grid(row=1, column=0, columnspan=2, padx=25, pady=15, sticky="w")

        self.batch_enable_darken_var = ctk.BooleanVar(value=False)
        self.batch_darken_checkbox = ctk.CTkCheckBox(bfx_row, text="Karanlık", variable=self.batch_enable_darken_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_purple)
        self.batch_darken_checkbox.pack(side="left", padx=(0, 20))

        self.batch_enable_fog_var = ctk.BooleanVar(value=False)
        self.batch_fog_checkbox = ctk.CTkCheckBox(bfx_row, text="Sis", variable=self.batch_enable_fog_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_purple)
        self.batch_fog_checkbox.pack(side="left", padx=(0, 20))

        self.batch_enable_sparks_var = ctk.BooleanVar(value=False)
        self.batch_sparks_checkbox = ctk.CTkCheckBox(bfx_row, text="Kıvılcım", variable=self.batch_enable_sparks_var, font=ctk.CTkFont(size=12, weight="bold"), border_width=2, checkmark_color=self.accent_purple)
        self.batch_sparks_checkbox.pack(side="left")

        # Bottom Action
        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.grid(row=2, column=0, pady=25, padx=40, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.batch_generate_btn = ctk.CTkButton(
            action_frame, text="⚡  TOPLU ÜRETİMİ BAŞLAT", 
            height=60, font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.accent_purple, hover_color="#7B3FAC", text_color="#FFFFFF",
            corner_radius=15, border_width=0,
            command=self.start_batch_generation
        )
        self.batch_generate_btn.grid(row=0, column=0, sticky="ew")

        # Progress / Logs
        info_frame = ctk.CTkFrame(f, fg_color="#0D0E16", height=180, corner_radius=15, border_width=1, border_color=self.border_color)
        info_frame.grid(row=3, column=0, padx=40, pady=(0, 30), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        self.batch_progress = ctk.CTkProgressBar(info_frame, mode="determinate", progress_color=self.accent_purple, height=10, corner_radius=5)
        self.batch_progress.grid(row=0, column=0, padx=25, pady=(20, 5), sticky="ew")
        self.batch_progress.set(0)

        self.batch_status_label = ctk.CTkLabel(info_frame, text="İşlem sırası bekleniyor...", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.accent_purple)
        self.batch_status_label.grid(row=1, column=0, padx=25, pady=5)

        self.batch_log_box = ctk.CTkTextbox(info_frame, height=90, fg_color="transparent", text_color="#A0A0A0", font=ctk.CTkFont(size=12))
        self.batch_log_box.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.batch_log_box.configure(state="disabled")

        self.batch_topics = []

    def init_settings_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["settings"] = f
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="Sistem Yapılandırması", font=ctk.CTkFont(size=32, weight="bold"), text_color=self.text_primary).grid(row=0, column=0, pady=(30, 20))

        s_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent", height=520)
        s_scroll.grid(row=1, column=0, padx=20, sticky="nsew")
        s_scroll.grid_columnconfigure(0, weight=1)

        # Settings Card
        s_card = ctk.CTkFrame(s_scroll, fg_color="#141624", corner_radius=18, border_width=1, border_color=self.border_color)
        s_card.pack(fill="x", padx=20, pady=10)
        s_card.grid_columnconfigure(1, weight=1)

        # AI Keys Section
        ctk.CTkLabel(s_card, text="⚙️  API ANAHTARLARI", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFCC00").grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")

        fields = [
            ("Gemini API Key:", "gemini_entry"),
            ("OtomasyonLabs Key:", "otomasyonlabs_entry"),
            ("OtomasyonLabs Voice:", "otomasyonlabs_voice_entry"),
            ("VoysLity Key:", "voyslity_entry"),
            ("VoysLity Voice:", "voyslity_voice_entry"),
            ("ElevenLabs Key:", "eleven_entry"),
            ("ElevenLabs Voice:", "voice_entry"),
            ("Pexels Key:", "pexels_entry"),
            ("Pixabay Key:", "pixabay_entry"),
            ("Leonardo.ai Key:", "leonardo_entry"),
            ("DubVoice Key:", "dubvoice_entry"),
            ("DubVoice Voice:", "dubvoice_voice_entry"),
            ("SpeshAudio Key:", "speshaudio_entry"),
            ("SpeshAudio Voice:", "speshaudio_voice_entry"),
            ("Kie.ai API Key:", "kie_ai_entry"),
            ("PicLumen API Key:", "piclumen_entry")
        ]

        for i, (label, attr) in enumerate(fields, 1):
            ctk.CTkLabel(s_card, text=label, text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=i, column=0, padx=25, pady=10, sticky="e")
            entry = ctk.CTkEntry(s_card, height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10, show="*" if "Key" in label else None)
            entry.grid(row=i, column=1, padx=(0, 25), pady=10, sticky="ew")
            setattr(self, attr, entry)

        # --- SES KLONLAMA BOLUMU ---
        clone_card = ctk.CTkFrame(s_scroll, fg_color="#161824", corner_radius=18, border_width=1, border_color=self.border_color)
        clone_card.pack(fill="x", padx=20, pady=20)
        clone_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(clone_card, text="SES KLONLAMA (VOICE CLONING)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFD700").grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")
        
        ctk.CTkLabel(clone_card, text="Ses Ismi:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        self.clone_name_entry = ctk.CTkEntry(clone_card, placeholder_text="Orn: Benim Sesim", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10)
        self.clone_name_entry.grid(row=1, column=1, padx=(0, 25), pady=10, sticky="ew")

        ctk.CTkLabel(clone_card, text="Ornek Ses (.mp3/.wav):", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=10, sticky="e")
        c_row = ctk.CTkFrame(clone_card, fg_color="transparent")
        c_row.grid(row=2, column=1, padx=(0, 25), pady=10, sticky="ew")
        c_row.grid_columnconfigure(0, weight=1)
        
        self.clone_file_entry = ctk.CTkEntry(c_row, placeholder_text="Dosya secin...", height=38, fg_color="#0A0B10", border_color=self.border_color, corner_radius=10, state="disabled")
        self.clone_file_entry.grid(row=0, column=0, sticky="ew")
        self.clone_browse_btn = ctk.CTkButton(c_row, text="Gözat", width=70, height=38, fg_color="#2A2D3E", hover_color="#3A3D4E", command=self.browse_clone_file)
        self.clone_browse_btn.grid(row=0, column=1, padx=(10, 0))

        self.clone_provider_var = ctk.StringVar(value="ElevenLabs")
        self.clone_provider_menu = ctk.CTkOptionMenu(clone_card, variable=self.clone_provider_var, values=["ElevenLabs", "DubVoice"], height=38, fg_color="#1F212E", corner_radius=10)
        self.clone_provider_menu.grid(row=3, column=1, padx=(0, 25), pady=10, sticky="w")

        self.clone_start_btn = ctk.CTkButton(clone_card, text="✨ KLONLA VE VOICE ID OLARAK ATA", height=45, fg_color="#FFCC00", hover_color="#ccac00", text_color="#000000", font=ctk.CTkFont(size=12, weight="bold"), corner_radius=12, command=self.start_voice_cloning)
        self.clone_start_btn.grid(row=4, column=1, padx=(0, 25), pady=(10, 25), sticky="ew")

        # --- YOUTUBE API SECTION ---
        yt_card = ctk.CTkFrame(s_scroll, fg_color="#181414", corner_radius=18, border_width=1, border_color="#3D1A1A")
        yt_card.pack(fill="x", padx=20, pady=10)
        yt_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(yt_card, text="📺 YOUTUBE API BAĞLANTISI", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FF4B4B").grid(row=0, column=0, columnspan=2, padx=25, pady=(20, 15), sticky="w")
        
        ctk.CTkLabel(yt_card, text="Durum:", text_color=self.text_secondary, font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=25, pady=10, sticky="e")
        self.yt_status_label = ctk.CTkLabel(yt_card, text="Bağlı Değil", text_color="#A0A0A0", font=ctk.CTkFont(size=12, weight="bold"))
        self.yt_status_label.grid(row=1, column=1, padx=(0, 25), pady=10, sticky="w")

        # Check for token.pickle to set initial status
        if os.path.exists("token.pickle"):
             self.yt_status_label.configure(text="BAĞLI (Hazır)", text_color="#4BB543")

        self.yt_auth_btn = ctk.CTkButton(yt_card, text="🔗 YOUTUBE HESABINI BAĞLA (API)", height=45, fg_color="#FF4B4B", hover_color="#D32F2F", text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), corner_radius=12, command=self.authorize_youtube)
        self.yt_auth_btn.grid(row=2, column=1, padx=(0, 25), pady=(10, 25), sticky="ew")

        save_btn = ctk.CTkButton(
            f, text="💾  YAPILANDIRMAYI KAYDET", 
            height=60, fg_color="#1B5E20", hover_color="#27802d",
            font=ctk.CTkFont(size=16, weight="bold"),
            corner_radius=15,
            command=self.save_settings
        )
        save_btn.grid(row=2, column=0, padx=40, pady=30, sticky="ew")

        self.load_settings_to_ui()

    def show_single(self):
        self.switch_frame("single")
        self.btn_single.configure(fg_color="#1A1C36", text_color=self.accent_color, border_width=1, border_color=self.accent_color)
        self.btn_batch.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_settings.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)

    def show_batch(self):
        self.switch_frame("batch")
        self.btn_batch.configure(fg_color="#2A1C36", text_color=self.accent_purple, border_width=1, border_color=self.accent_purple)
        self.btn_single.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_channels.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_settings.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)

    def show_channels(self):
        self.switch_frame("channels")
        self.btn_channels.configure(fg_color="#1C1C36", text_color="#FF4B4B", border_width=1, border_color="#FF4B4B")
        self.btn_single.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_batch.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_settings.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.refresh_channels()

    def show_settings(self):
        self.switch_frame("settings")
        self.btn_settings.configure(fg_color="#2A2A16", text_color="#FFCC00", border_width=1, border_color="#FFCC00")
        self.btn_single.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_batch.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)
        self.btn_channels.configure(fg_color="transparent", text_color=self.text_secondary, border_width=0)

    def switch_frame(self, frame_key):
        for frame in self.frames.values():
            frame.grid_forget()
        self.frames[frame_key].grid(row=0, column=0, sticky="nsew")

    def load_settings_to_ui(self):
         if os.path.exists(".env"):
              with open(".env", "r") as f:
                   lines = f.readlines()
                   for line in lines:
                        if line.startswith("GEMINI_API_KEY="):
                             self.gemini_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("OTOMASYONLABS_API_KEY="):
                             self.otomasyonlabs_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("OTOMASYONLABS_VOICE_ID="):
                             self.otomasyonlabs_voice_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("VOYSLITY_API_KEY="):
                             self.voyslity_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("VOYSLITY_VOICE_ID="):
                             self.voyslity_voice_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("ELEVENLABS_API_KEY="):
                             self.eleven_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("PEXELS_API_KEY="):
                             self.pexels_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("PIXABAY_API_KEY="):
                             self.pixabay_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("LEONARDO_API_KEY="):
                             self.leonardo_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("PICLUMEN_API_KEY="):
                             self.piclumen_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("DUBVOICE_API_KEY="):
                             self.dubvoice_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("DUBVOICE_VOICE_ID="):
                             self.dubvoice_voice_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("SPESHAUDIO_API_KEY="):
                             self.speshaudio_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("SPESHAUDIO_VOICE_ID="):
                             self.speshaudio_voice_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("ELEVENLABS_VOICE_ID="):
                             self.voice_entry.insert(0, line.split("=", 1)[1].strip())
                        elif line.startswith("KIE_AI_API_KEY="):
                             self.kie_ai_entry.insert(0, line.split("=", 1)[1].strip())

    def save_settings(self):
         gemini = self.gemini_entry.get().strip()
         otomasyonlabs = self.otomasyonlabs_entry.get().strip()
         otomasyonlabs_voice = self.otomasyonlabs_voice_entry.get().strip()
         voyslity = self.voyslity_entry.get().strip()
         voyslity_voice = self.voyslity_voice_entry.get().strip()
         eleven = self.eleven_entry.get().strip()
         pexels = self.pexels_entry.get().strip()
         pixabay = self.pixabay_entry.get().strip()
         leonardo = self.leonardo_entry.get().strip()
         dubvoice = self.dubvoice_entry.get().strip()
         dubvoice_voice = self.dubvoice_voice_entry.get().strip()
         speshaudio = self.speshaudio_entry.get().strip()
         speshaudio_voice = self.speshaudio_voice_entry.get().strip()
         piclumen = self.piclumen_entry.get().strip()
         voice = self.voice_entry.get().strip()
         kie_ai = self.kie_ai_entry.get().strip()
         
         with open(".env", "w") as f:
              f.write(f"GEMINI_API_KEY={gemini}\n")
              f.write(f"OTOMASYONLABS_API_KEY={otomasyonlabs}\n")
              f.write(f"OTOMASYONLABS_VOICE_ID={otomasyonlabs_voice}\n")
              f.write(f"VOYSLITY_API_KEY={voyslity}\n")
              f.write(f"VOYSLITY_VOICE_ID={voyslity_voice}\n")
              f.write(f"ELEVENLABS_API_KEY={eleven}\n")
              f.write(f"PEXELS_API_KEY={pexels}\n")
              f.write(f"PIXABAY_API_KEY={pixabay}\n")
              f.write(f"LEONARDO_API_KEY={leonardo}\n")
              f.write(f"DUBVOICE_API_KEY={dubvoice}\n")
              f.write(f"DUBVOICE_VOICE_ID={dubvoice_voice}\n")
              f.write(f"SPESHAUDIO_API_KEY={speshaudio}\n")
              f.write(f"SPESHAUDIO_VOICE_ID={speshaudio_voice}\n")
              f.write(f"KIE_AI_API_KEY={kie_ai}\n")
              f.write(f"PICLUMEN_API_KEY={piclumen}\n")
              f.write(f"ELEVENLABS_VOICE_ID={voice}\n")
              
         messagebox.showinfo("Başarılı", "API ayarları kaydedildi!")
         self.show_single()

    def check_env(self):
        if not os.path.exists(".env"):
             self.log_message("Sistem: .env dosyası bulunamadı. Lütfen Ayarlar sekmesinden anahtarlarınızı girin.")
        else:
             with open(".env", "r") as f:
                  content = f.read()
                  if "GEMINI_API_KEY=" not in content or len(content.split("GEMINI_API_KEY=")[1].split("\n")[0]) < 5:
                       self.log_message("⚠ Gemini API anahtarı eksik. Senaryo oluşturmak için Ayarlar'dan girin.")
                  else:
                       self.log_message("✅ Sistem hazır. Edge TTS (Ücretsiz) varsayılan ses motoru olarak ayarlı.")


    def authorize_youtube(self):
        """YouTube API login handler in a thread."""
        def auth_worker():
            self.yt_auth_btn.configure(state="disabled", text="Bağlanıyor...")
            self.yt_status_label.configure(text="Lütfen Tarayıcıda Doğrulayın...", text_color="#FFCC00")
            try:
                # This will open browser for OAuth
                service = youtube_uploader.get_authenticated_service()
                if service:
                    # Yeni kanali kaydetmek icin isim al
                    info = youtube_uploader.get_channel_info(service)
                    if info:
                        # Token'i kanal id'si ile sakla
                        tpath = os.path.join(self.tokens_dir, f"{info['id']}.pickle")
                        if os.path.exists("token.pickle"):
                            import shutil
                            shutil.move("token.pickle", tpath)
                        
                        self.after(0, lambda: self.yt_status_label.configure(text=f"BAĞLI: {info['title']}", text_color="#4BB543"))
                        self.log_message(f"Sistem: {info['title']} kanalı başarıyla bağlandı.")
                        self.after(0, self.refresh_channels)
                    else:
                        self.after(0, lambda: self.yt_status_label.configure(text="BAĞLI (Bilinmiyor)", text_color="#4BB543"))
                else:
                    self.after(0, lambda: self.yt_status_label.configure(text="HATA (client_secrets.json eksik)", text_color="#FF4B4B"))
            except Exception as e:
                self.after(0, lambda: self.yt_status_label.configure(text="HATA (Loga bakın)", text_color="#FF4B4B"))
                self.log_message(f"Sistem: YouTube Auth Hatası: {str(e)}")
            finally:
                self.after(0, lambda: self.yt_auth_btn.configure(state="normal", text="🔗 YOUTUBE HESABINI BAĞLA (API)"))

        threading.Thread(target=auth_worker, daemon=True).start()

    def init_channels_view(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["channels"] = f
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="Bağlı YouTube Kanalları", font=ctk.CTkFont(size=32, weight="bold"), text_color=self.text_primary).grid(row=0, column=0, pady=(30, 20))

        self.channels_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent", height=500)
        self.channels_scroll.grid(row=1, column=0, padx=20, sticky="nsew")
        self.channels_scroll.grid_columnconfigure(0, weight=1)
        
        # New Channel Button
        self.add_chan_btn = ctk.CTkButton(f, text="➕ YENİ KANAL EKLE", height=50, fg_color="#E91E63", hover_color="#C2185B", font=ctk.CTkFont(size=14, weight="bold"), corner_radius=15, command=self.show_settings)
        self.add_chan_btn.grid(row=2, column=0, padx=40, pady=20, sticky="ew")

    def refresh_channels(self):
        for widget in self.channels_scroll.winfo_children():
            widget.destroy()

        self._channel_map = {"Varsayılan": "token.pickle"}
        tokens = [f for f in os.listdir(self.tokens_dir) if f.endswith(".pickle")]
        chan_names = ["Varsayılan"]

        if not tokens:
            ctk.CTkLabel(self.channels_scroll, text="Henüz hiç kanal bağlanmadı.", text_color=self.text_secondary, font=ctk.CTkFont(size=14)).pack(pady=50)
            self._update_channel_menus(chan_names)
            return

        for idx, tfile in enumerate(tokens):
            tpath = os.path.join(self.tokens_dir, tfile)
            info = youtube_uploader.get_channel_info(token_path=tpath)
            
            if not info: continue
            
            self._channel_map[info['title']] = tpath
            chan_names.append(info['title'])

            # ... (rest of search/view logic remains same but using info)
            # (Re-pasting the card logic inside refresh_channels to ensure it's complete)
            card = ctk.CTkFrame(self.channels_scroll, fg_color="#181624", corner_radius=18, border_width=1, border_color=self.border_color)
            card.pack(fill="x", padx=20, pady=10)
            card.grid_columnconfigure(1, weight=1)

            # Details
            details = ctk.CTkFrame(card, fg_color="transparent")
            details.grid(row=0, column=1, padx=20, pady=15, sticky="ew")

            ctk.CTkLabel(details, text=info['title'], font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFFFFF").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(details, text=f"@{info.get('customUrl', info['id'])}", font=ctk.CTkFont(size=12), text_color=self.text_secondary).grid(row=1, column=0, sticky="w")

            stats_row = ctk.CTkFrame(details, fg_color="transparent")
            stats_row.grid(row=2, column=0, pady=(10, 0), sticky="w")

            def create_stat(parent, label, val, color):
                f = ctk.CTkFrame(parent, fg_color="transparent")
                f.pack(side="left", padx=(0, 20))
                ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=self.text_secondary).pack()
                ctk.CTkLabel(f, text=val, font=ctk.CTkFont(size=14, weight="bold"), text_color=color).pack()

            from humanize import intword
            try: subs = intword(int(info['subscribers']))
            except: subs = info['subscribers']
            try: vws = intword(int(info['views']))
            except: vws = info['views']

            create_stat(stats_row, "ABONE", subs, "#FF4B4B")
            create_stat(stats_row, "İZLENME", vws, "#00D1FF")
            create_stat(stats_row, "VİDEO", info['videos'], "#A100FF")

            # Actions
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=0, column=2, padx=20)
            
            del_btn = ctk.CTkButton(actions, text="Kaldır", width=80, height=32, fg_color="#3D1A1A", hover_color="#5D1A1A", text_color="#FF4B4B", corner_radius=8, command=lambda p=tpath: self.delete_channel(p))
            del_btn.pack(pady=5)
        
        self._update_channel_menus(chan_names)

    def _update_channel_menus(self, names):
        """Update dropdowns in Single and Batch views."""
        try:
            self.yt_channel_menu.configure(values=names)
            if self.yt_channel_var.get() not in names:
                self.yt_channel_var.set(names[0])
            
            self.batch_yt_channel_menu.configure(values=names)
            if self.batch_yt_channel_var.get() not in names:
                self.batch_yt_channel_var.set(names[0])
        except: pass

    def delete_channel(self, tpath):
        if messagebox.askyesno("Kanalı Kaldır", "Bu kanalı sistemden kaldırmak istediğinize emin misiniz?"):
            try:
                os.remove(tpath)
                self.refresh_channels()
                self.log_message("Sistem: Kanal başarıyla kaldırıldı.")
            except Exception as e:
                messagebox.showerror("Hata", f"Kanal kaldırılamadı: {e}")

    def log_message(self, message, is_batch=False):
        box = self.batch_log_box if is_batch else self.log_box
        status = self.batch_status_label if is_batch else self.status_label
        
        box.configure(state="normal")
        box.insert("end", f"[{threading.current_thread().name}] {message}\n")
        box.see("end")
        box.configure(state="disabled")
        status.configure(text=message[:50] + "..." if len(message) > 50 else message)



    def browse_output_dir(self):
         selected_dir = ctk.filedialog.askdirectory()
         if selected_dir:
              self.output_dir_entry.delete(0, "end")
              self.output_dir_entry.insert(0, selected_dir)
              
    def browse_batch_output_dir(self):
         selected_dir = ctk.filedialog.askdirectory()
         if selected_dir:
              self.batch_out_entry.delete(0, "end")
              self.batch_out_entry.insert(0, selected_dir)
              
    def browse_txt_file(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            self.batch_file_entry.configure(state="normal")
            self.batch_file_entry.delete(0, "end")
            self.batch_file_entry.insert(0, file_path)
            self.batch_file_entry.configure(state="disabled")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.batch_topics = [line.strip() for line in f if line.strip()]
                self.log_message(f"Dosya yüklendi: {len(self.batch_topics)} konu hazır.", is_batch=True)
            except Exception as e:
                self.log_message(f"Okuma Hatası: {e}", is_batch=True)

    def _on_video_source_change(self, choice):
        """Called when the video source dropdown changes."""
        if "Manuel" in choice:
            self.browse_videos_btn.configure(state="normal")
            self.manual_video_label.configure(text="Henüz video seçilmedi", text_color="orange")
        else:
            self.browse_videos_btn.configure(state="disabled")
            self.manual_video_label.configure(text="Pexels otomatik indirecek", text_color="gray")
            self.manual_video_files = []

    def browse_manual_videos(self):
        """Open file dialog to select multiple video files."""
        files = ctk.filedialog.askopenfilenames(
            title="Video Dosyalarını Seçin",
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")]
        )
        if files:
            self.manual_video_files = list(files)
            count = len(self.manual_video_files)
            self.manual_video_label.configure(
                text=f"✅ {count} video seçildi",
                text_color="green"
            )
            self.log_message(f"Manuel video: {count} dosya secildi.")

    def _on_edge_lang_change(self, choice):
        """Edge TTS dil secildinde sesleri guncelle (Tekil)."""
        locale = self._lang_display_to_locale.get(choice, "tr-TR")
        voices = self._edge_voices.get(locale, [])
        voice_labels = [v["label"] for v in voices]
        if voice_labels:
            self.edge_voice_menu.configure(values=voice_labels)
            self.edge_voice_var.set(voice_labels[0])
        else:
            self.edge_voice_menu.configure(values=["(Ses bulunamadi)"])
            self.edge_voice_var.set("(Ses bulunamadi)")

    def _on_batch_edge_lang_change(self, choice):
        """Edge TTS dil secildinde sesleri guncelle (Toplu)."""
        locale = self._lang_display_to_locale.get(choice, "tr-TR")
        voices = self._edge_voices.get(locale, [])
        voice_labels = [v["label"] for v in voices]
        if voice_labels:
            self.batch_edge_voice_menu.configure(values=voice_labels)
            self.batch_edge_voice_var.set(voice_labels[0])
        else:
            self.batch_edge_voice_menu.configure(values=["(Ses bulunamadi)"])
            self.batch_edge_voice_var.set("(Ses bulunamadi)")

    def _resolve_edge_voice_id(self, lang_display: str, voice_display: str) -> str:
        """Secilen dil ve ses gosterim adini Edge TTS ShortName'e cevirir."""
        locale = self._lang_display_to_locale.get(lang_display, "tr-TR")
        voices = self._edge_voices.get(locale, [])
        for v in voices:
            if v["label"] == voice_display:
                return v["short"]
        # Fallback: ilk sesi dondur
        if voices:
            return voices[0]["short"]
        return "tr-TR-AhmetNeural"


    def _on_batch_video_source_change(self, choice):
        """Called when the batch video source dropdown changes."""
        if "Manuel" in choice:
            self.batch_browse_videos_btn.configure(state="normal")
            self.batch_manual_video_label.configure(text="Henüz video seçilmedi", text_color="orange")
        else:
            self.batch_browse_videos_btn.configure(state="disabled")
            self.batch_manual_video_label.configure(text="Pexels otomatik indirecek", text_color="gray")
            self.batch_manual_video_files = []

    def browse_batch_manual_videos(self):
        """Open file dialog to select multiple video files for batch."""
        files = ctk.filedialog.askopenfilenames(
            title="Toplu Üretim İçin Video Dosyalarını Seçin",
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")]
        )
        if files:
            self.batch_manual_video_files = list(files)
            count = len(self.batch_manual_video_files)
            self.batch_manual_video_label.configure(
                text=f"✅ {count} video seçildi",
                text_color="green"
            )
            self.log_message(f"Manuel video (toplu): {count} dosya seçildi.", is_batch=True)

    def browse_bgm(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if file_path:
            self.bgm_entry.delete(0, "end")
            self.bgm_entry.insert(0, file_path)

    def browse_batch_bgm(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if file_path:
            self.batch_bgm_entry.delete(0, "end")
            self.batch_bgm_entry.insert(0, file_path)

    def start_generation(self):
        import traceback
        try:
            load_dotenv(override=True)
            topic = self.topic_textbox.get("1.0", "end-1c").strip()
            if topic == "Buraya video konusunu veya 2000 kelimelik talimatınızı girebilirsiniz...":
                topic = ""
            
            category = self.category_var.get()
            lang_raw = self.language_var.get()
            # Dil kodunu locale'den al
            language_locale = self._lang_display_to_locale.get(lang_raw, "tr-TR")
            language = language_locale.split("-")[0]  # tr-TR -> tr, en-US -> en

            if not topic:
                messagebox.showwarning("Eksik Bilgi", "Lütfen bir video konusu girin.")
                return
            
            output_dir = self.output_dir_entry.get().strip() or "output"
            enable_voice = self.enable_voice_var.get()
            bgm_path = self.bgm_entry.get().strip()
            bgm_volume = self.bgm_vol_slider.get()
            
            provider_val = self.tts_provider_var.get()
            edge_voice_id = "tr-TR-AhmetNeural" # Default initial value
            if "Edge" in provider_val:
                tts_provider = "edge"
                model_id = None
            elif "OtomasyonLabs" in provider_val:
                tts_provider = "otomasyonlabs"
                model_id = "eleven_multilingual_v2"
            elif "VoysLity" in provider_val:
                tts_provider = "voyslity"
                model_id = None
            elif "DubVoice" in provider_val:
                tts_provider = "dubvoice"
                model_id = "eleven_multilingual_v2"
            elif "Spesh Audio" in provider_val:
                tts_provider = "speshaudio"
                model_id = "eleven_multilingual_v2"
            else:
                tts_provider = "elevenlabs"
                model_id = None
            
            try:
                 word_count = int(self.word_count_entry.get().strip())
            except (ValueError, AttributeError):
                 word_count = 500

            # Resolve Edge voice - secilen dil ve sese gore
            if tts_provider == "edge":
                edge_voice_id = self._resolve_edge_voice_id(self.edge_lang_var.get(), self.edge_voice_var.get())

            # Resolve video source
            video_source = self.video_source_var.get()
            use_manual = "Manuel" in video_source
            manual_files = self.manual_video_files if use_manual else []
            if use_manual and not manual_files:
                messagebox.showwarning("Eksik Bilgi", "Manuel mod seçildi ama hiç video dosyası seçmediniz!")
                return

            enable_subtitles = self.enable_subtitles_var.get()
            upload_to_yt = self.enable_youtube_var.get()

            self.generate_btn.configure(state="disabled")
            self.topic_textbox.configure(state="disabled")

            self.browse_btn.configure(state="disabled")
            self.browse_bgm_btn.configure(state="disabled")
            self.voice_checkbox.configure(state="disabled")
            self.subtitle_checkbox.configure(state="disabled")
            self.youtube_checkbox.configure(state="disabled")
            self.bgm_entry.configure(state="disabled")
            self.bgm_vol_slider.configure(state="disabled")
            self.word_count_entry.configure(state="disabled")
            self.tts_provider_menu.configure(state="disabled")
            self.edge_voice_menu.configure(state="disabled")
            self.edge_lang_menu.configure(state="disabled")
            self.video_source_menu.configure(state="disabled")
            self.browse_videos_btn.configure(state="disabled")
            self.category_menu.configure(state="disabled")
            self.language_menu.configure(state="disabled")
            self.darken_checkbox.configure(state="disabled")
            self.fog_checkbox.configure(state="disabled")
            self.sparks_checkbox.configure(state="disabled")
            self.subtitle_style_menu.configure(state="disabled")
            self.orientation_menu.configure(state="disabled")
            self.content_provider_menu.configure(state="disabled")

            effects_config = {
                "darken": self.enable_darken_var.get(),
                "fog": self.enable_fog_var.get(),
                "sparks": self.enable_sparks_var.get()
            }

            use_leo_motion = "Leonardo.ai (Video)" in video_source
            if "Leonardo.ai" in video_source:
                video_source = "AI Görsel Üretimi (Leonardo.ai)" # Map back to internal name for main.py
            
            is_vertical = "Dikey" in self.orientation_var.get()
            use_gpu = self.use_gpu_var.get()
            sub_style = self.subtitle_style_var.get()
            
            auto_asset = self.auto_asset_var.get()
            ai_content_count = -1 if auto_asset else int(self.asset_count_slider.get())

            source_label = "Manuel" if use_manual else "Pexels"
            content_provider_raw = self.content_provider_var.get()
            content_provider = "kie" if "Kie" in content_provider_raw else "google"

            self.progress_bar.set(0)
            assets_info = "Otomatik" if auto_asset else str(ai_content_count)
            display_topic = (topic[:60] + '...') if len(topic) > 60 else topic
            
            # Resolve selected channel token path
            selected_chan = self.yt_channel_var.get()
            chan_token = "token.pickle" # Default
            if selected_chan != "Varsayılan" and hasattr(self, "_channel_map"):
                 chan_token = self._channel_map.get(selected_chan, "token.pickle")

            self.log_message(f"Başlatıldı: {display_topic} ({word_count} kelime) [Assets: {assets_info}] [Format: {'Dikey' if is_vertical else 'Yatay'}] [Kanal: {selected_chan}]")

            threading.Thread(target=self.run_pipeline, args=(topic, output_dir, enable_voice, bgm_path, bgm_volume, word_count, tts_provider, edge_voice_id, manual_files, category, language, video_source, enable_subtitles, upload_to_yt, effects_config, model_id, ai_content_count, use_leo_motion, is_vertical, sub_style, content_provider, use_gpu, chan_token), name="Worker", daemon=True).start()
        except Exception as e:
            print(f"\n!!! start_generation HATASI !!!")
            traceback.print_exc()
            messagebox.showerror("Hata", f"Başlatma hatası: {str(e)}")
            self.reset_ui()

    def start_batch_generation(self):
        if not self.batch_topics:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir konu dosyası seçin.")
            return

        load_dotenv(override=True)
        output_dir = self.batch_out_entry.get().strip() or "output"
        enable_voice = self.batch_enable_voice_var.get()
        bgm_path = self.batch_bgm_entry.get().strip()
        bgm_volume = self.batch_bgm_vol_slider.get()
        
        provider_val = self.batch_tts_provider_var.get()
        edge_voice_id = "tr-TR-AhmetNeural" # Default initial value
        if "Edge" in provider_val:
            tts_provider = "edge"
            model_id = None
        elif "OtomasyonLabs" in provider_val:
            tts_provider = "otomasyonlabs"
            model_id = "eleven_multilingual_v2"
        elif "VoysLity" in provider_val:
            tts_provider = "voyslity"
            model_id = None
        elif "DubVoice" in provider_val:
            tts_provider = "dubvoice"
            model_id = "eleven_multilingual_v2"
        elif "Spesh Audio" in provider_val:
            tts_provider = "speshaudio"
            model_id = "eleven_multilingual_v2"
        else:
            tts_provider = "elevenlabs"
            model_id = None

        # Resolve Edge voice - secilen dil ve sese gore
        if tts_provider == "edge":
            edge_voice_id = self._resolve_edge_voice_id(self.batch_edge_lang_var.get(), self.batch_edge_voice_var.get())

        # Read default word count
        try:
            default_word_count = int(self.batch_word_count_entry.get().strip())
        except (ValueError, AttributeError):
            default_word_count = 500

        # Resolve video source
        batch_video_source = self.batch_video_source_var.get()
        use_manual = "Manuel" in batch_video_source
        manual_files = self.batch_manual_video_files if use_manual else []
        if use_manual and not manual_files:
            messagebox.showwarning("Eksik Bilgi", "Manuel mod seçildi ama hiç video dosyası seçmediniz!")
            return

        enable_subtitles = self.batch_enable_subtitles_var.get()
        upload_to_yt = self.batch_enable_youtube_var.get()

        self.batch_generate_btn.configure(state="disabled")
        self.browse_txt_btn.configure(state="disabled")
        self.browse_batch_out_btn.configure(state="disabled")
        self.batch_browse_bgm_btn.configure(state="disabled")
        self.batch_voice_checkbox.configure(state="disabled")
        self.batch_subtitle_checkbox.configure(state="disabled")
        self.batch_youtube_checkbox.configure(state="disabled")
        self.batch_bgm_entry.configure(state="disabled")
        self.batch_bgm_vol_slider.configure(state="disabled")
        self.batch_tts_provider_menu.configure(state="normal") # Fix state? usually should be disabled
        self.batch_edge_voice_menu.configure(state="disabled")
        self.batch_edge_lang_menu.configure(state="disabled")
        self.batch_video_source_menu.configure(state="disabled")
        self.batch_browse_videos_btn.configure(state="disabled")
        self.batch_word_count_entry.configure(state="disabled")
        self.batch_category_menu.configure(state="disabled")
        self.batch_language_menu.configure(state="disabled")
        self.batch_darken_checkbox.configure(state="disabled")
        self.batch_fog_checkbox.configure(state="disabled")
        self.batch_sparks_checkbox.configure(state="disabled")
        self.batch_subtitle_style_menu.configure(state="disabled")
        self.batch_orientation_menu.configure(state="disabled")
        self.batch_content_provider_menu.configure(state="disabled")

        effects_config = {
            "darken": self.batch_enable_darken_var.get(),
            "fog": self.batch_enable_fog_var.get(),
            "sparks": self.batch_enable_sparks_var.get()
        }

        batch_category = self.batch_category_var.get()
        batch_lang_raw = self.batch_language_var.get()
        batch_language_locale = self._lang_display_to_locale.get(batch_lang_raw, "tr-TR")
        batch_language = batch_language_locale.split("-")[0]

        use_leo_motion = "Leonardo.ai (Video)" in batch_video_source
        if "Leonardo.ai" in batch_video_source:
            batch_video_source = "AI Görsel Üretimi (Leonardo.ai)" # Map back to internal name for main.py

        is_vertical = "Dikey" in self.batch_orientation_var.get()
        use_gpu = self.batch_use_gpu_var.get()
        batch_sub_style = self.batch_subtitle_style_var.get()
        
        auto_asset = self.batch_auto_asset_var.get()
        ai_content_count = -1 if auto_asset else int(self.batch_asset_count_slider.get())

        batch_content_raw = self.batch_content_provider_var.get()
        batch_content_provider = "kie" if "Kie" in batch_content_raw else "google"

        self.batch_progress.set(0)
        assets_info = "Otomatik" if auto_asset else str(ai_content_count)
        
        # Resolve selected channel token path
        selected_chan = self.batch_yt_channel_var.get()
        chan_token = "token.pickle"
        if selected_chan != "Varsayılan" and hasattr(self, "_channel_map"):
             chan_token = self._channel_map.get(selected_chan, "token.pickle")

        self.log_message(f"Toplu Üretim Başlatıldı... [Assets: {assets_info}] [Format: {'Dikey' if is_vertical else 'Yatay'}] [Kanal: {selected_chan}]", is_batch=True)
        
        threading.Thread(target=self.run_batch_pipeline, args=(self.batch_topics, output_dir, enable_voice, bgm_path, bgm_volume, tts_provider, edge_voice_id, manual_files, default_word_count, batch_category, batch_language, batch_video_source, enable_subtitles, upload_to_yt, effects_config, model_id, ai_content_count, use_leo_motion, is_vertical, batch_sub_style, batch_content_provider, use_gpu, chan_token), name="BatchWorker", daemon=True).start()

    def run_batch_pipeline(self, topics, output_dir, enable_voice, bgm_path, bgm_volume, tts_provider, edge_voice_id, manual_video_files=None, default_word_count=500, category="🎬 Genel", language="tr", video_source="Pexels (Otomatik İndir)", enable_subtitles=True, upload_to_youtube=False, effects_config=None, model_id=None, ai_content_count=10, use_leo_motion=False, is_vertical=False, subtitle_style="Standart (Kutu)", content_provider="google", use_gpu=False, yt_token_path="token.pickle"):
        success = 0
        try:
            self._lower_process_priority()
            
            for i, item in enumerate(topics):
                if ":" in item:
                    parts = item.split(":")
                    topic = parts[0].strip()
                    try:
                        word_count = int(parts[1].strip())
                    except:
                        word_count = default_word_count
                else:
                    topic = item.strip()
                    word_count = default_word_count
                    
                self.after(0, self.log_message, f"[{i+1}/{len(topics)}] {topic} ({word_count} kelime)", True)
                p = generate_full_video(topic, output_dir, enable_voice, bgm_path, bgm_volume, word_count, lambda m: self.after(0, self.log_message, m, True), tts_provider=tts_provider, edge_voice_id=edge_voice_id, manual_video_files=manual_video_files or [], category=category, language=language, video_source=video_source, enable_subtitles=enable_subtitles, effects_config=effects_config, model_id=model_id, ai_content_count=ai_content_count, use_leonardo_motion=use_leo_motion, is_vertical=is_vertical, subtitle_style=subtitle_style, content_provider=content_provider, use_gpu=use_gpu)
                if p and upload_to_youtube:
                    self.after(0, self.log_message, f"[{i+1}/{len(topics)}] YouTube'a yükleniyor...", True)
                    
                    # Extract metadata for upload
                    video_work_dir = os.path.dirname(p)
                    metadata_path = os.path.join(video_work_dir, "video_metadata.txt")
                    tags = []
                    yt_title = topic
                    yt_desc = f"{topic} #shorts #ai #video"
                    thumbnail_path = os.path.join(video_work_dir, "thumbnail.jpg")
                    
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, "r", encoding="utf-8") as f:
                                meta_content = f.read()
                                if "YOUTUBE BAŞLIK:" in meta_content:
                                    yt_title = meta_content.split("YOUTUBE BAŞLIK:")[1].split("\n\n")[0].strip()
                                if "ETİKETLER:" in meta_content:
                                    tags_str = meta_content.split("ETİKETLER:")[1].split("\n\n")[0].strip()
                                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                                if "AÇIKLAMA:" in meta_content:
                                    yt_desc = meta_content.split("AÇIKLAMA:")[1].split("\n\n")[0].strip()
                        except: pass

                    success_yt = youtube_uploader.upload_to_youtube(
                        p, 
                        yt_title, 
                        yt_desc, 
                        tags=tags, 
                        thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None,
                        token_path=yt_token_path
                    )
                    if success_yt:
                        self.after(0, self.log_message, f"[{i+1}/{len(topics)}] YouTube yüklemesi BAŞARILI (GİZLİ).", True)
                    else:
                        self.after(0, self.log_message, f"[{i+1}/{len(topics)}] YouTube yüklemesi BAŞARISIZ.", True)
                
                if p: 
                    success += 1
                
                # Update global batch progress
                new_progress = (i + 1) / len(topics)
                self.after(0, self.batch_progress.set, new_progress)
                
                # Force memory cleanup between batch videos
                gc.collect()
                
            self.after(0, lambda success=success, topics=topics: messagebox.showinfo("Bitti", f"Süreç tamamlandı. {success}/{len(topics)} video üretildi."))
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Hata", str(e)))
        finally:
            gc.collect()
            self.after(0, self.reset_batch_ui)

    def reset_batch_ui(self):
        self.batch_progress.stop()
        self.batch_progress.set(0)
        self.batch_generate_btn.configure(state="normal")
        self.browse_txt_btn.configure(state="normal")
        self.browse_batch_out_btn.configure(state="normal")
        self.batch_browse_bgm_btn.configure(state="normal")
        self.batch_voice_checkbox.configure(state="normal")
        self.batch_subtitle_checkbox.configure(state="normal")
        self.batch_youtube_checkbox.configure(state="normal")
        self.batch_bgm_entry.configure(state="normal")
        self.batch_bgm_vol_slider.configure(state="normal")
        self.batch_tts_provider_menu.configure(state="normal")
        self.batch_edge_voice_menu.configure(state="normal")
        self.batch_video_source_menu.configure(state="normal")
        if "Manuel" in self.batch_video_source_var.get():
            self.batch_browse_videos_btn.configure(state="normal")
        self.batch_word_count_entry.configure(state="normal")
        self.batch_category_menu.configure(state="normal")
        self.batch_language_menu.configure(state="normal")
        self.batch_darken_checkbox.configure(state="normal")
        self.batch_gpu_checkbox.configure(state="normal")
        self.batch_fog_checkbox.configure(state="normal")
        self.batch_sparks_checkbox.configure(state="normal")
        self.batch_orientation_menu.configure(state="normal")
        self.batch_subtitle_style_menu.configure(state="normal")
        self.batch_content_provider_menu.configure(state="normal")
        self.batch_status_label.configure(text="İşlem bitti.", text_color="green")

    def run_pipeline(self, topic, output_dir, enable_voice, bgm_path, bgm_volume, word_count, tts_provider, edge_voice_id, manual_video_files=None, category="🎬 Genel", language="tr", video_source="Pexels (Otomatik İndir)", enable_subtitles=True, upload_to_youtube=False, effects_config=None, model_id=None, ai_content_count=10, use_leo_motion=False, is_vertical=False, subtitle_style="Standart (Kutu)", content_provider="google", use_gpu=False, yt_token_path="token.pickle"):
        import traceback
        try:
            self._lower_process_priority()
            
            p = generate_full_video(
                topic, output_dir, enable_voice, bgm_path, bgm_volume, word_count, 
                lambda m: self.after(0, self.log_message, m, False), 
                tts_provider=tts_provider, edge_voice_id=edge_voice_id, 
                manual_video_files=manual_video_files or [], category=category, 
                language=language, video_source=video_source, 
                enable_subtitles=enable_subtitles, 
                effects_config=effects_config, model_id=model_id, 
                ai_content_count=ai_content_count, use_leonardo_motion=use_leo_motion, 
                is_vertical=is_vertical, subtitle_style=subtitle_style, 
                content_provider=content_provider, use_gpu=use_gpu,
                progress_val_callback=lambda v: self.after(0, self.progress_bar.set, v)
            )
            if p:
                if upload_to_youtube:
                    self.after(0, self.log_message, "Sistem: YouTube'a yükleniyor...", False)
                    
                    # Extract metadata for upload
                    video_work_dir = os.path.dirname(p)
                    metadata_path = os.path.join(video_work_dir, "video_metadata.txt")
                    tags = []
                    yt_title = topic
                    yt_desc = f"{topic} #shorts #ai #video"
                    thumbnail_path = os.path.join(video_work_dir, "thumbnail.jpg")
                    
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, "r", encoding="utf-8") as f:
                                meta_content = f.read()
                                if "YOUTUBE BAŞLIK:" in meta_content:
                                    yt_title = meta_content.split("YOUTUBE BAŞLIK:")[1].split("\n\n")[0].strip()
                                if "ETİKETLER:" in meta_content:
                                    tags_str = meta_content.split("ETİKETLER:")[1].split("\n\n")[0].strip()
                                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                                if "AÇIKLAMA:" in meta_content:
                                    yt_desc = meta_content.split("AÇIKLAMA:")[1].split("\n\n")[0].strip()
                        except: pass

                    success_yt = youtube_uploader.upload_to_youtube(
                        p, 
                        yt_title, 
                        yt_desc, 
                        tags=tags, 
                        thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None,
                        token_path=yt_token_path
                    )
                    if success_yt:
                        self.after(0, self.log_message, "YouTube yüklemesi BAŞARILI (GİZLİ).", False)
                    else:
                        self.after(0, self.log_message, "YouTube yüklemesi BAŞARISIZ.", False)
                
                self.after(0, lambda p=p: messagebox.showinfo("Başarılı", f"Video üretildi:\n{p}"))
        except Exception as e:
            print(f"\n!!! run_pipeline HATASI !!!")
            traceback.print_exc()
            err_msg = str(e)
            self.after(0, lambda err_msg=err_msg: messagebox.showerror("Hata", err_msg))
        finally:
            gc.collect()
            self.after(0, self.reset_ui)

    def _lower_process_priority(self):
        """Lower the current process priority so rendering doesn't freeze the OS."""
        try:
            if sys.platform == 'win32':
                import psutil
                p = psutil.Process(os.getpid())
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                print("İşlem önceliği düşürüldü (BELOW_NORMAL) - UI donması önlendi.")
        except ImportError:
            # psutil not installed, try Windows API directly
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetCurrentProcess()
                # BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
                kernel32.SetPriorityClass(handle, 0x00004000)
                print("İşlem önceliği düşürüldü (ctypes) - UI donması önlendi.")
            except Exception:
                pass
        except Exception:
            pass

    def reset_ui(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.generate_btn.configure(state="normal")
        self.topic_textbox.configure(state="normal")

        self.browse_btn.configure(state="normal")
        self.browse_bgm_btn.configure(state="normal")
        self.voice_checkbox.configure(state="normal")
        self.subtitle_checkbox.configure(state="normal")
        self.youtube_checkbox.configure(state="normal")
        self.bgm_entry.configure(state="normal")
        self.bgm_vol_slider.configure(state="normal")
        self.word_count_entry.configure(state="normal")
        self.tts_provider_menu.configure(state="normal")
        self.edge_voice_menu.configure(state="normal")
        self.video_source_menu.configure(state="normal")
        self.category_menu.configure(state="normal")
        self.language_menu.configure(state="normal")
        self.darken_checkbox.configure(state="normal")
        self.gpu_checkbox.configure(state="normal")
        self.fog_checkbox.configure(state="normal")
        self.sparks_checkbox.configure(state="normal")
        self.orientation_menu.configure(state="normal")
        self.subtitle_style_menu.configure(state="normal")
        self.content_provider_menu.configure(state="normal")
        # Re-enable browse button only if manual mode is selected
        if "Manuel" in self.video_source_var.get():
            self.browse_videos_btn.configure(state="normal")
        self.status_label.configure(text="İşlem bitti. Yeni konu girilebilir.", text_color="green")

    def _on_auto_asset_change(self):
        if self.auto_asset_var.get():
            self.asset_count_slider.configure(state="disabled")
            self.asset_count_label.configure(text_color="gray")
        else:
            self.asset_count_slider.configure(state="normal")
            self.asset_count_label.configure(text_color=self.accent_color)

    def _on_batch_auto_asset_change(self):
        if self.batch_auto_asset_var.get():
            self.batch_asset_count_slider.configure(state="disabled")
            self.batch_asset_count_label.configure(text_color="gray")
        else:
            self.batch_asset_count_slider.configure(state="normal")
            self.batch_asset_count_label.configure(text_color="#FFD700")


    def browse_clone_file(self):
        fpath = ctk.filedialog.askopenfilename(filetypes=[("Ses Dosyalari", "*.mp3 *.wav *.m4a")])
        if fpath:
            self.clone_file_entry.configure(state="normal")
            self.clone_file_entry.delete(0, "end")
            self.clone_file_entry.insert(0, fpath)
            self.clone_file_entry.configure(state="disabled")

    def start_voice_cloning(self):
        name = self.clone_name_entry.get().strip()
        fpath = self.clone_file_entry.get().strip()
        provider = self.clone_provider_var.get()
        
        if not name or not fpath:
            messagebox.showerror("Hata", "Lutfen ses ismi girin ve bir dosya secin!")
            return
            
        def run():
            try:
                self.clone_start_btn.configure(state="disabled", text="Klonlaniyor...")
                if provider == "ElevenLabs":
                    vid = clone_voice_elevenlabs(name, fpath)
                    self.voice_entry.delete(0, "end")
                    self.voice_entry.insert(0, vid)
                else:
                    vid = clone_voice_dubvoice(name, fpath)
                    self.dubvoice_voice_entry.delete(0, "end")
                    self.dubvoice_voice_entry.insert(0, vid)
                
                messagebox.showinfo("Basarili", f"Ses klonlandi ve {provider} Voice ID alanina eklendi! Kaydetmeyi unutmayin.")
            except Exception as e:
                messagebox.showerror("Klonlama Hatasi", str(e))
            finally:
                self.clone_start_btn.configure(state="normal", text="Klonla ve Voice ID Olarak Ata")
        
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
