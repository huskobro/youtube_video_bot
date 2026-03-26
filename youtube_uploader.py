
import os
import pickle
import socket
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube API scopes - Added readonly for analytics
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

def get_authenticated_service(token_path='token.pickle'):
    """Authenticates the user and returns the YouTube service object."""
    credentials = None
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                credentials = pickle.load(token)
        except Exception:
            credentials = None
            
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                return None
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            credentials = flow.run_local_server(port=0, authorization_prompt_message='YouTube hesabınızı yetkilendirin...')
            
        if credentials:
            with open(token_path, 'wb') as token:
                pickle.dump(credentials, token)

    return build('youtube', 'v3', credentials=credentials)

def get_channel_info(service=None, token_path='token.pickle'):
    """Fetches channel name, subscribers, views, and video count."""
    try:
        if not service:
            service = get_authenticated_service(token_path)
        if not service: return None

        request = service.channels().list(
            part="snippet,statistics",
            mine=True
        )
        response = request.execute()

        if response.get('items'):
            item = response['items'][0]
            snippet = item.get('snippet', {})
            stats = item.get('statistics', {})
            return {
                "id": item.get('id'),
                "title": snippet.get('title'),
                "customUrl": snippet.get('customUrl'),
                "thumbnail": snippet.get('thumbnails', {}).get('default', {}).get('url'),
                "subscribers": stats.get('subscriberCount', '0'),
                "views": stats.get('viewCount', '0'),
                "videos": stats.get('videoCount', '0')
            }
    except Exception as e:
        print(f"Error fetching channel info: {e}")
    return None

def upload_to_youtube(video_path, title, description, tags=None, thumbnail_path=None, category_id="22", token_path='token.pickle'):
    """
    Uploads a video to YouTube using the official YouTube Data API v3.
    Always uploads as 'private' as requested.
    """
    if tags is None:
        tags = []
        
    if not os.path.exists(video_path):
        print(f"  [!] Error: Video file not found: {video_path}")
        return False

    try:
        print(f"  [*] Initializing YouTube API for: {title}")
        youtube = get_authenticated_service(token_path)
        if not youtube: return False

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': 'private', # ALWAYS PRIVATE
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(
            video_path, 
            chunksize=-1, 
            resumable=True, 
            mimetype='video/mp4'
        )

        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        print(f"  [*] Uploading to YouTube...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                # print(f"    -> Progress: {progress}%")

        video_id = response.get('id')
        print(f"  [OK] Upload Success! ID: {video_id}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                print("  [OK] Thumbnail uploaded.")
            except: pass

        return True

    except Exception as e:
        print(f"  [!] YouTube Upload Error: {e}")
        return False

if __name__ == "__main__":
    # Test block (optional)
    # upload_to_youtube("test.mp4", "Test Title", "Test Description", ["test", "api"])
    pass
