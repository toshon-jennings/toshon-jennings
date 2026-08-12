#!/usr/bin/env python3
"""Render the deterministic motion assets used by the GitHub profile README."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
FPS = 12
MONO = "/System/Library/Fonts/SFNSMono.ttf"
SERIF = "/System/Library/Fonts/NewYork.ttf"

PROFILE_THEMES = {
    "light": {
        "bg": "#FFFFFF",
        "panel": "#F6F8FA",
        "text": "#1F2328",
        "muted": "#59636E",
        "blue": "#0969DA",
        "blue_soft": "#DDF4FF",
        "border": "#D0D7DE",
    },
    "dark": {
        "bg": "#0D1117",
        "panel": "#161B22",
        "text": "#F0F6FC",
        "muted": "#8B949E",
        "blue": "#4493F8",
        "blue_soft": "#1F3A5F",
        "border": "#30363D",
    },
}

VERSED_THEMES = {
    "light": {
        "bg": "#F8F5F0",
        "panel": "#F1EBE1",
        "text": "#2A261F",
        "muted": "#786E5D",
        "accent": "#B87F25",
        "border": "#D6CAB4",
    },
    "dark": {
        "bg": "#12100C",
        "panel": "#1B1713",
        "text": "#EDE4D3",
        "muted": "#A99884",
        "accent": "#CBA14D",
        "border": "#423A2F",
    },
}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smooth(start: float, end: float, value: float) -> float:
    x = clamp((value - start) / (end - start))
    return x * x * (3 - 2 * x)


def rgba(hex_color: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        round(255 * clamp(alpha)),
    )


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    typeface: ImageFont.FreeTypeFont,
    color: str,
    alpha: float = 1.0,
    anchor: str = "la",
    spacing: int = 4,
) -> None:
    # Pillow's direct RGBA text path ignores fill alpha for antialiased glyph
    # masks on an RGB target. Compose type on its own layer so opacity-driven
    # entrances stay genuinely absent before they begin.
    target = draw._image
    overlay = Image.new("RGBA", target.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.multiline_text(
        xy,
        text,
        font=typeface,
        fill=rgba(color, alpha),
        anchor=anchor,
        spacing=spacing,
    )
    target.paste(overlay, (0, 0), overlay)


def partial_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    progress: float,
    fill: tuple[int, int, int, int],
    width: int,
) -> tuple[float, float]:
    progress = clamp(progress)
    lengths = [
        math.dist(points[index], points[index + 1])
        for index in range(len(points) - 1)
    ]
    remaining = sum(lengths) * progress
    drawn = [points[0]]
    endpoint = points[0]

    for index, segment_length in enumerate(lengths):
        start = points[index]
        end = points[index + 1]
        if remaining >= segment_length:
            drawn.append(end)
            endpoint = end
            remaining -= segment_length
            continue
        if segment_length:
            ratio = remaining / segment_length
            endpoint = (
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio,
            )
            drawn.append(endpoint)
        break

    if len(drawn) > 1:
        draw.line(drawn, fill=fill, width=width, joint="curve")
    return endpoint


def fade_frame(image: Image.Image, background: str, opacity: float) -> Image.Image:
    if opacity >= 0.999:
        return image
    base = Image.new("RGB", image.size, background)
    return Image.blend(base, image, clamp(opacity))


def save_gif(frames: list[Image.Image], path: Path, static_path: Path) -> None:
    palette_frames = [
        frame.convert("RGB").quantize(colors=64, method=Image.Quantize.FASTOCTREE)
        for frame in frames
    ]
    palette_frames[0].save(
        path,
        save_all=True,
        append_images=palette_frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=1,
    )
    frames[round(len(frames) * 0.72)].convert("RGB").save(
        static_path, optimize=True
    )


def system_frame(theme_name: str, frame_index: int, total_frames: int) -> Image.Image:
    theme = PROFILE_THEMES[theme_name]
    width, height = 460, 280
    seconds = frame_index / FPS
    opacity = 1.0 - smooth(5.45, 5.95, seconds)
    # RGB plus an RGBA drawing context blends translucent strokes into the
    # opaque canvas. Keeping the canvas itself RGBA would preserve hidden RGB
    # values under alpha=0, which reappear when GIF drops the alpha channel.
    image = Image.new("RGB", (width, height), theme["bg"])
    draw = ImageDraw.Draw(image, "RGBA")

    draw.rounded_rectangle(
        (8, 8, width - 8, height - 8),
        radius=14,
        fill=rgba(theme["panel"]),
        outline=rgba(theme["border"]),
        width=2,
    )
    draw.line((8, 42, width - 8, 42), fill=rgba(theme["border"]), width=1)
    for x, color in zip((26, 42, 58), ("#BE5155", "#CBA14D", "#5F9E86")):
        draw.ellipse((x - 4, 25 - 4, x + 4, 25 + 4), fill=rgba(color, 0.9))
    draw_text(draw, (82, 25), "profile.system", font(MONO, 13), theme["muted"], anchor="lm")

    nodes = [
        (72, 82, "AI"),
        (72, 140, "DEVELOPER\nEXPERIENCE"),
        (72, 214, "TRUST"),
    ]
    paths = [
        [(124, 82), (194, 82), (242, 140), (274, 140)],
        [(124, 140), (274, 140)],
        [(124, 214), (194, 214), (242, 140), (274, 140)],
    ]
    intervals = [(0.45, 1.45), (1.25, 2.25), (2.05, 3.05)]

    for index, ((x, y, label), path, interval) in enumerate(zip(nodes, paths, intervals)):
        progress = smooth(interval[0], interval[1], seconds)
        active = progress > 0 and progress < 1
        node_color = theme["blue"] if progress > 0 else theme["border"]
        draw.rounded_rectangle(
            (24, y - 20, 124, y + 20),
            radius=8,
            fill=rgba(theme["blue_soft"], 0.45 if progress > 0 else 0.08),
            outline=rgba(node_color, 0.95 if active else 0.55),
            width=2 if active else 1,
        )
        draw_text(
            draw,
            (74, y),
            label,
            font(MONO, 10 if index == 1 else 12),
            theme["text"] if progress > 0 else theme["muted"],
            anchor="mm",
            spacing=1,
        )
        endpoint = partial_polyline(
            draw,
            path,
            progress,
            rgba(theme["blue"], 0.95),
            2,
        )
        if active:
            draw.ellipse(
                (endpoint[0] - 4, endpoint[1] - 4, endpoint[0] + 4, endpoint[1] + 4),
                fill=rgba(theme["blue"]),
            )

    output_alpha = smooth(3.0, 3.8, seconds)
    draw.rounded_rectangle(
        (274, 102, 436, 178),
        radius=10,
        fill=rgba(theme["bg"], 0.55 * output_alpha),
        outline=rgba(theme["blue"], output_alpha),
        width=2,
    )
    draw_text(
        draw,
        (355, 133),
        "HUMAN-CENTERED",
        font(MONO, 12),
        theme["blue"],
        output_alpha,
        anchor="mm",
    )
    draw_text(
        draw,
        (355, 153),
        "TOOLS",
        font(SERIF, 22),
        theme["text"],
        output_alpha,
        anchor="mm",
    )
    draw_text(
        draw,
        (436, 250),
        "complexity → clarity",
        font(MONO, 11),
        theme["muted"],
        smooth(3.55, 4.25, seconds),
        anchor="ra",
    )
    return fade_frame(image, theme["bg"], opacity)


def render_system(theme_name: str) -> tuple[Path, Path]:
    total = FPS * 6
    frames = [system_frame(theme_name, index, total) for index in range(total)]
    gif_path = ROOT / f"profile-system-{theme_name}.gif"
    png_path = ROOT / f"profile-system-{theme_name}.png"
    save_gif(frames, gif_path, png_path)
    return gif_path, png_path


def versed_frame(theme_name: str, frame_index: int, total_frames: int) -> Image.Image:
    theme = VERSED_THEMES[theme_name]
    width, height = 1200, 360
    seconds = frame_index / FPS
    opacity = 1.0 - smooth(5.45, 5.95, seconds)
    image = Image.new("RGB", (width, height), theme["bg"])
    draw = ImageDraw.Draw(image, "RGBA")

    draw.rounded_rectangle(
        (8, 8, width - 8, height - 8),
        radius=20,
        fill=rgba(theme["panel"]),
        outline=rgba(theme["border"]),
        width=2,
    )
    draw_text(
        draw,
        (54, 50),
        "FEATURED PROJECT  /  01",
        font(MONO, 15),
        theme["accent"],
        smooth(0.0, 0.55, seconds),
        anchor="lm",
    )
    draw_text(
        draw,
        (1146, 50),
        "BUILT ON GIT · DESIGNED FOR HUMANS",
        font(MONO, 13),
        theme["muted"],
        smooth(0.2, 0.75, seconds),
        anchor="rm",
    )

    rule_progress = smooth(0.35, 1.35, seconds)
    partial_polyline(
        draw,
        [(92, 266), (200, 266)],
        rule_progress,
        rgba(theme["accent"]),
        8,
    )
    partial_polyline(
        draw,
        [(260, 266), (368, 266)],
        rule_progress,
        rgba(theme["accent"]),
        8,
    )

    caret_progress = smooth(1.05, 2.25, seconds)
    partial_polyline(
        draw,
        [(126, 86), (230, 230), (334, 86)],
        caret_progress,
        rgba(theme["text"]),
        15,
    )

    word_alpha = smooth(2.0, 2.9, seconds)
    draw_text(
        draw,
        (430, 176),
        "Versed",
        font(SERIF, 96),
        theme["text"],
        word_alpha,
        anchor="lm",
    )
    draw_text(
        draw,
        (436, 238),
        "GITHUB FOR KNOWLEDGE WORK",
        font(MONO, 21),
        theme["accent"],
        smooth(2.55, 3.35, seconds),
        anchor="lm",
    )
    draw_text(
        draw,
        (1146, 312),
        "CHECKPOINTS · DRAFTS · HISTORY · LINKED DOCUMENTS",
        font(MONO, 12),
        theme["muted"],
        smooth(3.15, 3.95, seconds),
        anchor="rm",
    )

    cursor_alpha = 0.0
    if 3.25 <= seconds <= 5.25:
        cursor_alpha = 1.0 if int((seconds - 3.25) * 2) % 2 == 0 else 0.15
    draw.rectangle((777, 126, 783, 209), fill=rgba(theme["accent"], cursor_alpha))
    return fade_frame(image, theme["bg"], opacity)


def render_versed(theme_name: str) -> tuple[Path, Path]:
    total = FPS * 6
    frames = [versed_frame(theme_name, index, total) for index in range(total)]
    gif_path = ROOT / f"versed-feature-{theme_name}.gif"
    png_path = ROOT / f"versed-feature-{theme_name}.png"
    save_gif(frames, gif_path, png_path)
    return gif_path, png_path


def render_seed() -> tuple[Path, Path]:
    width = height = 72
    total = 48
    frames: list[Image.Image] = []
    palette = [
        0, 0, 0,
        59, 130, 246,
        147, 197, 253,
        9, 105, 218,
    ] + [0, 0, 0] * 252

    for index in range(total):
        seconds = index / 12
        image = Image.new("P", (width, height), 0)
        image.putpalette(palette)
        draw = ImageDraw.Draw(image)
        grow = smooth(0.35, 1.8, seconds)
        branch = smooth(1.35, 2.45, seconds)
        sparkle = smooth(2.15, 2.7, seconds) * (1 - smooth(3.3, 3.9, seconds))

        draw.ellipse((31, 54, 41, 64), fill=3)
        stem_top = 57 - round(33 * grow)
        draw.line((36, 57, 36, stem_top), fill=1, width=3)

        if branch > 0:
            left_end = (36 - round(18 * branch), stem_top - round(9 * branch))
            right_end = (36 + round(18 * branch), stem_top - round(9 * branch))
            draw.line((36, stem_top + 8, left_end[0], left_end[1]), fill=1, width=3)
            draw.line((36, stem_top + 8, right_end[0], right_end[1]), fill=1, width=3)
            for x, y in (left_end, (36, stem_top), right_end):
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=2)

        if sparkle > 0.2:
            for x, y in ((16, 18), (55, 16), (61, 34)):
                draw.point((x, y), fill=2)
                draw.point((x - 1, y), fill=2)
                draw.point((x + 1, y), fill=2)
                draw.point((x, y - 1), fill=2)
                draw.point((x, y + 1), fill=2)

        image.info["transparency"] = 0
        frames.append(image)

    gif_path = ROOT / "profile-seed.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / 12),
        loop=0,
        optimize=True,
        transparency=0,
        disposal=2,
    )
    png_path = ROOT / "profile-seed.png"
    rgba_image = frames[34].convert("RGBA")
    pixels = rgba_image.load()
    for y in range(height):
        for x in range(width):
            if frames[34].getpixel((x, y)) == 0:
                pixels[x, y] = (0, 0, 0, 0)
    rgba_image.save(png_path, optimize=True)
    return gif_path, png_path


def main() -> None:
    outputs: list[Path] = []
    for theme_name in ("light", "dark"):
        outputs.extend(render_system(theme_name))
        outputs.extend(render_versed(theme_name))
    outputs.extend(render_seed())

    manifest = {
        "version": 1,
        "generator": "assets/profile-motion/render.py",
        "fps": FPS,
        "outputs": [
            {
                "file": output.name,
                "bytes": output.stat().st_size,
                "sha256": __import__("hashlib").sha256(output.read_bytes()).hexdigest(),
            }
            for output in outputs
        ],
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
