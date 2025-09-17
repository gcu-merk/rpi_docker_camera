#!/usr/bin/env python3
"""
Capture service for Raspberry Pi AI Camera (Redis-only).

Behavior:
 - Runs the configured capture command to save a timestamped JPEG into OUTPUT_DIR
 - Updates Redis with latest capture metadata (timestamp and host path)
 - Keeps only the latest MAX_SAVED images on disk

Configuration via environment variables:
 - OUTPUT_DIR (default: /captures)  -- path inside container
 - HOST_OUTPUT_PATH (optional) -- absolute path on the host corresponding to OUTPUT_DIR
     e.g. /mnt/storage/camera_capture/rpi_docker_camera
 - CAPTURE_CMD (default: libcamera-jpeg -o {path} -n)
 - CAPTURE_INTERVAL (seconds, default: 5)
 - MAX_SAVED (default 10)
 - REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_KEY
"""
import os
import time
import subprocess
import glob
import redis
from datetime import datetime


OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/captures")
CAPTURE_CMD = os.environ.get("CAPTURE_CMD", "libcamera-jpeg -o {path} -n")
CAPTURE_INTERVAL = float(os.environ.get("CAPTURE_INTERVAL", "5"))

# If the container's OUTPUT_DIR is a bind-mount to a host path, set this to the host path
# so Redis stores host absolute paths. Example: /mnt/storage/camera_capture/rpi_docker_camera
HOST_OUTPUT_PATH = os.environ.get("HOST_OUTPUT_PATH")

# Number of most recent images to keep on disk
MAX_SAVED = int(os.environ.get("MAX_SAVED", "10"))

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_KEY = os.environ.get("REDIS_KEY", "camera:latest")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def capture_image():
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"capture_{ts}.jpg"
    path = os.path.join(OUTPUT_DIR, filename)
    cmd = CAPTURE_CMD.format(path=path, filename=filename, timestamp=ts)
    print(f"Running capture command: {cmd}")
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Capture command failed: {e}")
        return None
    return path


def rotate_files():
    pattern = os.path.join(OUTPUT_DIR, "*.jpg")
    files = glob.glob(pattern)
    if not files:
        return
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    to_remove = files[MAX_SAVED:]
    for p in to_remove:
        try:
            os.remove(p)
            print(f"Removed old file: {p}")
        except Exception as e:
            print(f"Failed to remove {p}: {e}")


def map_to_host_path(container_path: str) -> str:
    """If HOST_OUTPUT_PATH is set, convert a container path under OUTPUT_DIR to the host absolute path.
    Otherwise return the container path.
    """
    if not HOST_OUTPUT_PATH:
        return container_path
    # Ensure OUTPUT_DIR ends with no trailing slash
    cdir = OUTPUT_DIR.rstrip('/')
    if not container_path.startswith(cdir):
        return container_path
    rel = container_path[len(cdir):]
    if rel.startswith('/'):
        rel = rel[1:]
    return os.path.join(HOST_OUTPUT_PATH, rel)


def update_redis(r, container_path):
    ts = datetime.utcnow().isoformat() + "Z"
    host_path = map_to_host_path(container_path)
    data = {"timestamp": ts, "path": host_path}
    try:
        r.hset(REDIS_KEY, mapping=data)
        r.publish("camera:updates", f"{ts} {host_path}")
        print(f"Updated redis key {REDIS_KEY}: {data}")
    except Exception as e:
        print(f"Failed to update redis: {e}")


def main():
    ensure_output_dir()
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    print("Starting capture loop. CTRL-C to stop.")
    while True:
        path = capture_image()
        if path:
            try:
                update_redis(r, path)
            except Exception as e:
                print(f"Redis error: {e}")
            rotate_files()
        time.sleep(CAPTURE_INTERVAL)


if __name__ == "__main__":
    main()
