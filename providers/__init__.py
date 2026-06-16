"""Provider stubs for content generation and publishing.

Every provider degrades gracefully: in DRY_RUN or when a key is missing it
returns mock data / "not sent" status and NEVER raises (except Veo's hard
cost guard, which is intentional).
"""
