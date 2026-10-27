#!/usr/bin/env python3
"""Check that the Android launcher icon matches the Play store icon (see references/app-icon.md).

Usage:
  icon_check.py --aab app-release.aab --store-icon icon-512.png --out icon-check.png
  icon_check.py --project <repo>          # only flag template icon files (Expo placeholders)

The sheet shows the store icon under Play's rounded mask, then the launcher icon from the bundle
under circle, squircle and rounded-square masks, then the full 72dp viewport with the 66dp safe
circle in red. Anything that matters must sit inside that circle, and every panel should read as
the same icon. Requires Pillow.
"""
import argparse
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

# Expo placeholder launcher files. They survive until replaced on purpose, and Google rejects
# builds that install them under a real store icon.
TEMPLATE_SHA256 = {
    "9e3d0315a33c6799de601dd34cd8bf8cc3a8d16f3bf75592baec2ceb7240b391": "Expo SDK 54+ android-icon-foreground (blue 'A')",
    "fb139c2dee362ebf2070e23b96da6fc0d43f8492de38b8af1fd7223e19b5861d": "Expo SDK 54+ android-icon-background",
    "6371fc2c12e33ad2215a86c281db3d682a81bebe7c957a842c13b8bf00cceb83": "Expo SDK 54+ android-icon-monochrome (blue 'A')",
    "5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8": "Expo adaptive-icon.png (grey grid template)",
}
DENSITY = ["xxxhdpi", "xxhdpi", "xhdpi", "hdpi", "mdpi"]
P = 300  # panel size


def template_hits(root):
    hits = []
    for path in Path(root).rglob("*.png"):
        if any(part in {"node_modules", ".git", "build", "Pods", "ios"} for part in path.parts):
            continue
        name = TEMPLATE_SHA256.get(hashlib.sha256(path.read_bytes()).hexdigest())
        if name:
            hits.append((str(path.relative_to(root)), name))
    return hits


def layer(zf, stem):
    """Highest-density mipmap/drawable bitmap named `stem` inside the bundle (or APK)."""
    names = zf.namelist()
    for density in DENSITY:
        for n in names:
            if re.search(rf"res/(mipmap|drawable)-{density}[^/]*/{stem}\.(webp|png)$", n):
                return Image.open(io.BytesIO(zf.read(n))).convert("RGBA")
    return None


def masked(img, shape):
    m = Image.new("L", (P, P), 0)
    d = ImageDraw.Draw(m)
    if shape == "circle":
        d.ellipse([0, 0, P - 1, P - 1], fill=255)
    else:
        d.rounded_rectangle([0, 0, P - 1, P - 1], radius={"squircle": P * 0.32, "rounded": P * 0.2}[shape], fill=255)
    out = Image.new("RGBA", (P, P), (0, 0, 0, 0))
    out.paste(img.resize((P, P), Image.LANCZOS).convert("RGBA"), (0, 0), m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aab", help="release .aab (or .apk)")
    ap.add_argument("--store-icon", help="the 512x512 Play hi-res icon (ideally downloaded from the live listing)")
    ap.add_argument("--project", help="repo to scan for template icon files")
    ap.add_argument("--out", default="icon-check.png")
    a = ap.parse_args()

    status = 0
    if a.project:
        hits = template_hits(a.project)
        for path, name in hits:
            print(f"TEMPLATE  {path}: {name}")
        if hits:
            status = 1
        else:
            print("no known template icon files")
    if not a.aab:
        sys.exit(status)

    with zipfile.ZipFile(a.aab) as zf:
        fg, bg = layer(zf, "ic_launcher_foreground"), layer(zf, "ic_launcher_background")
        legacy = layer(zf, "ic_launcher")
    if fg is None and legacy is None:
        sys.exit("no launcher bitmaps found (vector drawables aren't rendered; check those on a device)")
    if fg is not None:
        if bg is None:
            print("note: background is not a bitmap (likely a colour); using white")
            bg = Image.new("RGBA", fg.size, "white")
        full = bg.resize(fg.size).copy()
        full.alpha_composite(fg)
        n = full.width
        v0 = round(n * 18 / 108)
        viewport = full.crop((v0, v0, n - v0, n - v0))  # what launchers mask
    else:
        print("note: no adaptive layers; showing the legacy ic_launcher")
        viewport = legacy

    panels = []
    if a.store_icon:
        panels.append(("store (Play mask)", masked(Image.open(a.store_icon), "rounded")))
    panels += [(s, masked(viewport, s)) for s in ("circle", "squircle", "rounded")]
    safe = viewport.resize((P, P), Image.LANCZOS).convert("RGBA")
    inset = round(P * (1 - 66 / 72) / 2)
    ImageDraw.Draw(safe).ellipse([inset, inset, P - inset, P - inset], outline=(255, 0, 0, 255), width=3)
    panels.append(("72dp viewport + 66dp safe circle", safe))

    sheet = Image.new("RGB", (len(panels) * (P + 20) + 20, P + 60), (232, 232, 236))
    d = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate(panels):
        x = 20 + i * (P + 20)
        sheet.paste(img, (x, 20), img)
        d.text((x, P + 30), label, fill=(40, 40, 40))
    sheet.save(a.out)
    print(f"wrote {a.out}")
    sys.exit(status)


if __name__ == "__main__":
    main()
