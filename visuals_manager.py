import os
import random

def get_video_clips(duration_required: float, videos_folder: str = "assets/videos") -> list:
    """
    Scans the videos_folder and returns a list of video file paths
    that total at least the required duration.
    """
    if not os.path.exists(videos_folder):
        os.makedirs(videos_folder, exist_ok=True)
        return []

    all_videos = [os.path.join(videos_folder, f) for f in os.listdir(videos_folder) 
                  if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.jpg', '.jpeg', '.png', '.webp'))]
    
    if not all_videos:
        print(f"Warning: No video files found in {videos_folder}. Add some stock videos here.")
        return []

    # Select random clips until we reach an estimated sufficient count
    # Note: MoviePy will determine actual duration, here we just fetch files.
    # In a full app, we would calculate actual durations. Here we'll return a shuffled pool
    # and the video editor will cut them to the exact audio length.
    random.shuffle(all_videos)
    return all_videos

def get_overlay_effect(effects_folder: str = "assets/effects") -> str:
    """
    Returns a path to a global overlay effect if one exists.
    """
    if not os.path.exists(effects_folder):
        return ""
    
    effects = [os.path.join(effects_folder, f) for f in os.listdir(effects_folder) 
               if f.lower().endswith(('.mp4', '.mov'))]
    
    return random.choice(effects) if effects else ""

if __name__ == "__main__":
    clips = get_video_clips(60.0)
    print(f"Selected clips: {clips}")
