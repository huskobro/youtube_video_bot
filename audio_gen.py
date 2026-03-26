import os
import requests
import base64
import asyncio
import edge_tts
import re
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────── Text Cleaning ────────────────────────
def clean_script_for_tts(text: str) -> str:
    """
    Cleans the script text from AI artifacts, markdown, and special characters
    that should not be read aloud.
    """
    # 1. Remove Markdown markers (bold, italic, headers)
    text = re.sub(r'\*\*|__', '', text)
    text = re.sub(r'^#+.*$', '', text, flags=re.MULTILINE)
    
    # 2. Remove anything inside square brackets [...] (AI scene markers)
    text = re.sub(r'\[.*?\]', '', text)
    
    # 3. Remove anything inside parentheses (...) (AI stage directions)
    text = re.sub(r'\(.*?\)', '', text) # More aggressive cleaning of parentheses
    
    # 4. Remove list markers like "-", "*", "1.", etc. at the start of lines
    text = re.sub(r'^[ \t]*[-*•][ \t]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*\d+\.[ \t]+', '', text, flags=re.MULTILINE)
    
    # 5. Remove leftover section markers
    markers = ["Bölüm 1:", "Bölüm 2:", "Bölüm 3:", "Giriş:", "Gelişme:", "Sonuç:", "Hook:", "Intro:", "Outro:", "Metin:"]
    for marker in markers:
        text = re.sub(re.escape(marker), "", text, flags=re.IGNORECASE)
        
    # 6. Clean up special characters that shouldn't be read
    text = text.replace('"', '').replace("'", "")
    
    # 7. Final cleanup of whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

# ──────────────────────── Edge TTS Voice Listing ────────────────────────
# Dil kodları -> Okunabilir isimler (bayrak emojileriyle)
EDGE_LANGUAGE_NAMES = {
    "af-ZA": "Afrikaans",
    "am-ET": "Amharca",
    "ar-AE": "Arapca (BAE)",
    "ar-BH": "Arapca (Bahreyn)",
    "ar-DZ": "Arapca (Cezayir)",
    "ar-EG": "Arapca (Misir)",
    "ar-IQ": "Arapca (Irak)",
    "ar-JO": "Arapca (Urdun)",
    "ar-KW": "Arapca (Kuveyt)",
    "ar-LB": "Arapca (Lubnan)",
    "ar-LY": "Arapca (Libya)",
    "ar-MA": "Arapca (Fas)",
    "ar-OM": "Arapca (Umman)",
    "ar-QA": "Arapca (Katar)",
    "ar-SA": "Arapca (Suudi)",
    "ar-SY": "Arapca (Suriye)",
    "ar-TN": "Arapca (Tunus)",
    "ar-YE": "Arapca (Yemen)",
    "az-AZ": "Azerbaycanca",
    "bg-BG": "Bulgarca",
    "bn-BD": "Bengalce (Banglades)",
    "bn-IN": "Bengalce (Hindistan)",
    "bs-BA": "Bosnakca",
    "ca-ES": "Katalanca",
    "cs-CZ": "Cekce",
    "cy-GB": "Galce",
    "da-DK": "Danimarkaca",
    "de-AT": "Almanca (Avusturya)",
    "de-CH": "Almanca (Isvicre)",
    "de-DE": "Almanca (Almanya)",
    "el-GR": "Yunanca",
    "en-AU": "Ingilizce (Avustralya)",
    "en-CA": "Ingilizce (Kanada)",
    "en-GB": "Ingilizce (Ingiltere)",
    "en-HK": "Ingilizce (Hong Kong)",
    "en-IE": "Ingilizce (Irlanda)",
    "en-IN": "Ingilizce (Hindistan)",
    "en-KE": "Ingilizce (Kenya)",
    "en-NG": "Ingilizce (Nijerya)",
    "en-NZ": "Ingilizce (Yeni Zelanda)",
    "en-PH": "Ingilizce (Filipinler)",
    "en-SG": "Ingilizce (Singapur)",
    "en-TZ": "Ingilizce (Tanzanya)",
    "en-US": "Ingilizce (ABD)",
    "en-ZA": "Ingilizce (G. Afrika)",
    "es-AR": "Ispanyolca (Arjantin)",
    "es-BO": "Ispanyolca (Bolivya)",
    "es-CL": "Ispanyolca (Sili)",
    "es-CO": "Ispanyolca (Kolombiya)",
    "es-CR": "Ispanyolca (Kosta Rika)",
    "es-CU": "Ispanyolca (Kuba)",
    "es-DO": "Ispanyolca (Dominik)",
    "es-EC": "Ispanyolca (Ekvador)",
    "es-ES": "Ispanyolca (Ispanya)",
    "es-GQ": "Ispanyolca (Ek. Gine)",
    "es-GT": "Ispanyolca (Guatemala)",
    "es-HN": "Ispanyolca (Honduras)",
    "es-MX": "Ispanyolca (Meksika)",
    "es-NI": "Ispanyolca (Nikaragua)",
    "es-PA": "Ispanyolca (Panama)",
    "es-PE": "Ispanyolca (Peru)",
    "es-PR": "Ispanyolca (Porto Riko)",
    "es-PY": "Ispanyolca (Paraguay)",
    "es-SV": "Ispanyolca (El Salvador)",
    "es-US": "Ispanyolca (ABD)",
    "es-UY": "Ispanyolca (Uruguay)",
    "es-VE": "Ispanyolca (Venezuela)",
    "et-EE": "Estonca",
    "fa-IR": "Farsca",
    "fi-FI": "Fince",
    "fil-PH": "Filipince",
    "fr-BE": "Fransizca (Belcika)",
    "fr-CA": "Fransizca (Kanada)",
    "fr-CH": "Fransizca (Isvicre)",
    "fr-FR": "Fransizca (Fransa)",
    "ga-IE": "Irlandaca",
    "gl-ES": "Galizyaca",
    "gu-IN": "Guceratca",
    "he-IL": "Ibranice",
    "hi-IN": "Hintce",
    "hr-HR": "Hirvatca",
    "hu-HU": "Macarca",
    "id-ID": "Endonezce",
    "is-IS": "Izlandaca",
    "it-IT": "Italyanca",
    "ja-JP": "Japonca",
    "jv-ID": "Cavaca",
    "ka-GE": "Gurcuce",
    "kk-KZ": "Kazakca",
    "km-KH": "Kmerce",
    "kn-IN": "Kannadaca",
    "ko-KR": "Korece",
    "lo-LA": "Laoca",
    "lt-LT": "Litvanyaca",
    "lv-LV": "Letonca",
    "mk-MK": "Makedonca",
    "ml-IN": "Malayalamca",
    "mn-MN": "Mogolca",
    "mr-IN": "Marathi",
    "ms-MY": "Malayca",
    "mt-MT": "Maltaca",
    "my-MM": "Birmanca",
    "nb-NO": "Norvecce",
    "ne-NP": "Nepalce",
    "nl-BE": "Flamanca",
    "nl-NL": "Felemenkce",
    "pl-PL": "Lehce (Polonyaca)",
    "ps-AF": "Pastuca",
    "pt-BR": "Portekizce (Brezilya)",
    "pt-PT": "Portekizce (Portekiz)",
    "ro-RO": "Rumence",
    "ru-RU": "Rusca",
    "si-LK": "Sinhalaca",
    "sk-SK": "Slovakca",
    "sl-SI": "Slovence",
    "so-SO": "Somalice",
    "sq-AL": "Arnavutca",
    "sr-RS": "Sirpca",
    "su-ID": "Sundaca",
    "sv-SE": "Isvecce",
    "sw-KE": "Svahilice (Kenya)",
    "sw-TZ": "Svahilice (Tanzanya)",
    "ta-IN": "Tamilce (Hindistan)",
    "ta-LK": "Tamilce (Sri Lanka)",
    "ta-MY": "Tamilce (Malezya)",
    "ta-SG": "Tamilce (Singapur)",
    "te-IN": "Teluguca",
    "th-TH": "Tayca",
    "tr-TR": "Turkce",
    "uk-UA": "Ukraynaca",
    "ur-IN": "Urduca (Hindistan)",
    "ur-PK": "Urduca (Pakistan)",
    "uz-UZ": "Ozbekce",
    "vi-VN": "Vietnamca",
    "zh-CN": "Cince (Cin)",
    "zh-HK": "Cince (Hong Kong)",
    "zh-TW": "Cince (Tayvan)",
    "zu-ZA": "Zuluca",
}


def get_edge_tts_voices() -> dict:
    """
    Edge TTS'den tum mevcut sesleri alir.
    Returns: {locale: [{"short": "tr-TR-AhmetNeural", "name": "Ahmet", "gender": "Male"}, ...]}
    """
    try:
        voices = asyncio.run(edge_tts.list_voices())
    except RuntimeError:
        # Eger event loop zaten calisiyor ise
        loop = asyncio.new_event_loop()
        voices = loop.run_until_complete(edge_tts.list_voices())
        loop.close()

    result = {}
    for v in voices:
        locale = v["Locale"]
        if locale not in result:
            result[locale] = []
        # Ses adini temizle (tr-TR-AhmetNeural -> Ahmet)
        raw_name = v["ShortName"].split("-")[-1]
        clean_name = raw_name.replace("Neural", "").replace("Multilingual", "").replace("Expressive", "")
        gender_label = "Erkek" if v["Gender"] == "Male" else "Kadin"
        result[locale].append({
            "short": v["ShortName"],
            "name": clean_name,
            "gender": v["Gender"],
            "label": f"{clean_name} ({gender_label})"
        })

    # Her locale icinde isimlere gore sirala
    for locale in result:
        result[locale].sort(key=lambda x: x["name"])

    return result


def get_edge_tts_languages() -> list:
    """
    Edge TTS'deki dillerin listesini okunabilir isimlerle dondurur.
    Returns: [(locale_code, display_name), ...] sorted by display_name
    """
    voices = get_edge_tts_voices()
    languages = []
    for locale in sorted(voices.keys()):
        display = EDGE_LANGUAGE_NAMES.get(locale, locale)
        languages.append((locale, display))
    # Turkce ve Ingilizce (ABD) basa gelsin
    priority = {"tr-TR": 0, "en-US": 1, "en-GB": 2, "de-DE": 3, "fr-FR": 4, "es-ES": 5, "ar-SA": 6, "ru-RU": 7}
    languages.sort(key=lambda x: (priority.get(x[0], 100), x[1]))
    return languages


# ──────────────────────── Edge TTS (ÜCRETSİZ / FREE) ────────────────────────
def generate_voiceover_edge(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
    voice_id: str = "tr-TR-AhmetNeural",
    language: str = "tr"
) -> str:
    """
    Generates voiceover using Microsoft Edge's free Neural TTS service.
    Also captures sentence timing for subtitle synchronization.
    """
    import json
    
    # Auto-adjust voice for English if target is English but voice is Turkish
    if language == "en":
        if "tr-TR" in voice_id:
            voice_id = "en-US-GuyNeural" if "Ahmet" in voice_id else "en-US-JennyNeural"
    
    # Clean script before synthesis
    cleaned_script = clean_script_for_tts(script)
    
    async def amain():
        # Wrap the text in emotional SSML for better human-like quality
        ssml_text = _build_emotional_ssml(cleaned_script, voice_id, language)
        
        communicate = edge_tts.Communicate(
            text=cleaned_script, # The library often handles plain text better for timing, but we can use SSML
            voice=voice_id,
            rate="-8%",   # Slightly slower for more emotional weight
            pitch="+0Hz"
        )
        
        # If we wanted to use SSML directly with edge-tts, we'd use Communicate(ssml=ssml_text)
        # However, for the best balance of timing data and quality, we'll use slightly slower rate
        # and rely on the Neural voices' natural prosody.
        
        # Ensure output directory exists
        temp_dir = os.path.dirname(output_filename)
        if temp_dir:
            os.makedirs(temp_dir, exist_ok=True)
        
        # Stream to capture audio, sentence timing, and word timing
        audio_data = bytearray()
        sentence_timings = []
        word_timings = []
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                offset_sec = chunk["offset"] / 10_000_000.0
                duration_sec = chunk["duration"] / 10_000_000.0
                sentence_timings.append({
                    "text": chunk["text"],
                    "start": offset_sec,
                    "end": offset_sec + duration_sec,
                    "type": "sentence"
                })
            elif chunk["type"] == "WordBoundary":
                offset_sec = chunk["offset"] / 10_000_000.0
                duration_sec = chunk["duration"] / 10_000_000.0
                word_timings.append({
                    "text": chunk["text"],
                    "start": offset_sec,
                    "end": offset_sec + duration_sec,
                    "type": "word"
                })
        
        # Save audio file
        if not audio_data:
            raise ValueError("Edge TTS ses verisi üretemedi (audio_data boş).")

        with open(output_filename, "wb") as f:
            f.write(audio_data)
        
        # Verify file presence and size (min 1KB)
        if not os.path.exists(output_filename) or os.path.getsize(output_filename) < 1000:
             if os.path.exists(output_filename): os.remove(output_filename)
             raise ValueError("Üretilen ses dosyası bozuk veya çok küçük.")

        # Save timing data as JSON alongside the audio
        timing_path = output_filename.replace(".mp3", "_timing.json")
        combined_timing = {
            "sentences": sentence_timings,
            "words": word_timings
        }
        if sentence_timings or word_timings:
            with open(timing_path, "w", encoding="utf-8") as f:
                json.dump(combined_timing, f, ensure_ascii=False, indent=2)
            print(f"  [OK] Zamanlama verisi kaydedildi ({len(sentence_timings)} cümle, {len(word_timings)} kelime).")

    print(f"Edge TTS (Ucretsiz) ile seslendiriliyor (Ses: {voice_id})...")
    try:
        asyncio.run(amain())
        print(f"[OK] Edge TTS seslendirme kaydedildi: {output_filename}")
        return output_filename
    except Exception as e:
        if os.path.exists(output_filename):
            try: os.remove(output_filename)
            except: pass
        raise ValueError(f"Edge TTS Hatasi: {str(e)}")


def _build_emotional_ssml(script: str, voice_id: str, language: str = "tr") -> str:
    """
    Converts plain script text into SSML with natural pauses, 
    expressive pacing, and emotional delivery. 
    Note: used for reference or high-quality manual overrides.
    """
    lang_code = "tr-TR" if language == "tr" else "en-US"
    # Split into paragraphs to add longer breaks between sections
    paragraphs = [p.strip() for p in script.split('\n') if p.strip()]
    
    ssml_parts = []
    for para in paragraphs:
        # Better sentence splitting logic
        sentences = re.split(r'(?<=[.!?])\s+', para)
        
        para_ssml = ""
        for sent in sentences:
            sent = sent.strip()
            if sent:
                # Use breath pauses and slight emphasis
                para_ssml += f'{sent} <break time="450ms"/> '
        
        ssml_parts.append(para_ssml.strip())
    
    # 800ms between major paragraphs for "reflection" look
    body = ' <break time="850ms"/> '.join(ssml_parts)
    
    # Wrap in speak block with warm prosody
    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang_code}">'
        f'<voice name="{voice_id}">'
        f'<prosody rate="-10%" pitch="-1%" volume="soft">'
        f'{body}'
        f'</prosody>'
        f'</voice>'
        f'</speak>'
    )
    
    return ssml



# ──────────────────────── VoysLity API ────────────────────────
def generate_voiceover_voyslity(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
    voice_id: str = "",
    model_id: str = "eleven_multilingual_v2",
) -> str:
    """
    Generates voiceover using VoysLity REST API.
    """
    # Clean script for API providers too
    script = clean_script_for_tts(script)
    
    api_key = os.getenv("VOYSLITY_API_KEY")
    if not api_key:
        raise ValueError("VOYSLITY_API_KEY bulunamadı! Lütfen Ayarlar'dan VoysLity lisans anahtarınızı girin.")

    if not voice_id:
        voice_id = os.getenv("VOYSLITY_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    url = "https://voyslity.com/api.php"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "text": script,
        "model_id": model_id,
        "voice_id": voice_id,
        "stability": 0.5,
        "similarity": 0.75,
        "style": 0.0,
        "use_speaker_boost": True,
        "language_code": "tr",
    }

    print(f"VoysLity API'ye istek gönderiliyor...")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        if response.status_code != 200:
            # Check for 403 bakiye error
            if response.status_code == 403:
                 raise ValueError("VoysLity Yetki/Bakiye Hatası: Yetersiz bakiye veya limit aşımı.")
            raise ValueError(f"VoysLity API Hatası (HTTP {response.status_code})")

        result = response.json()
        if result.get("status") != "success":
            raise ValueError(f"VoysLity API Hatası: {result.get('message', 'Bilinmeyen hata')}")

        data = result.get("data", {})
        temp_dir = os.path.dirname(output_filename)
        if temp_dir: os.makedirs(temp_dir, exist_ok=True)

        download_url = data.get("download_url")
        audio_base64 = data.get("audio_base64")

        if download_url:
            audio_response = requests.get(download_url, timeout=60)
            if audio_response.status_code == 200:
                with open(output_filename, "wb") as f:
                    f.write(audio_response.content)
                return output_filename

        if audio_base64:
            audio_bytes = base64.b64decode(audio_base64)
            with open(output_filename, "wb") as f:
                f.write(audio_bytes)
            return output_filename

        raise ValueError("Ses verisi alınamadı.")
    except Exception as e:
        raise ValueError(str(e))


# ──────────────────────── ElevenLabs API ────────────────────────
def generate_voiceover_elevenlabs(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
) -> str:
    from elevenlabs.client import ElevenLabs
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"

    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY bulunamadı!")

    script = clean_script_for_tts(script)
    
    client = ElevenLabs(api_key=api_key)
    try:
        audio = client.generate(text=script, voice=voice_id, model="eleven_multilingual_v2")
        temp_dir = os.path.dirname(output_filename)
        if temp_dir: os.makedirs(temp_dir, exist_ok=True)
        with open(output_filename, "wb") as f:
            for chunk in audio:
                if chunk: f.write(chunk)
        return output_filename
    except Exception as e:
        raise ValueError(f"ElevenLabs Hatası: {str(e)}")


# ──────────────────────── OtomasyonLabs TTS API ────────────────────────
BASE_URL_OTOMASYON = "https://www.otomasyonlabs.org"


def _otomasyon_headers():
    """OtomasyonLabs API için standart auth header döndürür."""
    api_key = os.getenv("OTOMASYONLABS_API_KEY")
    if not api_key:
        return None
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def get_otomasyonlabs_voices() -> list:
    """
    OtomasyonLabs API'den mevcut sesleri listeler.
    """
    headers = _otomasyon_headers()
    if not headers:
        return []

    try:
        resp = requests.get(
            f"{BASE_URL_OTOMASYON}/api/v1/voices",
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            # API, default_voices ve cloned_voices anahtarları döndürebilir
            if isinstance(data, dict):
                voices = data.get("default_voices", []) + data.get("cloned_voices", [])
                return voices if voices else data
            return data
        return []
    except Exception:
        return []


def generate_voiceover_otomasyonlabs(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
    voice_id: str = "",
    model_id: str = "eleven_multilingual_v2",
    language: str = "tr"
) -> str:
    """
    OtomasyonLabs REST API ile seslendirme üretir.
    Akış: POST /tts → Poll /tts/status/{id} → GET /tts/download/{id}
    """
    import time

    script = clean_script_for_tts(script)

    api_key = os.getenv("OTOMASYONLABS_API_KEY")
    if not api_key:
        raise ValueError("OTOMASYONLABS_API_KEY bulunamadi! Lutfen Ayarlar'dan anahtarinizi girin.")

    if not voice_id:
        voice_id = os.getenv("OTOMASYONLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # ── 1. SUBMIT ──────────────────────────────────────────────
    payload = {
        "text": script,
        "voice_id": voice_id,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.65,      # Increased for steadier emotional tone
            "similarity_boost": 0.8 # Higher for consistent human character
        }
    }

    print(f"OtomasyonLabs API'ye istek gonderiliyor (Metin: {len(script)} karakter)...")

    try:
        resp = requests.post(
            f"{BASE_URL_OTOMASYON}/api/v1/tts",
            json=payload,
            headers=headers,
            timeout=120
        )

        if resp.status_code not in (200, 201, 202):
            raise ValueError(f"API Hatasi (HTTP {resp.status_code}): {resp.text[:300]}")

        resp_data = resp.json()
        job_id = (
            resp_data.get("job_id")
            or resp_data.get("id")
            or resp_data.get("data", {}).get("job_id")
        )

        if not job_id:
            raise ValueError(f"API'den Job ID alinamadi: {resp_data}")

        remaining = resp_data.get("remaining_credits", "?")
        print(f"  [OK] Islem baslatildi. Job ID: {job_id}  (Kalan kredi: {remaining})")

        # ── 2. POLL ──────────────────────────────────────────────
        status_data = {}
        max_polls = 120  # 120 x 3s = 6 dakika maks
        for i in range(max_polls):
            time.sleep(3)
            try:
                sr = requests.get(
                    f"{BASE_URL_OTOMASYON}/api/v1/tts/status/{job_id}",
                    headers=headers,
                    timeout=30
                )
            except requests.exceptions.RequestException:
                continue  # Geçici ağ hatası, tekrar dene

            if sr.status_code != 200:
                continue

            status_data = sr.json()
            # API bazen veriyi "data" anahtarı altında döndürür
            if "data" in status_data and isinstance(status_data["data"], dict):
                status_data.update(status_data["data"])

            job_status = status_data.get("status", "")

            if job_status == "completed":
                print(f"  [OK] Ses uretimi tamamlandi!")
                break
            elif job_status == "failed":
                err = status_data.get("error") or status_data.get("message") or "Bilinmeyen hata"
                raise ValueError(f"Sunucu hatasi: {err}")

            # Her 30 saniyede bilgi ver
            if i > 0 and i % 10 == 0:
                detail = status_data.get("status_detail", "")
                print(f"  ... Isleniyor ({i*3}s) {detail}")
        else:
            raise ValueError("Islem zaman asimina ugradi (6 dk).")

        # ── 3. DOWNLOAD ──────────────────────────────────────────
        # Status yanıtındaki download_url'yi kullan (resmi API örnegi)
        rel_url = status_data.get("download_url") or status_data.get("downloadUrl")
        if rel_url and not rel_url.startswith("http"):
            dl_path = rel_url if rel_url.startswith("/") else "/" + rel_url
        else:
            dl_path = f"/api/v1/tts/download/{job_id}"

        # Indirme icin sadece Authorization header (Content-Type yok - resmi ornekteki gibi)
        dl_headers = {"Authorization": f"Bearer {api_key}"}

        print(f"  [INDIR] Ses dosyasi indiriliyor...")

        # Completed olduktan sonra kisa bekleme (sunucu dosyayi diske yaziyor olabilir)
        time.sleep(3)

        downloaded = False
        last_err = ""

        # 502 = nginx upstream timeout. Sunucu yogun oldugunda olusur.
        # Strateji: artan bekleme sureleri + alternatif domain denemesi
        max_attempts = 8
        domains = ["https://www.otomasyonlabs.org", "https://otomasyonlabs.org"]

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                # 502 icin ozel bekleme: 10, 15, 20, 25, 30, 40, 50s
                wait_sec = min(10 + (attempt - 2) * 5, 50)
                print(f"  ... Tekrar deneniyor ({attempt}/{max_attempts}, {wait_sec}s bekleniyor)...")
                time.sleep(wait_sec)

            # Ilk 4 denemede ana domain, sonraki 4'te alternatif domain
            domain = domains[0] if attempt <= 4 else domains[1]
            dl_url = f"{domain}{dl_path}"

            try:
                dr = requests.get(dl_url, headers=dl_headers, timeout=120)

                if dr.status_code == 200:
                    # Dosyayı kaydet
                    temp_dir = os.path.dirname(output_filename)
                    if temp_dir:
                        os.makedirs(temp_dir, exist_ok=True)

                    content = dr.content
                    total_bytes = len(content)

                    if total_bytes > 100:
                        with open(output_filename, "wb") as f:
                            f.write(content)
                        downloaded = True
                        print(f"  [OK] Ses dosyasi indirildi ({total_bytes} bytes)")
                        break
                    else:
                        last_err = f"Dosya cok kucuk ({total_bytes} bytes)"
                elif dr.status_code == 502:
                    last_err = f"HTTP 502 (sunucu yogun - nginx upstream timeout)"
                    print(f"  ... 502 Bad Gateway (deneme {attempt}/{max_attempts})")
                else:
                    last_err = f"HTTP {dr.status_code}"
            except requests.exceptions.RequestException as e:
                last_err = str(e)

        if not downloaded:
            raise ValueError(
                f"Indirme basarisiz ({last_err}). "
                f"Sunucu yogun olabilir, lutfen birka\u00e7 dakika sonra tekrar deneyin "
                f"veya Ayarlar'dan 'Edge TTS' secenegine gecin."
            )

        # ── 4. SRT (Opsiyonel) ───────────────────────────────────
        try:
            srt_resp = requests.get(
                f"{BASE_URL_OTOMASYON}/api/v1/tts/srt/{job_id}",
                headers=headers,
                timeout=20
            )
            if srt_resp.status_code == 200 and srt_resp.text.strip():
                srt_path = output_filename.replace(".mp3", ".srt")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_resp.text)
                print(f"  [OK] Altyazi (SRT) kaydedildi.")
        except Exception:
            pass

        return output_filename

    except requests.exceptions.Timeout:
        raise ValueError("OtomasyonLabs API zaman asimi. Lutfen tekrar deneyin.")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"OtomasyonLabs Hatasi: {str(e)}")


# ──────────────────────── DubVoice.ai TTS API ────────────────────────
BASE_URL_DUBVOICE = "https://www.dubvoice.ai"

def _dubvoice_headers():
    """DubVoice.ai API için auth header."""
    api_key = os.getenv("DUBVOICE_API_KEY")
    if not api_key:
        # Hata fırlatmak yerine None dönüp üst fonksiyonda kontrol edebiliriz
        # ama genelde bu tarz API'lerde key zorunludur.
        raise ValueError("DUBVOICE_API_KEY .env dosyasında bulunamadı!")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

async def get_dubvoice_voices():
    """DubVoice.ai API'den mevcut sesleri listeler."""
    try:
        url = f"{BASE_URL_DUBVOICE}/api/v1/voices"
        headers = _dubvoice_headers()
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("voices", [])
        return []
    except:
        return []

def generate_voiceover_dubvoice(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
    voice_id: str = "",
    model_id: str = "eleven_multilingual_v2",
) -> str:
    """
    DubVoice.ai REST API ile seslendirme üretir (Asenkron POST + POLL).
    """
    if not voice_id:
        voice_id = os.getenv("DUBVOICE_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
    
    # Clean script for API providers
    script = clean_script_for_tts(script)
    
    import time
    try:
        headers = _dubvoice_headers()
        
        # 1. POST - Task oluştur
        payload = {
            "text": script,
            "voice_id": voice_id,
            "model_id": model_id if model_id else "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": 1.0
            }
        }
        
        print(f"  [TTS] DubVoice: Task olusturuluyor... (Voice: {voice_id})")
        resp = requests.post(f"{BASE_URL_DUBVOICE}/api/v1/tts", json=payload, headers=headers, timeout=30)
        
        if resp.status_code not in (200, 201, 202):
            raise ValueError(f"POST Hatası ({resp.status_code}): {resp.text}")
            
        task_id = resp.json().get("task_id")
        if not task_id:
            raise ValueError("API task_id dönmedi!")

        # 2. POLL - Tamamlanmasını bekle
        print(f"  [WAIT] DubVoice: Ses isleniyor (Task: {task_id})...")
        max_attempts = 60 # 3 dakika civarı
        for attempt in range(max_attempts):
            time.sleep(3)
            status_resp = requests.get(f"{BASE_URL_DUBVOICE}/api/v1/tts/{task_id}", headers=headers, timeout=15)
            
            if status_resp.status_code == 200:
                data = status_resp.json()
                status = data.get("status")
                
                if status == "completed":
                    audio_url = data.get("result")
                    if not audio_url:
                        raise ValueError("İşlem tamamlandı ama ses URL'i gelmedi!")
                        
                    # 3. DOWNLOAD
                    print(f"  [INDIR] DubVoice: Ses indiriliyor...")
                    audio_resp = requests.get(audio_url, timeout=120)
                    if audio_resp.status_code == 200:
                        with open(output_filename, "wb") as f:
                            f.write(audio_resp.content)
                        return output_filename
                    else:
                        raise ValueError(f"İndirme hatası: {audio_resp.status_code}")
                
                elif status == "error":
                    raise ValueError(f"API hatası: {data.get('error', 'Bilinmeyen hata')}")
                    
                else:
                    if attempt % 5 == 0:
                        print(f"  ... DubVoice durumu: {status}")
            else:
                print(f"  [!] DubVoice Poll Hatasi ({status_resp.status_code}): Bekleniyor...")

        raise TimeoutError("DubVoice ses üretimi zaman aşımına uğradı!")

    except Exception as e:
        print(f"  [HATA] DubVoice Hatasi: {str(e)}")
        raise


# ──────────────────────── Spesh Audio TTS API ────────────────────────
BASE_URL_SPESH = "https://speshaudio.com/api/v1"

def generate_voiceover_speshaudio(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
    voice_id: str = "",
    model_id: str = "eleven_multilingual_v2",
    language: str = "tr"
) -> str:
    """
    SpeshAudio.com REST API ile seslendirme üretir (Doğrudan İndirme).
    """
    if not voice_id:
        voice_id = os.getenv("SPESHAUDIO_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
    
    script = clean_script_for_tts(script)
    
    api_key = os.getenv("SPESHAUDIO_API_KEY")
    if not api_key:
        raise ValueError("SPESHAUDIO_API_KEY .env dosyasında bulunamadı!")

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": script,
            "voice_id": voice_id,
            "model_id": model_id if model_id else "eleven_multilingual_v2",
            "language": language
        }
        
        print(f"  [TTS] Spesh Audio: Seslendirme üretiliyor... (Voice: {voice_id})")
        resp = requests.post(f"{BASE_URL_SPESH}/tts", json=payload, headers=headers, timeout=120)
        
        if resp.status_code == 200:
            # Spesh Audio returns a JSON containing a Supabase URL
            try:
                data = resp.json()
                if data.get("success"):
                    api_data = data.get("data", {})
                    audio_url = api_data.get("audio_url")
                    used = api_data.get("credits_used", "0")
                    rem = api_data.get("remaining_credits", "?")
                    
                    if audio_url:
                        print(f"  [TTS] Spesh Audio: Ses dosyası indiriliyor: {audio_url}")
                        audio_resp = requests.get(audio_url, timeout=60)
                        if audio_resp.status_code == 200:
                            with open(output_filename, "wb") as f:
                                f.write(audio_resp.content)
                            print(f"  [OK] Spesh Audio: Ses kaydedildi ({os.path.getsize(output_filename)} bytes)")
                            print(f"  [INFO] Kullanılan Kredi: {used} | Kalan Kredi: {rem}")
                            return output_filename
                        else:
                            raise ValueError(f"Ses indirme hatası (URL: {audio_resp.status_code})")
                    else:
                        raise ValueError(f"Spesh Audio JSON yanitinda URL bulunamadi: {data}")
                else:
                    raise ValueError(f"Spesh Audio API Basarisiz: {data.get('error', 'Bilinmeyen hata')}")
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback: maybe it's direct binary?
                if len(resp.content) > 1000:
                    with open(output_filename, "wb") as f:
                        f.write(resp.content)
                    print(f"  [OK] Spesh Audio (Direct): Ses kaydedildi ({len(resp.content)} bytes)")
                    return output_filename
                else:
                    raise ValueError(f"Spesh Audio Yaniti Gorevlenemedi: {resp.text[:250]}")
        else:
            raise ValueError(f"Spesh Audio Hatası ({resp.status_code}): {resp.text[:300]}")

    except Exception as e:
        print(f"  [HATA] Spesh Audio Hatasi: {str(e)}")
        raise


# ──────────────────────── Voice Cloning (Ses Klonlama) ──────────────────────
def clone_voice_elevenlabs(name: str, sample_file_path: str, description: str = "") -> str:
    """
    ElevenLabs Instant Voice Cloning: Örnek bir ses dosyasından yeni bir ses klonlar.
    Gereksinim: sample_file_path (mp3, wav vb.)
    Returns: Yeni oluşturulan voice_id
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY .env dosyasında bulunamadı!")

    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": api_key}
    
    # Dosyayı multipart/form-data olarak gönder
    try:
        with open(sample_file_path, 'rb') as f:
            files = {
                'files': (os.path.basename(sample_file_path), f, 'audio/mpeg')
            }
            data = {
                'name': name,
                'description': description or f"{name} klonlanmış ses",
                'labels': '{"cloned": "true"}'
            }
            print(f"  [CLONE] ElevenLabs: Ses klonlanıyor... ({name})")
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=60)
            
            if resp.status_code == 200:
                voice_id = resp.json().get("voice_id")
                print(f"  [OK] Ses başarıyla klonlandı! Voice ID: {voice_id}")
                return voice_id
            else:
                raise ValueError(f"Klonlama Hatası ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"  [!] ElevenLabs Klonlama Hatası: {e}")
        raise


def clone_voice_dubvoice(name: str, sample_file_path: str) -> str:
    """
    DubVoice Instant Voice Cloning.
    Returns: Yeni oluşturulan voice_id
    """
    api_key = os.getenv("DUBVOICE_API_KEY")
    if not api_key:
        raise ValueError("DUBVOICE_API_KEY bulunamadı!")

    url = "https://www.dubvoice.ai/api/v1/voices/clone"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        with open(sample_file_path, 'rb') as f:
            files = {'file': f}
            data = {'name': name}
            print(f"  [CLONE] DubVoice: Ses klonlanıyor... ({name})")
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=60)
            
            if resp.status_code in (200, 201):
                voice_id = resp.json().get("voice_id")
                print(f"  [OK] DubVoice: Ses klonlandı! Voice ID: {voice_id}")
                return voice_id
            else:
                raise ValueError(f"DubVoice Klonlama Hatası ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"  [!] DubVoice Klonlama Hatası: {e}")
        raise




# ──────────────────────── Unified Entry Point ────────────────────────
def generate_voiceover(
    script: str,
    output_filename: str = "temp/voiceover.mp3",
    tts_provider: str = "edge",
    edge_voice_id: str = "tr-TR-AhmetNeural",
    language: str = "tr",
    model_id: str = None
) -> str:
    """
    Unified voiceover generation function.
    tts_provider: "edge", "voyslity", "elevenlabs", "otomasyonlabs", "dubvoice", or "speshaudio"
    """
    try:
        if tts_provider == "edge":
            return generate_voiceover_edge(script, output_filename, voice_id=edge_voice_id, language=language)
        elif tts_provider == "voyslity":
            kwargs = {}
            if model_id: kwargs["model_id"] = model_id
            return generate_voiceover_voyslity(script, output_filename, **kwargs)
        elif tts_provider == "elevenlabs":
            return generate_voiceover_elevenlabs(script, output_filename)
        elif tts_provider == "otomasyonlabs":
            kwargs = {"language": language}
            if model_id: kwargs["model_id"] = model_id
            return generate_voiceover_otomasyonlabs(script, output_filename, **kwargs)
        elif tts_provider == "dubvoice":
            kwargs = {}
            if model_id: kwargs["model_id"] = model_id
            return generate_voiceover_dubvoice(script, output_filename, **kwargs)
        elif tts_provider == "speshaudio":
            try:
                kwargs = {"language": language}
                if model_id: kwargs["model_id"] = model_id
                return generate_voiceover_speshaudio(script, output_filename, **kwargs)
            except Exception as e:
                print(f"  [!] SPESHAUDIO hatasi: {str(e)}. DUBVOICE'a geciliyor...")
                kwargs = {}
                if model_id: kwargs["model_id"] = model_id
                return generate_voiceover_dubvoice(script, output_filename, **kwargs)
        else:
            raise ValueError(f"Bilinmeyen TTS sağlayıcı: {tts_provider}")
    except Exception as e:
        print(f"  [!] {tts_provider.upper()} hatasi: {str(e)}")
        
        # Spesh Audio veya DubVoice hata verdiğinde ücretsiz TTS'e geçişi engelle
        if tts_provider in ["speshaudio", "dubvoice"]:
            print(f"  [X] {tts_provider.upper()} ve varsa alternatifleri basarisiz oldu. Ucretsiz TTS'e gecilmiyor.")
            raise e

        if tts_provider != "edge":
            print(f"  [RETRY] Kritik: {tts_provider.upper()} basarisiz oldu, ucretsiz Edge TTS'e otomatik gecis yapiliyor...")
            
            # Ses kimliği bir dosya yolu ise (XTTS ornegi gibi), Edge icin gecerli bir ses sec
            fallback_voice = edge_voice_id
            if fallback_voice and ("\\" in fallback_voice or "/" in fallback_voice or fallback_voice.endswith((".wav", ".mp3", ".m4a"))):
                print(f"  [!] Edge TTS icin gecersiz ses ID ({fallback_voice}). Varsayılan kullanılıyor.")
                fallback_voice = "tr-TR-AhmetNeural" if language == "tr" else "en-US-GuyNeural"
                
            return generate_voiceover_edge(script, output_filename, voice_id=fallback_voice, language=language)
        else:
            raise e


if __name__ == "__main__":
    test_script = "Merhaba, bu ücretsiz Edge TTS seslendirmesidir."
    generate_voiceover(test_script, "temp/test_free.mp3", tts_provider="edge")
