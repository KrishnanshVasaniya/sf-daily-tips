# -*- coding: utf-8 -*-
"""
Generates ONE tip per run by pulling a real, highly-voted, answered question
from Salesforce Stack Exchange (site: salesforce.stackexchange.com) via their
free public API. No account, no API key, no cost -- and it never runs out,
since the community keeps posting new questions.

Content is CC BY-SA licensed: reused with attribution, which daily_post.py
adds to the caption automatically (source_url is carried through).

Rotates categories same as before: Apex -> SOQL -> OmniStudio -> LWC -> Flow.
Tracks used question IDs so the same question is never reposted.

Writes: data/current_tip.json (consumed by generate_card.py)
Updates: data/used_question_ids.json, data/category_state.json
"""

import json
import os
import re
import html as html_module
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
USED_IDS_PATH = os.path.join(DATA_DIR, "used_question_ids.json")
CATEGORY_STATE_PATH = os.path.join(DATA_DIR, "category_state.json")
CURRENT_TIP_PATH = os.path.join(DATA_DIR, "current_tip.json")

CATEGORIES = ["Apex", "SOQL", "OmniStudio", "LWC", "Flow"]
MAX_USED_IDS = 3000  # generous cap; content is effectively infinite so this
                      # mainly just keeps the tracking file from growing forever

SE_API = "https://api.stackexchange.com/2.3"
SITE = "salesforce"

# primary tag first, then fallbacks tried in order if a category comes up empty
CATEGORY_TAGS = {
    "Apex": ["apex-code"],
    "SOQL": ["soql"],
    "Flow": ["salesforce-flow", "process-builder", "visual-workflow"],
    "LWC": ["lightning-web-components"],
    "OmniStudio": ["omnistudio", "vlocity"],
}

MAX_TEXT_CHARS = 420
MAX_CODE_LINES = 10

CODE_BLOCK_RE = re.compile(r"<pre>\s*<code>(.*?)</code>\s*</pre>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_category():
    state = load_json(CATEGORY_STATE_PATH, {"index": 0})
    category = CATEGORIES[state["index"] % len(CATEGORIES)]
    state["index"] += 1
    save_json(CATEGORY_STATE_PATH, state)
    return category


def extract_first_code_block(body_html):
    """Pull the first <pre><code> block out of Stack Exchange's HTML body."""
    m = CODE_BLOCK_RE.search(body_html or "")
    if not m:
        return None
    code = html_module.unescape(m.group(1))
    lines = code.strip("\n").split("\n")
    if len(lines) > MAX_CODE_LINES:
        lines = lines[:MAX_CODE_LINES] + ["..."]
    return "\n".join(lines)


def strip_html_to_text(body_html, max_chars=MAX_TEXT_CHARS):
    """Remove code blocks + tags, decode entities, collapse whitespace, truncate cleanly."""
    text = CODE_BLOCK_RE.sub(" ", body_html or "")
    text = TAG_RE.sub(" ", text)
    text = html_module.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


def fetch_candidate_questions(tag, pagesize=20):
    resp = requests.get(
        f"{SE_API}/questions",
        params={
            "order": "desc",
            "sort": "votes",
            "tagged": tag,
            "site": SITE,
            "filter": "withbody",
            "pagesize": pagesize,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def fetch_top_answer(question_id):
    resp = requests.get(
        f"{SE_API}/questions/{question_id}/answers",
        params={
            "order": "desc",
            "sort": "votes",
            "site": SITE,
            "filter": "withbody",
            "pagesize": 5,
        },
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return items[0] if items else None


def pick_question(category, used_ids):
    tags = CATEGORY_TAGS.get(category, [category.lower()])
    for tag in tags:
        try:
            candidates = fetch_candidate_questions(tag)
        except requests.RequestException as e:
            print(f"Warning: fetch failed for tag '{tag}': {e}")
            continue
        for q in candidates:
            if q["question_id"] in used_ids:
                continue
            if not q.get("is_answered"):
                continue
            if q.get("score", 0) < 1:
                continue
            return q, tag
    return None, None


def build_tip(category, question):
    answer = fetch_top_answer(question["question_id"])
    if not answer:
        return None

    q_body = question.get("body", "")
    a_body = answer.get("body", "")

    tip = {
        "id": "daily",
        "category": category,
        "problem_title": html_module.unescape(question["title"]),
        "problem": strip_html_to_text(q_body),
        "code": extract_first_code_block(q_body),
        "fixed_code": extract_first_code_block(a_body),
        "explanation": strip_html_to_text(a_body),
        "source_url": question["link"],
    }
    # Guarantee explanation is never empty (fall back to problem text's tail case)
    if not tip["explanation"]:
        tip["explanation"] = "See the full answer on Salesforce Stack Exchange (link in caption)."
    return tip


def main():
    used_ids = load_json(USED_IDS_PATH, [])

    # Try the rotation category first; if it's genuinely out of fresh
    # questions, fall through to the next categories rather than fail the run.
    tried = []
    tip = None
    question = None
    for _ in range(len(CATEGORIES)):
        category = next_category()
        tried.append(category)
        question, tag_used = pick_question(category, used_ids)
        if question:
            tip = build_tip(category, question)
            if tip:
                break
        print(f"No fresh question found for {category}, trying next category...")

    if not tip:
        raise RuntimeError(f"Could not find any fresh question across categories: {tried}")

    save_json(CURRENT_TIP_PATH, tip)

    used_ids.append(question["question_id"])
    used_ids = used_ids[-MAX_USED_IDS:]
    save_json(USED_IDS_PATH, used_ids)

    print(f"Selected [{tip['category']}] {tip['problem_title']}")
    print(f"Source: {tip['source_url']}")


if __name__ == "__main__":
    main()
