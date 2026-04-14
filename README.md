# YouTube Bulk Downloader - Web Frontend

A modern web-based interface for bulk downloading YouTube playlists and channels.

## Features

- 📥 Download entire YouTube playlists or channels
- 🎬 Multiple quality options (1080p, 720p, 480p)
- ⚙️ 3-threaded parallel downloads for speed
- 📊 Real-time progress tracking
- 📝 Live logs and download history
- 🔄 Resume incomplete downloads
- 🎨 Dark theme UI with modern design

## Prerequisites

- Python 3.7+
- yt-dlp (for downloading videos)
- ffmpeg (for video processing)

## Installation

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg python3-pip
```

**macOS:**
```bash
brew install ffmpeg python3
```

**Windows:**
Download and install from:
- FFmpeg: https://ffmpeg.org/download.html
- Python: https://www.python.org/downloads/

### 2. Install yt-dlp

```bash
pip install yt-dlp
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Start the Web Server

```bash
python app.py
```

The server will start at `http://localhost:5000`

### Using the Web Interface

1. **Select Download Type**: Choose between "Playlist" or "Channel"
2. **Enter URL or Handle**: 
   - For playlists: Paste the full YouTube playlist URL
   - For channels: Paste the URL or just the handle (e.g., @mkbhd)
3. **Select Quality**: Choose your preferred video quality
4. **Click Start Download**: The download will begin in the background

### Features

- **Real-time Progress**: Watch the download progress update in real-time
- **Live Logs**: See exactly what's happening during download
- **Resume Downloads**: If interrupted, the downloader will resume from the last video
- **Download History**: Quick access to previously downloaded playlists/channels

## File Structure

```
youtube_bulk_downloader/
├── app.py                          # Flask backend application
├── utube_playlist_downloader.py    # Original downloader script
├── requirements.txt                # Python dependencies
├── download_history.json           # Download history (auto-created)
├── templates/
│   └── index.html                  # Web interface
└── static/
    ├── css/
    │   └── style.css               # Styling
    └── js/
        └── main.js                 # Frontend logic
```

## Configuration

Edit these values in `app.py` to customize:

- `BASE_DOWNLOAD_PATH`: Where downloaded videos are saved (default: `/home/s/Videos/YoutubeDownloads`)
- `HISTORY_FILE`: Where download history is stored (default: `download_history.json`)
- Download threads: Change `max_workers=3` in the `download_videos()` function

## API Endpoints

- `GET /` - Serve the web interface
- `POST /api/download` - Start a new download
- `GET /api/status` - Get current download status
- `GET /api/history` - Get download history

## Troubleshooting

### "yt-dlp not found" error
```bash
pip install --upgrade yt-dlp
```

### "FFmpeg not found" error
Make sure FFmpeg is installed and in your system PATH

### Videos not downloading
- Check internet connection
- Verify the URL is correct
- Make sure the playlist/channel is public
- Try with a different quality setting

## Advanced Usage

### Accessing from Other Devices

To access the web interface from other machines on your network:

1. Find your machine's IP address:
   - Linux/Mac: `ifconfig | grep inet`
   - Windows: `ipconfig`

2. Modify `app.py` line at the bottom:
   ```python
   app.run(debug=True, port=5000, host='0.0.0.0')
   ```

3. Access from another device: `http://YOUR_IP:5000`

### Running in Background

**Linux/Mac:**
```bash
nohup python app.py > downloader.log 2>&1 &
```

**Windows (PowerShell):**
```powershell
Start-Process python -ArgumentList "app.py" -WindowStyle Hidden
```

## Performance Tips

- **Parallel Threads**: Increase `max_workers` for faster downloads (use 5-6 for good balance)
- **Quality**: 480p downloads much faster than 1080p
- **Disk Space**: Ensure you have enough space for your downloads

## License

This tool uses yt-dlp which is licensed under the Unlicense.

## Support

For issues with yt-dlp, visit: https://github.com/yt-dlp/yt-dlp
