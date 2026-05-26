"""
Gita Daily Bot — Main Runner

Usage:
  python run_daily.py           # today's shloka, posts to all platforms
  python run_daily.py --test    # generate locally, no posting
  python run_daily.py --id BG_02_47  # specific shloka by ID
  python run_daily.py --day 42  # specific day number
  python run_daily.py --test --fast-preview --reel-only --id BG_02_47  # quick low-res preview
"""

import os, sys, json, argparse
from datetime import datetime

from config import OUTPUT_FOLDER, POSTED_FILE

GITA_FILE = "gita_data.json"


CHAPTER_TITLES = {
    1:"Arjuna Vishada Yoga", 2:"Sankhya Yoga", 3:"Karma Yoga",
    4:"Jnana Karma Sanyasa Yoga", 5:"Karma Sanyasa Yoga",
    6:"Atma Samyama Yoga", 7:"Jnana Vijnana Yoga",
    8:"Aksara Brahma Yoga", 9:"Raja Vidya Yoga",
    10:"Vibhuti Yoga", 11:"Vishwarupa Darshana Yoga",
    12:"Bhakti Yoga", 13:"Kshetra Kshetrajna Yoga",
    14:"Gunatraya Vibhaga Yoga", 15:"Purushottama Yoga",
    16:"Daivasura Sampad Yoga", 17:"Shraddhatraya Yoga",
    18:"Moksha Sanyasa Yoga",
}


def load_shlokas():
    path = os.path.join(os.path.dirname(__file__), GITA_FILE)
    with open(path, encoding="utf-8") as f:
        shlokas = json.load(f)
    for s in shlokas:
        if not s.get("chapter_name"):
            s["chapter_name"] = CHAPTER_TITLES.get(s["chapter"], "")
    return shlokas


def get_next_shloka(shlokas, advance=True):
    """
    Sequential rotation via posted.json.
    Picks the next unposted shloka in order.
    posted.json stores: {"last_index": N}
    """
    tracker_path = os.path.join(os.path.dirname(__file__), POSTED_FILE)
    if os.path.exists(tracker_path):
        with open(tracker_path, encoding="utf-8") as f:
            data = json.load(f)
        last = data.get("last_index", -1)
    else:
        last = -1

    next_idx = (last + 1) % len(shlokas)
    return shlokas[next_idx], next_idx + 1, next_idx


def save_posted_index(index):
    """Save the index of the shloka just posted."""
    tracker_path = os.path.join(os.path.dirname(__file__), POSTED_FILE)
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump({"last_index": index}, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                        help="Generate locally without posting")
    parser.add_argument("--reel-only", action="store_true",
                        help="Generate reel only, skip image post")
    parser.add_argument("--id", type=str, default=None,
                        help="Specific shloka ID e.g. BG_02_47")
    parser.add_argument("--day", type=int, default=None,
                        help="Specific day number (1-700)")
    parser.add_argument("--fast-preview", action="store_true",
                        help="With --test: faster reel (540x960 @ 16fps). Ignored without --test.")
    parser.add_argument("--image-only", action="store_true",
                        help="Generate and post image only, skip reel")
    args = parser.parse_args()

    if args.fast_preview and not args.test:
        print("  [!] --fast-preview only works with --test (ignored).")
        args.fast_preview = False

    print(f"\n🕉️  Gita Daily Bot — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if args.test:
        print("  [TEST MODE] — will NOT post to any platform")
    if args.test and args.fast_preview:
        print("  [FAST PREVIEW] — reel at 540x960 / 16fps for quicker local iteration")
    print("=" * 60)

    shlokas = load_shlokas()

    # Pick shloka
    if args.id:
        shloka = next((s for s in shlokas if s["id"] == args.id), None)
        if not shloka:
            print(f"  [!] ID '{args.id}' not found.")
            sys.exit(1)
        raw_index = next(i for i, s in enumerate(shlokas) if s["id"] == args.id)
        day_number = raw_index + 1
        print(f"\n[1/4] Using shloka: {args.id}")
    elif args.day:
        raw_index = (args.day - 1) % len(shlokas)
        shloka = shlokas[raw_index]
        day_number = args.day
        print(f"\n[1/4] Day {day_number}: BG {shloka['chapter']}.{shloka['verse']}")
    else:
        shloka, day_number, raw_index = get_next_shloka(shlokas, advance=True)
        print(f"\n[1/4] Next in sequence — Day {day_number} of {len(shlokas)}: BG {shloka['chapter']}.{shloka['verse']}")

    print(f"  {shloka.get('chapter_name', '')} | {shloka['category']}")

    # Output folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir   = os.path.join(OUTPUT_FOLDER, timestamp)
    os.makedirs(out_dir, exist_ok=True)

    # Generate image
    if not args.reel_only:
        print("\n[2/4] Generating image post...")
        from image_gen import create_post_image
        image_path = os.path.join(out_dir, "post.jpg")
        create_post_image(shloka, image_path, day_number)
    else:
        image_path = None
        print("\n[2/4] Skipping image (--reel-only)")

    # Generate reel
    if not args.image_only:
        print("\n[3/4] Generating reel...")
        from reel_gen import create_shloka_reel
        reel_path = os.path.join(out_dir, "reel.mp4")
        create_shloka_reel(
            shloka,
            reel_path,
            day_number,
            fast_preview=bool(args.test and args.fast_preview),
        )
    else:
        reel_path = None
        print("\n[3/4] Skipping reel (--image-only)")

    # Build caption
    caption = build_caption(shloka, day_number)
    caption_path = os.path.join(out_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)
    print(f"  [✓] Caption saved")

    if args.test:
        print(f"\n✅ Test complete! Files saved in: {out_dir}")
        print(f"   Image: {image_path}")
        print(f"   Reel:  {reel_path}")
        print(f"   Caption: {caption_path}\n")
        return

    # Post to platforms
    print("\n[4/4] Posting to platforms...")
    if args.image_only:
        _post_image(image_path, caption)
    elif args.reel_only:
        _post_reel(reel_path, caption, shloka, day_number)
    else:
        _post_all(image_path, reel_path, caption, shloka, day_number)

    # Save progress after successful reel post
    # --reel-only is the main daily workflow, so it owns the index advance
    if not args.test and not args.id and not args.day:
        save_posted_index(raw_index)
        print(f"  [✓] Progress saved (Day {day_number} posted)")

    print(f"\n✅ Done! Saved in: {out_dir}\n")


def build_caption(shloka, day_number):
    from config import HASHTAGS, PAGE_HANDLE
    ch = shloka["chapter"]
    v  = shloka["verse"]
    total = 700

    caption = f"""🕉️ Bhagavad Gita | Chapter {ch}, Verse {v}
📅 Day {day_number} of {total} — One shloka a day, every day.

✨ "{shloka.get('english_explanation', '')}"

💡 Life Lesson:
{shloka.get('life_lesson_english', '')}

🌸 In Hindi:
{shloka.get('life_lesson_hindi', '')}

{"─" * 28}
🙏 Follow {PAGE_HANDLE} for daily Gita wisdom
📖 700 shlokas · 700 days · One timeless truth

{" ".join(HASHTAGS[:15])}"""
    return caption


def _post_image(image_path, caption):
    """Post image to Instagram + Facebook."""
    from uploader.poster import (upload_image_to_cloudinary,
                                  post_to_instagram, post_image_to_facebook)
    print("  Uploading image to Cloudinary...")
    img_url = upload_image_to_cloudinary(image_path)

    print("  Posting image to Instagram...")
    post_to_instagram(img_url, caption)

    print("  Posting image to Facebook...")
    try:
        post_image_to_facebook(img_url, caption)
    except Exception as e:
        print(f"  [!] FB image failed (non-fatal): {e}")


def _post_reel(reel_path, caption, shloka, day_number):
    """Post reel to Instagram, Facebook, and YouTube."""
    from uploader.poster import (upload_video_to_cloudinary,
                                  post_reel_to_instagram, post_video_to_facebook)
    from uploader.youtube_upload import upload_to_youtube

    print("  Uploading reel to Cloudinary...")
    vid_url = upload_video_to_cloudinary(reel_path)

    print("  Posting reel to Instagram...")
    post_reel_to_instagram(vid_url, caption)

    print("  Posting reel to Facebook...")
    try:
        title = (f"BG {shloka['chapter']}.{shloka['verse']} | "
                 f"Day {day_number} | GitaDaily")
        post_video_to_facebook(reel_path, caption, title=title)
    except Exception as e:
        print(f"  [!] FB reel failed (non-fatal): {e}")

    print("  Uploading to YouTube...")
    try:
        yt_title = (f"Bhagavad Gita Ch{shloka['chapter']} V{shloka['verse']} | "
                    f"Day {day_number} | {shloka.get('chapter_name', '')} #Shorts")
        upload_to_youtube(reel_path, yt_title, caption)
    except FileNotFoundError:
        print("  [!] YouTube credentials not found — skipping")
    except Exception as e:
        print(f"  [!] YouTube failed (non-fatal): {e}")


def _post_all(image_path, reel_path, caption, shloka, day_number):
    """Post both image and reel to all platforms."""
    _post_image(image_path, caption)
    _post_reel(reel_path, caption, shloka, day_number)


if __name__ == "__main__":
    main()
