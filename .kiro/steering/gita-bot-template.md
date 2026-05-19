# Gita Daily Bot — New Project Template

## Purpose
This is a template steering file to copy into the NEW Gita bot repository.
When you create the new repo, copy this file to `.kiro/steering/project.md` there.

---

# Gita Daily Bot — Project Context

## What this project does
Automated daily posting of Bhagavad Gita shlokas and spiritual content.
Posts to Instagram, Facebook, and YouTube automatically via GitHub Actions + cron-job.org.
One shloka per day from gita.json (700 shlokas = ~2 years of content without repeating).

## Platforms
- Instagram: @[new handle — e.g. @gitadaily.in]
- Facebook Page: [new page name]
- YouTube: [new channel name]

## Tech stack (same as StockDev.in bot)
- Python 3.11
- Pillow — image generation
- MoviePy v2 — video/reel generation
- gTTS — Hindi text-to-speech narration
- google-api-python-client — YouTube upload
- GitHub Actions — scheduling
- Cloudinary — image/video hosting
- Meta Graph API — Instagram + Facebook posting

## Reference project
This project is based on: https://github.com/RISHABHBUD/market-with-grace
Copy these files directly and adapt:
- poster.py — Cloudinary + Instagram/Facebook/Reel API (no changes needed)
- youtube_upload.py — YouTube uploader (no changes needed)
- tracker.py — duplicate tracker (no changes needed)
- requirements.txt — same dependencies

## Repository structure
```
gita-bot/
  config.py              ← PAGE_NAME="GitaDaily.in", PAGE_HANDLE="@gitadaily.in"
  poster.py              ← copy from market-with-grace (update FB_PAGE_ID)
  youtube_upload.py      ← copy from market-with-grace (no changes)
  tracker.py             ← copy from market-with-grace (no changes)
  gita.json              ← 700 shlokas with chapter, verse, sanskrit, hindi, english, lesson
  image_gen.py           ← saffron/gold spiritual theme image generator
  reel_gen.py            ← shloka reel with Sanskrit + meaning animation
  run_daily.py           ← main runner
  requirements.txt
  music/                 ← devotional/peaceful background music
  posts/                 ← output (not committed)

.github/workflows/
  post_shloka.yml        ← daily shloka post
```

## Content data structure (gita.json)
```json
[
  {
    "id": "BG_02_47",
    "chapter": 2,
    "verse": 47,
    "sanskrit": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।",
    "transliteration": "Karmanye vadhikaraste ma phaleshu kadachana",
    "hindi": "तुम्हारा अधिकार केवल कर्म करने में है, फल में कभी नहीं।",
    "english": "You have the right to perform your duties, but never to the fruits of your actions.",
    "lesson": "Focus on effort, not outcome. Do your best without attachment to results.",
    "category": "karma"
  }
]
```

## Visual theme — Spiritual/Devotional
- Background: deep saffron gradient (#1A0A00 → #3D1A00) or dark lotus (#0A0A1A → #1A0A2E)
- Accents: gold (#FFD700), saffron (#FF6B00), lotus pink (#FF69B4)
- Text: warm white (#FFF8F0)
- Decorative: lotus patterns, Om symbol, subtle mandala

## Content rotation
- day_of_year % 700 → picks today's shloka
- Chapters 1-18, verses in order
- After 700 days, restarts from beginning with updated numbers

## Content schedule (suggested)
| Content | Time IST | Days |
|---------|----------|------|
| Shloka image post | 6:00 AM | Daily |
| Shloka reel | 7:00 AM | Daily |
| "Gita says about X" reel | 8:00 PM | Weekdays |

## GitHub Secrets needed (new accounts)
| Secret | Description |
|--------|-------------|
| CLOUDINARY_CLOUD_NAME | New Cloudinary account or same |
| CLOUDINARY_API_KEY | New Cloudinary account or same |
| CLOUDINARY_API_SECRET | New Cloudinary account or same |
| INSTAGRAM_USER_ID | New Instagram account |
| INSTAGRAM_ACCESS_TOKEN | New Meta app token |
| FACEBOOK_PAGE_TOKEN | New Facebook Page token |
| YOUTUBE_CLIENT_SECRETS | New Google Cloud project |
| YOUTUBE_TOKEN_PICKLE | New YouTube channel auth |

## Setup steps (follow AUTOMATION_SETUP.md from market-with-grace repo)
1. New Gmail account
2. New Instagram Professional account
3. New Facebook Page linked to Instagram
4. New Meta Developer app with Instagram API + Pages API use cases
5. New YouTube channel on new Gmail
6. New Google Cloud project → enable YouTube Data API v3
7. New Cloudinary account (or reuse existing — 25 credits/month free)
8. New GitHub repo → add all secrets
9. Set up cron-job.org jobs pointing to new repo workflows

## Local testing
```bash
cd gita-bot
python run_daily.py --test    # generate without posting
python run_daily.py --id BG_02_47  # specific shloka
```

## How to use this steering file
When you open the new Gita bot repo in Kiro, it will automatically read
.kiro/steering/project.md and have full context about the project.
Kiro will know the architecture, tech stack, and patterns without you
needing to explain anything.
