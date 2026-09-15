"""Creates a reusable cloud badge PNG (original art) for the card corner."""
import os
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE_DIR, "assets", "cloud_badge.png")

BLUE = (0, 161, 225)
BLUE_DK = (0, 140, 205)


def make(size=400):
    S = size * 3
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S / 2
    r = S * 0.15
    # fluffy cloud from circles + base slab
    d.rounded_rectangle([cx - 2.2*r, cy - 0.1*r, cx + 2.2*r, cy + 1.1*r],
                        radius=int(0.6*r), fill=BLUE)
    d.ellipse([cx - 2.1*r, cy - 0.6*r, cx - 0.5*r, cy + 1.0*r], fill=BLUE)
    d.ellipse([cx - 1.3*r, cy - 1.4*r, cx + 0.5*r, cy + 0.4*r], fill=BLUE)
    d.ellipse([cx + 0.1*r, cy - 1.0*r, cx + 2.0*r, cy + 0.9*r], fill=BLUE)
    d.ellipse([cx - 0.2*r, cy - 1.5*r, cx + 1.4*r, cy + 0.2*r], fill=BLUE)
    img = img.resize((size, size), Image.LANCZOS)
    img.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    make()
