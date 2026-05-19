# StockDev.in — Complete Automation Setup Guide

This guide documents the exact steps to set up the full automation pipeline from scratch.
Follow this if you ever need to recreate the setup on a new account or help someone else do it.

---

## What This Automation Does

| Platform | Content | Frequency |
|----------|---------|-----------|
| Instagram | Stock news image post | 8x/day (weekdays) |
| Instagram | Stock Spotlight reel | 2x/day (weekdays) |
| Instagram | Investment growth reel | 1x/day (weekdays) |
| Facebook Page | Same as Instagram (auto cross-post) | Same as above |
| YouTube Shorts | Same reels uploaded as Shorts | Same as above |
| YouTube | Daily Hindi market briefing video | 1x/day (weekdays) |

---

## Architecture Overview

```
cron-job.org (scheduler)
    → triggers GitHub Actions via API
        → Python scripts run on GitHub's servers
            → fetches news from Livemint
            → generates image/video with Pillow + MoviePy
            → uploads to Cloudinary (image) or directly (video)
            → posts to Instagram via Meta Graph API
            → posts to Facebook Page via Meta Graph API
            → uploads to YouTube via YouTube Data API v3
            → commits output files back to GitHub repo
```

---

## Part 1 — GitHub Setup

### Step 1 — Create GitHub repo
1. Go to github.com → New repository
2. Name it anything (e.g. `market-automation`)
3. Set to Public
4. Push your code to it

### Step 2 — Generate GitHub Personal Access Token
1. Go to github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Check scopes: `repo` + `workflow`
4. Copy the token — you'll need it for cron-job.org

**Important:** Regenerate this token if it expires. Update it in cron-job.org job headers.

---

## Part 2 — Cloudinary Setup (image hosting)

1. Sign up at cloudinary.com (free)
2. Go to Dashboard — note down:
   - Cloud name
   - API Key
   - API Secret
3. Add to GitHub Secrets:
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`

**Free tier:** 25 credits/month. You use less than 1 credit/month. No issues.

---

## Part 3 — Instagram + Facebook Setup (Meta Graph API)

This is the most complex part. Follow every step carefully.

### Step 1 — Instagram Professional Account
1. Open Instagram app → Profile → Settings → Account
2. Switch to Professional Account → Creator → Finance

### Step 2 — Create Facebook Page
1. Go to facebook.com/pages/create
2. Create a page with your brand name
3. Link your Instagram: Facebook Page → Settings → Linked Accounts → Instagram

### Step 3 — Create Meta Developer App
1. Go to developers.facebook.com
2. Click "My Apps" → "Create App"
3. Select "Other" → "Business"
4. Give it a name (e.g. "StockDevBot")

### Step 4 — Add Required Use Cases to App
In your app → Use Cases → Add these:
- **"Manage and publish content on Instagram"** (Instagram API)
- **"Manage everything on your Page"** (Pages API) ← CRITICAL for Facebook posting

**Without "Manage everything on your Page", you cannot post to Facebook.**

### Step 5 — Add Permissions
Go to each use case → Permissions and features → Add:
- `instagram_basic`
- `instagram_content_publish`
- `instagram_manage_comments`
- `instagram_manage_insights`
- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts` ← only available after adding Pages use case
- `business_management`

### Step 6 — Add Test User
1. App Roles → Roles → Add People
2. Select "Instagram Tester"
3. Enter your Instagram username
4. Accept the invite from Instagram app: Settings → Website Permissions → Tester Invites

### Step 7 — Get Instagram User ID
1. Go to developers.facebook.com/tools/explorer
2. Select your app
3. Query: `me/accounts` → get your Page ID
4. Query: `PAGE_ID?fields=instagram_business_account` → get Instagram User ID (long number)
5. Add to GitHub Secrets as `INSTAGRAM_USER_ID`

### Step 8 — Get Instagram Access Token (long-lived, 60 days)
1. Graph API Explorer → User or Page → "User Token"
2. Add permissions: all Instagram + pages permissions listed above
3. Click "Generate Access Token" → copy the short-lived token
4. Exchange for long-lived (60 days) — open in browser:
```
https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_TOKEN
```
5. Copy the `access_token` from response
6. Add to GitHub Secrets as `INSTAGRAM_ACCESS_TOKEN`

**Refresh every 55 days** — set a calendar reminder.

### Step 9 — Get Facebook Page Token (never expires)
1. Graph API Explorer → User or Page → select your **Facebook Page** (not User Token)
2. Add permissions: `pages_manage_posts` + `pages_read_engagement` + `pages_show_list`
3. Click "Generate Access Token" → copy the token
4. Exchange for long-lived Page token (same URL as above)
5. Add to GitHub Secrets as `FACEBOOK_PAGE_TOKEN`

**Page tokens exchanged from long-lived user tokens never expire.** No refresh needed.

---

## Part 4 — YouTube Setup

### Step 1 — Create YouTube Channel
1. Go to youtube.com → sign in with your Google account
2. Profile icon → Create a channel
3. Enter channel name

### Step 2 — Google Cloud Console
1. Go to console.cloud.google.com
2. Create new project
3. Search "YouTube Data API v3" → Enable it
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: Desktop App
6. Download the JSON → rename to `client_secrets.json`
7. Place in `stock-news-bot/` folder

### Step 3 — Add Test User
1. Left panel → Audience (or OAuth Consent Screen)
2. Add your Google account email as a test user

### Step 4 — Authorize locally (one time only)
```bash
cd stock-news-bot
pip install google-api-python-client google-auth-oauthlib
python youtube_upload.py --auth
```
This opens browser → log in → `token.pickle` is saved.

### Step 5 — Add to GitHub Secrets
```bash
# Get base64 of token.pickle
python -c "import base64; print(base64.b64encode(open('token.pickle','rb').read()).decode())"
```
Add to GitHub Secrets:
- `YOUTUBE_CLIENT_SECRETS` → full contents of `client_secrets.json`
- `YOUTUBE_TOKEN_PICKLE` → base64 string from above

**YouTube token does not expire** as long as you don't revoke it.

---

## Part 5 — cron-job.org Setup (scheduler)

Sign up at cron-job.org (free). Create one job per workflow:

### Job settings (same for all):
- Method: POST
- Headers:
  - `Authorization: Bearer YOUR_GITHUB_TOKEN`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- Body: `{"ref":"main"}`

### Jobs to create:

| Job Name | URL | Crontab | Description |
|----------|-----|---------|-------------|
| Image Posts | `.../post_to_instagram.yml/dispatches` | `0 * * * 1-5` | Every hour, weekdays |
| Stock Reels | `.../post_reel.yml/dispatches` | `30 6 * * 1-5` and `30 12 * * 1-5` | 12 PM + 6 PM IST |
| Investment Reels | `.../investment_reel.yml/dispatches` | `30 4 * * 1-5` | 10 AM IST |
| Daily Video | `.../daily_video.yml/dispatches` | `30 11 * * 1-5` | 5 PM IST |

Base URL for all: `https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/actions/workflows/`

**Note:** cron-job.org deactivates jobs on accounts inactive for 30 days. Log in once a month.

---

## Part 6 — GitHub Secrets Summary

Go to: `github.com/YOUR_REPO/settings/secrets/actions`

| Secret Name | What it is | Expires |
|-------------|-----------|---------|
| `CLOUDINARY_CLOUD_NAME` | Cloudinary dashboard | Never |
| `CLOUDINARY_API_KEY` | Cloudinary dashboard | Never |
| `CLOUDINARY_API_SECRET` | Cloudinary dashboard | Never |
| `INSTAGRAM_USER_ID` | From Graph API Explorer | Never |
| `INSTAGRAM_ACCESS_TOKEN` | Long-lived user token | 60 days |
| `FACEBOOK_PAGE_TOKEN` | Long-lived page token | Never |
| `YOUTUBE_CLIENT_SECRETS` | Google Cloud OAuth JSON | Never |
| `YOUTUBE_TOKEN_PICKLE` | Base64 of token.pickle | Never* |

*YouTube token stays valid unless revoked manually.

---

## Maintenance Schedule

| Task | Frequency | Time needed |
|------|-----------|-------------|
| Refresh `INSTAGRAM_ACCESS_TOKEN` | Every 55 days | 5 minutes |
| Log in to cron-job.org | Monthly | 1 minute |
| Check GitHub Actions logs | Weekly | 2 minutes |
| Clean up old posts/ folder | Every 3 months | 5 minutes |

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Session has expired` | Instagram token expired | Regenerate token, update secret |
| `Cannot parse access token` | Wrong token type | Make sure it's `EAA...` not `IGAAN...` |
| `pages_manage_posts required` | Missing Pages use case | Add "Manage everything on your Page" use case in Meta app |
| `me/accounts returns []` | Missing `business_management` permission | Add it to token permissions |
| `Not allowed to publish to timelines` | Using User token for Facebook | Use Page token (`FACEBOOK_PAGE_TOKEN`) |
| `youtubeSignupRequired` | No YouTube channel created | Create channel at youtube.com |
| `No module named X` | Missing Python package | Add to requirements.txt |
| GitHub Actions cron not triggering | GitHub deprioritises inactive repos | Use cron-job.org instead |

---

## Free Tier Limits

| Service | Free Limit | Monthly Usage |
|---------|-----------|---------------|
| GitHub Actions | 2,000 min/month | ~600 min |
| Cloudinary | 25 credits/month | ~1 credit |
| Meta Graph API | 25 posts/day | 11 posts/day |
| YouTube Data API | 10,000 units/day | ~100 units/day |
| cron-job.org | Unlimited jobs | 4 jobs |
