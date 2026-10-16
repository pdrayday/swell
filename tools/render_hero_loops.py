#!/usr/bin/env python3
"""Render the silent, seamless Swell/SWOLL home-page hero loops."""

from __future__ import annotations

import argparse
import math
import os
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH, HEIGHT = 720, 1280
FPS = 30
DURATION = 12.0
FRAMES = int(FPS * DURATION)

SCENES = {
    "shakes": ["cc", "choc", "cbutter", "shortcake", "matcha", "pumpkin"],
    "smoothies": ["sm_mango", "sm_berry", "sm_apple", "sm_blue", "sm_ring", "sm_pina"],
}

PALETTES = {
    "shakes": {
        "top": (247, 227, 233),
        "bottom": (224, 166, 181),
        "floor": (236, 197, 207),
        "particles": [(255, 251, 248), (252, 236, 226), (151, 97, 86), (109, 67, 60)],
    },
    "smoothies": {
        "top": (255, 247, 213),
        "bottom": (238, 207, 118),
        "floor": (247, 225, 160),
        "particles": [(255, 252, 230), (248, 218, 133), (183, 91, 91), (102, 126, 85)],
    },
}


def cover_gradient(line: str) -> Image.Image:
    p = PALETTES[line]
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    v = (yy / (HEIGHT - 1))[..., None]
    top = np.array(p["top"], dtype=np.float32)
    bottom = np.array(p["bottom"], dtype=np.float32)
    arr = top * (1 - v) + bottom * v

    # Soft studio light centered above the products.
    radial = np.exp(-(((xx - WIDTH * 0.5) / 430) ** 2 + ((yy - HEIGHT * 0.30) / 580) ** 2))[..., None]
    arr = arr * (1 - radial * 0.22) + 255 * radial * 0.22

    # A quiet floor below the bottles, with no visible scene cut.
    floor = np.array(p["floor"], dtype=np.float32)
    floor_mix = np.clip((yy - 1020) / 180, 0, 1)[..., None]
    arr = arr * (1 - floor_mix * 0.55) + floor * floor_mix * 0.55

    # Very light edge vignette keeps attention on the bottle silhouettes.
    edge = np.clip(((xx - WIDTH / 2) / (WIDTH / 2)) ** 2, 0, 1)[..., None]
    arr *= 1 - edge * 0.045
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def trim_alpha(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    box = im.getchannel("A").getbbox()
    return im.crop(box) if box else im


def fit_height(im: Image.Image, height: int) -> Image.Image:
    width = max(1, round(im.width * height / im.height))
    return im.resize((width, height), Image.Resampling.LANCZOS)


def paste_with_shadow(canvas: Image.Image, im: Image.Image, xy: tuple[int, int], shadow_strength: int = 95) -> None:
    x, y = xy
    alpha = im.getchannel("A")
    shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(23)).point(lambda a: a * shadow_strength // 255)
    shadow = Image.new("RGBA", im.size, (50, 25, 35, 0))
    shadow.putalpha(shadow_alpha)
    canvas.alpha_composite(shadow, (x + 14, y + 27))
    canvas.alpha_composite(im, (x, y))


def make_pair(root: Path, line: str, flavor: str) -> Image.Image:
    splash = trim_alpha(Image.open(root / "img" / f"splash_{flavor}.webp"))
    swoll = trim_alpha(Image.open(root / "img" / "swoll" / f"{flavor}.png"))

    swell_h = 760 if line == "shakes" else 750
    swoll_h = 820
    splash = fit_height(splash, swell_h)
    swoll = fit_height(swoll, swoll_h)

    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    # Keep both silhouettes fully inside the site's 4:5 hero crop.
    floor_y = 1060
    swoll_x = 252
    swell_x = -4
    paste_with_shadow(layer, swoll, (swoll_x, floor_y - swoll.height), 88)
    paste_with_shadow(layer, splash, (swell_x, floor_y - splash.height), 105)

    # Grounding shadow shared by both bottles.
    ground = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(ground)
    gd.ellipse((70, floor_y - 20, 690, floor_y + 52), fill=(70, 35, 45, 58))
    ground = ground.filter(ImageFilter.GaussianBlur(24))
    layer = Image.alpha_composite(ground, layer)
    return layer


def opacity(im: Image.Image, amount: float) -> Image.Image:
    if amount >= 0.999:
        return im
    out = im.copy()
    a = np.asarray(out.getchannel("A"), dtype=np.float32)
    out.putalpha(Image.fromarray(np.clip(a * amount, 0, 255).astype(np.uint8), "L"))
    return out


def particles(line: str, theta: float, foreground: bool = False) -> Image.Image:
    rng = random.Random(419 if line == "shakes" else 811)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    colors = PALETTES[line]["particles"]
    count = 10 if foreground else 24
    for i in range(count):
        bx = rng.uniform(-20, WIDTH + 20)
        by = rng.uniform(80, 1100)
        size = rng.uniform(3, 10) * (1.35 if foreground else 1)
        phase = rng.uniform(0, math.tau)
        speed = rng.choice((1, 1, 2, 3))
        x = bx + math.sin(theta * speed + phase) * rng.uniform(6, 20)
        y = by + math.cos(theta * speed + phase) * rng.uniform(8, 26)
        r, g, b = colors[i % len(colors)]
        alpha = 80 if foreground else 48
        if i % 4 == 0:
            draw.rounded_rectangle((x - size * .55, y - size, x + size * .55, y + size), radius=size * .35, fill=(r, g, b, alpha))
        else:
            draw.ellipse((x - size, y - size, x + size, y + size), fill=(r, g, b, alpha))
    if not foreground:
        layer = layer.filter(ImageFilter.GaussianBlur(1.2))
    return layer


def frame_for(line: str, pairs: list[Image.Image], index: int, background: Image.Image) -> Image.Image:
    t = index / FPS
    theta = math.tau * t / DURATION
    n = len(pairs)
    phase = t / (DURATION / n)
    current = int(math.floor(phase)) % n
    frac = phase - math.floor(phase)

    # Hold long enough to read the bottle, then ease into the next flavor.
    hold = 0.55
    if frac <= hold:
        nxt_w = 0.0
    else:
        u = (frac - hold) / (1 - hold)
        nxt_w = 0.5 - 0.5 * math.cos(math.pi * u)
    cur_w = 1.0 - nxt_w
    nxt = (current + 1) % n

    frame = background.copy()
    frame = Image.alpha_composite(frame, particles(line, theta, foreground=False))

    bob_cur = round(8 * math.sin(theta * 2 + current * .8))
    bob_nxt = round(8 * math.sin(theta * 2 + nxt * .8))
    cur_x = round(-18 * nxt_w + 6 * math.cos(theta + current))
    nxt_x = round(18 * cur_w + 6 * math.cos(theta + nxt))

    if cur_w > .001:
        frame.alpha_composite(opacity(pairs[current], cur_w), (cur_x, bob_cur))
    if nxt_w > .001:
        frame.alpha_composite(opacity(pairs[nxt], nxt_w), (nxt_x, bob_nxt))

    frame = Image.alpha_composite(frame, particles(line, theta, foreground=True))

    # Seamless breathing highlight; exact period is the full clip duration.
    sheen = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sx = WIDTH * .5 + math.sin(theta) * 90
    sd.ellipse((sx - 260, 75, sx + 260, 930), fill=(255, 255, 255, 18))
    sheen = sheen.filter(ImageFilter.GaussianBlur(80))
    frame = Image.alpha_composite(frame, sheen)
    return frame.convert("RGB")


def render_mp4(root: Path, line: str, output: Path, ffmpeg: str, qa_dir: Path) -> None:
    pairs = [make_pair(root, line, flavor) for flavor in SCENES[line]]
    background = cover_gradient(line)
    output.parent.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "title=Swell seamless hero loop",
        str(output),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for i in range(FRAMES):
        frame = frame_for(line, pairs, i, background)
        if i in (0, FRAMES // 2, FRAMES - 1):
            frame.save(qa_dir / f"{line}-{i:03d}.jpg", quality=88)
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit(f"Video render failed for {line}")


def make_webm(mp4: Path, webm: Path, ffmpeg: str) -> None:
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4),
        "-an", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-row-mt", "1",
        "-pix_fmt", "yuv420p", str(webm),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ffmpeg", default=os.environ.get("SWELL_FFMPEG", "ffmpeg"))
    parser.add_argument("--qa-dir", type=Path, default=Path("/tmp/swell-video-qa/new"))
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/swell-video-render"))
    args = parser.parse_args()

    for line in ("shakes", "smoothies"):
        mp4 = args.output_dir / f"hero_{line}.mp4"
        render_mp4(args.root, line, mp4, args.ffmpeg, args.qa_dir)
        make_webm(mp4, args.output_dir / f"hero_{line}.webm", args.ffmpeg)


if __name__ == "__main__":
    main()
