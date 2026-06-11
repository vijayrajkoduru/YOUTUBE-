"""
The starting point of the project. Run it with:  python main.py

It shows a simple menu. Pick a number and follow the prompts.
Everything here uses YouTube's official API and is safe for your channel.
"""
import config
from src import analytics, ab_testing, seo, youtube_client


def menu():
    print("\n=== YouTube Growth Toolkit ===")
    print("1. Channel report (your stats + recent videos)")
    print("2. Generate SEO titles, description, and tags")
    print("3. Track a thumbnail/title experiment")
    print("4. See your saved experiments")
    print("5. Read comments on a video (to reply faster)")
    print("0. Quit")
    return input("\nPick a number: ").strip()


def do_channel_report():
    print("\nFetching your channel data...\n")
    print(analytics.channel_report(config.MY_CHANNEL_ID))


def do_seo():
    topic = input("What's the video about? (e.g. 'meal prep'): ").strip()
    print("\n--- Title options (pick one and tweak it) ---")
    for i, title in enumerate(seo.suggest_titles(topic), 1):
        print(f"{i}. {title}")

    print("\n--- Description ---")
    raw_points = input("List 3 things you cover, separated by commas: ").strip()
    points = [p.strip() for p in raw_points.split(",") if p.strip()]
    print("\n" + seo.build_description(topic, points))

    print("\n--- Tags (copy these into YouTube) ---")
    print(", ".join(seo.suggest_tags(topic)))


def do_add_experiment():
    video = input("Video title: ").strip()
    variant = input("Variant label (e.g. 'A' or 'B'): ").strip()
    thumb = input("Thumbnail idea: ").strip()
    hook = input("Title/hook to test: ").strip()
    ab_testing.add_variant(video, variant, thumb, hook)
    print("\nSaved. After a few days, add real numbers in code with record_result().")


def do_list_experiments():
    experiments = ab_testing.list_experiments()
    if not experiments:
        print("\nNo experiments yet. Add one with option 3.")
        return
    print("")
    for e in experiments:
        ctr = f"{e['ctr_percent']}%" if e["ctr_percent"] is not None else "pending"
        print(f"[{e['date']}] {e['video']} (variant {e['variant']}) — CTR: {ctr}")
        print(f"    Thumbnail: {e['thumbnail_idea']}")
        print(f"    Hook: {e['hook_title']}")


def do_comments():
    video_id = input("Video ID (the part after watch?v= in the URL): ").strip()
    comments = youtube_client.get_video_comments(video_id)
    if not comments:
        print("\nNo comments found (or comments are disabled).")
        return
    print("")
    for c in comments:
        print(f"♥ {c['likes']:>4}  {c['author']}: {c['text'][:100]}")


def main():
    problems = config.check_setup()
    if problems:
        print("\n⚠️  Setup not finished yet:")
        for p in problems:
            print(f"   - {p}")
        print("\nOpen the README and follow 'Step 2: Get your API key'.")
        return

    actions = {
        "1": do_channel_report,
        "2": do_seo,
        "3": do_add_experiment,
        "4": do_list_experiments,
        "5": do_comments,
    }

    while True:
        choice = menu()
        if choice == "0":
            print("Bye! Keep making videos. 🎬")
            break
        action = actions.get(choice)
        if action:
            try:
                action()
            except Exception as e:
                print(f"\nSomething went wrong: {e}")
                print("Check your internet and that your API key is valid.")
        else:
            print("That's not an option — pick a number from the menu.")


if __name__ == "__main__":
    main()
