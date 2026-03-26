import os
import shutil
from script_gen import generate_script, get_visual_keywords, generate_youtube_metadata
from audio_gen import generate_voiceover
from video_editor import create_video
from pexels_manager import get_pexels_assets, get_pexels_images
from pixabay_manager import get_pixabay_assets, get_pixabay_images
from visual_gen import generate_ai_images, generate_single_leonardo_image, generate_youtube_thumbnail_with_text


def _sanitize_folder_name(name: str) -> str:
    """Create a safe folder name from the topic string."""
    # Remove or replace invalid characters for Windows folder names
    invalid_chars = '<>:"/\\|?*'
    safe = name.strip()
    for ch in invalid_chars:
        safe = safe.replace(ch, '')
    # Limit length and strip trailing dots/spaces
    safe = safe[:40].rstrip('. ')
    
    # Extra: specifically handle Turkish characters that FFmpeg/Windows can struggle with in paths
    char_map = {'İ': 'I', 'ı': 'i', 'Ş': 'S', 'ş': 's', 'Ğ': 'G', 'ğ': 'g', 'Ü': 'U', 'ü': 'u', 'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c'}
    for k, v in char_map.items():
        safe = safe.replace(k, v)
        
    return safe.replace(' ', '_') if safe else 'video'


def generate_full_video(
    topic: str,
    output_dir: str = "output",
    enable_voiceover: bool = True,
    bgm_path: str = "",
    bgm_volume: float = 0.5,
    word_count: int = 500,
    progress_callback=None,
    tts_provider: str = "edge",
    edge_voice_id: str = "tr-TR-AhmetNeural",
    manual_video_files: list = None,
    category: str = "🎬 Genel",
    language: str = "tr",
    video_source: str = "Pexels (Otomatik İndir)",
    enable_subtitles: bool = True,
    effects_config: dict = None,
    model_id: str = None,
    ai_content_count: int = 5,
    auto_asset_count: bool = False,
    use_leonardo_motion: bool = False,
    is_vertical: bool = False,
    subtitle_style: str = "Standart (Kutu)",
    content_provider: str = "google",
    use_gpu: bool = False,
    progress_val_callback=None
) -> str:
    """
    Main orchestration function to run the whole pipeline.
    Each video gets its own isolated folder under output_dir so
    assets (videos, audio, scripts) never mix between videos.
    
    manual_video_files: If provided (non-empty list), these video files are
    used instead of downloading from Pexels.
    """
    if manual_video_files is None:
        manual_video_files = []

    def log(msg):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    def set_progress(val):
        if progress_val_callback:
            progress_val_callback(val)

    try:
        set_progress(0.02)
        # ── Create a unique folder for this video ──
        folder_name = _sanitize_folder_name(topic)
        video_work_dir = os.path.join(output_dir, folder_name)
        os.makedirs(video_work_dir, exist_ok=True)

        # Sub-folders inside the video's own directory
        videos_dir = os.path.join(video_work_dir, "videos")   # Pexels / stock clips
        temp_dir = os.path.join(video_work_dir, "temp")        # Voiceover, script
        os.makedirs(videos_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        log(f"📁 Çalışma klasörü: {video_work_dir}")

        # ── Step 1: Script Generation ──
        provider_name = "Gemini" if content_provider == "google" else "Kie.ai (Gemini 3.1 Pro)"
        log(f" Adım 1: Video senaryosu AI tarafından oluşturuluyor ({provider_name})...")
        set_progress(0.05)
        script = generate_script(topic, word_count, category, language, provider=content_provider)
        if not script:
            raise ValueError("Senaryo oluşturulamadı.")
            
        set_progress(0.12)
        log(" Adım 1.5: Görsel anahtar kelimeler çıkarılıyor...")
        visual_keywords = get_visual_keywords(script, provider=content_provider, category=category)
        log(f"  → Anahtar Kelimeler: {visual_keywords}")

        # ── Step 1.6: Pre-Generation Analysis (Auto Asset Count) ──
        if ai_content_count == -1: # Flag for "Auto"
            set_progress(0.15)
            log(" Adım 1.6: Senaryo analiz ediliyor, ideal görsel sayısı belirleniyor...")
            from visual_gen import estimate_asset_count_from_script
            ai_content_count = estimate_asset_count_from_script(script)
            log(f"  → Zekâ Modu Kararı: Bu video için {ai_content_count} adet görsel/video üretilecek.")

        # Save script inside this video's temp folder
        script_path = os.path.join(temp_dir, "script.txt")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        # ── Step 1.7: YouTube Metadata Generation ──
        log(f"Adım 1.7: YouTube başlık, açıklama ve etiketler oluşturuluyor ({provider_name})...")
        metadata = generate_youtube_metadata(topic, script, provider=content_provider, language=language)
        if metadata:
            metadata_path = os.path.join(video_work_dir, "video_metadata.txt")
            with open(metadata_path, "w", encoding="utf-8") as f:
                f.write(f"VİDEO KONUSU: {topic}\n")
                f.write(f"{'='*30}\n")
                f.write(f"YOUTUBE BAŞLIK:\n{metadata.get('title', '')}\n\n")
                f.write(f"THUMBNAIL YAZISI:\n{metadata.get('thumbnail_text', '')}\n\n")
                f.write(f"ETİKETLER:\n{metadata.get('tags', '')}\n\n")
                f.write(f"AÇIKLAMA:\n{metadata.get('description', '')}\n\n")
                f.write(f"LEONARDO.AI THUMBNAIL PROMPT:\n{metadata.get('thumbnail_prompt', '')}\n")
            log(f"  ✓ Metadata kaydedildi: {metadata_path}")
            
            # ── Step 1.8: Thumbnail Generation ──
            if metadata.get('thumbnail_prompt'):
                log("Özel Thumbnail: Konuya özel kapak resmi üretiliyor (Leonardo AI + Yazı)...")
                thumb_path = os.path.join(video_work_dir, "thumbnail.jpg")
                generated_thumb = generate_youtube_thumbnail_with_text(
                    topic=topic,
                    thumbnail_prompt=metadata['thumbnail_prompt'],
                    save_path=thumb_path,
                    thumbnail_text=metadata.get('thumbnail_text')
                )
                if generated_thumb:
                    log(f"  ✓ Thumbnail kaydedildi: {thumb_path}")
                else:
                    # Fallback: Leonardo
                    generate_single_leonardo_image(metadata['thumbnail_prompt'], thumb_path, title=metadata.get('title'))

        # ── Step 2: Voiceover ──
        audio_path = ""
        if enable_voiceover:
            provider_names = {
                "edge": "Edge TTS (Ücretsiz)", 
                "voyslity": "VoysLity", 
                "elevenlabs": "ElevenLabs", 
                "otomasyonlabs": "OtomasyonLabs",
                "dubvoice": "DubVoice.ai",
                "speshaudio": "Spesh Audio"
            }
            provider_name = provider_names.get(tts_provider, tts_provider)
            log(f" Adım 2: Seslendirme oluşturuluyor ({provider_name})...")
            set_progress(0.18)
            voiceover_path = os.path.join(temp_dir, "voiceover.mp3")
            audio_path = generate_voiceover(script, output_filename=voiceover_path, tts_provider=tts_provider, edge_voice_id=edge_voice_id, language=language, model_id=model_id)
            set_progress(0.25)
        else:
            log(" Adım 2: Seslendirme İptal Edildi (Sadece Arkaplan/Müzik).")
            set_progress(0.25)

        # ── Step 3: Get video clips ──
        if manual_video_files:
            # MANUEL MOD: Kullanıcının kendi videolarını kopyala
            log(f"Adım 3: Manuel videolar kopyalanıyor ({len(manual_video_files)} dosya)...")
            for i, src_path in enumerate(manual_video_files):
                if os.path.exists(src_path):
                    ext = os.path.splitext(src_path)[1]
                    dst = os.path.join(videos_dir, f"manuel_video_{i}{ext}")
                    if not os.path.exists(dst):
                        shutil.copy2(src_path, dst)
                    log(f"  ✓ Kopyalandı: {os.path.basename(src_path)}")
                else:
                    log(f"  ⚠ Dosya bulunamadı: {src_path}")
        elif "Leonardo.ai" in video_source:
            mode = "Video (Motion)" if use_leonardo_motion else "Görsel (Fotoğraf)"
            log(f"Adım 3: Leonardo.ai {mode} Üretimi Başlatıldı ({ai_content_count} adet)...")
            generate_ai_images(topic, count=ai_content_count, save_dir=videos_dir, provider="leonardo", keywords=visual_keywords, use_motion=use_leonardo_motion)
        elif "PicLumen" in video_source:
            log(f"Adım 3: AI Görsel Üretimi + Stok Video Karışımı Hazırlanıyor ({ai_content_count} adet)...")
            # Use ai_content_count as total, split roughly 70/30
            ai_count = int(ai_content_count * 0.7)
            stock_count = max(1, ai_content_count - ai_count)
            generate_ai_images(topic, count=ai_count, save_dir=videos_dir, provider="pollinations", keywords=visual_keywords, script=script)
            if os.getenv("PEXELS_API_KEY"):
                get_pexels_assets(topic, target_count=stock_count, save_dir=videos_dir, keywords=visual_keywords)
        elif "Karma" in video_source:
            half = max(1, ai_content_count // 2)
            log(f" Adım 3: Pexels Karma ({half} Video + {half} Fotoğraf) indiriliyor...")
            set_progress(0.30)
            get_pexels_assets(topic, target_count=half, save_dir=videos_dir, keywords=visual_keywords)
            get_pexels_images(topic, target_count=half, save_dir=videos_dir, keywords=visual_keywords)
            set_progress(0.40)
        elif "Pexels + Pixabay" in video_source:
            half = max(1, ai_content_count // 2)
            log(f" Adım 3: Hibrit Mod ({half} Pexels + {half} Pixabay) indiriliyor...")
            set_progress(0.30)
            get_pexels_assets(topic, target_count=half, save_dir=videos_dir, keywords=visual_keywords)
            get_pixabay_assets(topic, target_count=half, save_dir=videos_dir, keywords=visual_keywords)
            set_progress(0.40)
        elif "Pixabay" in video_source:
            log(f" Adım 3: Pixabay üzerinden {ai_content_count} içerik indiriliyor...")
            set_progress(0.30)
            get_pixabay_assets(topic, target_count=ai_content_count, save_dir=videos_dir, keywords=visual_keywords)
            set_progress(0.40)
        elif "Pexels (Görsel" in video_source:
            log(f" Adım 3: Pexels üzerinden {ai_content_count} fotoğraf indiriliyor...")
            set_progress(0.30)
            get_pexels_images(topic, target_count=ai_content_count, save_dir=videos_dir, keywords=visual_keywords)
            set_progress(0.40)
        elif os.getenv("PEXELS_API_KEY"):
            log(f" Adım 3: Pexels üzerinden {ai_content_count} video indiriliyor...")
            set_progress(0.30)
            get_pexels_assets(topic, target_count=ai_content_count, save_dir=videos_dir, keywords=visual_keywords)
            set_progress(0.40)
        else:
            log(" Adım 3: Pexels anahtarı yok, yerel videolar kullanılacak.")
            set_progress(0.30)
            # Copy shared stock videos into this video's folder if it's empty
            base_path = os.path.dirname(os.path.abspath(__file__))
            shared_assets = os.path.join(base_path, "assets", "videos")
            if os.path.exists(shared_assets) and not os.listdir(videos_dir):
                log("  → Yerel stok videolar kopyalanıyor...")
                for f in os.listdir(shared_assets):
                    if f.lower().endswith(('.mp4', '.mov', '.avi')):
                        src = os.path.join(shared_assets, f)
                        dst = os.path.join(videos_dir, f)
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)

        # ── Step 4: Assemble video with subtitles ──
        log("Adım 4: Video montajlanıyor (bu işlem birkaç dakika sürebilir, lütfen bekleyin)...")
        
        # Check if we actually have any media files
        if os.path.exists(videos_dir):
            files_in_dir = os.listdir(videos_dir)
            log(f"  → Klasörde {len(files_in_dir)} dosya bulundu: {videos_dir}")
            for ff in files_in_dir[:15]:
                log(f"     - {ff}")
        else:
            files_in_dir = []

        if not files_in_dir:
            log("⚠ HATA: İndirilenler klasörü boş! Video kaynağı (Pexels/Pixabay/Leonardo/AI) başarısız olmuş olabilir.")
            log("Lütfen API anahtarlarınızı kontrol edin veya internet bağlantınızdan emin olun.")
            raise RuntimeError("Klasörde stok video veya görsel bulunamadı. Lütfen kaynağı kontrol edin.")

        output_file = os.path.join(video_work_dir, f"{folder_name}.mp4")

        # Final render progress callback inside assembly step
        def render_progress_hook(msg):
            log(msg)
            if "Render İlerlemesi: %" in msg and progress_val_callback:
                try:
                    p_str = msg.split("%")[1].strip()
                    render_p = int(p_str)
                    # Map 0-100% of render to 0.45 - 0.98 of overall bar
                    overall_p = 0.45 + (render_p / 100.0) * 0.53
                    set_progress(overall_p)
                except: pass

        try:
            final_video_path = create_video(
                audio_path,
                output_path=output_file,
                bgm_path=bgm_path,
                bgm_volume=bgm_volume,
                script=script,
                videos_folder=videos_dir,
                use_subtitles=enable_subtitles,
                effects_config=effects_config,
                is_vertical=is_vertical,
                subtitle_style=subtitle_style,
                use_gpu=use_gpu,
                progress_callback=render_progress_hook
            )
            set_progress(1.0)
        except Exception as ve:
            log(f"⚠ Montaj sırasında teknik hata: {str(ve)}")
            raise RuntimeError(f"Video montajı sırasında bir hata oluştu: {str(ve)}")

        if final_video_path:
            log(f"✅ TAMAMLANDI! Video başarıyla oluşturuldu: {final_video_path}")
            return final_video_path
        else:
            raise RuntimeError("Video dosyası oluşturulamadı (montaj algoritması başarısız oldu).")

    except Exception as e:
        log(f"İşlem Durduruldu: {str(e)}")
        raise e


if __name__ == "__main__":
    generate_full_video("Mars'ta Hayat Olasılığı ve Yeni Keşifler")
