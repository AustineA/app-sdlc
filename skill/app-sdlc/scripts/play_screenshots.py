#!/usr/bin/env python3
"""Replace Google Play phone screenshots for every locale from an App Store screenshot export.

Usage:
  play_screenshots.py --src <export dir with <asc-locale>/*.png> --out <work dir> [--map ar=ar-SA,...]
                      [--key <service-account.json> --package <pkg> --upload]

1. Crops each image to at most 2:1 (Play rejects a long side > 2x the short side). It keeps the
   top, so it suits layouts whose phone runs off the bottom. Check a contact sheet first.
2. With --upload: one edit; for each Play locale, delete phoneScreenshots, upload the PNGs in
   name order, then commit. It fetches a fresh token per image and retries with backoff,
   because long runs hit intermittent 401s and broken pipes. A failed run never commits.
"""
import argparse, sys, time
from pathlib import Path
from PIL import Image

# Play locale -> App Store / FrameCraft export locale. Override or extend with --map.
DEFAULT_MAP = {"ar": "ar-SA", "de-DE": "de-DE", "en-GB": "en-GB", "en-US": "en-US", "es-419": "es-MX", "es-ES": "es-ES",
               "fr-FR": "fr-FR", "hi-IN": "hi-IN", "id": "id-ID", "it-IT": "it-IT", "ja-JP": "ja-JP", "ko-KR": "ko-KR",
               "nl-NL": "nl-NL", "pt-BR": "pt-BR", "ru-RU": "ru-RU", "tr-TR": "tr-TR", "zh-CN": "zh-Hans", "zh-TW": "zh-Hant"}


def crop_all(src, out, mapping):
    done = {}
    for play, asc in mapping.items():
        files = sorted((src / asc).glob("*.png"))
        if not files:
            print(f"skip {play}: no images in {src / asc}")
            continue
        (out / play).mkdir(parents=True, exist_ok=True)
        for f in files:
            im = Image.open(f).convert("RGB")
            w, h = im.size
            if max(w, h) > 2 * min(w, h):
                im = im.crop((0, 0, w, 2 * w)) if h > w else im.crop((0, 0, 2 * h, h))
            im.save(out / play / f.name, optimize=True)
        done[play] = len(files)
    return done


def upload_all(out, locales, key, package):
    import requests
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_file(key, scopes=["https://www.googleapis.com/auth/androidpublisher"])

    def headers():
        creds.refresh(Request())  # fresh token every time; long uploads otherwise hit 401s
        return {"Authorization": f"Bearer {creds.token}"}

    base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{package}"
    upload = base.replace("/androidpublisher/v3/", "/upload/androidpublisher/v3/")
    eid = requests.post(base + "/edits", headers=headers(), json={}, timeout=60).json()["id"]

    def send(play, path):
        for attempt in range(5):
            try:
                r = requests.post(f"{upload}/edits/{eid}/listings/{play}/phoneScreenshots?uploadType=media",
                                  data=path.read_bytes(), headers={**headers(), "Content-Type": "image/png"}, timeout=180)
                if r.status_code == 200:
                    return
                err = f"{r.status_code} {r.text[:200]}"
            except requests.RequestException as e:
                err = str(e)
            time.sleep(3 * (attempt + 1))
        raise SystemExit(f"{play} {path.name}: {err} (edit not committed)")

    for play in locales:
        requests.delete(f"{base}/edits/{eid}/listings/{play}/phoneScreenshots", headers=headers(), timeout=60)
        files = sorted((out / play).glob("*.png"))
        for f in files:
            send(play, f)
        print(play, "uploaded", len(files), flush=True)
    r = requests.post(f"{base}/edits/{eid}:commit", headers=headers(), timeout=120)
    print("commit", r.status_code, r.text[:200])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--map", default="")
    ap.add_argument("--key")
    ap.add_argument("--package")
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    mapping = dict(DEFAULT_MAP)
    for pair in filter(None, a.map.split(",")):
        k, v = pair.split("=")
        mapping[k] = v
    done = crop_all(a.src, a.out, mapping)
    print("cropped", done)
    if a.upload:
        if not (a.key and a.package):
            sys.exit("--upload needs --key and --package")
        upload_all(a.out, list(done), a.key, a.package)
