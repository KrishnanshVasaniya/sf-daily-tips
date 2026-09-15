"""
Publishes the carousel described in data/run_meta.json to Instagram.
Requires the images to already be pushed to a PUBLIC GitHub repo.

Required environment variables:
    IG_USER_ID          - Instagram Business Account ID for this account
    IG_ACCESS_TOKEN     - long-lived Graph API access token for this account
    GITHUB_REPOSITORY   - "owner/repo" (auto-set by GitHub Actions)
    GITHUB_REF_NAME      - branch name (auto-set by GitHub Actions)
"""

import json
import os
import sys
import time
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_PATH = os.path.join(BASE_DIR, "data", "run_meta.json")
GRAPH_API = "https://graph.facebook.com/v21.0"


def raw_url(repo, branch, relative_path):
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{relative_path}"


def create_carousel_item(ig_user_id, token, image_url):
    resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media",
        data={"image_url": image_url, "is_carousel_item": "true", "access_token": token},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_until_ready(container_id, token, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed processing")
        time.sleep(3)
    raise TimeoutError(f"Container {container_id} did not finish in time")


def create_carousel_container(ig_user_id, token, children_ids, caption):
    resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": token,
        },
    )
    resp.raise_for_status()
    return resp.json()["id"]


def publish(ig_user_id, token, creation_id):
    resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
    )
    resp.raise_for_status()
    return resp.json()


def main():
    ig_user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("GITHUB_REF_NAME", "main")

    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)

    urls = [raw_url(repo, branch, meta[f"slide{i}_file"]) for i in (1, 2, 3)]
    for i, u in enumerate(urls, 1):
        print(f"Slide {i} URL: {u}")

    items = [create_carousel_item(ig_user_id, token, u) for u in urls]
    for it in items:
        wait_until_ready(it, token)

    carousel_id = create_carousel_container(ig_user_id, token, items, meta["caption"])
    wait_until_ready(carousel_id, token)

    result = publish(ig_user_id, token, carousel_id)
    print(f"Published! Media ID: {result.get('id')}")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"Graph API error: {e.response.text}", file=sys.stderr)
        sys.exit(1)
