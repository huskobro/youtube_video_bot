import os
import random
import gc
from proglog import ProgressBarLogger
import warnings
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips,
    CompositeVideoClip, CompositeAudioClip, vfx, ColorClip
)
from moviepy.video.fx import MultiplyColor, Loop
from moviepy.audio.fx import AudioLoop, MultiplyVolume
from visuals_manager import get_video_clips
from subtitle_gen import create_subtitle_clips

# Suppress MoviePy frame-read warnings (corrupted tail frames from downloads)
warnings.filterwarnings("ignore", category=UserWarning, module="moviepy")

# Default 720p HD (will be swapped if vertical)
TARGET_W = 1280
TARGET_H = 720
TARGET_FPS = 24

class MoviePyGUILogger(ProgressBarLogger):
    """
    Custom logger to pipe MoviePy rendering progress 
    to the GUI status label and log box.
    """
    def __init__(self, callback):
        super().__init__()
        self.gui_callback = callback
        self.last_percent = -1

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar == 'chunk': # MoviePy rendering bar (usually frames)
            total = self.bars['chunk'].get('total', 0)
            if total > 0:
                percent = int(value * 100 / total)
                if percent != self.last_percent:
                    self.last_percent = percent
                    if self.gui_callback:
                        if percent < 100:
                            self.gui_callback(f"Render İlerlemesi: %{percent}")
                        else:
                            # 100% logic: Encoding frames done, now muxing/finishing
                            self.gui_callback("Render %100: Görüntü işlendi. Ses birleştiriliyor ve dosya kapatılıyor (Lütfen bekleyin)...")

    def message_callback(self, message):
        """Pass important text messages from MoviePy to GUI."""
        if self.gui_callback:
             msg_low = message.lower()
             # Only pass relevant status updates to avoid cluttering
             if any(x in msg_low for x in ["render", "writing", "audio", "done", "encoding"]):
                 self.gui_callback(f"MoviePy: {message}")


def _apply_ken_burns(clip, duration, target_w, target_h):
    """
    Applies a slow, cinematic zoom and pan effect to an image.
    Makes static images feel like professional video footage.
    """
    # 50/50 chance for zoom-in or zoom-out
    zoom_in = random.choice([True, False])
    
    # Random zoom intensity (1.1x to 1.3x)
    # Slow means we don't want too much zoom if the duration is short
    zoom_start, zoom_end = (1.0, random.uniform(1.15, 1.25)) if zoom_in else (random.uniform(1.15, 1.25), 1.0)
    
    # Random pan offsets (max 10% of screen) to add "handheld" or "tracking" feel
    # This ensures the camera is always slightly moving
    pan_x_start = random.uniform(-0.05, 0.05)
    pan_y_start = random.uniform(-0.05, 0.05)
    pan_x_end = random.uniform(-0.05, 0.05)
    pan_y_end = random.uniform(-0.05, 0.05)

    def zoom_func(t):
        return zoom_start + (zoom_end - zoom_start) * (t / duration)
        
    def pos_func(t):
        curr_z = zoom_func(t)
        prog = t / duration # 0.0 to 1.0
        
        # Calculate current panning offset
        curr_off_x = pan_x_start + (pan_x_end - pan_x_start) * prog
        curr_off_y = pan_y_start + (pan_y_end - pan_y_start) * prog
        
        # New dimensions of the zoomed image
        nw = target_w * curr_z
        nh = target_h * curr_z
        
        # Center the image and apply the smooth pan offset
        # (nw - target_w) is the "extra" space we have to move around
        x = (target_w - nw) / 2 + (curr_off_x * (nw - target_w))
        y = (target_h - nh) / 2 + (curr_off_y * (nh - target_h))
        
        return (x, y)

    # Apply transformations using MoviePy 1.x / 2.x compatibility
    if hasattr(clip, "resized"):
        clip = clip.resized(zoom_func)
    else:
        clip = clip.resize(zoom_func)
        
    if hasattr(clip, "with_position"):
        return clip.with_position(pos_func)
    else:
        return clip.set_position(pos_func)

# Trim this many seconds from the END of every clip to avoid corrupted tail frames
TAIL_TRIM_SECONDS = 0.5
TRANSITION_DURATION = 0.3  # Reduced for faster rendering and snappier feel
TURBO_CUTS = True        # Use 'chain' method for instant concatenation on vertical videos if transitions not needed



def _safe_close(obj):
    """Safely call .close() on an object if it exists and is callable."""
    if obj is not None:
        close_func = getattr(obj, "close", None)
        if callable(close_func):
            try:
                close_func()
            except:
                pass


def _load_clip(clip_path: str, target_w: int, target_h: int) -> VideoFileClip | None:
    try:
        is_image = clip_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.jfif'))
        if is_image:
            try:
                with open(clip_path, 'rb') as f:
                    header = f.read(20).strip().lower()
                    if header.startswith(b"<!doctype") or header.startswith(b"<html>"):
                        print(f"  ⚠ Atlandı (Hatalı Dosya/HTML): {os.path.basename(clip_path)}")
                        return None
            except: pass
            
            clip = ImageClip(clip_path)
            if hasattr(clip, "with_duration"):
                clip = clip.with_duration(3.0)
            else:
                clip = clip.set_duration(3.0)
        else:
            # Handle videos - Try hardware acceleration for decoding
            try:
                if clip_path.lower().endswith(('.mp4', '.mov')):
                    # Use cuda for faster decoding on RTX 4060
                    clip = VideoFileClip(clip_path, ffmpeg_params=["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
                else:
                    clip = VideoFileClip(clip_path)
            except Exception as e:
                # Fallback to CPU decoding if CUDA fails
                clip = VideoFileClip(clip_path)
                
            # Skip extremely short clips
            clip_duration = float(clip.duration) if clip.duration is not None else 0.0
            if clip_duration < 1.0:
                print(f"  ⚠ Klip çok kısa (<1s), atlandı: {os.path.basename(clip_path)}")
                _safe_close(clip)
                return None

            # Trim tail and remove audio
            safe_end = max(0.5, clip_duration - TAIL_TRIM_SECONDS)
            clip = clip.subclipped(0, safe_end) if hasattr(clip, "subclipped") else clip.subclip(0, safe_end)
            clip = clip.without_audio()

        if clip.w < 1 or clip.h < 1:
            print(f"  ⚠ Geçersiz boyut ({clip.w}x{clip.h}), atlandı: {os.path.basename(clip_path)}")
            _safe_close(clip)
            return None

        if clip.w != target_w or clip.h != target_h:
            # Smart crop/resize to fit target aspect ratio
            w_ratio = target_w / clip.w
            h_ratio = target_h / clip.h
            ratio = max(w_ratio, h_ratio)
            
            new_w = max(1, int(clip.w * ratio))
            new_h = max(1, int(clip.h * ratio))
            
            # Resize
            try:
                if hasattr(clip, "resized"):
                    clip = clip.resized(new_size=(new_w, new_h))
                else:
                    clip = clip.resize(newsize=(new_w, new_h))
            except Exception as re:
                print(f"  ⚠ Resize hatası ({new_w}x{new_h}): {re}")
                _safe_close(clip)
                return None
            
            # Crop to center
            if target_w > 0 and target_h > 0:
                try:
                    if hasattr(clip, "cropped"):
                        clip = clip.cropped(
                            x_center=new_w/2, y_center=new_h/2, 
                            width=target_w, height=target_h
                        )
                    else:
                        # Safer fallback for v1 crop using explicit coordinates if x_center fails
                        x1 = max(0, (new_w - target_w) // 2)
                        y1 = max(0, (new_h - target_h) // 2)
                        clip = clip.crop(x1=x1, y1=y1, x2=x1+target_w, y2=y1+target_h)
                except Exception as ce:
                    print(f"  ⚠ Crop hatası (Target: {target_w}x{target_h}): {ce}")
                    _safe_close(clip)
                    return None

        type_str = "Resim (Image)" if isinstance(clip, ImageClip) else "Video"
        print(f"  ✓ Yüklendi ({type_str}): {os.path.basename(clip_path)}")
        return clip
    except Exception as e:
        print(f"  ⚠ Klip yüklenemedi {os.path.basename(clip_path)}: {str(e)}")
        _safe_close(clip if 'clip' in locals() else None)
        return None


def create_video(
    audio_path: str,
    output_path: str = "output/final_video.mp4",
    bgm_path: str = "",
    bgm_volume: float = 0.5,
    script: str = "",
    videos_folder: str = "assets/videos",
    use_subtitles: bool = True,
    effects_config: dict = None,
    is_vertical: bool = False,
    subtitle_style: str = "Standart (Kutu)",
    use_gpu: bool = False,
    progress_callback = None
) -> str:
    """
    Assembled video creation.
    is_vertical: True for 9:16 Shorts/TikTok (1280x720 -> 720x1280)
    """
    if effects_config is None:
        effects_config = {"darken": False, "fog": False, "sparks": False}

    # Set dimensions based on orientation
    target_w = 720 if is_vertical else 1280
    target_h = 1280 if is_vertical else 720
    
    # Absolute safety
    target_w = max(1, target_w)
    target_h = max(1, target_h)
    
    print(f"🎬 Video Modu: {'DİKEY (Shorts/9:16)' if is_vertical else 'YATAY (YouTube/16:9)'}")
    print(f"   Çözünürlük: {target_w}x{target_h}")


    final_audio = None
    target_duration = 60.0

    # ── Step 1: Determine target duration from the voiceover ──
    if audio_path and os.path.exists(audio_path):
        final_audio = AudioFileClip(audio_path)
        target_duration = final_audio.duration
        print(f"Seslendirme süresi: {target_duration:.1f} saniye")
    elif bgm_path and os.path.exists(bgm_path):
        target_duration = 120.0
    else:
        print("Uyarı: Audio yok. 60 saniyelik default video üretilecek.")

    # ── Step 2: Get available video clip paths ──
    available_clips = get_video_clips(target_duration, videos_folder=videos_folder)
    if not available_clips:
        err_msg = f"HATA: {videos_folder} klasöründe geçerli video/görsel dosyası bulunamadı. Kaynak indirilememiş olabilir."
        print(err_msg)
        if final_audio:
            final_audio.close()
        raise RuntimeError(err_msg)

    print(f"Hedef video süresi: {target_duration:.1f} saniye")
    print(f"Kullanılabilir klip sayısı: {len(available_clips)}")

    loaded_clips: list[tuple[str, VideoFileClip]] = []
    print(f"Klipler taranıyor: {videos_folder}")
    for path in available_clips:
        c = _load_clip(path, target_w, target_h)
        if c is not None:
            loaded_clips.append((path, c))
    
    # Summary of loaded types
    v_count = sum(1 for p, c in loaded_clips if not p.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
    i_count = len(loaded_clips) - v_count
    print(f"Yükleme tamamlandı: {v_count} Video, {i_count} Resim bulundu.")

    if not loaded_clips:
        print("HATA: Hiçbir video yüklenemedi.")
        _safe_close(final_audio)
        return ""

    total_unique_dur = sum(float(c.duration) for _, c in loaded_clips if c.duration is not None)
    print(f"Toplam benzersiz klip süresi: {total_unique_dur:.1f}s")

    # ── Step 4: Build clip sequence — Dynamic Duration & Repetition Logic ──
    print(f"🎬 Görsel dağılım algoritması başlatılıyor (Hedef: {target_duration:.1f}s)...")
    
    num_unique = len(loaded_clips)
    
    # Repetition logic based on user rules
    # < 5 min (300s) -> 1 repeat (once)
    # 5-10 min (300-600s) -> 2 repeats
    # 11-30 min (660-1800s) -> 3 repeats
    if target_duration <= 300:
        repeats = 1
    elif target_duration <= 600:
        repeats = 2
    else:
        repeats = 3
        
    total_segments = num_unique * repeats
    avg_segment_dur = target_duration / total_segments
    
    print(f"  → Tekrar Sayısı: {repeats}x | Toplam Parça: {total_segments}")
    print(f"  → Ortalama Görsel Süresi: {avg_segment_dur:.1f}s")

    assembled_clips: list[VideoFileClip] = []
    current_duration: float = 0.0
    
    # Create the full sequence of paths/clips to use
    full_sequence = []
    for _ in range(repeats):
        # Shuffle each "set" for variety but keep the set complete
        order = list(range(num_unique))
        random.shuffle(order)
        for idx in order:
            full_sequence.append(loaded_clips[idx])

    # Now assign durations and add to assembly
    for i, (path, original) in enumerate(full_sequence):
        if current_duration >= float(target_duration):
            break
            
        # Calculate duration for THIS segment
        # Add +/- 15% randomness for a more natural feel, while keeping total exact
        remaining_time = float(target_duration) - current_duration
        remaining_segments = total_segments - i
        
        if remaining_segments <= 1:
            this_dur = remaining_time
        else:
            # Randomize duration between 85% and 115% of average, 
            # ensuring it's at least 2 seconds and not more than remaining
            variation = random.uniform(0.85, 1.15)
            this_dur = min(remaining_time - 1.0, avg_segment_dur * variation)
            this_dur = max(2.0, this_dur)

        try:
            # Stretch or Loop the clip to match the calculated duration
            if path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                # Images: Set duration (keep static as per user request)
                new_piece = original.with_duration(this_dur)
            else:
                # Videos: loop if shorter, cut if longer
                v_dur = float(original.duration)
                
                # Add overlap duration to ensure smooth crossfade
                # Each clip needs to be slightly longer except the last
                segment_dur_needed = this_dur
                if i < len(full_sequence) - 1:
                    segment_dur_needed += TRANSITION_DURATION

                if v_dur < segment_dur_needed:
                    # Loop the video to fill the slotted time
                    new_piece = original.with_effects([Loop(duration=segment_dur_needed)])
                else:
                    # Random start point or just start from 0
                    start_ptr = random.uniform(0, max(0, v_dur - segment_dur_needed))
                    new_piece = original.subclipped(start_ptr, start_ptr + segment_dur_needed)
            
            # Apply CrossFade effect
            # First clip doesn't fade in from nothing, but others fade in from previous
            if i > 0:
                if hasattr(new_piece, "crossfadein"):
                    new_piece = new_piece.crossfadein(TRANSITION_DURATION)
                else:
                    from moviepy.video.fx import CrossFadeIn
                    new_piece = new_piece.with_effects([CrossFadeIn(TRANSITION_DURATION)])

            assembled_clips.append(new_piece)
            current_duration += this_dur # Only add the effective duration (without overlap)
            
            # Print periodic progress for long videos
            if i % 5 == 0 or i == total_segments - 1:
                print(f"  [Segment {i+1}/{total_segments}] {os.path.basename(path)} | "
                      f"Süre: {float(new_piece.duration):.1f}s | "
                      f"Toplam: {current_duration:.1f}/{target_duration:.1f}s")
                      
        except Exception as e:
            print(f"  ⚠ Segment işlenemedi {os.path.basename(path)}: {e}")
            continue

    if not assembled_clips:
        print("HATA: Klip dizisi oluşturulamadı.")
        _safe_close(final_audio)
        return ""

    print(f"Toplam {len(assembled_clips)} klip parçası birleştiriliyor "
          f"({current_duration:.1f}s)...")

    # ── Step 5: Concatenate ──
    # Optimization: Use 'chain' for extreme speed if it's a Short (Turbo Cuts) or duration is 0
    if (is_vertical and TURBO_CUTS) or TRANSITION_DURATION <= 0:
        print(f"🎬 Hızlı Mod (Turbo Cuts) aktif. Geçişsiz birleştiriliyor...")
        base_video = concatenate_videoclips(assembled_clips, method="chain")
    else:
        print(f"🎬 {len(assembled_clips)} parça sinematik geçişlerle birleştiriliyor...")
        base_video = concatenate_videoclips(
            assembled_clips, 
            method="compose", 
            padding=-TRANSITION_DURATION,
            bg_color=(0,0,0)
        )
    # Ensure final dimensions are correct (crops overhanging Ken Burns edges)
    if base_video.w != target_w or base_video.h != target_h:
        if hasattr(base_video, "cropped"):
            base_video = base_video.cropped(width=target_w, height=target_h, x_center=target_w/2, y_center=target_h/2)
        else:
            base_video = base_video.crop(x1=0, y1=0, width=target_w, height=target_h)

    # ── Step 6: Add subtitles ──
    subtitle_layer = None
    subtitle_clips_list = [] # For cleanup
    if use_subtitles and script and script.strip():
        print("Altyazılar oluşturuluyor...")
        try:
            import json
            timing_data = None
            if audio_path:
                timing_path = audio_path.replace(".mp3", "_timing.json")
                if os.path.exists(timing_path):
                    with open(timing_path, "r", encoding="utf-8") as f:
                        timing_data = json.load(f)
            
            s_clips = create_subtitle_clips(
                script, base_video.duration, target_w, target_h,
                timing_data=timing_data,
                style=subtitle_style
            )
            
            if s_clips:
                subtitle_clips_list = s_clips
                # OPTIMIZATION: Composite subtitles once into a single layer
                print(f"  ✓ {len(s_clips)} altyazı klibi oluşturuldu. Katman optimize ediliyor...")
                subtitle_layer = CompositeVideoClip(s_clips, size=(target_w, target_h)).with_duration(base_video.duration)
        except Exception as e:
            print(f"  ⚠ Altyazı oluşturulamadı: {e}")

    # ── Step 6.1: Add Visual Effects (Overlays) ──
    overlay_clips = []
    
    if effects_config.get("darken"):
        print("  → Karartma efekti uygulanıyor...")
        try:
            dark_mask = ColorClip(size=(target_w, target_h), color=(0, 0, 0))
            dark_mask = dark_mask.with_duration(base_video.duration).with_opacity(0.25)
            overlay_clips.append(dark_mask)
        except: pass

    # Fog / Sis Effect
    if effects_config.get("fog"):
        fog_path = os.path.join("assets", "effects", "istockphoto-1175691070-640_adpp_is.mp4")
        if os.path.exists(fog_path):
            print("  → Sis efekti ekleniyor (Turbo)...")
            try:
                fog_raw = VideoFileClip(fog_path).without_audio()
                # Single resize is faster
                fog_final = fog_raw.resized(new_size=(target_w, target_h)).with_effects([Loop(duration=base_video.duration)]).with_opacity(0.3)
                overlay_clips.append(fog_final)
            except: pass

    # Sparks / Kıvılcım Effect
    if effects_config.get("sparks"):
        sparks_path = os.path.join("assets", "effects", "istockphoto-1436573217-640_adpp_is.mp4")
        if os.path.exists(sparks_path):
            print("  → Kıvılcım efekti ekleniyor (Turbo)...")
            try:
                sparks_raw = VideoFileClip(sparks_path).without_audio()
                sparks_final = sparks_raw.resized(new_size=(target_w, target_h)).with_effects([Loop(duration=base_video.duration)]).with_opacity(0.4)
                overlay_clips.append(sparks_final)
            except: pass

    # ── Step 7: Final Composition ──
    if not overlay_clips and not subtitle_layer:
        # Optimization: Don't use CompositeVideoClip if there are no layers
        final_video = base_video
    else:
        main_layers = [base_video] + overlay_clips
        if subtitle_layer:
            main_layers.append(subtitle_layer)
        final_video = CompositeVideoClip(main_layers, size=(target_w, target_h))


    # ── Step 7: Build audio track ──
    audio_tracks = []
    if final_audio:
        audio_tracks.append(final_audio)

    if bgm_path and os.path.exists(bgm_path):
        try:
            bgm_clip = AudioFileClip(bgm_path)
            # Apply volume and loop to match video duration
            bgm_clip = bgm_clip.with_effects([
                MultiplyVolume(bgm_volume),
                AudioLoop(duration=final_video.duration),
            ])
            audio_tracks.append(bgm_clip)
            print(f"BGM {final_video.duration:.1f}s boyunca tekrar edecek.")
        except Exception as e:
            print(f"  ⚠ BGM yüklenemedi: {e}")

    if audio_tracks:
        final_composite_audio = CompositeAudioClip(audio_tracks)
        final_video = final_video.with_audio(final_composite_audio)

    # ── Step 8: Export ──
    import time as _render_time
    render_start = _render_time.time()
    print(f"Video dışa aktarılıyor ({final_video.duration:.0f}s video)...")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cpu_count = os.cpu_count() or 4
    # For RTX 4060 systems, we can push more threads
    render_threads = cpu_count * 2 if cpu_count <= 8 else cpu_count + 4

    # Use temp audio file in same directory to avoid orphan temp files
    temp_audio_path = output_path.replace(".mp4", "_TEMP_audio.m4a")

    try:
        if use_gpu:
            # ── NVIDIA NVENC (RTX 4060) - TURBO MODE ──
            print(f"🚀 [TURBO GPU] NVENC Aktif (RTX 4060) | {render_threads} CPU Threads...")
            
            render_codec = "h264_nvenc"
            extra_params = [
                "-preset", "p1",        # Fastest NVENC preset (High Performance)
                "-tune", "hq",          # High quality tuning
                "-rc", "vbr",           # Variable Bitrate
                "-cq", "24",            # Quality (24 is a good balance)
                "-2pass", "0",          # Fast single pass
                "-gpu", "any",          # Use any available NVIDIA GPU
                "-b:v", "8M",           # Target bitrate for 1080p/720p
                "-maxrate", "12M",
                "-bufsize", "15M",
                "-profile:v", "high",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-threads", str(render_threads),
                "-sn", "-map_metadata", "-1"
            ]
            
            # TURBO: Use 0 for threads in write_videofile if using ffmpeg_params threads
            # MoviePy threads can sometimes conflict with encoder threads
            
            # Setup logger
            render_logger = MoviePyGUILogger(progress_callback) if progress_callback else None
            
            final_video.write_videofile(
                output_path,
                fps=TARGET_FPS,
                codec=render_codec,
                audio_codec="aac",
                threads=render_threads,
                ffmpeg_params=extra_params,
                temp_audiofile=temp_audio_path,
                remove_temp=True,
                logger=render_logger # Use custom logger instead of None
            )
        else:
            # ── CPU (libx264) - SUPERFAST ──
            print(f"⚡ [CPU SUPERFAST] İşlemci render modu | {render_threads} thread...")
            render_codec = "libx264"
            extra_params = [
                "-preset", "superfast", # superfast is better balance than ultrafast
                "-crf", "24",
                "-threads", str(render_threads),
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ]
            
            render_logger = MoviePyGUILogger(progress_callback) if progress_callback else None
            
            final_video.write_videofile(
                output_path,
                fps=TARGET_FPS,
                codec=render_codec,
                audio_codec="aac",
                threads=render_threads,
                ffmpeg_params=extra_params,
                temp_audiofile=temp_audio_path,
                remove_temp=True,
                logger=render_logger # Use custom logger
            )

        
        render_elapsed = _render_time.time() - render_start
        speed_ratio = final_video.duration / render_elapsed if render_elapsed > 0 else 0
        print(f"✅ Render tamamlandı: {render_elapsed:.0f}s ({speed_ratio:.1f}x hız)")
    except Exception as e:
        print(f"❌ Kritik Hata: Render başarısız oldu: {e}")
        raise e

    # ── Step 9: Cleanup ──
    print("Bellek temizleniyor...")
    
    # Close assembled subclips
    for c in assembled_clips:
        _safe_close(c)
            
    # Close original pre-loaded clips
    for _, c in loaded_clips:
        _safe_close(c)

    for sc in subtitle_clips_list:
        _safe_close(sc)

    _safe_close(final_video)
    _safe_close(final_audio)

    gc.collect()

    print(f"✅ Video başarıyla oluşturuldu: {output_path}")
    return output_path


if __name__ == "__main__":
    test_audio = "temp/test_voice.mp3"
    if os.path.exists(test_audio):
        create_video(test_audio, "output/test_video.mp4")
    else:
        print("Test ses dosyası bulunamadı.")
