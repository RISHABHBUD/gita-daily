"""
platform/poster.py — Cloudinary + Instagram + Facebook uploader
Reusable across any bot project. Only change FB_PAGE_ID per project.

Functions:
  upload_image_to_cloudinary(image_path)  → public URL
  upload_video_to_cloudinary(video_path)  → public URL
  post_to_instagram(image_url, caption)
  post_reel_to_instagram(video_url, caption)
  post_image_to_facebook(image_url, caption)
  post_video_to_facebook(video_path, caption, title="")

Secrets required (GitHub / environment):
  CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
  INSTAGRAM_USER_ID, INSTAGRAM_ACCESS_TOKEN
  FACEBOOK_PAGE_TOKEN  (falls back to INSTAGRAM_ACCESS_TOKEN if missing)
"""

import os
import time
import hashlib
import requests

# ── UPDATE THIS per project ────────────────────────────────────
# Get your Page ID from: Graph API Explorer → me/accounts
FB_PAGE_ID = "YOUR_FACEBOOK_PAGE_ID"
# ──────────────────────────────────────────────────────────────


# ── Cloudinary ─────────────────────────────────────────────────

def _cloudinary_upload(file_path, resource_type, filename):
    """Generic signed upload to Cloudinary."""
    cloud_name = os.environ["CLOUDINARY_CLOUD_NAME"]
    api_key    = os.environ["CLOUDINARY_API_KEY"]
    api_secret = os.environ["CLOUDINARY_API_SECRET"]

    timestamp = str(int(time.time()))
    sig_str   = f"timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(sig_str.encode("utf-8")).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"

    with open(file_path, "rb") as f:
        resp = requests.post(
            url,
            files={"file": (filename, f)},
            data={"api_key": api_key, "timestamp": timestamp, "signature": signature},
        )

    print(f"  Cloudinary [{resource_type}] status: {resp.status_code}")
    print(f"  Cloudinary response: {resp.text[:300]}")
    resp.raise_for_status()

    secure_url = resp.json()["secure_url"]
    print(f"  [✓] Cloudinary URL: {secure_url}")
    return secure_url


def upload_image_to_cloudinary(image_path):
    """Upload a JPEG/PNG image and return its public URL."""
    return _cloudinary_upload(image_path, "image", "post.jpg")


def upload_video_to_cloudinary(video_path):
    """Upload an MP4 video and return its public URL."""
    return _cloudinary_upload(video_path, "video", "reel.mp4")


# ── Instagram ──────────────────────────────────────────────────

def post_to_instagram(image_url, caption):
    """Publish a single image post to Instagram via Graph API."""
    ig_user_id   = os.environ["INSTAGRAM_USER_ID"]
    access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    base         = f"https://graph.facebook.com/v19.0/{ig_user_id}"

    # Step 1: Create media container
    resp = requests.post(f"{base}/media", data={
        "image_url":    image_url,
        "caption":      caption,
        "access_token": access_token,
    })
    print(f"  IG container status: {resp.status_code}", flush=True)
    print(f"  IG container response: {resp.text}", flush=True)
    if not resp.ok:
        raise Exception(f"Instagram media creation failed: {resp.text}")
    container_id = resp.json()["id"]
    print(f"  [✓] Container created: {container_id}")

    # Step 2: Wait for processing, then publish
    time.sleep(8)
    resp = requests.post(f"{base}/media_publish", data={
        "creation_id":  container_id,
        "access_token": access_token,
    })
    print(f"  IG publish status: {resp.status_code}")
    resp.raise_for_status()
    post_id = resp.json()["id"]
    print(f"  [✓] Published to Instagram! Post ID: {post_id}")
    return post_id


def post_reel_to_instagram(video_url, caption):
    """Publish a Reel to Instagram via Graph API (with processing poll)."""
    ig_user_id   = os.environ["INSTAGRAM_USER_ID"]
    access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    base         = f"https://graph.facebook.com/v19.0/{ig_user_id}"

    # Step 1: Create reel container
    resp = requests.post(f"{base}/media", data={
        "media_type":    "REELS",
        "video_url":     video_url,
        "caption":       caption,
        "share_to_feed": "true",
        "access_token":  access_token,
    })
    print(f"  Reel container status: {resp.status_code}", flush=True)
    print(f"  Reel container response: {resp.text}", flush=True)
    if not resp.ok:
        raise Exception(f"Reel container creation failed: {resp.text}")
    container_id = resp.json()["id"]
    print(f"  [✓] Reel container created: {container_id}")

    # Step 2: Poll until video processing is done (up to 4 min)
    print("  Waiting for video to process...")
    for attempt in range(24):
        time.sleep(10)
        status_resp = requests.get(
            f"https://graph.facebook.com/v19.0/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
        )
        status_code = status_resp.json().get("status_code", "")
        print(f"  Status check {attempt + 1}: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise Exception(f"Instagram video processing failed: {status_resp.json()}")
    else:
        print("  [!] Timed out — attempting publish anyway")

    # Step 3: Publish
    resp = requests.post(f"{base}/media_publish", data={
        "creation_id":  container_id,
        "access_token": access_token,
    })
    print(f"  Reel publish status: {resp.status_code}", flush=True)
    if not resp.ok:
        raise Exception(f"Reel publish failed: {resp.text}")
    post_id = resp.json()["id"]
    print(f"  [✓] Reel published! Post ID: {post_id}")
    return post_id


# ── Facebook ───────────────────────────────────────────────────

def _get_page_token():
    """Page token (never expires). Falls back to user token if not set."""
    return os.environ.get("FACEBOOK_PAGE_TOKEN") or os.environ["INSTAGRAM_ACCESS_TOKEN"]


def post_image_to_facebook(image_url, caption):
    """Post an image to the Facebook Page."""
    resp = requests.post(
        f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
        data={"url": image_url, "caption": caption, "access_token": _get_page_token()},
    )
    print(f"  FB image status: {resp.status_code}", flush=True)
    if not resp.ok:
        print(f"  FB image error: {resp.text}")
        return None
    post_id = resp.json().get("post_id") or resp.json().get("id")
    print(f"  [✓] Posted to Facebook! Post ID: {post_id}")
    return post_id


def post_video_to_facebook(video_path, caption, title=""):
    """Upload and post a video directly to the Facebook Page."""
    print("  Uploading video to Facebook...")
    with open(video_path, "rb") as f:
        resp = requests.post(
            f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos",
            files={"source": ("video.mp4", f, "video/mp4")},
            data={
                "description":  caption,
                "title":        title or caption[:80],
                "access_token": _get_page_token(),
            },
        )
    print(f"  FB video status: {resp.status_code}", flush=True)
    if not resp.ok:
        print(f"  FB video error: {resp.text}")
        return None
    post_id = resp.json().get("id")
    print(f"  [✓] Posted to Facebook! Video ID: {post_id}")
    return post_id
