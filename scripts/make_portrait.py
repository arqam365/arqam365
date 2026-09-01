#!/usr/bin/env python3
"""Turn a photo into assets/portrait.svg - a self-typing ASCII portrait.

    pip install pillow numpy opencv-python-headless rembg
    python3 scripts/make_portrait.py photo.png --crop 88,2,382,452

The first run downloads a background-removal model, once. The portrait is a
one-off artifact, so unlike the stat graphics it is not on a schedule.

Two things decide whether the output is any good, and neither is a parameter
you can leave alone:

  * The photo. ASCII draws with shadow, not detail - thirteen brightness
    levels in total. It wants side light (a window at about 45 degrees,
    everything else off), real resolution, and framing from mid-chest to just
    above the hair. Flat frontal light renders the face as a hole; a small
    source loses thin features like glasses frames on the downscale.
  * The crop. Leave background around the head. Crop tight to the face and
    the cutout has nothing to cut against, so the result fills its rectangle
    as a block instead of reading as a person.

CLAHE pulls local contrast up so brows, glasses and lips separate from the
skin; the gamma curve then sets how dark the whole thing sits. Push CLAHE too
far and skin texture becomes noise.

The grid bakes in an advance width of exactly 0.600 em (CHAR_W / FONT_SIZE).
JetBrains Mono is 600/1000 units, so inlining its ramp subset as base64 pins
the geometry for every viewer - one whose default monospace is narrower
(Consolas is about 0.55) would otherwise see the portrait some 7% too narrow.
An external font URL cannot work here: the SVG is loaded through <img>, and
browsers refuse subresource fetches for an image document. Inlining is the
only mechanism, and it keeps the page free of third-party requests.

Motion is SMIL, because GitHub strips <script> from READMEs: each row is
revealed by a clipPath wipe with a cursor block riding its edge, staggered top
to bottom and frozen at the end, so it prints once and stops. The clip rect
carries its finished width as a plain attribute and SMIL animates it up from
zero, so a renderer that ignores SMIL shows the completed portrait rather than
an empty box.
"""
import argparse
import base64
import os

import cv2
import numpy as np
from PIL import Image

RAMP = " .`:-=+*cs#%@"     # sparse/bright -> dense/dark; leading space = blank
COLS = 84
CLAHE_CLIP = 3.5           # higher amplifies skin texture into noise
CURVE = 1.70               # tone exponent, applied after CLAHE
ROW_RATIO = 0.48           # monospace cells are about twice as tall as wide

FG_LIGHT = "#6e7681"       # the portrait's grey, readable on GitHub light
FG_DARK = "#c9d1d9"        # and its dark-mode step
FONT_SIZE = 12.9
CHAR_W = 7.74              # 0.600 em at FONT_SIZE - keep these in step
LINE_H = 15
PAD = 14
ROW_DELAY = 0.055          # per-row stagger, seconds
FAMILY = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
          "&apos;Liberation Mono&apos;,monospace")
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "fonts", "jbmono-ramp.woff2")


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
            for c in range(cols)).rstrip())
    # Trim fully blank rows top and bottom so the SVG carries no dead margin.
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def font_face():
    """The ramp subset inlined as a data URI - see the module docstring."""
    with open(FONT, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:400;font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def to_svg(rows, cols, alt):
    width = int(cols * CHAR_W + PAD * 2)
    height = len(rows) * LINE_H + PAD * 2

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
         f'height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="{FAMILY}" role="img" aria-label="{esc(alt)}">',
         f"<title>{esc(alt)}</title>",
         f"<style>{font_face()}.a{{fill:{FG_LIGHT}}}"
         f"@media(prefers-color-scheme:dark){{.a{{fill:{FG_DARK}}}}}</style>"]

    for i, line in enumerate(rows):
        y = PAD + i * LINE_H
        begin = f"{i * ROW_DELAY:.2f}s"
        end = f"{(i + 1) * ROW_DELAY:.2f}s"
        w = max(len(line), 1) * CHAR_W

        # width carries the finished value, so a renderer with no SMIL draws
        # the complete row instead of an empty one.
        p.append(f'<clipPath id="c{i}"><rect x="{PAD}" y="{y}" '
                 f'height="{LINE_H}" width="{w:.1f}">'
                 f'<animate attributeName="width" from="0" to="{w:.1f}" '
                 f'begin="{begin}" dur="{ROW_DELAY}s" fill="freeze"/>'
                 f"</rect></clipPath>")
        p.append(f'<g clip-path="url(#c{i})"><text xml:space="preserve" '
                 f'x="{PAD}" y="{y + 11.2:.1f}" class="a" '
                 f'font-size="{FONT_SIZE}">{esc(line)}</text></g>')
        # the cursor: a block riding the wipe edge, gone once the row lands
        p.append(f'<rect y="{y + 1}" width="6" height="12" class="a" '
                 f'opacity="0">'
                 f'<animate attributeName="x" from="{PAD}" to="{PAD + w:.1f}" '
                 f'begin="{begin}" dur="{ROW_DELAY}s" fill="freeze"/>'
                 f'<set attributeName="opacity" to="0.8" begin="{begin}"/>'
                 f'<set attributeName="opacity" to="0" begin="{end}"/></rect>')

    p.append("</svg>")
    return "".join(p)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("photo")
    p.add_argument("-o", "--out", default="assets/portrait.svg")
    p.add_argument("--crop", help="left,top,right,bottom, applied before rembg")
    p.add_argument("--cols", type=int, default=COLS)
    p.add_argument("--clip", type=float, default=CLAHE_CLIP)
    p.add_argument("--curve", type=float, default=CURVE)
    p.add_argument("--alt", default="ASCII portrait")
    p.add_argument("--preview", action="store_true")
    a = p.parse_args()

    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    rows = to_rows(prep(a.photo, crop, a.clip, a.curve), a.cols)
    if a.preview:
        print("\n".join(rows))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(to_svg(rows, a.cols, a.alt))
    print(f"{a.out}: {a.cols} cols x {len(rows)} rows, font inlined")


if __name__ == "__main__":
    main()
