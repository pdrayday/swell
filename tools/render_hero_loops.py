#!/usr/bin/env python3
"""Render the silent, seamless Swell/SWOLL homepage hero loops.

Bottles stay stationary against a still studio background. Flavors crossfade
without floating ingredients, animated splashes, particles, or moving lights.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH, HEIGHT, FPS = 720, 1280, 30
DURATION = 18.0
FRAMES = int(FPS * DURATION)
FLOOR_Y = 1045

SCENES = {
    "shakes": ["cc", "choc", "cbutter", "shortcake", "matcha", "pumpkin"],
    "smoothies": ["sm_mango", "sm_berry", "sm_apple", "sm_blue", "sm_ring", "sm_pina"],
}

PALETTES = {
    "shakes": {"top": (248, 231, 236), "bottom": (224, 169, 184), "floor": (235, 198, 207)},
    "smoothies": {"top": (255, 248, 219), "bottom": (239, 210, 126), "floor": (247, 226, 162)},
}


def opacity(im: Image.Image, amount: float) -> Image.Image:
    if amount >= .999:
        return im
    out = im.copy()
    alpha = np.asarray(out.getchannel("A"), dtype=np.float32)
    out.putalpha(Image.fromarray(np.clip(alpha * amount, 0, 255).astype(np.uint8), "L"))
    return out


def trim_alpha(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    box = im.getchannel("A").getbbox()
    return im.crop(box) if box else im


def fit_height(im: Image.Image, height: int) -> Image.Image:
    width = max(1, round(im.width * height / im.height))
    return im.resize((width, height), Image.Resampling.LANCZOS)


def studio_background(line: str) -> Image.Image:
    p = PALETTES[line]
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    v = (yy / (HEIGHT - 1))[..., None]
    top = np.array(p["top"], np.float32)
    bottom = np.array(p["bottom"], np.float32)
    arr = top * (1 - v) + bottom * v

    central = np.exp(-(((xx - WIDTH * .5) / 420) ** 2 + ((yy - HEIGHT * .30) / 550) ** 2))[..., None]
    arr = arr * (1 - central * .23) + 255 * central * .23
    floor = np.array(p["floor"], np.float32)
    floor_mix = np.clip((yy - 1000) / 170, 0, 1)[..., None]
    arr = arr * (1 - floor_mix * .57) + floor * floor_mix * .57
    edge = np.clip(((xx - WIDTH / 2) / (WIDTH / 2)) ** 2, 0, 1)[..., None]
    arr *= 1 - edge * .045
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def approved_bottles(root: Path, flavor: str) -> tuple[Image.Image, Image.Image]:
    swell = trim_alpha(Image.open(root / "img" / f"b_{flavor}.webp"))
    swoll_path = root / "img" / f"sw_{flavor}_lg.webp"
    if not swoll_path.exists():
        swoll_path = root / "img" / "swoll" / f"{flavor}.png"
    swoll = trim_alpha(Image.open(swoll_path))
    swoll_h = 820
    swell_h = round(swoll_h * .75)
    return fit_height(swell, swell_h), fit_height(swoll, swoll_h)


@dataclass(eq=False)
class Scene:
    flavor: str
    swell: Image.Image
    swoll: Image.Image


def make_scene(root: Path, flavor: str) -> Scene:
    swell, swoll = approved_bottles(root, flavor)
    return Scene(flavor, swell, swoll)


def composite(canvas: Image.Image, im: Image.Image, x: float, y: float, amount: float = 1) -> None:
    if amount <= 0:
        return
    canvas.alpha_composite(opacity(im, amount), (round(x), round(y)))


def stationary_bottle(canvas: Image.Image, bottle: Image.Image, center_x: float, amount: float) -> None:
    x, y = center_x - bottle.width / 2, FLOOR_Y - bottle.height
    alpha = bottle.getchannel("A")
    soft = alpha.filter(ImageFilter.GaussianBlur(22)).point(lambda a: a * 78 // 255)
    shadow = Image.new("RGBA", bottle.size, (62, 40, 48, 0))
    shadow.putalpha(soft)
    composite(canvas, shadow, x + 13, y + 23, amount)
    composite(canvas, bottle, x, y, amount)


@lru_cache(maxsize=12)
def scene_layer(scene: Scene) -> Image.Image:
    """A still product composition: flavor artwork stays on the bottle label."""
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    amount = 1.0

    ground = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(ground)
    gd.ellipse((40, FLOOR_Y - 17, 684, FLOOR_Y + 47), fill=(64, 39, 47, round(50 * amount)))
    layer = Image.alpha_composite(layer, ground.filter(ImageFilter.GaussianBlur(25)))

    stationary_bottle(layer, scene.swell, 154, amount)
    stationary_bottle(layer, scene.swoll, 505, amount)
    return layer


def frame_for(scenes: list[Scene], bg: Image.Image, index: int) -> Image.Image:
    t = index / FPS
    phase = t / (DURATION / len(scenes))
    current = int(math.floor(phase)) % len(scenes)
    frac = phase - math.floor(phase)
    if frac <= .66:
        next_weight = 0.0
    else:
        u = (frac - .66) / .34
        next_weight = .5 - .5 * math.cos(math.pi * u)
    current_weight = 1 - next_weight
    nxt = (current + 1) % len(scenes)

    frame = bg.copy()
    if current_weight > .001:
        frame = Image.alpha_composite(frame, opacity(scene_layer(scenes[current]), current_weight))
    if next_weight > .001:
        frame = Image.alpha_composite(frame, opacity(scene_layer(scenes[nxt]), next_weight))

    return frame.convert("RGB")


def render_mp4(root: Path, line: str, output: Path, ffmpeg: str, qa_dir: Path) -> None:
    scenes = [make_scene(root, flavor) for flavor in SCENES[line]]
    bg = studio_background(line)
    frame_for(scenes, bg, 0).save(root / "img" / f"poster_{line}.jpg", quality=91)
    output.parent.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "title=Swell seamless product film",
        str(output),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    qa_frames = {0, FRAMES // 6, FRAMES * 2 // 6, FRAMES * 3 // 6, FRAMES * 4 // 6, FRAMES * 5 // 6, FRAMES - 1}
    for i in range(FRAMES):
        frame = frame_for(scenes, bg, i)
        if i in qa_frames:
            frame.save(qa_dir / f"{line}-{i:03d}.jpg", quality=91)
        proc.stdin.write(np.asarray(frame, np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit(f"Video render failed for {line}")


def make_webm(mp4: Path, webm: Path, ffmpeg: str) -> None:
    subprocess.run([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4),
        "-an", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "31", "-row-mt", "1", "-pix_fmt", "yuv420p", str(webm),
    ], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ffmpeg", default=os.environ.get("SWELL_FFMPEG", "ffmpeg"))
    parser.add_argument("--qa-dir", type=Path, default=Path("/tmp/swell-video-qa/approved-bottles"))
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/swell-video-render/approved-bottles"))
    args = parser.parse_args()
    for line in ("shakes", "smoothies"):
        mp4 = args.output_dir / f"hero_{line}.mp4"
        render_mp4(args.root, line, mp4, args.ffmpeg, args.qa_dir)
        make_webm(mp4, args.output_dir / f"hero_{line}.webm", args.ffmpeg)


if __name__ == "__main__":
    main()
