import os
import subprocess

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".ts", ".vob", ".iso", ".img", ".m2ts", ".dv",
    ".divx", ".3gp", ".3g2", ".ogv", ".ogm",
}


def scan_videos(root_path):
    videos = []
    for dirpath, _, filenames in os.walk(root_path):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                full_path = os.path.join(dirpath, fname)
                videos.append(full_path)
    return sorted(videos)


def get_video_duration(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0
