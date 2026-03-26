import requests
import os
import random
import time

def _download_file(url, filename):
    """
    Generic downloader for images or videos.
    """
    try:
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"Pixabay İndirme Hatası: {e}")
    return False

def search_pixabay_videos(query, per_page=5):
    """
    Searches Pixabay for videos.
    """
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        print("HATA: Pixabay API Key bulunamadı.")
        return []

    # Pixabay API uses '+' instead of spaces
    query = query.replace(' ', '+')
    url = f"https://pixabay.com/api/videos/?key={api_key}&q={query}&per_page={per_page}&safesearch=true"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            video_urls = []
            for hit in data.get("hits", []):
                # Pixabay provides different qualities. Try to get a good one.
                v_files = hit.get("videos", {})
                # Preferred: small (usually 960x540) or medium (often 1280x720)
                best_file = v_files.get("medium") or v_files.get("small") or v_files.get("large")
                if best_file and best_file.get("url"):
                    video_urls.append(best_file.get("url"))
            return video_urls
    except Exception as e:
        print(f"Pixabay Video Arama Hatası: {e}")
    return []

def search_pixabay_photos(query, per_page=10):
    """
    Searches Pixabay for photos.
    """
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        print("HATA: Pixabay API Key bulunamadı.")
        return []

    query = query.replace(' ', '+')
    url = f"https://pixabay.com/api/?key={api_key}&q={query}&image_type=photo&orientation=horizontal&per_page={per_page}&safesearch=true"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            image_urls = []
            for hit in data.get("hits", []):
                url = hit.get("largeImageURL") or hit.get("webformatURL")
                if url:
                    image_urls.append(url)
            return image_urls
    except Exception as e:
        print(f"Pixabay Fotoğraf Arama Hatası: {e}")
    return []

import concurrent.futures

def get_pixabay_assets(topic, target_count=5, save_dir="assets/videos", keywords=None):
    """
    Downloads videos from Pixabay in parallel.
    """
    os.makedirs(save_dir, exist_ok=True)
    queries = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else [topic.split(':')[0] if ':' in topic else topic]
    
    all_links_to_download = []
    for query in queries:
        if len(all_links_to_download) >= target_count: break
        
        print(f"Pixabay Video Araştırılıyor: {query}")
        links = search_pixabay_videos(query, per_page=max(target_count * 2, 15))
        
        for i, link in enumerate(links):
            if len(all_links_to_download) >= target_count: break
            safe_q = "".join([c if c.isalnum() else "_" for c in query.lower()])
            filename = os.path.join(save_dir, f"pixabay_v_{safe_q}_{len(all_links_to_download)}_{random.randint(100,999)}.mp4")
            all_links_to_download.append((link, filename))

    if not all_links_to_download:
        return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pixabay_v" in f][:target_count]

    print(f"  🚀 {len(all_links_to_download)} Pixabay videosu paralel olarak indiriliyor...")
    
    downloaded_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(_download_file, link, fn): fn for link, fn in all_links_to_download}
        for future in concurrent.futures.as_completed(future_to_url):
            fn = future_to_url[future]
            try:
                if future.result():
                    downloaded_files.append(fn)
                    print(f"    ✓ Bitti: {os.path.basename(fn)}")
            except Exception as e:
                print(f"    ⚠ İndirme hatası: {e}")
                
    return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pixabay_v" in f][:target_count]

def get_pixabay_images(topic, target_count=10, save_dir="assets/videos", keywords=None):
    """
    Downloads photos from Pixabay in parallel.
    """
    os.makedirs(save_dir, exist_ok=True)
    queries = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else [topic.split(':')[0] if ':' in topic else topic]
    
    all_links_to_download = []
    for query in queries:
        if len(all_links_to_download) >= target_count: break
        
        print(f"Pixabay Fotoğraf Araştırılıyor: {query}")
        links = search_pixabay_photos(query, per_page=max(target_count * 2, 20))
        
        for i, link in enumerate(links):
            if len(all_links_to_download) >= target_count: break
            safe_q = "".join([c if c.isalnum() else "_" for c in query.lower()])
            filename = os.path.join(save_dir, f"pixabay_i_{safe_q}_{len(all_links_to_download)}_{random.randint(100,999)}.jpg")
            all_links_to_download.append((link, filename))

    if not all_links_to_download:
        return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pixabay_i" in f][:target_count]

    print(f"  🚀 {len(all_links_to_download)} Pixabay fotoğrafı paralel olarak indiriliyor...")

    downloaded_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {executor.submit(_download_file, link, fn): fn for link, fn in all_links_to_download}
        for future in concurrent.futures.as_completed(future_to_url):
            fn = future_to_url[future]
            try:
                if future.result():
                    downloaded_files.append(fn)
            except Exception as e:
                print(f"    ⚠ İndirme hatası: {e}")
                
    return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pixabay_i" in f][:target_count]
