# SF Daily Tips — Automated Salesforce Instagram Account

Posts a fresh Salesforce developer tip **3x/day** as a swipe carousel
(3 slides: Problem, Solution, Engagement) — fully automated. Every tip is
generated fresh by the Claude API, so there's no content list to run out of
and nothing to write manually.

Carousel is the default because code content needs reading time (people swipe
at their own pace and SAVE tips to reference later). A Reel workflow is also
included for manual use when you want a reach boost on a specific tip.

Handle: @sf_daily_tips

---

## How it works

Each scheduled run:
1. `generate_tip.py` calls the Claude API for ONE fresh tip in the next
   rotation category, avoiding recent topics.
2. `generate_card.py` renders 3 slides: Problem, Solution, Engagement
   (Salesforce-style: blue cloud branding, raised 3D card, dark code blocks).
3. GitHub Actions commits the slides, then `post_to_instagram.py` publishes
   them as a 3-image swipe carousel.
   (For a Reel instead: trigger the "Salesforce Reel (manual)" workflow from
   the Actions tab — it builds an animated MP4 with your music via
   `make_reel.py` and posts via `post_reel_to_instagram.py`.)

## Content rotation (no repeats)
- Categories cycle: **Apex -> SOQL -> OmniStudio -> LWC -> Flow** -> repeat,
  continuously (never resets), so categories stay evenly spread across the
  3 daily posts.
- The last 200 tip titles are remembered and passed to the model each run with
  a "don't repeat these" instruction, preventing topic repeats (~2 months of
  history at 3 posts/day).

## Schedule
3 posts/day at 09:30 AM, 02:00 PM, 07:00 PM IST (`.github/workflows/daily_post.yml`).
Adjust the cron lines to change times.

---

## One-time setup

### 1. Anthropic API key
console.anthropic.com -> Settings -> API Keys -> Create Key (starts sk-ant-...).
Cost is tiny — a few cents/month at 3 posts/day using Claude Haiku.

### 2. Instagram + Meta app
Same as any IG automation: professional/Creator account, linked Facebook Page,
Meta Developer App with Instagram Graph API, long-lived token + IG User ID.

### 3. GitHub
Public repo. Add secrets under Settings -> Secrets and variables -> Actions:
- ANTHROPIC_API_KEY
- IG_USER_ID
- IG_ACCESS_TOKEN

### 4. Music
`assets/music.mp3` is already included. Swap it for any royalty-free track if
you like (see assets/README.md for sources).

---

## Assets you can upload now
- `output/profile_picture.png` — profile photo (cloud + SF Daily wordmark)

## Local testing
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
cd scripts
python daily_post.py                 # generate one tip + 3 cards + reel
python generate_card.py --id 1       # re-render a specific sample tip
python make_profile_pic.py           # regenerate the profile picture
```

## Token expiry
The Instagram long-lived token expires ~60 days; refresh it before then.
