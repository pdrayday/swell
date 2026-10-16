#!/usr/bin/env python3
"""Render silent Swell/SWOLL loops as original motion graphics.

Everything visible is drawn here. No screenshots, product photos, splash renders,
or pre-existing bottle graphics are composited into the videos.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
import os
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT, FPS = 720, 1280, 30
DURATION = 18.0
FRAMES = int(FPS * DURATION)
FLOOR_Y = 1040

SCENES = {
    "shakes": ["cc", "choc", "cbutter", "shortcake", "matcha", "pumpkin"],
    "smoothies": ["sm_mango", "sm_berry", "sm_apple", "sm_blue", "sm_ring", "sm_pina"],
}

FLAVORS = {
    "cc": ("COOKIES & CREAM", "MILKSHAKE TASTE"),
    "choc": ("CHOCOLATE", "MILKSHAKE TASTE"),
    "cbutter": ("COOKIE BUTTER", "MILKSHAKE TASTE"),
    "shortcake": ("STRAWBERRY\nSHORTCAKE", "MILKSHAKE TASTE"),
    "matcha": ("MATCHA", "MILKSHAKE TASTE"),
    "pumpkin": ("PUMPKIN SPICE", "MILKSHAKE TASTE"),
    "sm_mango": ("MANGO", "SMOOTH & CREAMY"),
    "sm_berry": ("BERRY BLISS", "SMOOTH & CREAMY"),
    "sm_apple": ("SOUR APPLE", "SMOOTH & CREAMY"),
    "sm_blue": ("BLUE RASPBERRY", "SMOOTH & CREAMY"),
    "sm_ring": ("PEACH RING", "SMOOTH & CREAMY"),
    "sm_pina": ("PIÑA COLADA", "SMOOTH & CREAMY"),
}

PALETTES = {
    "shakes": {"top": (249, 232, 237), "bottom": (225, 173, 188), "floor": (235, 198, 208), "swell": (235, 193, 205)},
    "smoothies": {"top": (255, 249, 222), "bottom": (239, 211, 130), "floor": (247, 228, 169), "swell": (244, 220, 140)},
}

FONT_SCRIPT = "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc"
FONT_SERIF = "/System/Library/Fonts/Supplemental/Didot.ttc"
FONT_BODONI = "/System/Library/Fonts/Supplemental/Bodoni 72.ttc"
FONT_SANS = "/System/Library/Fonts/Avenir Next.ttc"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_BLOCK = "/System/Library/Fonts/Supplemental/Impact.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(7, size))


def centered(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, face: ImageFont.FreeTypeFont, fill, spacing: int = 2) -> None:
    draw.multiline_text(xy, text, font=face, fill=fill, anchor="mm", align="center", spacing=spacing)


def fitted(draw: ImageDraw.ImageDraw, text: str, path: str, size: int, width: int) -> ImageFont.FreeTypeFont:
    while size > 7:
        face = font(path, size)
        box = draw.multiline_textbbox((0, 0), text, font=face, align="center", spacing=1)
        if box[2] - box[0] <= width:
            return face
        size -= 1
    return font(path, 7)


def background(line: str) -> Image.Image:
    p = PALETTES[line]
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    v = (yy / (HEIGHT - 1))[..., None]
    top, bottom = np.array(p["top"], np.float32), np.array(p["bottom"], np.float32)
    arr = top * (1 - v) + bottom * v
    glow = np.exp(-(((xx - WIDTH * .5) / 410) ** 2 + ((yy - HEIGHT * .29) / 520) ** 2))[..., None]
    arr = arr * (1 - glow * .24) + 255 * glow * .24
    floor = np.array(p["floor"], np.float32)
    mix = np.clip((yy - 995) / 180, 0, 1)[..., None]
    arr = arr * (1 - mix * .58) + floor * mix * .58
    edge = np.clip(((xx - WIDTH / 2) / (WIDTH / 2)) ** 2, 0, 1)[..., None]
    arr *= 1 - edge * .055
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def bottle_mask(w: int, h: int) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx = w / 2
    profile = [
        (.00, .24), (.07, .29), (.12, .29), (.15, .235), (.19, .33),
        (.25, .43), (.39, .42), (.46, .375), (.56, .365), (.63, .385),
        (.88, .44), (.96, .43), (1.00, .36),
    ]
    left = [(cx - w * half, h * y) for y, half in profile]
    right = [(cx + w * half, h * y) for y, half in reversed(profile)]
    d.polygon(left + right, fill=255)
    d.rounded_rectangle((cx - w * .27, 0, cx + w * .27, h * .135), radius=w * .075, fill=255)
    d.rectangle((cx - w * .235, h * .11, cx + w * .235, h * .205), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(max(1, w * .003)))


def symbol(flavor: str, size: int, variant: int = 0, angle: float = 0) -> Image.Image:
    im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def leaf(x: int, y: int, r: int, color=(65, 111, 63, 255)) -> None:
        d.ellipse((x - r, y - r // 2, x + r, y + r // 2), fill=color)
        d.line((x - r, y, x + r, y), fill=(38, 79, 43, 210), width=max(2, r // 8))

    if flavor == "cc":
        d.ellipse((34, 34, 146, 146), fill=(48, 35, 31, 255), outline=(18, 13, 12, 255), width=7)
        d.ellipse((51, 51, 129, 129), fill=(245, 238, 223, 255))
        d.ellipse((62, 62, 118, 118), fill=(54, 38, 32, 255))
        for a in range(0, 360, 45):
            x, y = 90 + math.cos(math.radians(a)) * 42, 90 + math.sin(math.radians(a)) * 42
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(110, 83, 70, 255))
    elif flavor == "choc":
        d.rounded_rectangle((34, 40, 146, 140), radius=10, fill=(83, 43, 30, 255), outline=(48, 24, 20, 255), width=6)
        d.line((90, 43, 90, 137), fill=(153, 91, 61, 255), width=5)
        d.line((37, 90, 143, 90), fill=(153, 91, 61, 255), width=5)
        d.polygon([(42, 48), (82, 48), (72, 78), (49, 78)], fill=(132, 72, 48, 255))
    elif flavor == "cbutter":
        d.rounded_rectangle((34, 48, 146, 132), radius=15, fill=(185, 119, 58, 255), outline=(111, 65, 31, 255), width=6)
        d.rounded_rectangle((48, 61, 132, 119), radius=11, outline=(222, 163, 87, 255), width=5)
        d.line((59, 78, 121, 78), fill=(125, 76, 37, 255), width=4)
        d.line((59, 101, 121, 101), fill=(125, 76, 37, 255), width=4)
    elif flavor == "shortcake":
        if variant % 2:
            d.polygon([(42, 48), (142, 48), (126, 136), (58, 136)], fill=(246, 229, 196, 255), outline=(175, 111, 78, 255))
            d.rectangle((50, 74, 134, 91), fill=(207, 74, 81, 255)); d.rectangle((54, 103, 130, 116), fill=(255, 252, 242, 255))
        else:
            d.ellipse((45, 45, 135, 139), fill=(207, 46, 62, 255), outline=(143, 26, 39, 255), width=5)
            d.polygon([(48, 54), (68, 24), (90, 52), (112, 24), (134, 54)], fill=(70, 126, 65, 255))
            for x, y in ((65, 74), (94, 67), (112, 92), (76, 108), (100, 119)):
                d.ellipse((x - 3, y - 4, x + 3, y + 4), fill=(248, 224, 125, 255))
    elif flavor == "matcha":
        leaf(88, 92, 58, (81, 127, 72, 255)); leaf(105, 68, 44, (111, 151, 89, 255))
        d.arc((38, 38, 144, 148), 195, 322, fill=(222, 235, 193, 255), width=6)
    elif flavor == "pumpkin":
        if variant % 2:
            d.rounded_rectangle((70, 24, 98, 151), radius=10, fill=(128, 70, 36, 255), outline=(83, 43, 24, 255), width=5)
            d.line((76, 36, 92, 140), fill=(206, 130, 72, 255), width=4)
        else:
            d.ellipse((35, 52, 145, 140), fill=(218, 119, 44, 255), outline=(137, 71, 29, 255), width=5)
            d.ellipse((59, 47, 121, 143), fill=(239, 143, 54, 255), outline=(183, 94, 34, 255), width=4)
            d.rectangle((83, 28, 98, 56), fill=(80, 100, 55, 255))
    elif flavor == "sm_mango":
        d.pieslice((28, 38, 150, 152), 205, 350, fill=(248, 181, 55, 255), outline=(213, 120, 35, 255), width=6)
        d.pieslice((51, 60, 129, 133), 205, 350, fill=(255, 226, 112, 255)); leaf(114, 53, 34)
    elif flavor == "sm_berry":
        colors = [(180, 32, 58, 255), (46, 62, 132, 255), (205, 48, 68, 255)]
        for i, (x, y) in enumerate(((64, 66), (100, 57), (122, 88), (88, 101), (58, 111), (111, 121))):
            d.ellipse((x - 25, y - 25, x + 25, y + 25), fill=colors[i % 3], outline=(255, 255, 255, 70), width=3)
        leaf(89, 43, 35)
    elif flavor == "sm_apple":
        d.ellipse((43, 46, 137, 142), fill=(147, 190, 67, 255), outline=(77, 123, 40, 255), width=6)
        d.pieslice((58, 62, 129, 137), 60, 300, fill=(232, 241, 186, 255)); d.line((90, 52, 96, 25), fill=(86, 62, 38, 255), width=7); leaf(112, 38, 27)
    elif flavor == "sm_blue":
        for x, y in ((74, 48), (108, 51), (53, 78), (89, 82), (124, 83), (65, 114), (102, 119)):
            d.ellipse((x - 25, y - 25, x + 25, y + 25), fill=(47, 84, 180, 255), outline=(26, 54, 131, 255), width=4)
        leaf(112, 34, 30)
    elif flavor == "sm_ring":
        d.ellipse((34, 34, 146, 146), fill=(244, 139, 76, 255), outline=(218, 86, 61, 255), width=7)
        d.ellipse((65, 65, 115, 115), fill=(255, 225, 152, 0)); d.arc((43, 43, 137, 137), 195, 335, fill=(255, 220, 142, 255), width=13)
    elif flavor == "sm_pina":
        if variant % 2:
            d.pieslice((35, 45, 145, 155), 180, 360, fill=(247, 245, 226, 255), outline=(108, 78, 54, 255), width=7)
            d.pieslice((55, 65, 125, 135), 180, 360, fill=(222, 221, 208, 255))
        else:
            d.ellipse((54, 55, 126, 150), fill=(230, 177, 50, 255), outline=(147, 103, 30, 255), width=5)
            for off in (-20, 0, 20):
                d.line((64, 100 + off, 116, 135 + off), fill=(160, 112, 32, 255), width=3); d.line((116, 100 + off, 64, 135 + off), fill=(160, 112, 32, 255), width=3)
            d.polygon([(60, 63), (70, 20), (88, 59), (101, 16), (109, 64), (132, 33), (120, 75)], fill=(66, 123, 65, 255))

    im = im.filter(ImageFilter.GaussianBlur(.25)).resize((size, size), Image.Resampling.LANCZOS)
    return im.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True) if angle else im


def droplets(layer: Image.Image, mask: Image.Image, seed: int, w: int, h: int) -> None:
    rng = random.Random(seed)
    drops = Image.new("RGBA", layer.size, (0, 0, 0, 0)); d = ImageDraw.Draw(drops)
    for _ in range(72):
        x, y = rng.randint(round(w * .12), round(w * .88)), rng.randint(round(h * .03), round(h * .94))
        r = rng.randint(max(1, w // 180), max(2, w // 46))
        d.ellipse((x - r, y - r * 1.35, x + r, y + r * 1.35), fill=(255, 255, 255, 34), outline=(255, 255, 255, 72), width=max(1, w // 170))
        d.ellipse((x - r * .35, y - r * .75, x + r * .05, y - r * .2), fill=(255, 255, 255, 115))
    drops.putalpha(Image.fromarray(np.minimum(np.asarray(drops.getchannel("A")), np.asarray(mask)).astype(np.uint8)))
    layer.alpha_composite(drops)


def make_bottle(line: str, flavor: str, swoll: bool) -> Image.Image:
    height = 820 if swoll else round(820 * .75)
    width = round(height * (.37 if swoll else .36))
    s = 2; w, h = width * s, height * s
    mask = bottle_mask(w, h)
    base = (177, 204, 239) if swoll else PALETTES[line]["swell"]
    yy, xx = np.mgrid[0:h, 0:w]
    light = .74 + (1 - np.abs((xx - w / 2) / (w / 2))) * .28
    top_glow = .05 * np.exp(-((yy - h * .23) / (h * .23)) ** 2)
    arr = np.zeros((h, w, 4), np.uint8)
    for c in range(3): arr[..., c] = np.clip(base[c] * light + 255 * top_glow, 0, 255)
    arr[..., 3] = np.asarray(mask)
    bottle = Image.fromarray(arr, "RGBA")

    details = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(details)
    ink = (20, 23, 27, 255)
    accent = (69, 99, 137, 255) if swoll else ((158, 77, 96, 255) if line == "shakes" else (126, 102, 45, 255))
    cx = w / 2
    d.rounded_rectangle((w * .23, h * .018, w * .77, h * .125), radius=w * .07, outline=(255, 255, 255, 145), width=max(2, w // 75))
    for i in range(7):
        x = w * (.29 + i * .07); d.line((x, h * .03, x, h * .105), fill=(82, 91, 108, 35), width=max(1, w // 150))
    d.line((w * .23, h * .115, w * .77, h * .115), fill=(79, 83, 95, 72), width=max(2, w // 80))
    d.line((w * .17, h * .418, w * .83, h * .418), fill=accent, width=max(3, w // 70))
    d.line((w * .15, h * .595, w * .85, h * .595), fill=accent, width=max(3, w // 70))
    d.line((w * .15, h * .96, w * .85, h * .96), fill=(45, 52, 61, 45), width=max(2, w // 90))
    centered(d, (cx, h * (.235 if swoll else .275)), "Swell", font(FONT_SCRIPT, round(w * (.16 if swoll else .22))), ink)
    product = "PROTEIN SMOOTHIE" if line == "smoothies" else "PROTEIN SHAKE"
    if swoll:
        centered(d, (cx, h * .305), "SWOLL", font(FONT_BLOCK, round(w * .22)), ink)
        centered(d, (cx, h * .365), product, fitted(d, product, FONT_BOLD, round(w * .052), round(w * .72)), accent)
        centered(d, (cx, h * .486), "50g", font(FONT_SERIF, round(w * .25)), ink)
        centered(d, (cx, h * .555), "PROTEIN", font(FONT_BOLD, round(w * .066)), accent)
    else:
        centered(d, (cx, h * .355), product, fitted(d, product, FONT_BOLD, round(w * .058), round(w * .72)), accent)
        centered(d, (cx, h * .505), "30g", font(FONT_SERIF, round(w * .27)), ink)
        centered(d, (cx, h * .57), "PROTEIN", font(FONT_BOLD, round(w * .067)), accent)
    name, taste = FLAVORS[flavor]
    centered(d, (cx, h * .64), name, fitted(d, name, FONT_BODONI, round(w * .075), round(w * .76)), ink, spacing=max(1, w // 90))
    icon = symbol(flavor, round(w * .41), angle=-4 if swoll else 4)
    details.alpha_composite(icon, (round(cx - icon.width / 2), round(h * .68)))
    centered(d, (cx, h * .885), taste, fitted(d, taste, FONT_BOLD, round(w * .047), round(w * .70)), accent)
    centered(d, (cx, h * .922), "14 FL OZ (414 mL)", fitted(d, "14 FL OZ (414 mL)", FONT_SANS, round(w * .043), round(w * .65)), accent)
    details.putalpha(Image.fromarray(np.minimum(np.asarray(details.getchannel("A")), np.asarray(mask)).astype(np.uint8)))
    bottle.alpha_composite(details)
    gloss = Image.new("RGBA", (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(gloss)
    gd.ellipse((w * .19, h * .16, w * .42, h * .91), fill=(255, 255, 255, 28))
    gloss = gloss.filter(ImageFilter.GaussianBlur(w * .065))
    gloss.putalpha(Image.fromarray(np.minimum(np.asarray(gloss.getchannel("A")), np.asarray(mask)).astype(np.uint8)))
    bottle.alpha_composite(gloss)
    droplets(bottle, mask, sum(ord(c) for c in flavor) + (700 if swoll else 300), w, h)
    return bottle.resize((width, height), Image.Resampling.LANCZOS)


@dataclass
class Prop:
    sprite: Image.Image
    x: float
    y: float
    amp: float
    phase: float
    speed: float


@dataclass
class Scene:
    flavor: str
    swell: Image.Image
    swoll: Image.Image
    back: list[Prop]
    front: list[Prop]


def make_props(flavor: str) -> tuple[list[Prop], list[Prop]]:
    rng = random.Random(2401 + sum((i + 1) * ord(c) for i, c in enumerate(flavor)))
    back, front = [], []
    anchors = [(-8, 360), (55, 510), (118, 305), (175, 745), (240, 450), (310, 260), (380, 690), (450, 390), (525, 785), (602, 505), (682, 325), (725, 725), (92, 900), (645, 925), (332, 890)]
    for i, (x, y) in enumerate(anchors):
        size = rng.randint(34, 68) if i < 12 else rng.randint(46, 78)
        prop = Prop(symbol(flavor, size, i, rng.uniform(-30, 30)), x + rng.uniform(-22, 22), y + rng.uniform(-35, 35), rng.uniform(7, 22), rng.uniform(0, math.tau), rng.choice((.8, 1., 1.2, 1.5)))
        # All flavor motion remains behind the products so label readability never changes.
        back.append(prop)
    return back, front


def make_scene(line: str, flavor: str) -> Scene:
    back, front = make_props(flavor)
    return Scene(flavor, make_bottle(line, flavor, False), make_bottle(line, flavor, True), back, front)


def composite(canvas: Image.Image, sprite: Image.Image, x: float, y: float, amount: float) -> None:
    if amount <= 0: return
    im = sprite
    if amount < .999:
        im = sprite.copy(); a = np.asarray(im.getchannel("A"), np.float32)
        im.putalpha(Image.fromarray(np.clip(a * amount, 0, 255).astype(np.uint8), "L"))
    canvas.alpha_composite(im, (round(x), round(y)))


def draw_prop(canvas: Image.Image, prop: Prop, theta: float, amount: float) -> None:
    x = prop.x + math.cos(theta * prop.speed + prop.phase) * prop.amp * .55 - prop.sprite.width / 2
    y = prop.y + math.sin(theta * prop.speed + prop.phase) * prop.amp - prop.sprite.height / 2
    composite(canvas, prop.sprite, x, y, amount)


def paste_bottle(canvas: Image.Image, bottle: Image.Image, cx: float, base: float, theta: float, phase: float, amount: float) -> None:
    # The product stays completely fixed; only the flavor environment moves.
    x, y = cx - bottle.width / 2, base - bottle.height
    shadow_alpha = bottle.getchannel("A").filter(ImageFilter.GaussianBlur(20)).point(lambda a: a * 70 // 255)
    shadow = Image.new("RGBA", bottle.size, (55, 35, 42, 0)); shadow.putalpha(shadow_alpha)
    composite(canvas, shadow, x + 12, y + 22, amount); composite(canvas, bottle, x, y, amount)


def scene_layer(scene: Scene, theta: float, amount: float, x_shift: float) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    for prop in scene.back: draw_prop(layer, prop, theta, amount * .72)
    milk = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)); d = ImageDraw.Draw(milk)
    rng = random.Random(981 + sum(ord(c) for c in scene.flavor))
    for i in range(26):
        bx, by, r = rng.uniform(12, WIDTH - 12), rng.uniform(260, 990), rng.uniform(2.5, 8)
        x = bx + math.sin(theta * (1 + i % 3) + i) * rng.uniform(5, 18)
        y = by + math.cos(theta * (1 + i % 2) + i * .7) * rng.uniform(6, 20)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 252, 244, round(105 * amount)), outline=(255, 255, 255, round(160 * amount)), width=1)
    layer = Image.alpha_composite(layer, milk)
    ground = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)); gd = ImageDraw.Draw(ground)
    gd.ellipse((34, FLOOR_Y - 15, 686, FLOOR_Y + 48), fill=(62, 39, 47, round(50 * amount)))
    layer = Image.alpha_composite(layer, ground.filter(ImageFilter.GaussianBlur(24)))
    paste_bottle(layer, scene.swell, 155 + x_shift, FLOOR_Y, theta, .6, amount)
    paste_bottle(layer, scene.swoll, 505 + x_shift, FLOOR_Y, theta, 2.1, amount)
    for prop in scene.front: draw_prop(layer, prop, theta, amount * .92)
    return layer


def make_frame(scenes: list[Scene], bg: Image.Image, index: int) -> Image.Image:
    t = index / FPS; theta = math.tau * t / DURATION; n = len(scenes)
    phase = t / (DURATION / n); current = int(math.floor(phase)) % n; frac = phase - math.floor(phase)
    if frac <= .66: nxt_w = 0.
    else:
        u = (frac - .66) / .34; nxt_w = .5 - .5 * math.cos(math.pi * u)
    cur_w, nxt = 1 - nxt_w, (current + 1) % n
    frame = bg.copy()
    if cur_w > .001: frame = Image.alpha_composite(frame, scene_layer(scenes[current], theta, cur_w, 0))
    if nxt_w > .001: frame = Image.alpha_composite(frame, scene_layer(scenes[nxt], theta, nxt_w, 0))
    sheen = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)); sd = ImageDraw.Draw(sheen); sx = WIDTH * .5 + math.sin(theta) * 90
    sd.ellipse((sx - 280, 90, sx + 280, 965), fill=(255, 255, 255, 17))
    return Image.alpha_composite(frame, sheen.filter(ImageFilter.GaussianBlur(90))).convert("RGB")


def render_mp4(line: str, output: Path, ffmpeg: str, qa_dir: Path) -> None:
    scenes, bg = [make_scene(line, f) for f in SCENES[line]], background(line)
    output.parent.mkdir(parents=True, exist_ok=True); qa_dir.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "title=Swell original motion-graphics loop", str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE); assert proc.stdin is not None
    qa = {0, FRAMES // 6, FRAMES * 2 // 6, FRAMES * 3 // 6, FRAMES * 4 // 6, FRAMES * 5 // 6, FRAMES - 1}
    for i in range(FRAMES):
        frame = make_frame(scenes, bg, i)
        if i in qa: frame.save(qa_dir / f"{line}-{i:03d}.jpg", quality=91)
        proc.stdin.write(np.asarray(frame, np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait() != 0: raise SystemExit(f"Video render failed for {line}")


def make_webm(mp4: Path, webm: Path, ffmpeg: str) -> None:
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4), "-an", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "31", "-row-mt", "1", "-pix_fmt", "yuv420p", str(webm)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ffmpeg", default=os.environ.get("SWELL_FFMPEG", "ffmpeg"))
    parser.add_argument("--qa-dir", type=Path, default=Path("/tmp/swell-video-qa/original-motion"))
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/swell-video-render/original-motion"))
    args = parser.parse_args()
    for line in ("shakes", "smoothies"):
        mp4 = args.output_dir / f"hero_{line}.mp4"
        render_mp4(line, mp4, args.ffmpeg, args.qa_dir)
        make_webm(mp4, args.output_dir / f"hero_{line}.webm", args.ffmpeg)


if __name__ == "__main__":
    main()
