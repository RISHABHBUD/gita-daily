# StockDev.in — Automated Content Bot

## What this project does
Fully automated social media content pipeline for Indian stock market content.
Posts to Instagram, Facebook, and YouTube automatically via GitHub Actions + cron-job.org.

## Platforms
- Instagram: @stockdev.in
- Facebook Page: Prettysmartmoney (Page ID: 1158981393954289)
- YouTube: StockDev.in channel

## Tech stack
- Python 3.11
- Pillow — image generation
- MoviePy v2 — video/reel generation
- yfinance — stock market data
- matplotlib — charts
- gTTS — Hindi text-to-speech for daily video
- requests + beautifulsoup4 — Livemint news scraping
- google-api-python-client — YouTube upload
- GitHub Actions — scheduling and execution
- Cloudinary — image/video hosting (free tier)
- Meta Graph API — Instagram + Facebook posting

## Repository structure
```
stock-news-bot/          ← all Python code lives here
  config.py              ← branding: PAGE_NAME, PAGE_HANDLE, hashtags, colors
  fetcher.py             ← scrapes Livemint stock market news
  composer.py            ← builds Instagram captions
  tracker.py             ← posted.json manager (avoids duplicate posts)
  poster.py              ← Cloudinary upload + Instagram/Facebook/Reel API
  image_gen.py           ← 1080x1080 Instagram image post generator
  reel_gen.py            ← Stock Spotlight + Market Pulse reel generator
  investment_reel.py     ← Investment history reel (Rs 1 lakh growth chart)
  facts_reel.py          ← Stock market facts reel (100 facts rotation)
  run_auto.py            ← runner: image post
  run_reel.py            ← runner: stock spotlight reel (--test flag)
  run_investment_reel.py ← runner: investment reel
  run_facts_reel.py      ← runner: facts reel (--test, --id flags)
  run_daily_video.py     ← runner: daily Hindi YouTube video
  youtube_upload.py      ← YouTube Data API v3 uploader
  nifty500.py            ← 100 Nifty stocks for investment reel rotation
  facts.json             ← 100 stock market facts (20 categories)
  posted.json            ← tracks posted articles to avoid duplicates
  requirements.txt       ← single unified requirements file
  music/                 ← royalty-free MP3 tracks for reels
  daily_video/           ← daily video modules (data_fetch, script_gen, audio_gen, video_gen)
  posts/                 ← output folder (auto-generated, not committed except captions)

.github/workflows/
  post_to_instagram.yml  ← image posts (triggered by cron-job.org)
  post_reel.yml          ← stock spotlight reel
  investment_reel.yml    ← investment history reel
  facts_reel.yml         ← facts reel
  daily_video.yml        ← daily Hindi YouTube video
```

## Content schedule (via cron-job.org)
| Content | Time IST | Days | Workflow |
|---------|----------|------|---------|
| Image post | Every 4 hours | Daily | post_to_instagram.yml |
| Investment reel | 10:00 AM | Weekdays | investment_reel.yml |
| Market summary reel | 12:00 PM | Weekdays | post_reel.yml |
| Facts reel | 6:00 PM | Weekdays | facts_reel.yml |
| Daily Hindi video | 5:00 PM | Weekdays | daily_video.yml |

## GitHub Secrets required
| Secret | Description | Expires |
|--------|-------------|---------|
| CLOUDINARY_CLOUD_NAME | dkeqa5otl | Never |
| CLOUDINARY_API_KEY | Cloudinary dashboard | Never |
| CLOUDINARY_API_SECRET | Cloudinary dashboard | Never |
| INSTAGRAM_USER_ID | 17841432871141691 | Never |
| INSTAGRAM_ACCESS_TOKEN | Long-lived user token (EAA...) | 60 days — refresh every 55 days |
| FACEBOOK_PAGE_TOKEN | Page token (never expires) | Never |
| YOUTUBE_CLIENT_SECRETS | Full JSON from Google Cloud | Never |
| YOUTUBE_TOKEN_PICKLE | Base64 of token.pickle | Never |

## Visual theme — Cinematic midnight/neon
- Background: deep navy (#09081E → #160C34)
- Accents: cyan (#20E0FF), violet (#9A6AFF), gold (#FFD25C)
- Performance: green (#00F392), red (#FF507A)
- All content uses same palette for brand consistency

## Key patterns
- Stock detection: yf.Search() dynamic lookup — covers all 5000+ NSE/BSE stocks
- Fact rotation: day_of_year % len(facts) — deterministic daily rotation
- Investment reel: fetches historical data from yfinance, calculates Rs 1 lakh growth
- Video compression: preset="medium", crf=28 — keeps files under 50MB
- Crossfade transitions: 0.4s blend between clips in facts_reel.py

## Token refresh reminder
INSTAGRAM_ACCESS_TOKEN expires every 60 days. Refresh process:
1. Graph API Explorer → generate new EAA... token with all permissions
2. Exchange for long-lived: graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&...
3. Update GitHub Secret INSTAGRAM_ACCESS_TOKEN

## Local testing
```bash
cd stock-news-bot
python run_reel.py --test           # stock reel, no posting
python run_facts_reel.py --test     # facts reel, no posting
python run_facts_reel.py --test --id fact_042  # specific fact
python run_investment_reel.py       # investment reel (posts to all platforms)
```
