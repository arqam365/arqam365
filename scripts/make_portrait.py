#!/usr/bin/env python3
"""Turn a photo into assets/portrait.svg - a monochrome ASCII portrait.

    pip install pillow numpy
    pip install "rembg[cpu]"          # optional, but see --cutout below
    python3 scripts/make_portrait.py photo.png --cutout -o assets/portrait.svg

Nothing here loads from a third-party server, so the portrait cannot
rate-limit or go dark the way a badge service does.

Three knobs decide whether the output is any good, and they need eyeballing
on the actual photo - there is no correct value to hardcode:

  --cutout  Drop the background with rembg (first run pulls a ~1 GB model).
            This is the difference-maker. ASCII has ~13 brightness levels
            total and cannot spare any of them on a wall; without it the
            background fills with # and @ and the face stops reading.
            Without rembg installed the script still runs - crop tightly.
  --crop    left,top,right,bottom. Defaults to the subject's bounding box
            plus --pad when --cutout is on.
  --curve   The tone exponent. Below 1.0 lifts midtones, above 1.0 darkens.
            Too bright and brows, glasses and lips dissolve; too dark and the
            face fills in solid. Depends entirely on the photo's exposure.

The grid assumes a monospace advance width of 0.600 em. Rather than inline a
subset font to guarantee that, every row is drawn with textLength +
lengthAdjust="spacingAndGlyphs", which pins each row to the same width in any
renderer - a viewer whose default monospace is narrower (Consolas is ~0.55)
still sees square columns.

Motion is SMIL, because GitHub strips <script> from READMEs. The clip rect
carries its full width as a plain attribute and SMIL animates it from 0, so a
renderer that ignores SMIL shows the finished portrait instead of nothing.
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter, ImageOps

RAMP = " .`:-=+*cs#%@"     # sparse/bright -> dense/dark; leading space = blank
COLS = 78
CURVE = 0.85               # tone exponent; <1 lifts midtones, >1 darkens
FLATTEN = 0.30             # illumination-cancel blend; 0 = off, 1 = fully flat
BLUR = 24                  # radius of the illumination estimate, in pixels
SHARP = 170                # local-contrast boost %; stands in for CLAHE
SUBJECT_FLOOR = 0          # darkest value the subject may take
SUBJECT_CEIL = 232         # brightest - must stay under the blank ramp slot
COVER_MIN = 0.35           # min subject coverage for a cell to print at all
ROW_RATIO = 0.50           # monospace cells are about twice as tall as wide

FG_LIGHT = "#57606a"       # readable on GitHub light
FG_DARK = "#8b98a5"        # and its dark-mode step
FONT_SIZE = 13.0
CHAR_W = FONT_SIZE * 0.600
LINE_H = 15.0
ROW_DELAY = 0.055          # per-row stagger, seconds
FAMILY = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def prep(path, crop, curve, cutout, pad, flatten=FLATTEN, sharp=SHARP):
    """Cut out the background, flatten the lighting, then set the tone."""
    src = Image.open(path).convert("RGBA")
    # Composite onto white so transparent corners map to the blank end of the
    # ramp instead of black.
    src = Image.alpha_composite(Image.new("RGBA", src.size, "white"), src)

    matte, box = None, None
    if cutout:
        from rembg import remove

        cut = remove(src)
        alpha = np.array(cut.split()[-1])
        src = Image.alpha_composite(Image.new("RGBA", cut.size, "white"), cut)
        matte = Image.fromarray(alpha)
        ys, xs = np.where(alpha >= 20)
        if len(xs):
            box = (max(0, xs.min() - pad), max(0, ys.min() - pad),
                   min(src.size[0], xs.max() + pad),
                   min(src.size[1], ys.max() + pad))

    box = crop or box or (0, 0, *src.size)
    src = src.convert("L").crop(box)
    if matte is not None:
        matte = matte.crop(box)

    g = np.asarray(ImageOps.autocontrast(src, cutoff=1), dtype=np.float32)

    # Divide by a heavy blur to estimate and cancel the illumination, so one
    # side of the face being lit does not eat the whole ramp. Stands in for
    # CLAHE's brightness normalisation without pulling in OpenCV.
    if flatten > 0:
        est = np.asarray(
            Image.fromarray(g.astype("uint8")).filter(
                ImageFilter.GaussianBlur(BLUR)), dtype=np.float32)
        lit = np.clip(g / np.maximum(est, 1.0) * 140.0, 0, 255)
        g = np.clip(flatten * lit + (1 - flatten) * g, 0, 255)

    # Amplify local structure so brows, glasses and lips survive as marks
    # inside the dark mass of hair and beard. Without this the head downsamples
    # into one flat silhouette - a 3px glasses frame simply averages away.
    out = Image.fromarray(g.astype("uint8"))
    if sharp:
        out = out.filter(ImageFilter.UnsharpMask(radius=6, percent=int(sharp),
                                                 threshold=2))
    g = np.asarray(ImageOps.autocontrast(out, cutoff=1), dtype=np.float32)
    g = np.clip(255.0 * (g / 255.0) ** curve, 0, 255)

    # Blank is reserved for the matte. Squeeze the subject into the printing
    # part of the ramp, or its lit skin maps to the same empty cell as the
    # background and the face becomes a hole.
    if matte is not None:
        g = SUBJECT_FLOOR + g * (SUBJECT_CEIL - SUBJECT_FLOOR) / 255.0
        g[np.array(matte) < 20] = 255.0
    return Image.fromarray(g.astype("uint8")), matte


def to_rows(img, cols, matte=None):
    w, h = img.size
    rows = max(1, round(h / w * cols * ROW_RATIO))
    small = img.resize((cols, rows), Image.LANCZOS)
    px = small.load()
    # A cell straddling the cutout edge averages to a light-but-not-blank
    # value and prints a stray mark in open space. Blank any cell the subject
    # barely covers.
    cover = (np.asarray(matte.resize((cols, rows), Image.BOX), dtype=np.float32)
             / 255.0) if matte is not None else None
    out = []
    for y in range(rows):
        # Brightest pixel -> last ramp index; ramp is dark-to-light reversed
        # below so that dark pixels pick the dense glyphs.
        line = "".join(
            " " if cover is not None and cover[y, x] < COVER_MIN
            else RAMP[::-1][px[x, y] * (len(RAMP) - 1) // 255]
            for x in range(cols))
        out.append(line.rstrip())
    # Trim fully blank rows top and bottom so the SVG has no dead margin.
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(rows, cols, alt):
    w = round(cols * CHAR_W, 2)
    h = round(len(rows) * LINE_H + 6, 2)
    total = round(len(rows) * ROW_DELAY + 0.9, 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(alt)}">',
        f"  <title>{esc(alt)}</title>",
        "  <style>",
        f"    text {{ font-family: {FAMILY}; font-size: {FONT_SIZE}px; "
        f"white-space: pre; fill: {FG_LIGHT}; }}",
        "    @media (prefers-color-scheme: dark) {",
        f"      text {{ fill: {FG_DARK}; }}",
        "    }",
        "  </style>",
        "  <defs>",
    ]

    for i in range(len(rows)):
        # width carries the finished value, so a renderer with no SMIL draws
        # the complete row rather than an empty one.
        parts += [
            f'    <clipPath id="w{i}">',
            f'      <rect x="0" y="{round(i * LINE_H, 2)}" '
            f'width="{w}" height="{round(LINE_H + 4, 2)}">',
            f'        <animate attributeName="width" from="0" to="{w}" '
            f'begin="{round(i * ROW_DELAY, 3)}s" dur="0.42s" fill="freeze"/>',
            "      </rect>",
            "    </clipPath>",
        ]
    parts.append("  </defs>")

    for i, row in enumerate(rows):
        y = round(i * LINE_H + FONT_SIZE, 2)
        parts.append(
            f'  <text x="0" y="{y}" clip-path="url(#w{i})" '
            f'textLength="{w}" lengthAdjust="spacingAndGlyphs">{esc(row)}</text>'
        )

    parts.append(f"  <!-- prints once in {total}s, then holds -->")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photo")
    p.add_argument("-o", "--out", default="assets/portrait.svg")
    p.add_argument("--crop", help="left,top,right,bottom in source pixels")
    p.add_argument("--cols", type=int, default=COLS)
    p.add_argument("--curve", type=float, default=CURVE)
    p.add_argument("--cutout", action="store_true", help="drop background")
    p.add_argument("--pad", type=int, default=8, help="px around the subject")
    p.add_argument("--flatten", type=float, default=FLATTEN)
    p.add_argument("--sharp", type=int, default=SHARP)
    p.add_argument("--alt", default="ASCII portrait")
    a = p.parse_args()

    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    img, matte = prep(a.photo, crop, a.curve, a.cutout, a.pad,
                      a.flatten, a.sharp)
    rows = to_rows(img, a.cols, matte)
    with open(a.out, "w") as f:
        f.write(to_svg(rows, a.cols, a.alt))
    print(f"{a.out}: {a.cols} cols x {len(rows)} rows")


if __name__ == "__main__":
    main()
