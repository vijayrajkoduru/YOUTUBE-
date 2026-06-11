# How to Open the Website on Your iPad

Your iPad can't *run* the website (that needs Python, which iPads don't have),
but it CAN open it once the site is hosted online. You'll put the site on a
free hosting service, get a web address, and open that address in Safari.

Everything below can be done **entirely from your iPad** — no computer needed.
You only do this setup once. After that you just open the link.

---

## The easiest path: Render.com (free)

This project already includes a `render.yaml` file that tells Render what to do,
so this is mostly clicking buttons.

### Step 1 — Make sure your code is on GitHub
It already is, on this branch. (If you want, merge it into `main` first — ask
me and I'll open a pull request.)

### Step 2 — Create a free Render account
1. In Safari on your iPad, go to **https://render.com**.
2. Tap **Get Started** and sign up with your GitHub account (easiest, so it can
   see your repo).

### Step 3 — Connect this repository
1. In the Render dashboard, tap **New +** → **Web Service**.
2. Choose **Build and deploy from a Git repository**.
3. Pick your repo: **vijayrajkoduru/YOUTUBE-**.
4. Render reads `render.yaml` automatically. Confirm:
   - Runtime: **Python**
   - Start command: **gunicorn web.app:app**
   - Plan: **Free**
5. Tap **Create Web Service**.

### Step 4 — Wait, then open it
1. Render installs everything and starts the site (takes a few minutes).
2. When it says **Live**, you'll see a web address like
   `https://youtube-growth-toolkit.onrender.com`.
3. Tap it — that opens YOUR website, in Safari, on your iPad. 🎉
4. Bookmark it / add to Home Screen so it's one tap next time.

### Step 5 (optional) — Turn on the Channel Report + Comments pages
The SEO Generator and A/B Tracker work right away. The Channel Report and
Comments pages need your YouTube API key:
1. In Render, open your service → **Environment** tab.
2. Add two variables:
   - `YOUTUBE_API_KEY` = your key (see main README, "Step 2")
   - `MY_CHANNEL_ID` = your channel ID (starts with `UC...`)
3. Save. Render restarts the site and those pages start working.

---

## Good to know

- **Free plan sleeps.** On Render's free plan the site "sleeps" after a while
  with no visitors, so the first visit after a quiet period takes ~30 seconds to
  wake up. That's normal.
- **Other hosts work too.** Railway.app and PythonAnywhere are similar. The
  included `Procfile` works for most Python hosts.
- **Your secrets stay safe.** You enter your API key in the host's dashboard,
  never in the code. The `.gitignore` keeps `.env` off GitHub.

---

## Want me to do more of this for you?
I can't create your Render account (that needs your login), but I can:
- Open a pull request to merge this into `main` so it's your live code.
- Adjust any settings or add a custom home-screen icon/title.
Just ask.
