# One-Time Login Setup (OAuth)

The Analytics, Upload, and Queue features act on YOUR OWN channel, so Google
makes you log in and approve access. You do this **once**. After that, a saved
token keeps you logged in (and refreshes itself).

## Step 1 — Turn on the APIs
In the [Google Cloud Console](https://console.cloud.google.com/), in your project:
1. **APIs & Services → Enable APIs**, enable **YouTube Data API v3**.
2. Also enable **YouTube Analytics API**.

## Step 2 — Set up the consent screen
1. **APIs & Services → OAuth consent screen**.
2. Choose **External**, fill in the app name and your email.
3. Under **Test users**, add your own Google email (the one that owns the channel).
   (While the app is in "testing", only test users can log in — that's fine for you.)

## Step 3 — Create OAuth credentials
1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Create it, then **Download JSON**.
4. Rename the downloaded file to **`client_secret.json`** and put it in the
   project's top folder (next to `authorize.py`).

> 🔒 `client_secret.json` and the `token.json` it creates are secrets.
> `.gitignore` already blocks both — never commit them.

## Step 4 — Log in
In the terminal, in the project folder:
```bash
python authorize.py
```
A browser opens. Sign in with your channel's Google account and click **Allow**
(you may see an "unverified app" warning because it's your own test app —
click Advanced → continue). A `token.json` file is saved.

## Done
Now the Analytics, Upload, and Queue pages work — in the website
(`python web/app.py`) and the terminal menu (`python main.py`).

## What each permission is for
- **youtube.upload** — upload your video files.
- **youtube** — change a video's status (publish it).
- **youtube.readonly** — list your own videos for the review queue.
- **yt-analytics.readonly** — read your private watch-time/retention stats.

Nothing here can touch other people's channels or post without your approval.
