"""
Run this ONCE to log in to your Google/YouTube account:

    python authorize.py

A browser window opens. Sign in with the Google account that owns your channel
and click "Allow". A token.json file is saved so you won't have to do this again
(until it expires, when it refreshes automatically).

You need a client_secret.json file in this folder first — see docs/OAUTH-SETUP.md.
"""
from src import auth


def main():
    print("Opening your browser to log in to Google...")
    try:
        auth.get_credentials()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return
    except Exception as e:
        print(f"\n❌ Login failed: {e}")
        return
    print("\n✅ Success! You're logged in. token.json was saved.")
    print("You can now upload, schedule, and read your private analytics.")


if __name__ == "__main__":
    main()
