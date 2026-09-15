"""
Publishes a Reel (video) to Instagram via the Graph API.

Reels differ from carousels: media_type=REELS, a video_url, and processing
takes longer so we poll the container until FINISHED before publishing.

Required env:
    IG_USER_ID, IG_ACCESS_TOKEN, GITHUB_REPOSITORY, GITHUB_REF_NAME
Reads data/run_meta.json for the caption and the reel file path.
"""

import json
import os
import sys
import time
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_PATH = os.path.join(BASE_DIR, "data", "run_meta.json")
GRAPH_API = "https://graph.facebook.com/v21.0"


def raw_url(repo, branch, rel):
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{rel}"


def create_reel_container(ig_user_id, token, video_url, caption):
    resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
    )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_until_ready(container_id, token, timeout=300):
    """Reels take longer to process than images."""
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
            raise RuntimeError(f"Reel container {container_id} failed processing")
        time.sleep(6)
    raise TimeoutError("Reel did not finish processing in time")


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

    reel_rel = meta.get("reel_file", "output/reel.mp4")
    video_url = raw_url(repo, branch, reel_rel)
    print(f"Reel URL: {video_url}")

    container = create_reel_container(ig_user_id, token, video_url, meta["caption"])
    print(f"Created reel container: {container}")

    wait_until_ready(container, token)

    result = publish(ig_user_id, token, container)
    print(f"Published Reel! Media ID: {result.get('id')}")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"Graph API error: {e.response.text}", file=sys.stderr)
        sys.exit(1)
