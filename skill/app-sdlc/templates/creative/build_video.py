"""App Store Search Results video (iOS 27): 3:2, 1920x1280, 30 fps, 15 s, muted loop.

The table in late sun sets itself: the disposable camera, the negative and the rolls slide in,
then the prints land one by one, straight out of the app's film shaders. The big print keeps
being re-developed through another film (Gold Snap -> 35 Lux -> Early Digital), each change
washed by a warm light leak, its name changing in the chin. The headline never moves.
Everything lifts away in the last second, so the loop restarts on the bare table.

Layers are shot from search.html's layer mode (?only=...) with Playwright's headless shell on a
transparent page, then animated here with PIL and piped to ffmpeg.
    python3 build_video.py [locale]   -> ../creative-export/<locale>/search.mp4
"""
import os, subprocess, sys, glob
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALE = sys.argv[1] if len(sys.argv) > 1 else "en-US"
OUT = os.path.join(HERE, "..", "creative-export", LOCALE)
LAY = os.path.join(HERE, "build", "layers", LOCALE)
W, H, FPS, DUR = 1920, 1280, 30, 15.0
CHROME = sorted(glob.glob(os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell")))[-1]

# The hero print's films, in order. Same diner shot, developed through each in the app.
HERO = [("diner-gold", "Gold Snap"), ("diner-lux", "35 Lux"), ("diner-digital", "Early Digital")]


def shoot(name, query):
    path = os.path.join(LAY, name + ".png")
    if not os.path.exists(path):
        os.makedirs(LAY, exist_ok=True)
        url = f"file://{HERE}/search.html?{query}"
        subprocess.run([CHROME, "--headless", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--default-background-color=00000000", "--allow-file-access-from-files",
                        f"--window-size={W},{H}", "--virtual-time-budget=4000", f"--screenshot={path}", url],
                       check=True, capture_output=True)
    return Image.open(path).convert("RGBA")


def sprite(img):
    """Crop a full-frame layer to its content: (sprite, x, y)."""
    box = img.getchannel("A").point(lambda a: 255 if a > 2 else 0).getbbox()
    return img.crop(box), box[0], box[1]


def ease(x):  # crisp ease-out, no overshoot
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 4


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 3


desk = np.asarray(shoot("desk", "only=desk").convert("RGB"), dtype=np.float32)
type_layer = shoot("type", "only=type")

# id, query, entrance kind, start, offset for slides
PIECES = [
    ("cam",  "only=cam",  "slide", 0.30, (-760, 260)),
    ("neg",  "only=neg",  "slide", 0.55, (-640, 220)),
    ("can1", "only=can1", "slide", 0.85, (180, 520)),
    ("can2", "only=can2", "slide", 1.00, (60, 460)),
    ("can3", "only=can3", "slide", 1.15, (260, 420)),
    ("pr1",  "only=pr1&src=dance-home-video&label=Home%20Video", "drop", 1.45, None),
    ("pr2",  None, "drop", 1.95, None),   # the hero, see HERO
    ("pr3",  "only=pr3",  "drop", 2.45, None),
    ("pr4",  "only=pr4",  "drop", 2.95, None),
]
sprites = {}
for pid, query, *_ in PIECES:
    if pid == "pr2":
        sprites[pid] = [sprite(shoot(f"pr2-{src}", f"only=pr2&src={src}&label={label.replace(' ', '%20')}")) for src, label in HERO]
    else:
        sprites[pid] = sprite(shoot(pid, query))

SWITCHES = [4.5, 6.7, 8.9, 11.1]        # hero re-develops (index advances, wraps)
EXIT, EXIT_STEP, EXIT_LEN = 13.0, 0.09, 0.55


def hero_index(t):
    return sum(t >= s for s in SWITCHES) % len(HERO)


def place(frame, spr, x, y, scale=1.0, alpha=1.0):
    if alpha <= 0.003:
        return
    img, sx, sy = spr
    if scale != 1.0:
        w, h = img.size
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        cx, cy = sx + x + w / 2, sy + y + h / 2
        img = img.resize((nw, nh), Image.BILINEAR)
        px, py = round(cx - nw / 2), round(cy - nh / 2)
    else:
        px, py = round(sx + x), round(sy + y)
    if alpha < 1:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img = img.copy(); img.putalpha(a)
    frame.alpha_composite(img, (px, py)) if 0 <= px and 0 <= py and px + img.width <= W and py + img.height <= H \
        else frame.paste(img, (px, py), img)


def leak_strength(t):
    """A warm leak washes in around each re-develop and fades."""
    s = 0.0
    for sw in SWITCHES:
        d = t - (sw - 0.18)
        if 0 <= d <= 0.9:
            s = max(s, np.sin(np.pi * min(d / 0.9, 1)) ** 1.5)
    return s


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def leak(t, s):
    # an orange glow entering from the left edge and drifting right while it lasts
    cx = -200 + 900 * (t % 2.2) / 2.2
    g = np.exp(-(((xx - cx) / 700) ** 2 + ((yy - 380) / 900) ** 2))
    col = np.array([255, 128, 30], dtype=np.float32)
    return (g[..., None] * col * 0.55 * s)


def frame_at(t):
    base = Image.fromarray(desk.astype(np.uint8)).convert("RGBA")
    for i, (pid, _, kind, start, off) in enumerate(PIECES):
        spr = sprites[pid]
        if pid == "pr2":
            spr = spr[hero_index(t)]
        # leave in reverse order, prints first
        k = len(PIECES) - 1 - i
        e0 = EXIT + k * EXIT_STEP
        out = ease_in((t - e0) / EXIT_LEN)
        if t < start:
            continue
        p = ease((t - start) / (0.75 if kind == "slide" else 0.45))
        if kind == "slide":
            dx, dy = off
            x, y = dx * (1 - p), dy * (1 - p)
            alpha, scale = min(1.0, (t - start) / 0.2), 1.0
        else:
            x = y = 0
            alpha, scale = min(1.0, (t - start) / 0.18), 1.18 - 0.18 * p
        if out > 0:
            scale *= 1 + 0.10 * out
            alpha *= 1 - out
            y -= 40 * out
        place(base, spr, x, y, scale, alpha)
        # the hero cross-fades into its next film
        if pid == "pr2":
            for sw in SWITCHES:
                d = (t - sw) / 0.28
                if 0 <= d < 1 and out <= 0:
                    prev = sprites["pr2"][(hero_index(t) - 1) % len(HERO)]
                    place(base, prev, x, y, scale, alpha * (1 - d))
    base.alpha_composite(type_layer)
    rgb = np.asarray(base.convert("RGB"), dtype=np.float32)
    s = leak_strength(t)
    if s > 0.01:
        L = leak(t, s)
        rgb = 255 - (255 - rgb) * (255 - L) / 255   # screen
    return rgb.astype(np.uint8)


def main():
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "search.mp4")
    n = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-f", "lavfi", "-t", str(DUR), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                           "-map", "0:v", "-map", "1:a", "-t", str(DUR),
                           "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.2", "-preset", "slow",
                           "-b:v", "12M", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dst], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame_at(i / FPS).tobytes())
        if i % 90 == 0:
            print(f"{i / FPS:.1f}s", flush=True)
    ff.stdin.close(); ff.wait()
    for t, name in [(3.6, "search-video-still"), (5.0, "search-video-lux"), (0.0, "search-video-start")]:
        Image.fromarray(frame_at(t)).save(os.path.join(OUT, name + ".jpg"), quality=85)
    print("wrote", dst)


if __name__ == "__main__":
    main()
