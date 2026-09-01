#!/usr/bin/env python3
"""Turn a photo into assets/portrait.svg - a monochrome ASCII portrait.

    pip install pillow numpy opencv-python-headless rembg
    python3 scripts/make_portrait.py photo.png --crop 128,18,396,378

The first run downloads a background-removal model, once. Nothing here loads
from a third-party server at render time, so the portrait cannot rate-limit or
go dark the way a badge service can.

Three things decide whether the output is any good, and none of them is a
parameter you can leave alone:

  * The photo. ASCII draws with shadow, not detail - thirteen brightness
    levels in total. It wants side light, real resolution, and a tight crop
    from the chin to just above the hair. Flat frontal light renders the face
    as a hole; a small source loses thin features like glasses frames on the
    downscale.
  * The background. --crop first, then rembg cuts the rest. Any wall that
    survives is spent out of the same thirteen levels the face needs, and it
    fills with # and @.
  * The two tone knobs below. CLAHE pulls local contrast up so brows, glasses
    and lips survive; the gamma curve then sets how dark the whole thing sits.
    Push CLAHE too far and skin texture becomes noise.

The grid assumes a monospace advance width of 0.600 em. Rather than inline a
subset font to guarantee it, every row carries textLength with
lengthAdjust="spacingAndGlyphs", which pins the row width in any renderer -
a viewer whose default monospace is narrower (Consolas is about 0.55) still
gets square columns. That only holds if every row is the same number of
characters, so rows keep their trailing blanks instead of being stripped.

Alignment rides on the leading blanks, so the text carries xml:space="preserve".
CSS white-space:pre is SVG 2 and is not reliable for an SVG loaded through an
<img> tag, which is how GitHub embeds it.

Motion is SMIL, because GitHub strips <script> from READMEs: each row is
revealed by a clipPath wipe, staggered top to bottom and frozen at the end, so
it prints once and stops. The clip rect carries its finished width as a plain
attribute and SMIL animates it up from zero, so a renderer that ignores SMIL
shows the completed portrait rather than an empty box.
"""
import argparse

import cv2
import numpy as np
from PIL import Image

RAMP = " .`:-=+*cs#%@"     # sparse/bright -> dense/dark; leading space = blank
COLS = 90                  # below ~88 the face muddies; far above it turns to noise
CLAHE_CLIP = 3.0           # higher amplifies skin texture into noise
CURVE = 1.15               # tone exponent, applied after CLAHE
ROW_RATIO = 0.48           # monospace cells are about twice as tall as wide

FG_LIGHT = "#57606a"       # readable on GitHub light
FG_DARK = "#8b98a5"        # and its dark-mode step
FONT_SIZE = 12.9
CHAR_W = 7.74              # 0.600 em at FONT_SIZE - keep these in step
LINE_H = 15.0
ROW_DELAY = 0.055          # per-row stagger, seconds
FAMILY = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def prep(path, crop, clip, curve):
    """Cut the background out, even the local contrast, then set the tone."""
    src = Image.open(path).convert("RGBA")
    # Composite onto white so transparent corners map to the blank end of the
    # ramp rather than to black.
    src = Image.alpha_composite(Image.new("RGBA", src.size, "white"), src)
    if crop:
        src = src.crop(crop)

    from rembg import remove

    cut = remove(src)
    alpha = np.array(cut.split()[-1])
    white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    gray = np.array(Image.alpha_composite(white, cut).convert("L"))

    gray = cv2.bilateralFilter(gray, 11, 50, 50)        # smooth skin, keep edges
    gray = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(gray)
    gray = (255.0 * (gray / 255.0) ** curve).astype("uint8")
    gray[alpha < 20] = 255                              # force the matte to white
    return Image.fromarray(gray)


def to_rows(img, cols):
    w, h = img.size
    rows = max(1, int(cols * (h / w) * ROW_RATIO))
    small = img.resize((cols, rows), Image.LANCZOS)
    px = list(small.getdata())
    n = len(RAMP)

    out = []
    for r in range(rows):
        out.append("".join(
            RAMP[min(n - 1, int((1 - px[r * cols + c] / 255.0) * n))]
            for c in range(cols)))
    # Trim fully blank rows top and bottom so the SVG carries no dead margin.
    # Rows keep their trailing blanks: every row has to stay exactly `cols`
    # characters or the shared textLength stretches the short ones.
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    assert all(len(r) == cols for r in out), "rows must be equal width"
    return out


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(rows, cols, alt):
    pad = 14
    w = round(cols * CHAR_W, 2)
    width = round(w + pad * 2, 2)
    height = round(len(rows) * LINE_H + pad * 2, 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'xml:space="preserve" font-family="{FAMILY}" '
        f'font-size="{FONT_SIZE}" role="img" aria-label="{esc(alt)}">',
        f"  <title>{esc(alt)}</title>",
        f"  <style>.a{{fill:{FG_LIGHT}}}"
        f"@media(prefers-color-scheme:dark){{.a{{fill:{FG_DARK}}}}}</style>",
        "  <defs>",
    ]

    for i in range(len(rows)):
        y = round(pad + i * LINE_H, 2)
        # width carries the finished value, so a renderer with no SMIL draws
        # the complete row instead of an empty one.
        parts += [
            f'    <clipPath id="w{i}"><rect x="{pad}" y="{y}" '
            f'width="{w}" height="{round(LINE_H + 4, 2)}">'
            f'<animate attributeName="width" from="0" to="{w}" '
            f'begin="{round(i * ROW_DELAY, 3)}s" dur="0.42s" fill="freeze"/>'
            "</rect></clipPath>",
        ]
    parts.append("  </defs>")

    for i, row in enumerate(rows):
        y = round(pad + i * LINE_H + FONT_SIZE * 0.87, 2)
        parts.append(
            f'  <text xml:space="preserve" class="a" x="{pad}" y="{y}" '
            f'clip-path="url(#w{i})" textLength="{w}" '
            f'lengthAdjust="spacingAndGlyphs">{esc(row)}</text>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("photo")
    p.add_argument("-o", "--out", default="assets/portrait.svg")
    p.add_argument("--crop", help="left,top,right,bottom, applied before rembg")
    p.add_argument("--cols", type=int, default=COLS)
    p.add_argument("--clip", type=float, default=CLAHE_CLIP)
    p.add_argument("--curve", type=float, default=CURVE)
    p.add_argument("--alt", default="ASCII portrait")
    a = p.parse_args()

    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    rows = to_rows(prep(a.photo, crop, a.clip, a.curve), a.cols)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(to_svg(rows, a.cols, a.alt))
    print(f"{a.out}: {a.cols} cols x {len(rows)} rows")


if __name__ == "__main__":
    main()
