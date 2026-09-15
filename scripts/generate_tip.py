# -*- coding: utf-8 -*-
"""
Generates ONE tip per run by pulling a real, well-vetted question from
Salesforce Stack Exchange (free public API, no key, no cost, never runs out).

Quality bar (tightened after the first live run surfaced a non-technical
"how do I sign up" question with no code involved):
  - must have an ACCEPTED answer (not just "some answer exists")
  - question score >= 2 (filters out unvetted/low-quality posts)
  - either the question or its accepted answer must contain an actual code
    block -- this is what filters out administrative/access/signup issues
    that aren't real "Problem -> Solution" coding tips

Rotates categories: Apex -> SOQL -> OmniStudio -> LWC -> Flow.
Tracks used question IDs so nothing repeats.

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
MAX_USED_IDS = 3000

SE_API = "https://api.stackexchange.com/2.3"
SITE = "salesforce"

CATEGORY_TAGS = {
    "Apex": ["apex-code"],
    "SOQL": ["soql"],
    "Flow": ["salesforce-flow", "process-builder", "visual-workflow"],
    "LWC": ["lightning-web-components"],
    "OmniStudio": ["omnistudio", "vlocity"],
}

MIN_SCORE = 2
MAX_TEXT_CHARS = 420
MAX_CODE_LINES = 10
CANDIDATES_PER_TAG = 30  # cast a wider net since the quality bar is stricter now

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
    m = CODE_BLOCK_RE.search(body_html or "")
    if not m:
        return None
    code = html_module.unescape(m.group(1))
    lines = code.strip("\n").split("\n")
    if len(lines) > MAX_CODE_LINES:
        lines = lines[:MAX_CODE_LINES] + ["..."]
    return "\n".join(lines)


def strip_html_to_text(body_html, max_chars=MAX_TEXT_CHARS):
    text = CODE_BLOCK_RE.sub(" ", body_html or "")
    text = TAG_RE.sub(" ", text)
    text = html_module.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


def fetch_candidate_questions(tag, pagesize=CANDIDATES_PER_TAG):
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


def fetch_answer_by_id(answer_id):
    """Fetch a specific answer by ID (used to get the ACCEPTED answer, not
    just 'some' answer)."""
    resp = requests.get(
        f"{SE_API}/answers/{answer_id}",
        params={"site": SITE, "filter": "withbody"},
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return items[0] if items else None


def passes_quality_bar(question):
    """First-pass filters that don't require an extra API call."""
    if not question.get("accepted_answer_id"):
        return False
    if question.get("score", 0) < MIN_SCORE:
        return False
    return True


def pick_tip(category, used_ids):
    """Find a question that passes ALL quality bars, including 'has real
    code involved' -- which requires fetching the accepted answer to check."""
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
            if not passes_quality_bar(q):
                continue

            try:
                answer = fetch_answer_by_id(q["accepted_answer_id"])
            except requests.RequestException:
                continue
            if not answer:
                continue

            q_body = q.get("body", "")
            a_body = answer.get("body", "")
            code = extract_first_code_block(q_body)
            fixed_code = extract_first_code_block(a_body)

            # The real fix: skip anything with no actual code in it --
            # this is what filters out signup/access/admin-type questions.
            if not code and not fixed_code:
                continue

            tip = {
                "id": "daily",
                "category": category,
                "problem_title": html_module.unescape(q["title"]),
                "problem": strip_html_to_text(q_body),
                "code": code,
                "fixed_code": fixed_code,
                "explanation": strip_html_to_text(a_body) or
                    "See the full accepted answer on Salesforce Stack Exchange (link in caption).",
                "source_url": q["link"],
            }
            return tip, q

    return None, None


def main():
    used_ids = load_json(USED_IDS_PATH, [])

    tried = []
    tip = None
    question = None
    for _ in range(len(CATEGORIES)):
        category = next_category()
        tried.append(category)
        tip, question = pick_tip(category, used_ids)
        if tip:
            break
        print(f"No quality-qualifying question found for {category}, trying next category...")

    if not tip:
        raise RuntimeError(
            f"Could not find any fresh, code-containing, accepted-answer question "
            f"across categories: {tried}"
        )

    save_json(CURRENT_TIP_PATH, tip)

    used_ids.append(question["question_id"])
    used_ids = used_ids[-MAX_USED_IDS:]
    save_json(USED_IDS_PATH, used_ids)

    print(f"Selected [{tip['category']}] {tip['problem_title']}")
    print(f"Source: {tip['source_url']}")


if __name__ == "__main__":
    main()
