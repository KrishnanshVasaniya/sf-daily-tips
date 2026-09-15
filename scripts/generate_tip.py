"""
Generates ONE fresh Salesforce Problem->Solution tip using the Claude API.
Rotates through categories (Apex, Flow, LWC, SOQL, OmniStudio) and avoids
repeating recent topics by tracking titles already used.

Requires env var: ANTHROPIC_API_KEY
Writes: data/current_tip.json (consumed by generate_card.py)
Updates: data/recent_titles.json, data/category_state.json
"""

import json
import os
import re
import sys
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECENT_PATH = os.path.join(DATA_DIR, "recent_titles.json")
CATEGORY_STATE_PATH = os.path.join(DATA_DIR, "category_state.json")
CURRENT_TIP_PATH = os.path.join(DATA_DIR, "current_tip.json")

CATEGORIES = ["Apex", "SOQL", "OmniStudio", "LWC", "Flow"]
MAX_RECENT_TITLES = 200  # ~2 months of history at 3 posts/day, prevents repeats

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You write short, technically accurate Salesforce developer tips \
for an Instagram carousel account. Each tip follows a strict Problem -> Solution \
format based on a realistic scenario a Salesforce developer would actually hit.

Output ONLY a single JSON object, no markdown fences, no commentary, matching \
exactly this schema:

{
  "category": "<one of: Apex, Flow, LWC, SOQL, OmniStudio>",
  "problem_title": "<short punchy title, under 8 words>",
  "problem": "<2-3 sentences describing a realistic scenario and what error/symptom \
appears. Can include a short literal error message on its own line if relevant.>",
  "code": "<short BAD code snippet showing the problem, or null if not code-specific>",
  "fixed_code": "<short GOOD code snippet showing the fix, or null if not code-specific>",
  "explanation": "<2-3 sentences, ~30-45 words, explaining WHY the fix works, \
written in a warm but precise technical voice>"
}

Rules:
- Must be technically accurate about real Salesforce platform behavior (governor \
limits, actual API names, actual Flow/LWC/OmniStudio behavior). Never invent fake \
APIs or fake error messages.
- code/fixed_code should be short (under 8 lines), illustrative, not full production code.
- Do not repeat a topic/title from the list of recent titles you're given.
- Vary the specific sub-topic within the category (e.g. don't always pick governor \
limits for Apex -- also cover triggers, testing, security, async, etc.)
"""


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


def call_claude(category, recent_titles):
    api_key = os.environ["ANTHROPIC_API_KEY"]
    recent_list = "\n".join(f"- {t}" for t in recent_titles[-40:]) or "(none yet)"

    user_prompt = f"""Category for this tip: {category}

Recent titles already used (do NOT repeat these topics):
{recent_list}

Generate one new tip now."""

    resp = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 700,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=60,
    )
    if not resp.ok:
        print("Anthropic API error response:", resp.text)
    resp.raise_for_status()
    data = resp.json()
    text = "".join(block["text"] for block in data["content"] if block["type"] == "text")

    # strip stray markdown fences if the model adds them anyway
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    tip = json.loads(cleaned)
    return tip


def main():
    category = next_category()
    recent_titles = load_json(RECENT_PATH, [])

    tip = call_claude(category, recent_titles)

    # basic validation
    required = ["category", "problem_title", "problem", "explanation"]
    for key in required:
        if key not in tip or not tip[key]:
            print(f"ERROR: generated tip missing required field '{key}': {tip}", file=sys.stderr)
            sys.exit(1)

    tip["id"] = "daily"  # single working filename, overwritten each run
    save_json(CURRENT_TIP_PATH, tip)

    recent_titles.append(tip["problem_title"])
    recent_titles = recent_titles[-MAX_RECENT_TITLES:]
    save_json(RECENT_PATH, recent_titles)

    print(f"Generated [{tip['category']}] {tip['problem_title']}")


if __name__ == "__main__":
    main()
