import subprocess
import json
import os
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Resolve yt-dlp path — prefer the venv's binary, fall back to system PATH
YTDLP = shutil.which("yt-dlp", path=os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""))
if not YTDLP:
    raise RuntimeError("yt-dlp not found. Run: pip install yt-dlp")

HISTORY_FILE = "download_history.json"
BASE_DOWNLOAD_PATH = "/home/s/Videos/YoutubeDownloads"

# Global state for tracking downloads
download_state = {
    "active": False,
    "progress": 0,
    "total": 0,
    "current_video": "",
    "status": "idle",
    "folder": "",
    "logs": []
}

def log_message(msg):
    """Add a message to logs with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    download_state["logs"].append(full_msg)
    print(msg)

def get_playlist_title(playlist_url):
    log_message("📥 Fetching official title...")
    result = subprocess.run([
        YTDLP, "--yes-playlist", "--flat-playlist", "--playlist-end", "1",
        "--print", "%(playlist_title)s|%(channel)s|%(uploader)s",
        "--no-warnings", playlist_url
    ], stdout=subprocess.PIPE, text=True)
    
    out = result.stdout.strip()
    if out:
        lines = out.split("\n")
        if lines:
            parts = lines[0].split("|")
            if len(parts) >= 2 and parts[1] and parts[1] != "NA":
                return parts[1]
            if len(parts) >= 3 and parts[2] and parts[2] != "NA":
                return parts[2]
            if len(parts) >= 1 and parts[0] and parts[0] != "NA":
                return parts[0].replace(" - Videos", "")
                
    result_fallback = subprocess.run([
        YTDLP, "--get-title", "--flat-playlist", "--playlist-end", "1", "--no-warnings", playlist_url
    ], stdout=subprocess.PIPE, text=True)
    lines = result_fallback.stdout.strip().split("\n")
    return lines[0] if lines else "Unknown_Target"

def save_history_entry(playlist_url, video_ids):
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: 
            pass
    history[playlist_url] = video_ids
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_video_ids(playlist_url):
    log_message("📥 Fetching all video IDs (this may take a moment for large playlists)...")
    result = subprocess.run([
        YTDLP, "--flat-playlist", "--print", "id", "--yes-playlist", playlist_url
    ], stdout=subprocess.PIPE, text=True)
    ids = [i.strip() for i in result.stdout.strip().split("\n") if i.strip()]
    log_message(f"✅ Found {len(ids)} videos.")
    return ids

def single_video_worker(args):
    """Worker function to be run in a thread."""
    index, video_id, fmt, save_path = args
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    formatted_index = f"{index:03d}"
    
    existing_files = [f for f in os.listdir(save_path) if f.startswith(formatted_index)]
    if existing_files:
        log_message(f"⏭️  Skipping {formatted_index} (Already exists)")
        download_state["progress"] += 1
        return

    log_message(f"🚀 Downloading {formatted_index}...")
    download_state["current_video"] = f"Video {formatted_index}"
    
    subprocess.run([
        YTDLP, "-f", fmt,
        "--merge-output-format", "mp4",
        "--downloader-args", "ffmpeg:-threads 3",
        "-o", f"{save_path}/{formatted_index} - [No.{index}] %(title)s.%(ext)s",
        "--no-playlist",
        video_url
    ])
    
    download_state["progress"] += 1

def download_videos(all_video_ids, to_dl_ids, folder_name, quality):
    clean_folder = re.sub(r'[\\/*?:"<>|]', "", folder_name)
    save_path = os.path.join(BASE_DOWNLOAD_PATH, clean_folder)
    if not os.path.exists(save_path): 
        os.makedirs(save_path)

    fmt = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best"

    tasks = []
    for vid in to_dl_ids:
        original_index = all_video_ids.index(vid) + 1
        tasks.append((original_index, vid, fmt, save_path))

    download_state["total"] = len(tasks)
    download_state["progress"] = 0
    
    log_message(f"⚡ Processing {len(tasks)} videos using 3 parallel threads...")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(single_video_worker, tasks))

    log_message("🏁 All tasks complete.")
    return True

def perform_download(playlist_url, quality, download_type, limit=None):
    """Perform download in a separate thread"""
    try:
        download_state["active"] = True
        download_state["status"] = "running"
        download_state["logs"] = []
        
        title = get_playlist_title(playlist_url)
        download_state["folder"] = title
        log_message(f"🎯 Target: {title}")

        video_ids = get_video_ids(playlist_url)
        if not video_ids:
            log_message("❌ Could not find any videos.")
            download_state["status"] = "error"
            return

        # Load history of downloaded IDs
        history = {}
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    history = json.load(f)
            except: pass
        
        downloaded_ids = set(history.get(playlist_url, []))
        
        # Filter out already downloaded videos
        to_dl = [vid for vid in video_ids if vid not in downloaded_ids]
        
        # Apply limit if specified (take latest N)
        if limit and limit > 0:
            # yt-dlp usually returns latest first for channels, but to be sure:
            # we take the first 'limit' videos from the ORIGINAL list that are NOT downloaded
            to_dl = to_dl[:limit]
            log_message(f"📍 Limited to {limit} newest videos.")

        if not to_dl:
            log_message("✅ Everything is already downloaded.")
            download_state["status"] = "complete"
            return

        if download_videos(video_ids, to_dl, title, quality):
            # Update history with newly downloaded IDs
            new_history = list(downloaded_ids.union(set(to_dl)))
            save_history_entry(playlist_url, new_history)
            download_state["status"] = "complete"
        
    except Exception as e:
        log_message(f"❌ Error: {str(e)}")
        download_state["status"] = "error"
    finally:
        download_state["active"] = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url', '').strip()
    quality = data.get('quality', '1080')
    download_type = data.get('type', 'playlist')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    if download_state["active"]:
        return jsonify({'error': 'Download already in progress'}), 400
    
    # Normalize channel URLs
    if download_type == 'channel':
        if not url.startswith("http"):
            if not url.startswith("@"):
                url = "@" + url
            url = f"https://www.youtube.com/{url}/videos"
        else:
            if not url.endswith("/videos") and not url.endswith("/shorts") and not url.endswith("/streams"):
                url = url.rstrip("/") + "/videos"
    
    # Start download in a background thread
    limit = data.get('limit')
    try:
        limit = int(limit) if limit else None
    except ValueError:
        limit = None
        
    thread = threading.Thread(target=perform_download, args=(url, quality, download_type, limit))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/api/status')
def get_status():
    return jsonify({
        'active': download_state["active"],
        'progress': download_state["progress"],
        'total': download_state["total"],
        'current_video': download_state["current_video"],
        'status': download_state["status"],
        'folder': download_state["folder"],
        'logs': download_state["logs"][-50:]  # Last 50 logs
    })

@app.route('/api/history')
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify({'history': {}})
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
        return jsonify({'history': history})
    except:
        return jsonify({'history': {}})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
