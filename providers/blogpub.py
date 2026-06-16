"""Blog publishing: WordPress (canonical) + Dev.to + Hashnode.

publish_blog() publishes to each requested target independently with its own
try/except so one failure never blocks the others. WordPress is the canonical
home; Dev.to and Hashnode get canonical_url set to the WP URL when available.

In DRY_RUN or when a target's creds are missing, that target returns
"DRY_RUN (not sent)". This function NEVER raises.
"""
import base64

import requests

import config

DEVTO_ENDPOINT = "https://dev.to/api/articles"
HASHNODE_ENDPOINT = "https://gql.hashnode.com/"


def _wp_configured():
    return bool(
        config.WORDPRESS_URL
        and config.WORDPRESS_USER
        and config.WORDPRESS_APP_PASSWORD
    )


def _publish_wordpress(title, html, tags):
    """Publish to WordPress via REST + Application Password basic auth.

    Returns the published post URL (string) on success.
    """
    token = base64.b64encode(
        f"{config.WORDPRESS_USER}:{config.WORDPRESS_APP_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "content": html,
        "status": "publish",
    }
    # TODO(next-phase): resolve tag names -> tag IDs via /wp/v2/tags before
    # attaching; WP expects integer term IDs, not strings.
    url = f"{config.WORDPRESS_URL}/wp-json/wp/v2/posts"
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("link") or f"{config.WORDPRESS_URL}/?p={data.get('id', '')}"


def _publish_devto(title, html, tags, canonical_url):
    """Publish to Dev.to via the articles API. Returns the article URL."""
    headers = {
        "api-key": config.DEVTO_API_KEY,
        "Content-Type": "application/json",
    }
    article = {
        "title": title,
        "published": True,
        "body_markdown": html,  # Dev.to also accepts HTML inside markdown
        "tags": [t.replace("-", "")[:20] for t in (tags or [])][:4],
    }
    if canonical_url:
        article["canonical_url"] = canonical_url
    # TODO(next-phase): Dev.to prefers markdown; convert HTML->markdown for
    # cleaner rendering instead of passing raw HTML.
    resp = requests.post(
        DEVTO_ENDPOINT, headers=headers, json={"article": article}, timeout=60
    )
    resp.raise_for_status()
    return resp.json().get("url", "posted")


def _hashnode_gql(headers, query, variables):
    """Run a single Hashnode GraphQL request and return its `data` object.

    Raises on HTTP errors or GraphQL-level `errors` so the per-target
    try/except in publish_blog() can record the failure.
    """
    resp = requests.post(
        HASHNODE_ENDPOINT,
        headers=headers,
        json={"query": query, "variables": variables},
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(str(body["errors"]))
    return body.get("data", {}) or {}


def _hashnode_slug(tag):
    """Normalize a tag name into a Hashnode-acceptable slug."""
    slug = "".join(
        ch if (ch.isalnum() or ch == "-") else "-" for ch in tag.strip().lower()
    )
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "general"


def _publish_hashnode(title, html, tags, canonical_url):
    """Publish to Hashnode via GraphQL PAT: create a draft, then publish it.

    Hashnode's public API has no single direct-publish mutation for this
    flow, so we createDraft -> publishDraft and return the live post URL.
    The WordPress URL (when present) is passed as originalArticleURL, which
    is Hashnode's canonical-URL field.
    """
    headers = {
        "Authorization": config.HASHNODE_TOKEN,
        "Content-Type": "application/json",
    }

    draft_input = {
        "title": title,
        "contentMarkdown": html,
        "publicationId": config.HASHNODE_PUBLICATION_ID,
        "tags": [
            {"name": t, "slug": _hashnode_slug(t)} for t in (tags or []) if t.strip()
        ][:5],
    }
    if canonical_url:
        draft_input["originalArticleURL"] = canonical_url

    create_mutation = """
    mutation CreateDraft($input: CreateDraftInput!) {
      createDraft(input: $input) {
        draft { id }
      }
    }
    """
    created = _hashnode_gql(headers, create_mutation, {"input": draft_input})
    draft_id = (
        created.get("createDraft", {}).get("draft", {}).get("id")
    )
    if not draft_id:
        raise RuntimeError("Hashnode createDraft returned no draft id")

    publish_mutation = """
    mutation PublishDraft($input: PublishDraftInput!) {
      publishDraft(input: $input) {
        post { url }
      }
    }
    """
    published = _hashnode_gql(
        headers, publish_mutation, {"input": {"draftId": draft_id}}
    )
    return (
        published.get("publishDraft", {})
        .get("post", {})
        .get("url", "posted")
    )


def publish_blog(title, html, tags, targets):
    """Publish to each target. Returns {"results": {target: status_or_url}}.

    Targets are publisher names: "wordpress", "devto", "hashnode".
    """
    targets = targets or []
    results = {}
    wp_url = None

    # Always do WordPress first so its URL can be the canonical for the others.
    ordered = [t for t in ("wordpress",) if t in targets]
    ordered += [t for t in targets if t != "wordpress"]

    for target in ordered:
        try:
            if target == "wordpress":
                if config.DRY_RUN or not _wp_configured():
                    results[target] = "DRY_RUN (not sent)"
                else:
                    wp_url = _publish_wordpress(title, html, tags)
                    results[target] = wp_url

            elif target == "devto":
                if config.DRY_RUN or not config.DEVTO_API_KEY:
                    results[target] = "DRY_RUN (not sent)"
                else:
                    results[target] = _publish_devto(title, html, tags, wp_url)

            elif target == "hashnode":
                if config.DRY_RUN or not (
                    config.HASHNODE_TOKEN and config.HASHNODE_PUBLICATION_ID
                ):
                    results[target] = "DRY_RUN (not sent)"
                else:
                    results[target] = _publish_hashnode(title, html, tags, wp_url)

            else:
                results[target] = f"FAILED (unknown target: {target})"

        except Exception as exc:  # noqa: BLE001  (per-target isolation)
            results[target] = f"FAILED ({exc})"

    return {"results": results}
