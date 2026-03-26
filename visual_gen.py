import os
import requests
import random
import time
import textwrap
import re as _re
from PIL import Image, ImageDraw, ImageFont


def generate_youtube_thumbnail_with_text(topic: str, thumbnail_prompt: str, save_path: str = None, thumbnail_text: str = None) -> str:
    """
    YouTube icin thumbnail uretir.
    - Leonardo AI ile sinematik arka plan
    - AI uretimli kisa yazi (4-5 kelime) gorselin karanlik tarafina yerlestirilir
    """
    from io import BytesIO
    import requests as _req
    import time as _time
    import numpy as np

    if save_path is None:
        save_path = f"thumbnail_{int(_time.time())}.jpg"
    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    # Thumbnail yazisi yoksa konudan olustur
    if not thumbnail_text:
        thumbnail_text = _make_short_title(topic).upper()

    # 1. Prompt hazirla
    if not thumbnail_prompt:
        base_prompt = (
            f"dramatic cinematic YouTube thumbnail background about {topic} "
            f"no text no letters extreme close up intense expression "
            f"dark vignette volumetric god rays deep gold crimson palette "
            f"8K photorealistic hyperdetailed award winning photography"
        )
    else:
        base_prompt = thumbnail_prompt[:400]
        base_prompt += " no text no letters YouTube thumbnail high contrast dramatic"

    # 2. Leonardo.ai ile gorsel indir
    api_key = os.getenv("LEONARDO_API_KEY")
    bg_image = None

    if api_key:
        print(f"  [THUMBNAIL] Leonardo.ai ile gorsel uretiliyor...")
        url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }
        payload = {
            "height": 720,
            "width": 1280,
            "modelId": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",
            "prompt": base_prompt,
            "num_images": 1
        }
        try:
            resp = _req.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                gen_id = resp.json().get("sdGenerationJob", {}).get("generationId")
                if gen_id:
                    get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}"
                    for attempt in range(12):
                        wait_time = 6 if attempt > 2 else 10
                        _time.sleep(wait_time)
                        res = _req.get(get_url, headers=headers, timeout=20)
                        if res.status_code == 200:
                            data = res.json().get("generations_by_pk", {})
                            if data.get("status") == "COMPLETE":
                                img_url = data.get("generated_images", [{}])[0].get("url")
                                if img_url:
                                    img_resp = _req.get(img_url, timeout=30)
                                    if img_resp.status_code == 200:
                                        bg_image = Image.open(BytesIO(img_resp.content)).convert("RGB").resize((1280, 720), Image.LANCZOS)
                                        print(f"  [THUMBNAIL] Leonardo gorseli alindi!")
                                        break
        except Exception as e:
            print(f"  [THUMBNAIL] Leonardo hatasi: {e}")

    # 3. Pollinations Fallback
    if bg_image is None:
        print(f"  [THUMBNAIL] Pollinations Fallback kullaniliyor...")
        safe_prompt = base_prompt.replace(",", " ").replace(":", " ").replace('"', "").replace("'", "")
        safe_prompt = " ".join(safe_prompt.split())[:500]
        for seed in [42, 7]:
            try:
                encoded = _req.utils.quote(safe_prompt, safe="")
                url = f"https://image.pollinations.ai/prompt/{encoded}"
                params = {"width": 1280, "height": 720, "seed": seed, "nologo": "true"}
                resp = _req.get(url, params=params, timeout=90)
                if resp.status_code == 200:
                    bg_image = Image.open(BytesIO(resp.content)).convert("RGB").resize((1280, 720), Image.LANCZOS)
                    break
            except:
                pass

    if bg_image is None:
        bg_image = Image.new("RGB", (1280, 720), (30, 30, 30))

    # 4. Akilli pozisyon: gorselin karanlik tarafina yaz
    left_half = bg_image.crop((0, 0, 640, 720)).convert("L")
    right_half = bg_image.crop((640, 0, 1280, 720)).convert("L")
    left_avg = np.mean(np.array(left_half))
    right_avg = np.mean(np.array(right_half))
    side = "left" if left_avg < right_avg else "right"
    print(f"  [THUMBNAIL] Yazi '{side}' tarafa yerlestirilecek")

    # 5. Yazi tarafina gradient overlay (okunabilirlik)
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    if side == "left":
        for xi in range(640):
            alpha = int(160 * (1 - xi / 640))
            draw_ov.line([(xi, 0), (xi, 720)], fill=(0, 0, 0, alpha))
    else:
        for xi in range(640, 1280):
            alpha = int(160 * ((xi - 640) / 640))
            draw_ov.line([(xi, 0), (xi, 720)], fill=(0, 0, 0, alpha))

    composited = Image.alpha_composite(bg_image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(composited)

    # 6. Font yukle (Impact / Segoe UI Black = Modern & Kalin)
    font_size = 150 # Daha buyuk, daha carpiyici
    font = None
    pref_fonts = [
        "C:/Windows/Fonts/impact.ttf",           # Klasik YouTube
        "C:/Windows/Fonts/seguibl.ttf",         # Segoe UI Black (Modern & Kalin)
        "C:/Windows/Fonts/arialbd.ttf",         # Arial Bold
    ]
    for p in pref_fonts:
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, font_size)
                break
            except: pass
    if not font:
        font = ImageFont.load_default()

    # 7. Yazıyı satırlara böl ve yerleştir
    text = thumbnail_text.upper().strip()
    max_width = int(1280 * 0.55) # Biraz daha genis alan
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test = " ".join(current_line + [word])
        try:
            bbox = draw.textbbox((0, 0), test, font=font)
            line_w = bbox[2] - bbox[0]
        except: line_w = len(test) * (font_size * 0.6)
            
        if line_w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    if not lines:
        lines = [text[:20]]

    # Satir araligini ayarla (buyuk fontlarda daha dar satir araligi daha şık durur)
    line_height = font_size * 1.05 
    total_height = len(lines) * line_height
    start_y = (720 - total_height) / 2
    margin = 60

    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
        except: line_w = len(line) * (font_size * 0.6)
            
        x = margin if side == "left" else (1280 - line_w - margin)
        y = start_y + (i * line_height)

        # ── 3 KATMANLI YAZI EFEKTI (PREMIUM GORUNUM) ──
        
        # 1. Uzak Drop Shadow (Derinlik saglar)
        shadow_offset = 12
        draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill=(0, 0, 0, 180))

        # 2. Kalin Dis Outline (Okunabilirlik saglar)
        outline_thickness = 10
        for off_x in range(-outline_thickness, outline_thickness + 1):
            for off_y in range(-outline_thickness, outline_thickness + 1):
                if off_x*off_x + off_y*off_y <= outline_thickness*outline_thickness:
                    draw.text((x + off_x, y + off_y), line, font=font, fill=(0, 0, 0))

        # 3. Ana Yazi: PARLAK SARI
        draw.text((x, y), line, font=font, fill=(255, 235, 0))

    composited.save(save_path, "JPEG", quality=95)
    print(f"  [THUMBNAIL] Premium stil kaydedildi: {save_path}")
    return save_path



def _make_short_title(topic: str) -> str:
    """Konuyu thumbnail için max 30 karakter kısaltır."""
    # Parantez ve emoji temizle
    clean = _re.sub(r'\(.*?\)', '', topic).strip()
    clean = _re.sub(r'[^\w\s\-\']', '', clean).strip()
    if len(clean) <= 30:
        return clean
    # Nokta veya virgülden kes
    for sep in ['.', ',', ':', ';', '!', '?']:
        if sep in clean:
            return clean.split(sep)[0].strip()[:30]
    # Kelime sınırından kes
    words = clean.split()
    result = ""
    for word in words:
        if len(result) + len(word) + 1 <= 28:
            result += (" " if result else "") + word
        else:
            break
    return result if result else clean[:28]


def _extract_keywords(topic: str) -> list:
    """Konudan görsel anahtar kelimeleri çıkarır."""
    stop = {'ve', 'ile', 'için', 'bir', 'bu', 'da', 'de', 'ki', 'mi', 'mu',
            'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'is', 'and', 'or'}
    words = _re.findall(r'\b\w{3,}\b', topic)
    return [w.upper() for w in words if w.lower() not in stop][:5]


def _call_kie_for_prompts(prompt_text: str) -> str:
    """Kie.ai Gemini API cagrisi - dogru URL formati ile."""
    import json
    api_key = os.getenv("KIE_AI_API_KEY")
    if not api_key:
        return ""
    # Dogru format: https://api.kie.ai/{model}/v1/chat/completions
    url = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "gemini-3.1-pro",
        "messages": [{"role": "user", "content": prompt_text}],
        "stream": False,
        "max_tokens": 4096,
        "temperature": 0.7
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            print(f"  [Kie.ai visual] HTTP {resp.status_code}: {resp.text[:200]}")
            return ""
        data = resp.json()
        if "code" in data and data["code"] != 200:
            print(f"  [Kie.ai visual] API kodu={data['code']}: {data.get('msg','')}")
            return ""
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [!] Kie.ai prompt cagrisi basarisiz: {e}")
    return ""


def _generate_image_prompts_with_ai(topic, keywords, count=5, script=None):
    """
    Kie.ai Gemini 3.1 Pro kullanarak konuya özel, script'e göre sıralı
    görsel prompt'lar üretir. Leonardo.ai için optimize edilmiştir.
    """
    import re
    kw_hint = f"\nKeywords: {keywords}" if keywords else ""
    script_hint = ""
    if script:
        # Script'in ilk 16000 karakterini analiz için gönder
        script_hint = f"\n\nVIDEO SCRIPT (for scene context):\n{script[:16000]}"


    prompt_text = f"""You are a professional cinematographer and art director for YouTube documentaries.

TASK: Generate exactly {count} image generation prompts in ENGLISH for the topic: "{topic}"{kw_hint}{script_hint}

RULES:
1. Each prompt must describe a UNIQUE, DISTINCT visual scene — no repetition.
2. Order the prompts to MATCH THE NARRATIVE FLOW of the script (beginning → middle → end scenes).
3. Every prompt must include: subject, setting, lighting style, camera angle, mood/atmosphere, color palette.
4. Use cinematic keywords: "golden hour", "dramatic side lighting", "shallow depth of field", "anamorphic lens flare", "8K RAW", "photorealistic", "hyperdetailed", "award-winning photography".
5. Prompts must directly support the VOICEOVER narration — each image should visually represent what is being described at that moment.
6. Style: cinematic documentary, photorealistic, hyper-detailed.
7. AVOID generic stock photo descriptions. Be SPECIFIC to the topic.

OUTPUT FORMAT: Only output the prompts, one per line, numbered 1-{count}. No extra text or explanation."""

    # Önce kie.ai dene
    result = _call_kie_for_prompts(prompt_text)

    if not result:
        # Fallback: Google Gemini
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-flash-latest',
                    contents=prompt_text
                )
                result = response.text.strip()
        except Exception as e:
            print(f"  [!] Gemini fallback başarısız: {e}")

    if not result:
        return None

    lines = [l.strip() for l in result.split('\n') if l.strip()]
    import re
    prompts = []
    for line in lines:
        cleaned = re.sub(r'^\d+[.)\-]\s*', '', line).strip()
        if cleaned and len(cleaned) > 20:
            prompts.append(cleaned)

    if prompts:
        # Fulfill exactly count if AI gave fewer
        kw_list = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else []
        while len(prompts) < count:
            subject = kw_list[len(prompts) % len(kw_list)] if kw_list else topic
            prompts.append(f"Cinematic documentary shot of {subject}, high detail, photorealistic, 8K.")
            
        print(f"  [AI] Kie.ai Gemini 3.1 Pro ile {len(prompts)} sinematik görsel prompt üretildi.")
        return prompts[:count]



    return None


def estimate_asset_count_from_script(script):
    """
    Kie.ai Gemini 3.1 Pro kullanarak script'i analiz eder ve kaç farklı
    görsel sahne gerektiğini tahmin eder (her 5-10 saniyede bir görsel değişim).
    """
    import re
    prompt_text = f"""Analyze this video script and count how many DISTINCT visual scenes/topics are described.
A new visual asset is needed for each unique segment or major idea (visual change every 5-10 seconds).

SCRIPT:
{script[:16000]}

OUTPUT: Only output a single INTEGER (Min: 6, Max: 25). No text, no explanation."""


    # Önce kie.ai dene
    result = _call_kie_for_prompts(prompt_text)
    if result:
        match = re.search(r'\d+', result)
        if match:
            count = int(match.group())
            count = max(6, min(20, count))
            print(f"  [AI] Kie.ai sahne analizi: {count} görsel sahne tespit edildi.")
            return count

    # Fallback: Google Gemini
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt_text
            )
            match = re.search(r'\d+', response.text)
            if match:
                return max(6, min(20, int(match.group())))
    except Exception as e:
        print(f"  [!] Asset sayısı tahmini başarısız: {e}")

    return 8


def generate_scene_ordered_prompts(topic: str, script: str, count: int = 10, keywords: str = "") -> list:
    """
    Script metnini analiz ederek narratife uygun, kronolojik sıralı
    görsel prompt'lar üretir. Her prompt, seslendirmenin o anındaki
    sahneyi görsel olarak destekler.
    Döner: [{"scene": 1, "timestamp_hint": "giriş", "prompt": "..."}] formatında liste
    """
    import re, json as _json
    kw_hint = f"\nKeywords/Themes: {keywords}" if keywords else ""

    prompt_text = f"""You are a world-class video director creating a YouTube documentary.

TOPIC: "{topic}"{kw_hint}

VIDEO SCRIPT:
{script[:16000]}

TASK: Create exactly {count} image generation prompts that visually match the NARRATIVE FLOW of this script.


REQUIREMENTS:
- Prompts must follow the CHRONOLOGICAL ORDER of the script (first prompt = opening scene, last = closing scene)
- Each prompt must visually represent what the VOICEOVER is describing at that moment
- Use cinematic language: "dramatic chiaroscuro lighting", "8K photorealistic", "shallow depth of field", "anamorphic bokeh", "golden hour", "hyperdetailed"
- Include SPECIFIC subjects from the script (real names, places, objects mentioned)
- Each scene must be VISUALLY DISTINCT from others
- Style: cinematic documentary photography

OUTPUT: Return ONLY a JSON array. No markdown, no explanation.
Format:
[
  {{"scene": 1, "timestamp_hint": "opening", "prompt": "cinematic prompt here..."}},
  {{"scene": 2, "timestamp_hint": "background", "prompt": "cinematic prompt here..."}}
]"""

    result = _call_kie_for_prompts(prompt_text)

    if result:
        # JSON parse et
        try:
            # Markdown code block varsa temizle
            clean = re.sub(r'```json|```', '', result).strip()
            scenes = _json.loads(clean)
            if isinstance(scenes, list) and scenes:
                prompts = [s.get("prompt", "") for s in scenes if s.get("prompt")]
                print(f"  [AI] Kie.ai ile {len(prompts)} narratif-uyumlu sahne prompt'u üretildi.")
                return prompts[:count]
        except Exception:
            # JSON parse edilemezse satır satır al
            lines = [l.strip() for l in result.split('\n') if l.strip()]
            prompts = []
            for line in lines:
                cleaned = re.sub(r'^\d+[.)\-]\s*', '', line).strip()
                if cleaned and len(cleaned) > 30 and not cleaned.startswith('{'):
                    prompts.append(cleaned)
            if prompts:
                # Fulfill exactly count
                while len(prompts) < count:
                    prompts.append(prompts[len(prompts) % len(prompts)])
                return prompts[:count]


    # Fallback: temel prompt listesi
    return _generate_image_prompts_with_ai(topic, keywords, count, script) or []


def generate_ai_images(topic, count=5, save_dir="assets/images", provider="pollinations", keywords=None, use_motion=False, script=None):
    """
    Konuya özel, script narratifine uygun sıralı AI görselleri üretir.
    script parametresi verilirse kie.ai Gemini 3.1 Pro sahne analizi yapar.
    """
    os.makedirs(save_dir, exist_ok=True)
    images = []

    # Keyword listesi oluştur
    keyword_list = []
    if keywords:
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]

    if provider == "leonardo":
        api_key = os.getenv("LEONARDO_API_KEY")
        if not api_key:
            print("  [!] Leonardo.ai API Key bulunamadı! Pollinations'a (ücretsiz) geçiliyor...")
            provider = "pollinations"
        else:
            if use_motion:
                result = _generate_leonardo_videos_direct(topic, count, save_dir, keyword_list)
            else:
                result = _generate_leonardo_images(topic, count, save_dir, keyword_list, use_motion=False)

            if result:
                return result
            else:
                print("  [!] Leonardo.ai başarısız. Pollinations ile deneniyor...")
                provider = "pollinations"
    
    import concurrent.futures

    def _download_pollination(i, current_subject, prompt, save_dir):
        filename = os.path.join(save_dir, f"ai_gen_{int(time.time())}_{i}_{random.randint(100,999)}.jpg")
        encoded_prompt = requests.utils.quote(prompt)
        # Using image.pollinations.ai subdomain which is more dedicated for image generation
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&seed={random.randint(1, 999999)}&nologo=true"
        try:
            response = requests.get(url, timeout=45)
            if response.status_code == 200:
                # CRITICAL: Check if we actually got an image
                content_type = response.headers.get("Content-Type", "").lower()
                if "image" not in content_type:
                    print(f"  [!] Pollinations Hatası: Gelen içerik bir resim değil ({content_type}).")
                    return None
                    
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"  [OK] AI Görseli ({i+1}): {current_subject}")
                return filename
            else:
                print(f"  [!] Pollinations API Hatası ({response.status_code})")
        except Exception as e:
            print(f"  [!] Pollinations Hatası: {e}")
        return None

    if provider == "pollinations":
        print(f"  [START] Kie.ai Gemini 3.1 Pro ile {count} narratif-uyumlu görsel prompt üretiliyor...")

        # Önce kie.ai ile script'e uygun sıralı prompt'ları üret
        ai_prompts = []
        if script:
            ai_prompts = generate_scene_ordered_prompts(topic, script, count, keywords or "")
        
        if not ai_prompts:
            # Fallback: basit keyword bazlı prompt üretimi
            ai_prompts = _generate_image_prompts_with_ai(topic, keywords, count, script)

        print(f"  [START] {count} AI görseli paralel olarak üretiliyor...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(count):
                if ai_prompts and i < len(ai_prompts):
                    prompt = ai_prompts[i]
                    current_subject = f"Sahne {i+1}"
                else:
                    current_subject = keyword_list[i % len(keyword_list)] if keyword_list else topic
                    prompt = (
                        f"cinematic documentary photo of {current_subject}, "
                        f"8K photorealistic, dramatic chiaroscuro lighting, shallow depth of field, "
                        f"anamorphic lens, hyperdetailed, award-winning photography, "
                        f"professional color grading, masterpiece quality"
                    )
                futures.append(executor.submit(_download_pollination, i, current_subject, prompt, save_dir))

            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    images.append(res)
        return images

    # Diğer provider'lar için fallback
    for i in range(count):
        current_subject = keyword_list[i % len(keyword_list)] if keyword_list else topic
        prompt = (
            f"cinematic documentary photo of {current_subject}, "
            f"8K photorealistic, dramatic lighting, hyperdetailed, masterpiece"
        )

    return images

def _generate_leonardo_images(topic, count, save_dir, keyword_list, use_motion=False, motion_strength=5):
    """
    Internal helper for Leonardo.ai (Asynchronous API).
    Handles batches naturally as Leonardo limits num_images to 4 for high res.
    If use_motion is True, it will also generate a short video from each image.
    """
    api_key = os.getenv("LEONARDO_API_KEY")
    if not api_key:
        print("  [!] Leonardo.ai API Key bulunamadi.")
        return []

    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }

    all_downloaded = []
    
    # Phoenix 1.0 only allows 1 image per request
    MAX_BATCH_SIZE = 1
    remaining_count = count
    
    print(f"  [*] Leonardo.ai Toplam {count} gorsel icin sureci baslatiliyor (Birer birer)...")

    # Try AI-generated prompts first (much more relevant to the topic)
    print(f"  [AI] Script'e uygun narratif prompt'lar üretiliyor...")
    ai_prompts = _generate_image_prompts_with_ai(topic, ', '.join(keyword_list) if keyword_list else None, count)
    
    while remaining_count > 0:
        batch_size = min(remaining_count, MAX_BATCH_SIZE)
        
        # Determine subject for this image
        offset = count - remaining_count
        current_subject = keyword_list[offset % len(keyword_list)] if keyword_list else topic
        
        if ai_prompts and offset < len(ai_prompts):
            prompt = ai_prompts[offset]
        else:
            # Fallback: simple but effective prompt
            prompt = (
                f"A dramatic cinematic scene depicting {current_subject} related to {topic}. "
                f"Photorealistic, 8K resolution, dramatic lighting, professional color grading, "
                f"highly detailed, epic atmosphere, masterpiece quality"
            )
        
        payload = {
            "height": 720,
            "width": 1280,
            "modelId": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",
            "prompt": prompt,
            "num_images": batch_size
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"  [!] Leonardo API Hatasi ({response.status_code}): {response.text}")
                break

            generation_id = response.json().get("sdGenerationJob", {}).get("generationId")
            if not generation_id:
                print("  [!] Generation ID alinamadi.")
                break

            print(f"  -> Grup Isleniyor (ID: {generation_id}). Bekleniyor...")
            
            # Polling for status
            get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
            
            is_done = False
            for attempt in range(20): # Adaptive polling
                wait_time = 5 if attempt > 2 else 10 # Start with 10s, then 5s
                time.sleep(wait_time)
                res = requests.get(get_url, headers=headers, timeout=20)
                if res.status_code == 200:
                    data = res.json().get("generations_by_pk", {})
                    status = data.get("status")
                    if status == "COMPLETE":
                        generated_images = data.get("generated_images", [])
                        for idx, img in enumerate(generated_images):
                            img_url = img.get("url")
                            filename = os.path.join(save_dir, f"leonardo_ai_{int(time.time())}_{offset+idx}.jpg")
                            r = requests.get(img_url, timeout=30)
                            if r.status_code == 200:
                                with open(filename, "wb") as f:
                                    f.write(r.content)
                                
                                # --- AI Verification (Opsiyonel) ---
                                if os.getenv("ENABLE_AI_VERIFY", "false").lower() == "true":
                                    if not _verify_asset_relevance(filename, prompt):
                                        print(f"  [!] Uyumluluk: Atlandı (yetersiz eşleşme).")
                                        # skipping addition to all_downloaded for speed
                                        continue

                                if use_motion:
                                    print(f"  [*] Gorsel videoya donusturuluyor (Motion)...")
                                    video_filename = filename.replace(".jpg", ".mp4")
                                    motion_res = _generate_leonardo_motion(img.get("id"), video_filename, motion_strength)
                                    if motion_res:
                                        all_downloaded.append(motion_res)
                                    else:
                                        all_downloaded.append(filename)
                                else:
                                    all_downloaded.append(filename)
                                
                                remaining_count -= 1
                                print(f"  [OK] Leonardo Varlıgı Eklendi ({len(all_downloaded)}/{count})")
                        is_done = True
                        break
                    elif status == "FAILED":
                        print("  [!] Bu grup uretimi basarisiz oldu.")
                        remaining_count -= batch_size # Skip to avoid infinite loop
                        break

                else:
                    print(f"  [!] Status check hatasi ({res.status_code})")
            
            if not is_done:
                print("  [!] Zaman asimi: Gorseller henuz tamamlanmadi, bir sonraki gruba geciliyor.")

        except Exception as e:
            print(f"  [!] Leonardo API Istek Hatasi: {e}")
            break
            
        if not is_done:
            # If we didn't succeed with this batch, we must decrement remaining_count
            # so we don't loop forever, but only if we truly want to skip it.
            # Actually, to be safe and fulfill user count, better not decrement on failure
            # unless we hit a retry limit. For now, let's just make it correctly count successes.
            pass


    return all_downloaded


def _generate_leonardo_videos_direct(topic, count, save_dir, keyword_list):
    """
    Direct Text-to-Video generation using Leonardo.ai API.
    Avoids generating an image first, saving cost and time.
    """
    api_key = os.getenv("LEONARDO_API_KEY")
    if not api_key: return []

    url = "https://cloud.leonardo.ai/api/rest/v1/generations-text-to-video"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }

    all_downloaded = []
    
    print(f"  [*] Leonardo.ai Doğrudan {count} video (Text-to-Video) süreci başlatılıyor...")

    print(f"  [AI] Script'e uygun narratif video prompt'lar üretiliyor...")
    ai_prompts_direct = _generate_image_prompts_with_ai(topic, ', '.join(keyword_list) if keyword_list else None, count)

    for i in range(count):
        offset = i
        current_subject = keyword_list[offset % len(keyword_list)] if keyword_list else topic
        
        if ai_prompts_direct and i < len(ai_prompts_direct):
            prompt = ai_prompts_direct[i]
        else:
            prompt = (
                f"A cinematic high-quality motion scene of {current_subject}. "
                f"Epic lighting, realistic motion, highly detailed, 8K resolution, professional grade animation."
            )
        
        payload = {
            "height": 720,
            "width": 1280,
            "prompt": prompt,
            "modelId": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3" # phoenix 1.0 or standard video model
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"  [!] Leonardo Video API Hatasi ({response.status_code}): {response.text}")
                # Fallback to Image+Motion if direct fails
                continue

            generation_id = response.json().get("textToVideoGenerationJob", {}).get("generationId")
            if not generation_id:
                print("  [!] Video Generation ID alinamadi.")
                continue

            print(f"  -> Video İşleniyor (ID: {generation_id}). Bekleniyor...")
            
            # Polling (reuse logic)
            get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
            
            for attempt in range(30): # Videos take longer
                wait_time = 7 if attempt > 3 else 12
                time.sleep(wait_time)
                res = requests.get(get_url, headers=headers, timeout=20)
                if res.status_code == 200:
                    data = res.json().get("generations_by_pk", {})
                    if data.get("status") == "COMPLETE":
                        # For T2V, the result is in motionMP4URL or similar
                        generated_assets = data.get("generated_images", [])
                        if generated_assets:
                            asset = generated_assets[0]
                            # Try to find video URL
                            video_url = asset.get("motionMP4URL") or asset.get("url")
                            if video_url:
                                filename = os.path.join(save_dir, f"leonardo_video_{int(time.time())}_{i}.mp4")
                                r = requests.get(video_url, timeout=60)
                                if r.status_code == 200:
                                    with open(filename, "wb") as f:
                                        f.write(r.content)
                                    
                                    # --- AI Verification (Opsiyonel) ---
                                    should_verify = os.getenv("ENABLE_AI_VERIFY", "false").lower() == "true"
                                    if not should_verify or _verify_asset_relevance(filename, prompt):
                                        all_downloaded.append(filename)
                                        print(f"  [OK] Leonardo Video Eklendi ({len(all_downloaded)}/{count})")
                                    else:
                                        print(f"  [!] Video uyumsuz bulundu, atlanıyor...")
                                        os.remove(filename)
                        break
                    elif data.get("status") == "FAILED":
                        print("  [!] Video üretimi başarısız oldu.")
                        break
                else:
                    print(f"  [!] Status check hatasi ({res.status_code})")

        except Exception as e:
            print(f"  [!] Leonardo Video API Istek Hatasi: {e}")
            break
            
    return all_downloaded


def _verify_asset_relevance(file_path, prompt):
    """
    Uses Gemini Vision to check if the generated image/video is relevant to the prompt.
    Returns True if relevant, False otherwise.
    """
    try:
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: return True # Default to True if no key
        
        client = genai.Client(api_key=api_key)
        
        target_path = file_path
        is_video = file_path.endswith((".mp4", ".mov", ".avi"))
        
        # For videos, we extract a single frame to verify relevance
        if is_video:
            try:
                from moviepy import VideoFileClip
                clip = VideoFileClip(file_path)
                frame_path = file_path + "_verify.jpg"
                # Get frame at 1.5s or halfway
                t = min(1.5, clip.duration / 2)
                clip.save_frame(frame_path, t=t)
                clip.close()
                target_path = frame_path
            except Exception as ve:
                print(f"  [!] Video kare alma hatası: {ve}")
                return True

        print(f"  [*] AI Denetçi: İçerik uyumluluğu kontrol ediliyor...")
        with open(target_path, "rb") as f:
            image_bytes = f.read()
            
        verify_prompt = f"""Analyze this image and decide if it is a GOOD visual match for this description: "{prompt}"
        
        Rules:
        1. Answer ONLY with 'YES' or 'NO'. 
        2. 'YES' if the image accurately depicts the SUBJECT and MOOD of the prompt.
        3. 'NO' if it's completely irrelevant, visually broken, or doesn't match the topic at all.
        """
        
        response = client.models.generate_content(
            model='gemini-flash-latest', # Fast & Cost-effective
            contents=[
                verify_prompt,
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ]
        )
        
        result = response.text.strip().upper()
        # Cleanup temp frame
        if is_video and os.path.exists(target_path):
            os.remove(target_path)
            
        if "NO" in result:
            return False
        return True
    except Exception as e:
        print(f"  [!] Denetçi Hatası: {e}")
        return True # Fallback to True to avoid stopping everything



def _generate_leonardo_motion(image_id, save_path, motion_strength=None):
    """
    Converts a Leonardo image into a video using the Motion API.
    """
    if motion_strength is None:
        motion_strength = int(os.getenv("LEONARDO_MOTION_STRENGTH", "5"))

    api_key = os.getenv("LEONARDO_API_KEY")
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    # 1. Start motion generation
    url = "https://cloud.leonardo.ai/api/rest/v1/generations-motion-svd"
    payload = {
        "imageId": image_id,
        "isPublic": False,
        "motionStrength": motion_strength
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"  [!] Motion API Hatasi ({response.status_code}): {response.text}")
            return None
        
        motion_id = response.json().get("motionSvdGenerationJob", {}).get("generationId")
        if not motion_id: return None
        
        # 2. Poll for video
        print(f"  [*] Motion (SVD) video üretiliyor (ID: {motion_id})...")
        # CORRECT ENDPOINT: Just /generations/{id}
        get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{motion_id}"
        for attempt in range(30): # 30 * 12s = 6 mins
            time.sleep(12)
            res = requests.get(get_url, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json().get("generations_by_pk", {})
                status = data.get("status")
                if status == "COMPLETE":
                    image_data = data.get("generated_images", [])
                    if image_data:
                        video_url = image_data[0].get("motionMP4URL")
                        if video_url:
                            print(f"  [√] Motion video hazır, indiriliyor...")
                            r = requests.get(video_url, timeout=45)
                            if r.status_code == 200:
                                with open(save_path, "wb") as f:
                                    f.write(r.content)
                                return save_path
                elif status == "FAILED":
                    print(f"  [!] Motion SVD üretimi başarısız oldu (API FAILED).")
                    break
            else:
                print(f"  [!] Motion status check hatasi: {res.status_code}")
    except Exception as e:
        print(f"  [!] Motion Hatasi: {e}")
        
    return None


def add_text_to_image(image_path, text):
    """
    Adds the full video title to the thumbnail with smart positioning (side-aligned)
    and enhanced visual effects (glow, shadow, multi-line).
    """
    if not text:
        return
    
    try:
        # Clean and prepare text
        text = text.strip().strip('"').strip("'").upper()
        
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # 1. SMART POSITIONING logic
        # Analyze left vs right half of the image to find the "darker" or "empty" side
        left_half = img.crop((0, 0, width // 2, height)).convert("L")
        right_half = img.crop((width // 2, 0, width, height)).convert("L")
        
        import numpy as np
        left_avg = np.mean(np.array(left_half))
        right_avg = np.mean(np.array(right_half))
        
        # We prefer the darker side for text, or simply choose based on contrast
        # If right is brighter, put text on the left, and vice versa.
        side = "left" if left_avg < right_avg else "right"
        
        # 2. FONT & LINE BREAKING
        font_paths = [
            "C:\\Windows\\Fonts\\impact.ttf",   # Best for thumbnails
            "C:\\Windows\\Fonts\\arialbd.ttf", 
            "C:\\Windows\\Fonts\\segoeuib.ttf",
        ]
        
        font_size = int(width / 15)
        font = None
        for path in font_paths:
            if os.path.exists(path):
                font = ImageFont.truetype(path, font_size)
                break
        if not font: font = ImageFont.load_default()

        # Wrap text to fit roughly 40% of the image width
        max_px_width = width * 0.45
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_px_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # 3. DRAWING
        total_text_height = len(lines) * (font_size * 1.2)
        start_y = (height - total_text_height) / 2 # Center vertically
        
        margin = 60
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            
            if side == "left":
                x = margin
            else:
                x = width - line_w - margin
            
            y = start_y + (i * font_size * 1.1)
            
            # Enhanced Glow/Outline effect
            glow_layers = 12
            for offset in range(1, glow_layers):
                alpha = int(180 * (1 - offset/glow_layers))
                draw.text((x-offset, y), line, font=font, fill=(0,0,0, alpha))
                draw.text((x+offset, y), line, font=font, fill=(0,0,0, alpha))
                draw.text((x, y-offset), line, font=font, fill=(0,0,0, alpha))
                draw.text((x, y+offset), line, font=font, fill=(0,0,0, alpha))
                # Diagonals
                draw.text((x-offset, y-offset), line, font=font, fill=(0,0,0, alpha))
                draw.text((x+offset, y+offset), line, font=font, fill=(0,0,0, alpha))

            # Main text
            # Use gradient-like color or just punchy White/Yellow
            draw.text((x,y), line, font=font, fill=(255, 255, 255)) # White
            
        img.save(image_path, quality=95)
        print(f"  [OK] Thumbnail metni ({side} yan) eklendi.")
        
    except Exception as e:
        print(f"  [!] Smart Thumbnail Hatası: {e}")


def generate_single_leonardo_image(prompt: str, save_path: str, title: str = None) -> bool:
    """
    Generates a single high-quality image using Leonardo.ai from a specific prompt.
    Useful for thumbnails or specific scenes.
    """
    api_key = os.getenv("LEONARDO_API_KEY")
    if not api_key:
        print("  [!] Leonardo.ai API Key bulunamadı.")
        return False

    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }

    payload = {
        "height": 720,
        "width": 1280,
        "modelId": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3", # Phoenix 1.0
        "prompt": prompt,
        "num_images": 1
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"  [!] Leonardo API Hatası: {response.status_code}")
            return False

        generation_id = response.json().get("sdGenerationJob", {}).get("generationId")
        if not generation_id: return False

        print(f"  [*] Leonardo Thumbnail üretiliyor... (ID: {generation_id})")
        
        get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        
        # Poll for completion
        for attempt in range(15):
            wait_time = 6 if attempt > 2 else 10
            time.sleep(wait_time)
            res = requests.get(get_url, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json().get("generations_by_pk", {})
                if data.get("status") == "COMPLETE":
                    img_url = data.get("generated_images", [])[0].get("url")
                    r = requests.get(img_url, timeout=30)
                    if r.status_code == 200:
                        with open(save_path, "wb") as f:
                            f.write(r.content)
                        print(f"  [OK] Thumbnail kaydedildi: {save_path}")
                        
                        # Add text if title is provided
                        if title:
                            # Thumbnail production is slow, let's use the provided add_text_to_image
                            add_text_to_image(save_path, title)
                            
                        return True
            else:
                break
    except Exception as e:
        print(f"  [!] Leonardo Hatası: {e}")
    
    return False
