import subprocess
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

HISTORY_FILE = "download_history.json"
BASE_DOWNLOAD_PATH = "/home/s/Videos/YoutubeDownloads"

def get_playlist_title(playlist_url):
    print("📥 Fetching official title...")
    result = subprocess.run([
        "yt-dlp", "--yes-playlist", "--flat-playlist", "--playlist-end", "1", 
        "--print", "%(playlist_title)s|%(channel)s|%(uploader)s",
        "--no-warnings", playlist_url
    ], stdout=subprocess.PIPE, text=True)
    
    out = result.stdout.strip()
    if out:
        lines = out.split("\n")
        if lines:
            parts = lines[0].split("|")
            # Prefer channel or uploader to avoid " - Videos" from playlist_title
            if len(parts) >= 2 and parts[1] and parts[1] != "NA":
                return parts[1]
            if len(parts) >= 3 and parts[2] and parts[2] != "NA":
                return parts[2]
            if len(parts) >= 1 and parts[0] and parts[0] != "NA":
                return parts[0].replace(" - Videos", "")
                
    # Fallback
    result_fallback = subprocess.run([
        "yt-dlp", "--get-title", "--flat-playlist", "--playlist-end", "1", "--no-warnings", playlist_url
    ], stdout=subprocess.PIPE, text=True)
    lines = result_fallback.stdout.strip().split("\n")
    return lines[0] if lines else "Unknown_Target"

def load_last_video(playlist_url):
    if not os.path.exists(HISTORY_FILE): return None
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        return history.get(playlist_url)
    except:
        return None

def save_last_video(playlist_url, video_id):
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: pass
    history[playlist_url] = video_id
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_video_ids(playlist_url):
    print("📥 Fetching all video IDs (this may take a moment for large playlists)...")
    # Added --yes-playlist to ensure we don't just grab one video if the URL is a video-in-a-playlist
    result = subprocess.run([
        "yt-dlp", "--flat-playlist", "--print", "id", "--yes-playlist", playlist_url
    ], stdout=subprocess.PIPE, text=True)
    ids = [i.strip() for i in result.stdout.strip().split("\n") if i.strip()]
    print(f"✅ Found {len(ids)} videos.")
    return ids

def single_video_worker(args):
    """Worker function to be run in a thread."""
    index, video_id, fmt, save_path = args
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # We use index:03d to make 001, 002, etc.
    formatted_index = f"{index:03d}"
    
    # Check if a file with this index already exists to avoid re-downloading
    existing_files = [f for f in os.listdir(save_path) if f.startswith(formatted_index)]
    if existing_files:
        print(f"⏭️  Skipping {formatted_index} (Already exists)")
        return

    print(f"🚀 Thread {formatted_index} starting...")
    
    subprocess.run([
        "yt-dlp", "-f", fmt, 
        "--merge-output-format", "mp4",
        "--downloader-args", "ffmpeg:-threads 3",
        # Added 'No. %(playlist_index)s' or we can just pass our Python index
        "-o", f"{save_path}/{formatted_index} - [No.{index}] %(title)s.%(ext)s",
        "--no-playlist",
        video_url
    ])

def download_videos(all_video_ids, to_dl_ids, folder_name, quality):
    clean_folder = re.sub(r'[\\/*?:"<>|]', "", folder_name)
    save_path = os.path.join(BASE_DOWNLOAD_PATH, clean_folder)
    if not os.path.exists(save_path): os.makedirs(save_path)

    fmt = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best"

    # We use the index from the ORIGINAL full list to maintain overall order
    tasks = []
    for vid in to_dl_ids:
        original_index = all_video_ids.index(vid) + 1
        tasks.append((original_index, vid, fmt, save_path))

    print(f"⚡ Processing {len(tasks)} videos using 3 parallel threads...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        # We use list() to force the execution of the generator
        list(executor.map(single_video_worker, tasks))

    # Import locally to avoid issues
    try:
        from generate_frontend import generate_frontend 
        # (Or just keep your generate_frontend function in the same file)
        generate_frontend(save_path, folder_name)
    except ModuleNotFoundError:
        print("⏭️  generate_frontend module not found. Skipping frontend generation.")
    return True

# ... [Keep your generate_frontend function here] ...

def collect_and_download(playlist_url):
    title = get_playlist_title(playlist_url)
    print(f"🎯 Target: {title}")

    print("Select Quality (1080, 720, 480) [Default: 1080]:")
    q_in = input().strip()
    quality = q_in if q_in in ["1080", "720", "480"] else "1080"

    video_ids = get_video_ids(playlist_url)
    if not video_ids:
        print("❌ Could not find any videos in playlist.")
        return

    last = load_last_video(playlist_url)
    
    # Fix: Safer index finding
    if last in video_ids:
        start_index = video_ids.index(last) + 1
        print(f"🔄 Resuming from video {start_index + 1}...")
    else:
        start_index = 0
        print("🆕 Starting fresh download...")

    to_dl = video_ids[start_index:]
    
    if not to_dl:
        print("✅ Everything is already downloaded.")
        return

    if download_videos(video_ids, to_dl, title, quality):
        save_last_video(playlist_url, to_dl[-1])
        print("🏁 All tasks complete.")

def main():
    print("Select Download Type:")
    print("1. Playlist")
    print("2. Channel")
    choice = input().strip()
    
    if choice == "2":
        print("Enter Channel URL or Handle (e.g. @mkbhd or https://youtube.com/@mkbhd):")
        url = input().strip()
        if url:
             if not url.startswith("http"):
                 if not url.startswith("@"):
                     url = "@" + url
                 url = f"https://www.youtube.com/{url}/videos"
             else:
                 # If it's a channel URL without /videos, we can append it conceptually or let yt-dlp handle it.
                 # Appending /videos keeps it strictly to video uploads instead of shorts/streams sometimes.
                 if not url.endswith("/videos") and not url.endswith("/shorts") and not url.endswith("/streams"):
                     url = url.rstrip("/") + "/videos"
             collect_and_download(url)
    else:
        print("Paste Playlist URL:")
        url = input().strip()
        if url:
            collect_and_download(url)

if __name__ == "__main__":
    main()