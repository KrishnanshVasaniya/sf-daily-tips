"""
Builds a vertical MP4 Reel from the 3 generated tip slides.

Pipeline:
  - Each slide is shown for a set duration with a gentle zoom (Ken Burns)
  - Crossfade transitions between slides
  - Background music mixed in (looped/trimmed to video length), faded out at end
  - Output is 1080x1920 (9:16), H.264 + AAC, Instagram-Reels compatible

Requires: ffmpeg on PATH, and a music file at assets/music.mp3
(You supply the music file -- see README for free sources.)

Usage:
  python make_reel.py --slides output/tip1_slide1.png output/tip1_slide2.png output/tip1_slide3.png
  python make_reel.py            # auto-uses the 3 slides referenced in data/run_meta.json
"""

import argparse
import json
import os
import subprocess
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
META_PATH = os.path.join(BASE_DIR, "data", "run_meta.json")
MUSIC_PATH = os.path.join(ASSETS_DIR, "music.mp3")

REEL_W, REEL_H = 1080, 1920
# seconds each slide is on screen (problem gets a bit longer to read)
SLIDE_DURATIONS = [5.0, 6.0, 4.0]
XFADE = 0.6  # crossfade duration between slides


def slide_paths_from_meta():
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    # meta stores slide1/slide2; slide3 is same tag with _slide3
    s1 = os.path.join(BASE_DIR, meta["slide1_file"])
    base = s1.replace("_slide1.png", "")
    return [f"{base}_slide{i}.png" for i in (1, 2, 3)]


def build_slide_clip(src_png, duration, out_path):
    """Create a padded 9:16 clip from a slide with a slow zoom."""
    # Scale the 1080x1350 card onto a 1080x1920 canvas (blurred fill behind),
    # with a subtle zoom over the duration.
    fps = 30
    total_frames = int(duration * fps)
    vf = (
        # background: blurred, scaled-up copy filling 9:16
        f"[0:v]scale={REEL_W}:{REEL_H}:force_original_aspect_ratio=increase,"
        f"crop={REEL_W}:{REEL_H},boxblur=40:2,eq=brightness=-0.05[bg];"
        # foreground: the card, slow zoom
        f"[0:v]scale={REEL_W}:-1,"
        f"zoompan=z='min(zoom+0.0006,1.06)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={REEL_W}x{int(REEL_W*1350/1080)}:fps={fps}[fg];"
        # overlay fg centered on bg
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto[v]"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", src_png,
        "-filter_complex", vf, "-map", "[v]",
        "-t", str(duration), "-r", str(fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_with_xfade(clips, out_path):
    """Crossfade a list of clips together sequentially."""
    if len(clips) == 1:
        subprocess.run(["ffmpeg", "-y", "-i", clips[0], "-c", "copy", out_path],
                       check=True, capture_output=True)
        return

    # build filter chain of successive xfades
    inputs = []
    for c in clips:
        inputs += ["-i", c]

    filpieces = []
    prev = "0:v"
    offset = 0.0
    for i in range(1, len(clips)):
        offset += SLIDE_DURATIONS[i - 1] - XFADE
        out_label = f"x{i}"
        filpieces.append(
            f"[{prev}][{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[{out_label}]"
        )
        prev = out_label
    filtergraph = ";".join(filpieces)

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filtergraph, "-map", f"[{prev}]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def add_music(video_path, music_path, out_path):
    total = sum(SLIDE_DURATIONS) - XFADE * (len(SLIDE_DURATIONS) - 1)
    if not os.path.exists(music_path):
        # no music supplied: just copy the silent video through
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-c", "copy", out_path],
                       check=True, capture_output=True)
        print("NOTE: no assets/music.mp3 found -> Reel exported without audio.")
        return
    # loop/trim music to video length, fade out last 1s
    af = f"afade=t=out:st={max(0,total-1):.2f}:d=1,volume=0.6"
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-stream_loop", "-1", "-i", music_path,
        "-filter:a", af, "-map", "0:v", "-map", "1:a",
        "-t", f"{total:.2f}", "-c:v", "copy", "-c:a", "aac", "-shortest", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main_from_paths(slides, out_path):
    """Programmatic entry point used by daily_post.py."""
    for s in slides:
        if not os.path.exists(s):
            raise FileNotFoundError(f"Slide not found: {s}")
    with tempfile.TemporaryDirectory() as tmp:
        clips = []
        for i, src in enumerate(slides):
            clip = os.path.join(tmp, f"clip{i}.mp4")
            build_slide_clip(src, SLIDE_DURATIONS[i], clip)
            clips.append(clip)
        silent = os.path.join(tmp, "silent.mp4")
        concat_with_xfade(clips, silent)
        add_music(silent, MUSIC_PATH, out_path)
    print(f"Reel written: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slides", nargs=3)
    ap.add_argument("--out", default=os.path.join(OUTPUT_DIR, "reel.mp4"))
    args = ap.parse_args()
    slides = args.slides or slide_paths_from_meta()
    main_from_paths(slides, args.out)


if __name__ == "__main__":
    main()
