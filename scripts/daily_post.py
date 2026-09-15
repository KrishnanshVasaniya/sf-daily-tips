"""
Full daily pipeline:
  1. Pull one fresh tip from Salesforce Stack Exchange (generate_tip.py) --
     free, no API key, never runs out.
  2. Render the 3-slide carousel (generate_card.py)
  3. Write data/run_meta.json with image paths + caption, for the poster script
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CURRENT_TIP_PATH = os.path.join(DATA_DIR, "current_tip.json")
META_PATH = os.path.join(DATA_DIR, "run_meta.json")

import generate_tip   # noqa: E402
import generate_card  # noqa: E402

HASHTAGS_BY_CATEGORY = {
    "Apex": "#Apex #Salesforce #SalesforceDeveloper #ApexCode #SFDC",
    "Flow": "#SalesforceFlow #Salesforce #Automation #SFDC #FlowBuilder",
    "LWC": "#LWC #LightningWebComponents #Salesforce #SFDC #JavaScript",
    "SOQL": "#SOQL #Salesforce #SFDC #Database #ApexCode",
    "OmniStudio": "#OmniStudio #Salesforce #Vlocity #SFDC #IndustriesCloud",
}
COMMON_TAGS = "#SalesforceTips #SalesforceDeveloper #Trailblazer #CodeNewbie #100DaysOfCode"


def build_caption(tip):
    tags = HASHTAGS_BY_CATEGORY.get(tip["category"], "") + " " + COMMON_TAGS
    attribution = ""
    if tip.get("source_url"):
        attribution = (
            f"\n\nOriginally asked on Salesforce Stack Exchange (CC BY-SA): "
            f"{tip['source_url']}"
        )
    return (
        f"{tip['problem_title']}\n\n"
        f"\U0001F534 The Problem: {tip['problem']}\n\n"
        f"\u2705 The Fix: {tip['explanation']}"
        f"{attribution}\n\n"
        f"\U0001F4BE Save this for later & follow @sf_daily_tips for a new "
        f"Salesforce tip every day.\n"
        f"\U0001F4AC Questions? Drop them in the comments \u2193\n\n"
        f"{tags}"
    )


def main():
    generate_tip.main()

    with open(CURRENT_TIP_PATH, encoding="utf-8") as f:
        tip = json.load(f)

    slides = generate_card.generate(tip)  # returns [slide1, slide2, slide3]
    slide1_path, slide2_path, slide3_path = slides

    meta = {
        "category": tip["category"],
        "problem_title": tip["problem_title"],
        "caption": build_caption(tip),
        "slide1_file": os.path.relpath(slide1_path, BASE_DIR),
        "slide2_file": os.path.relpath(slide2_path, BASE_DIR),
        "slide3_file": os.path.relpath(slide3_path, BASE_DIR),
    }

    # Only build the Reel video when explicitly requested (BUILD_REEL=1),
    # so carousel runs stay fast and don't require ffmpeg.
    if os.environ.get("BUILD_REEL") == "1":
        import make_reel
        reel_path = os.path.join(BASE_DIR, "output", "reel.mp4")
        make_reel.main_from_paths(slides, reel_path)
        meta["reel_file"] = os.path.relpath(reel_path, BASE_DIR)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Ready to post: [{tip['category']}] {tip['problem_title']}")


if __name__ == "__main__":
    main()
