#!/usr/bin/env python3
"""Small Google Play Developer API helper (read-mostly).

Usage:
  play_api.py --key <service-account.json> --package <pkg> tracks
  play_api.py --key ... --package ... listings            # locales + titles
  play_api.py --key ... --package ... screenshots         # phone screenshot count per locale
  play_api.py --key ... --package ... upload-listings <metadata/android dir>   # PUT title/short/full per locale, commit

Each command opens its own edit, and deletes it afterwards unless it committed. The key file
is only handed to google-auth, never printed. Requires `pip install google-auth requests`.
"""
import json, sys, argparse
from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

SCOPE = "https://www.googleapis.com/auth/androidpublisher"


class Play:
    def __init__(self, key, package):
        self.creds = service_account.Credentials.from_service_account_file(key, scopes=[SCOPE])
        self.base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{package}"

    def h(self):
        if not self.creds.valid:
            self.creds.refresh(Request())
        return {"Authorization": f"Bearer {self.creds.token}"}

    def call(self, method, path, body=None):
        r = requests.request(method, self.base + path, headers=self.h(), json=body, timeout=120)
        if r.status_code >= 400:
            raise SystemExit(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
        return r.json() if r.text else {}

    def edit(self):
        return self.call("POST", "/edits", {})["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--package", required=True)
    ap.add_argument("cmd")
    ap.add_argument("arg", nargs="?")
    a = ap.parse_args()
    p = Play(a.key, a.package)
    eid = p.edit()
    committed = False
    try:
        if a.cmd == "tracks":
            for t in p.call("GET", f"/edits/{eid}/tracks")["tracks"]:
                rel = [(r.get("versionCodes"), r["status"], r.get("userFraction")) for r in t.get("releases", [])]
                print(t["track"], rel)
        elif a.cmd == "listings":
            for l in p.call("GET", f"/edits/{eid}/listings").get("listings", []):
                print(l["language"], "|", l.get("title"), "|", len(l.get("fullDescription", "")), "chars")
        elif a.cmd == "screenshots":
            for l in p.call("GET", f"/edits/{eid}/listings").get("listings", []):
                imgs = p.call("GET", f"/edits/{eid}/listings/{l['language']}/phoneScreenshots").get("images", [])
                print(l["language"], len(imgs))
        elif a.cmd == "upload-listings":
            root = Path(a.arg)
            for d in sorted(x for x in root.iterdir() if (x / "full_description.txt").exists()):
                body = {"language": d.name, "title": (d / "title.txt").read_text().strip(),
                        "shortDescription": (d / "short_description.txt").read_text().strip(),
                        "fullDescription": (d / "full_description.txt").read_text().strip()}
                p.call("PUT", f"/edits/{eid}/listings/{d.name}", body)
                print("listing", d.name)
            print("commit", p.call("POST", f"/edits/{eid}:commit").get("id"))
            committed = True
        else:
            raise SystemExit(f"unknown command {a.cmd}")
    finally:
        if not committed:
            requests.delete(p.base + f"/edits/{eid}", headers=p.h(), timeout=60)


if __name__ == "__main__":
    main()
