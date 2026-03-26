"""
Subtitle Generator — PIL-based styled subtitle system.
Creates beautiful single-line subtitles with:
  - White bold text with dark outline for readability
  - Semi-transparent dark background
  - Yellow/gold border around the text box
  - Centered at the bottom of the video
No ImageMagick dependency required — pure PIL/Pillow.
"""

import re
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Standard Style (for long videos)
SUBTITLE_FONT_SIZE = 42
SUBTITLE_COLOR = (255, 255, 255, 255)
SUBTITLE_STROKE_COLOR = (0, 0, 0, 255)
SUBTITLE_STROKE_WIDTH = 3
BORDER_COLOR = (255, 200, 0, 230)
BG_COLOR = (10, 10, 10, 190)
BORDER_THICKNESS = 3
BORDER_RADIUS = 14
PADDING_X = 26
PADDING_Y = 14
BOTTOM_MARGIN = 50
MAX_WORDS_PER_LINE = 7

# Dynamic Style (for Shorts/Snappy content)
MAX_WORDS_DYNAMIC = 3                           # Hormozi style words count
DYNAMIC_FONT_SIZE = 72                          # Large for Shorts
HIGHLIGHT_COLOR = (255, 255, 0, 255)            # Bright Yellow for highlighted word
WHITE_COLOR = (255, 255, 255, 255)              # White for other words
STOKE_WIDTH_DYNAMIC = 5                         # Thicker stroke for bold look


# ──────────────────────── Font Loader ────────────────────────
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a bold, clean font. Falls back gracefully."""
    font_candidates = [
        "C:/Windows/Fonts/arialbd.ttf",    # Arial Bold
        "C:/Windows/Fonts/impact.ttf",     # Impact
        "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold
        "C:/Windows/Fonts/arial.ttf",      # Arial Regular
        "C:/Windows/Fonts/calibrib.ttf",   # Calibri Bold
    ]
    for path in font_candidates:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    # Ultimate fallback
    return ImageFont.load_default()


# ──────────────────────── Text Splitter ────────────────────────
def split_script_to_subtitles(script: str, max_words: int = MAX_WORDS_PER_LINE) -> list[str]:
    """
    Split the full script into short, single-line subtitle chunks.
    Each chunk has at most `max_words` words.
    """
    script = script.strip()
    if not script:
        return []

    # Split by sentence endings (.  !  ?  …)
    sentences = re.split(r'(?<=[.!?…])\s+', script)

    chunks: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()

        if len(words) <= max_words:
            chunks.append(sentence)
        else:
            # Try to split at commas first for natural breaks
            parts = re.split(r',\s*', sentence)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                part_words = part.split()
                if len(part_words) <= max_words:
                    chunks.append(part)
                else:
                    # Force-split by word count
                    for i in range(0, len(part_words), max_words):
                        chunk = ' '.join(part_words[i:i + max_words])
                        if chunk:
                            chunks.append(chunk)

    return chunks if chunks else [script[:80]]


# ──────────────────────── Frame Renderer ────────────────────────
def create_subtitle_frame(text: str, video_w: int, video_h: int, style: str = "Standart (Kutu)") -> np.ndarray:
    """
    Render a single subtitle line as an RGBA numpy array.
    Supports multiple aesthetic styles.
    """
    # Baseline settings
    font_size = SUBTITLE_FONT_SIZE
    stroke_width = SUBTITLE_STROKE_WIDTH
    font = _get_font(font_size)
    
    # Style definitions
    text_color = (255, 255, 255, 255)
    stroke_color = (0, 0, 0, 255)
    bg_fill = None
    border_fill = None
    has_box = False

    if style == "Standart (Kutu)":
        text_color = SUBTITLE_COLOR
        stroke_color = SUBTITLE_STROKE_COLOR
        bg_fill = BG_COLOR
        border_fill = BORDER_COLOR
        has_box = True
    elif style == "Neon Mavi":
        # No box, just glowy blue outline
        text_color = (255, 255, 255, 255)
        stroke_color = (0, 180, 255, 230)
        stroke_width = 5
        font_size = 46
    elif style == "Altın Işıltı":
        # No box, gold/yellow glow
        text_color = (255, 255, 255, 255)
        stroke_color = (255, 215, 0, 240)
        stroke_width = 5
        font_size = 46
    elif style == "Modern Sade":
        # Minimalist shadow
        text_color = (255, 255, 255, 255)
        stroke_color = (0, 0, 0, 180)
        stroke_width = 2
        bg_fill = (0, 0, 0, 100)
        has_box = True
        border_fill = (255, 255, 255, 40) # Subtle white border

    # Sanity check for dimensions
    video_w = max(1, video_w)
    video_h = max(1, video_h)
    
    if not text.strip():
        text = " " 

    # ---- Measure text ----
    font = _get_font(font_size)
    tmp = Image.new('RGBA', (1, 1))
    tmp_draw = ImageDraw.Draw(tmp)
    bbox = tmp_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Auto-shrink if too wide
    max_text_w = video_w - 100
    while text_w > max_text_w and font_size > 22:
        font_size -= 2
        font = _get_font(font_size)
        bbox = tmp_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    # ---- Create frame ----
    frame = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # ---- Draw Box if needed ----
    if has_box:
        box_w = text_w + PADDING_X * 2
        box_h = text_h + PADDING_Y * 2
        total_w = box_w + BORDER_THICKNESS * 2
        total_h = box_h + BORDER_THICKNESS * 2
        
        box_x = (video_w - total_w) // 2
        box_y = video_h - total_h - BOTTOM_MARGIN
        
        # Outer Border
        if border_fill:
            draw.rounded_rectangle(
                [box_x, box_y, box_x + total_w, box_y + total_h],
                radius=BORDER_RADIUS, fill=border_fill
            )
        
        # Inner BG
        inner_x = box_x + BORDER_THICKNESS
        inner_y = box_y + BORDER_THICKNESS
        draw.rounded_rectangle(
            [inner_x, inner_y, inner_x + box_w, inner_y + box_h],
            radius=max(BORDER_RADIUS - 2, 2), fill=bg_fill
        )
        t_pos = (inner_x + PADDING_X, inner_y + PADDING_Y)
    else:
        # Floating text
        t_pos = ((video_w - text_w) // 2, video_h - text_h - BOTTOM_MARGIN - 20)

    # ---- Draw text ----
    draw.text(
        t_pos, text, fill=text_color, font=font,
        stroke_width=stroke_width, stroke_fill=stroke_color
    )

    return np.array(frame)


def create_dynamic_subtitle_frame(words_data: list, highlight_idx: int, video_w: int, video_h: int) -> np.ndarray:
    """
    Render a Hormozi-style subtitle block where one word is highlighted.
    words_data: list of strings (the words in the current chunk)
    highlight_idx: index of the word to highlight
    """
    font = _get_font(DYNAMIC_FONT_SIZE)
    
    # Measure total line width to center it
    tmp = Image.new('RGBA', (1, 1))
    tmp_draw = ImageDraw.Draw(tmp)
    
    # We need to measure each word and space to position them
    word_widths = []
    space_width = tmp_draw.textbbox((0,0), " ", font=font)[2]
    
    total_text_w = 0
    for i, word in enumerate(words_data):
        bbox = tmp_draw.textbbox((0,0), word, font=font, stroke_width=STOKE_WIDTH_DYNAMIC)
        w = bbox[2] - bbox[0]
        word_widths.append(w)
        total_text_w += w
    
    total_text_w += space_width * (len(words_data) - 1)
    
    # Create frame
    frame = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    
    current_x = (video_w - total_text_w) // 2
    # Vertically positioned at 75% depth (good for Shorts)
    y_pos = int(video_h * 0.70)
    
    # Draw background box (optional for dynamic style, usually just shadows/stroke)
    # Let's add a subtle dark background strip for better readability
    bg_padding = 20
    draw.rectangle(
        [current_x - bg_padding, y_pos - 10, current_x + total_text_w + bg_padding, y_pos + 90],
        fill=(0, 0, 0, 100) # Semi-transparent black strip
    )

    for i, word in enumerate(words_data):
        color = HIGHLIGHT_COLOR if i == highlight_idx else WHITE_COLOR
        
        # Hormozi style: Highlighted word is slightly bigger? 
        # For simplicity in PIL, let's just use color and bold stroke
        draw.text(
            (current_x, y_pos),
            word,
            fill=color,
            font=font,
            stroke_width=STOKE_WIDTH_DYNAMIC,
            stroke_fill=(0,0,0,255)
        )
        current_x += word_widths[i] + space_width

    return np.array(frame)


# ──────────────────────── MoviePy Integration ────────────────────────
def create_subtitle_clips(
    script: str,
    total_duration: float,
    video_w: int,
    video_h: int,
    timing_data: dict = None,
    style: str = "Standart (Kutu)"
) -> list:
    """
    Create timed subtitle ImageClips from the full script text.
    If timing_data (from Edge TTS SentenceBoundary) is provided,
    subtitles will be synchronized to the actual audio timing.
    Otherwise falls back to proportional word-count based timing.
    """
    from moviepy import ImageClip

    # --- Strategy A: Use real TTS timing data ---
    if timing_data:
        # Check if it's the new combined format (dict) or old (list)
        sentences = timing_data if isinstance(timing_data, list) else timing_data.get("sentences", [])
        words = [] if isinstance(timing_data, list) else timing_data.get("words", [])
        
        # Logic: 
        # 1. If Dynamic style requested AND we have word timing -> Go Dynamic
        # 2. If Standart requested OR no word timing -> Use Standard (Sentences)
        is_dynamic_requested = "Dinamik" in style
        
        if is_dynamic_requested and words:
            print(f"  🔥 Dinamik (Shorts) altyazılar oluşturuluyor ({len(words)} kelime)...")
            subtitle_clips = []
            
            # Group words into small chunks (e.g. 2-3 words)
            chunk_size = MAX_WORDS_DYNAMIC
            for i in range(0, len(words), chunk_size):
                chunk = words[i : i + chunk_size]
                chunk_words = [w["text"] for w in chunk]
                
                # For each word in the chunk, create a frame where it is highlighted
                for idx, word_entry in enumerate(chunk):
                    start_t = word_entry["start"]
                    end_t = word_entry["end"]
                    dur = max(0.15, end_t - start_t) # Ensure visible
                    
                    if start_t >= total_duration: break
                    dur = min(dur, total_duration - start_t)
                    
                    frame = create_dynamic_subtitle_frame(chunk_words, idx, video_w, video_h)
                    
                    # Pop-out effect (slight zoom)
                    clip = ImageClip(frame).with_duration(dur).with_start(start_t).with_position((0, 0))
                    
                    # Manual "pop" via resize if possible, or just color highlight
                    # clip = clip.resize(lambda t: 1.0 + 0.05 * (1 - t/dur)) 
                    
                    subtitle_clips.append(clip)
            
            return subtitle_clips

        # Fallback to Sentence mode if no words
        if sentences:
            print(f"  Altyazılar TTS zamanlamasıyla senkronize ediliyor ({len(sentences)} cümle)...")
            subtitle_clips = []
            # ... (rest of sentence logic) ...
            for entry in sentences:
                text = entry.get("text", "").strip()
                start = entry.get("start", 0.0)
                end = entry.get("end", 0.0)
                duration = end - start
                
                if not text or duration <= 0: continue
                
                words_list = text.split()
                sub_chunks = []
                for j in range(0, len(words_list), MAX_WORDS_PER_LINE):
                    sub_chunks.append(' '.join(words_list[j : j + MAX_WORDS_PER_LINE]))
                
                total_words_in_sentence = len(words_list)
                chunk_time = start
                
                for chunk_text in sub_chunks:
                    chunk_wc = len(chunk_text.split())
                    chunk_dur = (chunk_wc / max(total_words_in_sentence, 1)) * duration
                    chunk_dur = max(chunk_dur, 0.5)
                    
                    if chunk_time >= total_duration: break
                    chunk_dur = min(chunk_dur, total_duration - chunk_time)
                    
                    frame = create_subtitle_frame(chunk_text, video_w, video_h, style=style)
                    clip = ImageClip(frame).with_duration(chunk_dur).with_start(chunk_time).with_position((0, 0))
                    subtitle_clips.append(clip)
                    chunk_time += chunk_dur
            return subtitle_clips

    # --- Strategy B: Fallback — word-count proportional timing ---
    chunks = split_script_to_subtitles(script)
    if not chunks:
        return []

    word_counts = [len(c.split()) for c in chunks]
    total_words = sum(word_counts)
    if total_words == 0:
        return []

    subtitle_clips = []
    current_time = 0.0

    for chunk, wc in zip(chunks, word_counts):
        duration = (wc / total_words) * total_duration
        duration = max(duration, 0.8)

        remaining = total_duration - current_time
        if remaining <= 0.1:
            break
        duration = min(duration, remaining)

        frame = create_subtitle_frame(chunk, video_w, video_h, style=style)
        clip = (
            ImageClip(frame)
            .with_duration(duration)
            .with_start(current_time)
            .with_position((0, 0))
        )
        subtitle_clips.append(clip)
        current_time += duration

    print(f"  ✓ {len(subtitle_clips)} altyazı klibi oluşturuldu "
          f"(toplam {current_time:.1f}s / {total_duration:.1f}s)")

    return subtitle_clips


# ──────────────────────── Standalone Test ────────────────────────
if __name__ == "__main__":
    test_text = (
        "Uzayın derinliklerinde karadeliklerin gizemi yatıyor. "
        "Bu devasa kozmik canavarlar ışığı bile yutabilecek güce sahip. "
        "Peki bir karadeliğe düşersek ne olur? "
        "İşte bilim insanlarının bu soruya verdiği cevaplar."
    )

    # Test splitting
    chunks = split_script_to_subtitles(test_text)
    print(f"Chunks ({len(chunks)}):")
    for i, c in enumerate(chunks):
        print(f"  [{i+1}] {c}")

    # Test rendering a single frame
    frame = create_subtitle_frame("Uzayın derinliklerinde gizem yatıyor!", 1280, 720)
    img = Image.fromarray(frame)
    os.makedirs("temp", exist_ok=True)
    img.save("temp/subtitle_test.png")
    print("\nTest altyazı kaydedildi: temp/subtitle_test.png")
