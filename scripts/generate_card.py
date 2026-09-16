"""
Reference-style Salesforce tip cards (inspired by popular SF Instagram educators):
  - soft blue-tinted background
  - BIG bold blue section headers (not fake app-UI chrome)
  - real dark code-editor blocks with window dots + syntax highlighting
  - cloud badge + page counter (e.g. 1/3) top-right
  - wordmark footer anchor

3 slides:
  1) PROBLEM  : big header "The Problem" + scenario + bad code block
  2) SOLUTION : big header "The Fix" + good code block + short explanation
  3) ENGAGE   : "Found this helpful?" + save/like/comment/follow + handle

Headline font is switchable (Poppins or Sora) via HEADLINE_FONT env or arg,
so we can compare both on the same layout.
"""

import json
import os
import re
import argparse
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350
MARGIN = 70

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
DATA_PATH = os.path.join(BASE_DIR, "data", "tips.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS = os.path.join(BASE_DIR, "assets")
EMOJI_DIR = os.path.join(ASSETS, "emoji")

# ---- palette (reference-inspired) ----
BG = (233, 240, 251)          # soft blue-lavender page
INK = (17, 24, 39)            # near-black body
INK_SOFT = (75, 85, 104)
SF_BLUE = (0, 123, 214)       # the headline blue used by these accounts
SF_BLUE_DK = (0, 90, 170)
SF_CLOUD = (0, 161, 225)      # bright cloud-blue (matched from SF cloud, color only)
ACCENT = (0, 123, 214)
CODE_BG = (30, 30, 34)        # dark editor
CODE_TEXT = (236, 238, 242)
FOOTER_BLUE = (0, 123, 214)

# code syntax colors (on dark) - slightly brighter for a touch more contrast
C_KW = (108, 175, 235)
C_STR = (222, 165, 140)
C_COMMENT = (128, 172, 108)
C_NUM = (196, 220, 184)
C_DEF = (236, 238, 242)

# fonts
F_POP_XB = os.path.join(FONTS_DIR, "Poppins-ExtraBold.ttf")
F_POP_B = os.path.join(FONTS_DIR, "Poppins-Bold.ttf")
F_POP_SB = os.path.join(FONTS_DIR, "Poppins-SemiBold.ttf")
F_POP_M = os.path.join(FONTS_DIR, "Poppins-Medium.ttf")
F_POP_R = os.path.join(FONTS_DIR, "Poppins-Regular.ttf")
F_SORA_B = os.path.join(FONTS_DIR, "Sora-Bold.otf")
F_SORA_SB = os.path.join(FONTS_DIR, "Sora-SemiBold.otf")
F_INTER_R = os.path.join(FONTS_DIR, "Inter-Regular.otf")
F_INTER_M = os.path.join(FONTS_DIR, "Inter-Medium.otf")
F_INTER_SB = os.path.join(FONTS_DIR, "Inter-SemiBold.otf")
F_ITALIC = os.path.join(FONTS_DIR, "Poppins-MediumItalic.ttf")
F_MONO = os.path.join(FONTS_DIR, "FiraCode-Regular.ttf")

KEYWORDS = {
    "public","private","protected","class","static","void","for","if","else","return",
    "new","update","insert","delete","trigger","on","before","after","import","from",
    "export","default","extends","const","let","var","function","this",
    "List","Map","Set","String","Integer","Boolean","Id","null","true","false",
    "SELECT","FROM","WHERE","GROUP","BY","HAVING","IN","AND","OR","get",
}
CATEGORY_COLORS = {
    "Apex": (0, 123, 214), "Flow": (255, 138, 0), "LWC": (150, 90, 190),
    "SOQL": (46, 160, 90), "OmniStudio": (0, 160, 220),
}

# headline font family, set at runtime
HL = {"xb": F_POP_XB, "b": F_POP_B, "sb": F_POP_SB}


def set_headline(family):
    if family == "sora":
        HL["xb"] = F_SORA_B
        HL["b"] = F_SORA_B
        HL["sb"] = F_SORA_SB
    else:
        HL["xb"] = F_POP_XB
        HL["b"] = F_POP_B
        HL["sb"] = F_POP_SB


def draw_cloud_shape(draw, cx, cy, w, fill, outline=None, outline_w=0):
    """Draw a smooth horizontal cloud centered at (cx, cy), roughly w wide.
    Original shape (not a copy of any logo), tuned to read as a soft cloud."""
    r = w * 0.13
    # base slab (the flat bottom + body)
    draw.rounded_rectangle([cx - 2.5*r, cy - 0.1*r, cx + 2.5*r, cy + 1.15*r],
                           radius=int(0.7*r), fill=fill)
    # left small puff
    draw.ellipse([cx - 2.5*r, cy - 0.55*r, cx - 0.8*r, cy + 1.05*r], fill=fill)
    # tall left-center puff
    draw.ellipse([cx - 1.55*r, cy - 1.35*r, cx + 0.15*r, cy + 0.45*r], fill=fill)
    # tallest center puff
    draw.ellipse([cx - 0.35*r, cy - 1.75*r, cx + 1.35*r, cy + 0.15*r], fill=fill)
    # right puff
    draw.ellipse([cx + 0.55*r, cy - 1.15*r, cx + 2.5*r, cy + 1.05*r], fill=fill)


def font(path, size):
    return ImageFont.truetype(path, size)


def soft_shadow(img, box, radius, blur=22, alpha=55, dy=10, dx=0):
    """Paste a soft blurred drop shadow beneath a rounded box."""
    from PIL import ImageFilter
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x0 + dx, y0 + dy, x1 + dx, y1 + dy], radius=radius,
                         fill=(20, 40, 80, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste(layer, (0, 0), layer)


def raised_panel(img, box, radius, fill, bevel=True, shadow=True,
                 shadow_alpha=55, shadow_blur=24, shadow_dy=12):
    """Draw a rounded panel that looks lifted: soft shadow beneath + a light
    top bevel and subtle bottom shade for a clean 3D raised effect."""
    x0, y0, x1, y1 = box
    if shadow:
        soft_shadow(img, box, radius, blur=shadow_blur, alpha=shadow_alpha, dy=shadow_dy)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=radius, fill=fill)
    if bevel:
        # light highlight along the top edge, faint shade along the bottom edge
        hl = tuple(min(255, c + 18) for c in fill)
        sh = tuple(max(0, c - 16) for c in fill)
        d.rounded_rectangle([x0, y0, x1, y0 + radius * 2], radius=radius, outline=hl, width=2)
        d.arc([x0, y1 - radius * 2, x1, y1], start=20, end=160, fill=sh, width=2)


def emoji_img(cp, size):
    p = os.path.join(EMOJI_DIR, f"{cp}.png")
    if not os.path.exists(p):
        return None
    return Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)


def wrap(draw, text, fnt, max_w):
    out = []
    for para in text.split("\n"):
        if not para.strip():
            out.append("")
            continue
        words, cur = para.split(" "), ""
        for w in words:
            # Hard-break a single "word" that alone exceeds max_w (e.g. a long
            # URL/path with no spaces) -- without this it just overflows the
            # image edge instead of wrapping.
            if draw.textlength(w, font=fnt) > max_w:
                if cur:
                    out.append(cur)
                    cur = ""
                piece = ""
                for ch in w:
                    if piece and draw.textlength(piece + ch, font=fnt) > max_w:
                        out.append(piece)
                        piece = ch
                    else:
                        piece += ch
                cur = piece
                continue
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=fnt) <= max_w or not cur:
                cur = t
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def draw_wrap(draw, text, fnt, x, y, max_w, fill, lh, max_lines=None):
    """Draw wrapped text. If max_lines is given, truncate with an ellipsis
    instead of letting content grow past its allotted space."""
    lines = wrap(draw, text, fnt, max_w)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "...", font=fnt) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip() + "..."
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def draw_fitted_block(draw, text, font_path, x, y, max_w, max_h, fill,
                      start_size, min_size, line_height_ratio=1.45, step=2):
    """Draw text that SHRINKS its font size to fit within max_h, rather than
    truncating it -- so a longer question keeps (almost) all of its wording,
    just a little smaller, instead of getting cut off with '...'.
    Only truncates as a last resort if it still doesn't fit at min_size."""
    size = start_size
    while size >= min_size:
        fnt = font(font_path, size)
        lh = max(int(size * line_height_ratio), size + 6)
        lines = wrap(draw, text, fnt, max_w)
        if lh * len(lines) <= max_h:
            for ln in lines:
                draw.text((x, y), ln, font=fnt, fill=fill)
                y += lh
            return y
        size -= step

    # Even the smallest readable size doesn't fit -- truncate gracefully.
    fnt = font(font_path, min_size)
    lh = max(int(min_size * line_height_ratio), min_size + 6)
    lines = wrap(draw, text, fnt, max_w)
    max_lines = max(1, int(max_h // lh))
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "...", font=fnt) > max_w:
            last = last[:-1]
        lines[-1] = last.rstrip() + "..."
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def tokenize(line):
    toks = []
    m = re.search(r'(//.*$|--.*$)', line)
    code, comment = (line[:m.start()], line[m.start():]) if m else (line, "")
    for tok in re.findall(r'(".*?"|\'.*?\'|\b\d+\b|\w+|[^\w\s])', code):
        if tok in KEYWORDS:
            toks.append((tok, C_KW))
        elif re.match(r'^[\"\'].*[\"\']$', tok):
            toks.append((tok, C_STR))
        elif re.match(r'^\d+$', tok):
            toks.append((tok, C_NUM))
        else:
            toks.append((tok, C_DEF))
        toks.append((" ", C_DEF))
    if comment:
        toks.append((comment, C_COMMENT))
    return toks


def code_block(img, draw, code, x, y, w, fsize=25, lh=37, max_lines=None):
    """Render a code block. If max_lines is given and the code is longer,
    it's truncated with a '...' line so the block's height stays predictable
    and never overflows whatever space the caller has budgeted for it."""
    lines = code.split("\n")
    truncated = False
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    h = lh * (len(lines) + (1 if truncated else 0)) + 76
    # soft shadow beneath the editor for a raised look
    soft_shadow(img, [x, y, x + w, y + h], radius=18, blur=20, alpha=60, dy=10)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=18, fill=CODE_BG)
    # title-bar dots, positioned clear of the top edge
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        dx = x + 32 + i * 32
        draw.ellipse([dx, y + 26, dx + 18, y + 44], fill=c)
    fnt = font(F_MONO, fsize)
    max_line_w = w - 72
    cy = y + 70
    for ln in lines:
        cx = x + 36
        # IMPORTANT: tokenize() inserts a space after every single token
        # (brackets, commas, everything), which makes the rendered line
        # visibly WIDER than the plain string. Measuring the plain string
        # (as an earlier version of this function did) under-counts the
        # real width and lets long lines bleed past the block -- so here
        # we measure and truncate using the actual token-by-token width.
        toks = tokenize(ln)
        total_w = sum(draw.textlength(t, font=fnt) for t, _ in toks)
        if total_w > max_line_w:
            ellipsis_w = draw.textlength("...", font=fnt)
            kept, run = [], 0.0
            for tok, color in toks:
                tw = draw.textlength(tok, font=fnt)
                if run + tw + ellipsis_w > max_line_w:
                    break
                kept.append((tok, color))
                run += tw
            toks = kept + [("...", C_COMMENT)]
        for text, color in toks:
            if text == "":
                continue
            draw.text((cx, cy), text, font=fnt, fill=color)
            cx += draw.textlength(text, font=fnt)
        cy += lh
    if truncated:
        draw.text((x + 36, cy), "...", font=fnt, fill=C_COMMENT)
        cy += lh
    return y + h


def top_bar(img, draw, category, page_idx, total=3):
    """Cloud badge top-right, wordmark top-left. (Instagram shows its own page dots.)"""
    # wordmark top-left
    draw.text((MARGIN, MARGIN - 10), "SF Daily", font=font(HL["xb"], 34), fill=SF_BLUE)
    draw.text((MARGIN, MARGIN + 34), "developer tips", font=font(F_INTER_M, 22), fill=INK_SOFT)
    # cloud badge top-right (no counter -- IG provides page indicator)
    badge = Image.open(os.path.join(ASSETS, "cloud_badge.png")).convert("RGBA")
    bsize = 110
    badge = badge.resize((bsize, bsize), Image.LANCZOS)
    bx, by = WIDTH - MARGIN - bsize, MARGIN - 18
    img.paste(badge, (bx, by), badge)
    draw = ImageDraw.Draw(img)
    return draw


def category_chip(draw, category, x, y):
    color = CATEGORY_COLORS.get(category, SF_BLUE)
    label = category
    f = font(HL["sb"], 26)
    b = draw.textbbox((0, 0), label, font=f)
    w = b[2] - b[0]
    draw.rounded_rectangle([x, y, x + w + 44, y + 52], radius=999, fill=color)
    draw.text((x + 22, y + 10), label, font=f, fill=(255, 255, 255))
    return y + 52


def big_header(draw, text, x, y, color=SF_BLUE, size=76):
    f = font(HL["xb"], size)
    draw.text((x, y), text, font=f, fill=color)
    # underline accent like the references
    b = draw.textbbox((0, 0), text, font=f)
    uy = y + (b[3] - b[1]) + 24
    draw.rounded_rectangle([x, uy, x + min(b[2]-b[0], 260), uy + 8], radius=4, fill=color)
    return uy + 30


def footer(draw):
    f = font(HL["b"], 28)
    txt = "@sf_daily_tips"
    b = draw.textbbox((0, 0), txt, font=f)
    draw.text(((WIDTH - (b[2]-b[0]))/2, CARD_BOTTOM - 58), txt, font=f, fill=FOOTER_BLUE)


# ---------------- slides ----------------

# Raised content card geometry (shared by all slides)
CARD_TOP = 176
CARD_BOTTOM = HEIGHT - 96
CARD_PAD = 44
FOOTER_RESERVE = 70   # vertical space always kept clear for the footer text
MIN_CODE_LINES = 3    # below this, a code block isn't worth showing -- skip it
CODE_LINE_H = 37


def page_base(category, page_idx):
    """Create the page: blue bg, subtle beveled edge frame, top bar, and a
    raised white content card. Returns (img, draw, content_x, content_y)."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)
    # subtle beveled frame around the whole slide edge
    d.rounded_rectangle([8, 8, WIDTH - 8, HEIGHT - 8], radius=28,
                        outline=(255, 255, 255), width=3)
    d.rounded_rectangle([12, 12, WIDTH - 12, HEIGHT - 12], radius=26,
                        outline=(210, 222, 240), width=2)
    # raised white content card
    raised_panel(img, [MARGIN - 6, CARD_TOP, WIDTH - MARGIN + 6, CARD_BOTTOM],
                 radius=30, fill=(255, 255, 255),
                 shadow_alpha=48, shadow_blur=26, shadow_dy=14)
    d = ImageDraw.Draw(img)
    d = top_bar(img, d, category, page_idx)
    return img, d


def slide_problem(tip):
    img, d = page_base(tip["category"], 1)

    x = MARGIN + CARD_PAD - 6
    inner_w = (WIDTH - 2 * MARGIN) - 2 * (CARD_PAD - 6)
    y = CARD_TOP + CARD_PAD
    category_chip(d, tip["category"], x, y)
    y += 84

    y = big_header(d, "The Problem", x, y, color=(210, 70, 66))
    y += 10

    # Title: shrinks its font size to fit within a bounded box, rather than
    # cutting text off with "..." -- most titles are short so this rarely
    # even needs to shrink.
    y = draw_fitted_block(d, tip["problem_title"], HL["b"], x, y, inner_w, 168,
                          INK, start_size=46, min_size=34, line_height_ratio=1.26) + 14

    # Problem text: this is the one that was getting cut off early. Give it
    # a generous height budget and let the font shrink (down to a still
    # comfortably readable size) so nearly all of it shows, instead of
    # truncating after a fixed number of lines.
    y = draw_fitted_block(d, tip["problem"], F_INTER_R, x, y, inner_w, 260,
                          INK_SOFT, start_size=30, min_size=22, line_height_ratio=1.47) + 24

    if tip.get("code"):
        # The code block gets whatever real room is left -- sized (or
        # skipped, if there's truly no room) so it always ends before the
        # footer, never past it.
        available = (CARD_BOTTOM - FOOTER_RESERVE) - y
        max_lines = int((available - 76) // CODE_LINE_H)
        if max_lines >= MIN_CODE_LINES:
            code_block(img, d, tip["code"], x, y, inner_w, max_lines=max_lines)

    footer(d)
    return img


def slide_solution(tip):
    img, d = page_base(tip["category"], 2)

    x = MARGIN + CARD_PAD - 6
    inner_w = (WIDTH - 2 * MARGIN) - 2 * (CARD_PAD - 6)
    y = CARD_TOP + CARD_PAD
    category_chip(d, tip["category"], x, y)
    y += 84

    y = big_header(d, "The Fix", x, y, color=(40, 150, 84))
    y += 10

    code = tip.get("fixed_code") or tip.get("code")
    if code:
        # Reserve a minimum for the explanation (it'll still shrink-to-fit
        # rather than truncate), then size the code block to what's left.
        reserved_for_explanation = 170
        available = (CARD_BOTTOM - FOOTER_RESERVE) - y - reserved_for_explanation
        max_lines = int((available - 76) // CODE_LINE_H)
        if max_lines >= MIN_CODE_LINES:
            y = code_block(img, d, code, x, y, inner_w, max_lines=max_lines) + 30
        # else: skip the code block, give the explanation the full space below

    # Explanation: shrinks to fit whatever vertical room remains before the
    # footer, instead of being cut off with "...".
    remaining = (CARD_BOTTOM - FOOTER_RESERVE) - y
    draw_fitted_block(d, tip["explanation"], F_INTER_R, x, y, inner_w, remaining,
                      INK, start_size=31, min_size=22, line_height_ratio=1.48)

    footer(d)
    return img


def slide_engage(tip):
    img, d = page_base(tip["category"], 3)

    cx = WIDTH / 2
    y = CARD_TOP + CARD_PAD + 6
    title = "Found this helpful?"
    tf = font(HL["xb"], 58)
    tb = d.textbbox((0, 0), title, font=tf)
    d.text((cx - (tb[2]-tb[0])/2, y), title, font=tf, fill=SF_BLUE)
    y += 98
    d.rounded_rectangle([cx - 60, y, cx + 60, y + 8], radius=4, fill=SF_BLUE)
    y += 60

    # light chip backgrounds so the colorful emoji pop; label color carries the accent
    CHIP_BG = (255, 255, 255)
    # order requested: Like, Comment, Share, Save, Follow
    actions = [
        ("2764",  (210, 70, 66),  "LIKE",    "if it saved you time"),
        ("1f4ac", SF_BLUE,        "COMMENT", "ask your question below"),
        ("1f501", (150, 90, 190), "SHARE",   "send it to a teammate"),
        ("1f4be", (40, 150, 84),  "SAVE",    "keep this fix for later"),
        ("2795",  SF_BLUE_DK,     "FOLLOW",  "a new tip every day"),
    ]
    chip = 82
    block_w = 600
    bx = cx - block_w/2
    for cp, color, label, desc in actions:
        d.rounded_rectangle([bx, y, bx + chip, y + chip], radius=24,
                            fill=CHIP_BG, outline=color, width=3)
        em = emoji_img(cp, 48)
        if em:
            img.paste(em, (int(bx + (chip-48)/2), int(y + (chip-48)/2)), em)
            d = ImageDraw.Draw(img)
        d.text((bx + chip + 34, y + 8), label, font=font(HL["b"], 34), fill=color)
        d.text((bx + chip + 34, y + 50), desc, font=font(F_ITALIC, 25), fill=INK_SOFT)
        y += chip + 22

    # cloud-shaped handle badge - sized small, placed fully INSIDE the card
    handle = "@sf_daily_tips"
    hf = font(HL["xb"], 28)
    hb = d.textbbox((0, 0), handle, font=hf)
    text_w = hb[2] - hb[0]
    cloud_w = max((text_w + 130) / 0.598, 500)
    r = cloud_w * 0.13
    # cloud extends ~1.75*r above center and ~1.15*r below; keep the whole shape
    # comfortably above the card's bottom edge (CARD_BOTTOM)
    cloud_cy = CARD_BOTTOM - 1.15 * r - 40
    draw_cloud_shape(d, cx, cloud_cy, cloud_w, SF_CLOUD)
    d = ImageDraw.Draw(img)
    d.text((cx - text_w/2, cloud_cy - (hb[3]-hb[1])/2 - hb[1]),
           handle, font=hf, fill=(255, 255, 255))
    return img


def generate(tip, out_dir=OUTPUT_DIR, suffix=""):
    os.makedirs(out_dir, exist_ok=True)
    tag = f"tip{tip['id']}{suffix}"
    paths = []
    for i, maker in enumerate([slide_problem, slide_solution, slide_engage], 1):
        p = os.path.join(out_dir, f"{tag}_slide{i}.png")
        maker(tip).save(p)
        paths.append(p)
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--headline", choices=["poppins", "sora"],
                    default=os.environ.get("HEADLINE_FONT", "sora"))
    ap.add_argument("--suffix", default="")
    args = ap.parse_args()
    set_headline(args.headline)
    with open(DATA_PATH, encoding="utf-8") as f:
        tips = json.load(f)
    if args.id is not None:
        tips = [t for t in tips if t["id"] == args.id]
    for t in tips:
        paths = generate(t, suffix=args.suffix)
        print("Generated:", ", ".join(paths))


if __name__ == "__main__":
    main()
