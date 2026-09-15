"""
Generates a circular Instagram profile picture (DP) for the Salesforce tips
account: a cloud-blue gradient disc with a stylized cloud + code prompt mark.
Original artwork -- evokes Salesforce's cloud/blue identity without using
their actual logo.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZE = 1000
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

BRAND_BLUE = (0, 112, 210)
CLOUD_CYAN = (0, 172, 238)
DEEP = (0, 64, 133)
WHITE = (255, 255, 255)

F_XBOLD = os.path.join(FONTS_DIR, "Inter-ExtraBold.otf")
F_BOLD = os.path.join(FONTS_DIR, "Inter-Bold.otf")


def radial_gradient(size, inner, outer):
    img = Image.new("RGB", (size, size), outer)
    cx = cy = size / 2
    maxr = size / 2
    px = img.load()
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - cx, y - cy) / maxr
            d = min(1, d)
            r = int(inner[0] * (1 - d) + outer[0] * d)
            g = int(inner[1] * (1 - d) + outer[1] * d)
            b = int(inner[2] * (1 - d) + outer[2] * d)
            px[x, y] = (r, g, b)
    return img


def draw_cloud(draw, cx, cy, scale, fill):
    """Rounded cloud silhouette from overlapping circles + flat base."""
    r = 100 * scale
    # base slab
    draw.rounded_rectangle([cx - 2.0*r, cy - 0.1*r, cx + 2.0*r, cy + 1.0*r],
                           radius=int(0.55*r), fill=fill)
    # puffs
    draw.ellipse([cx - 1.9*r, cy - 0.5*r, cx - 0.5*r, cy + 0.9*r], fill=fill)
    draw.ellipse([cx - 1.1*r, cy - 1.2*r, cx + 0.5*r, cy + 0.4*r], fill=fill)
    draw.ellipse([cx + 0.2*r, cy - 0.9*r, cx + 1.9*r, cy + 0.8*r], fill=fill)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    S = SIZE * 2
    img = radial_gradient(S, CLOUD_CYAN, BRAND_BLUE)
    draw = ImageDraw.Draw(img)

    draw.ellipse([0, 0, S, S], outline=DEEP, width=int(S*0.018))

    # cloud sits in the upper third
    draw_cloud(draw, S/2, S*0.36, S/1000 * 1.7, WHITE)

    # code prompt mark </> centered inside the cloud
    prompt_font = ImageFont.truetype(F_XBOLD, int(S * 0.11))
    txt = "</>"
    tb = draw.textbbox((0, 0), txt, font=prompt_font)
    tw, th = tb[2]-tb[0], tb[3]-tb[1]
    draw.text((S/2 - tw/2, S*0.36 - th/2 - tb[1]), txt, font=prompt_font, fill=BRAND_BLUE)

    # wordmark
    wm_font = ImageFont.truetype(F_XBOLD, int(S * 0.092))
    wm = "SF DAILY"
    wb = draw.textbbox((0, 0), wm, font=wm_font)
    draw.text((S/2 - (wb[2]-wb[0])/2, S*0.64), wm, font=wm_font, fill=WHITE)

    sub_font = ImageFont.truetype(F_BOLD, int(S * 0.044))
    sub = "DEVELOPER TIPS"
    sbb = draw.textbbox((0, 0), sub, font=sub_font)
    draw.text((S/2 - (sbb[2]-sbb[0])/2, S*0.64 + int(S*0.105)), sub, font=sub_font, fill=(214, 237, 252))

    # circular mask
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    mask = Image.new("L", (SIZE, SIZE), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, SIZE, SIZE], fill=255)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    path = os.path.join(OUTPUT_DIR, "profile_picture.png")
    out.save(path)
    print("Saved", path)


if __name__ == "__main__":
    main()
