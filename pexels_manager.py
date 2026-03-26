import requests
import os
import random

def _download_file(url, filename):
    """
    Generic downloader for images or videos.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"İndirme Hatası: {e}")
    return False

def search_pexels_videos(query, per_page=5):
    """
    Searches Pexels for videos based on query.
    """
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("HATA: Pexels API Key bulunamadı.")
        return []

    url = f"https://api.pexels.com/videos/search?query={query}&per_page={per_page}&orientation=landscape"
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            video_urls = []
            for video in data.get("videos", []):
                # Get the highest quality HD file
                video_files = video.get("video_files", [])
                hd_file = next((f for f in video_files if f.get("quality") == "hd"), video_files[0])
                video_urls.append(hd_file.get("link"))
            return video_urls
        else:
            print(f"Pexels Hatası: {response.status_code}")
            return []
    except Exception as e:
        print(f"Pexels İstek Hatası: {e}")
        return []

def search_pexels_photos(query, per_page=10):
    """
    Searches Pexels for photos based on query.
    """
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("HATA: Pexels API Key bulunamadı.")
        return []

    url = f"https://api.pexels.com/v1/search?query={query}&per_page={per_page}&orientation=landscape"
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            image_urls = []
            for photo in data.get("photos", []):
                # Use large or original size
                src = photo.get("src", {})
                image_urls.append(src.get("large") or src.get("original"))
            return image_urls
        else:
            print(f"Pexels Fotoğraf Hatası: {response.status_code}")
            return []
    except Exception as e:
        print(f"Pexels İstek Hatası: {e}")
        return []

def download_video(url, filename):
    return _download_file(url, filename)

import concurrent.futures

def get_pexels_assets(topic, target_count=5, save_dir="assets/videos", keywords=None):
    """
    Orchestrates searching and downloading videos.
    Uses multi-threading for faster downloads.
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Use keywords for better variety, fallback to topic
    queries = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else [topic.split(':')[0] if ':' in topic else topic]
    
    all_links_to_download = []
    
    for q_idx, query in enumerate(queries):
        if len(all_links_to_download) >= target_count: break
        
        print(f"Pexels Video Araştırılıyor: {query}")
        video_links = search_pexels_videos(query, per_page=max(target_count * 2, 15)) 
        
        for link in video_links:
            if len(all_links_to_download) >= target_count: break
            
            safe_q = "".join([c if c.isalnum() else "_" for c in query.lower()])
            # Add a bit of randomness to filename to avoid collisions in parallel
            filename = os.path.join(save_dir, f"pexels_v_{safe_q}_{len(all_links_to_download)}_{random.randint(100,999)}.mp4")
            
            if not os.path.exists(filename):
                all_links_to_download.append((link, filename, query))
            else:
                # Still count existing as downloaded
                pass

    if not all_links_to_download:
        return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pexels_v" in f][:target_count]

    print(f"  🚀 {len(all_links_to_download)} video paralel olarak indiriliyor...")
    
    downloaded_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(_download_file, link, fn): fn for link, fn, q in all_links_to_download}
        for future in concurrent.futures.as_completed(future_to_url):
            fn = future_to_url[future]
            try:
                if future.result():
                    downloaded_files.append(fn)
                    print(f"    ✓ Tamamlandı: {os.path.basename(fn)}")
            except Exception as exc:
                print(f"    ⚠ İndirme hatası: {fn} -> {exc}")
    
    # Return all in directory that match pattern
    return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pexels_v" in f][:target_count]

def get_pexels_images(topic, target_count=10, save_dir="assets/videos", keywords=None):
    """
    Downloads photos from Pexels with multi-threading.
    """
    os.makedirs(save_dir, exist_ok=True)
    
    queries = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else [topic.split(':')[0] if ':' in topic else topic]
    
    all_links_to_download = []
    for q_idx, query in enumerate(queries):
        if len(all_links_to_download) >= target_count: break
        
        print(f"Pexels Fotoğraf Araştırılıyor: {query}")
        image_links = search_pexels_photos(query, per_page=max(target_count * 2, 20))
        
        for link in image_links:
            if len(all_links_to_download) >= target_count: break
            
            safe_q = "".join([c if c.isalnum() else "_" for c in query.lower()])
            filename = os.path.join(save_dir, f"pexels_i_{safe_q}_{len(all_links_to_download)}_{random.randint(100,999)}.jpg")
            
            if not os.path.exists(filename):
                all_links_to_download.append((link, filename, query))

    if not all_links_to_download:
        return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pexels_i" in f][:target_count]

    print(f"  🚀 {len(all_links_to_download)} fotoğraf paralel olarak indiriliyor...")

    downloaded_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {executor.submit(_download_file, link, fn): fn for link, fn, q in all_links_to_download}
        for future in concurrent.futures.as_completed(future_to_url):
            fn = future_to_url[future]
            try:
                if future.result():
                    downloaded_files.append(fn)
            except Exception as exc:
                print(f"    ⚠ İndirme hatası: {fn} -> {exc}")
            
    return [os.path.join(save_dir, f) for f in os.listdir(save_dir) if "pexels_i" in f][:target_count]
