# iOS 27 creative assets: product page header + search results

App Store Connect (iOS 27) takes three creative assets per version localization, through the
**Asset Library** API. They are separate from screenshots: the header sits at the top of the product
page, the search asset replaces the screenshot strip in search results. Shipped this way for Grain
(2026-11-06, 18 locales) and Last Summer (2026-11-08).

## Contents
- Specs
- Design rules
- Pipeline
- Upload (`scripts/asc_creative.mjs`)
- Verify
- Lessons

## Specs

| Asset | Canvas (author at half size, render @2x) | File | Placement |
|---|---|---|---|
| Product page header | 1920×823 CSS → **3840×1646** PNG (≈2.33:1) | `header.png` | `PRODUCT_PAGE_HEADER_ASSET` |
| Search results image | 1920×1280 → **3840×2560** PNG (3:2) | `search.png` | none: keep it in the library as the fallback |
| Search results video | **1920×1280**, 30 fps, 15–30 s, H.264 High, `yuv420p`, `+faststart`, silent stereo AAC | `search.mp4` | `APP_STORE_SEARCH_RESULTS_ASSET` |

- The search slot takes **one** asset; give it the video. Upload the still anyway as the fallback.
- **iPhone shows only the header's centre band: x 345–1575 of 1920 CSS px** (the middle 2460 of 3840).
  Headline and hero must sit inside it; the outer bands are extra scene for iPad and Mac. Always make
  an iPhone crop preview (`crop((690, 0, 3150, 1646))`) and judge that, not the full banner.
- The video loops: its last frame must equal its first (lift everything away, rest on the bare scene).
- Uploads ~8–22 MB each are fine.

## Design rules
- **One scene for all three.** A styled surface ("desk") with real app output on it plus a few props,
  headline in the brand's display face. Grain: bone paper, instant prints, stickers. Last Summer: dark
  table in late sun, prints from the film shaders, disposable camera, canisters.
- **Real product output, not mockups.** The hero is something the app actually made: a rendered
  template frame, a photo through the real filter (reuse the screenshot campaign's captures). Label it
  when it helps (Last Summer writes each film's name in the print's chin).
- Headline = the approved screenshot headline 1 (or its first two lines). Don't invent new copy; offer
  options if none is approved.
- Check the brand font has every glyph you use (VCR OSD Mono has no `·`; use `/`).
- Type gets a soft radial scrim plus text-shadow so it reads on busy plates.
- Keep text and hero clear of each other: check every print/card edge against the headline in the render.
- No device frames needed; it's marketing art, not a screen capture. Nothing that implies features the
  app lacks.

## Pipeline
Folder: `<project>/appstore/creative/` (sources, committed) and `<project>/appstore/creative-export/<locale>/`
(outputs, gitignored with `creative/gen/` and `creative/build/`). Start from `templates/creative/` in this skill:

| File | Role |
|---|---|
| `desk.css` | shared look: plate, scrim, `.print` (instant print + chin `.label`), shadows, type classes |
| `header.html`, `search.html` | the two comps, absolutely positioned at half size; `search.html` has **layer mode** |
| `render.sh header\|search [locale]` | Playwright headless shell, `--force-device-scale-factor=2` → PNG + preview JPG |
| `build_video.py [locale]` | shoots each element alone (`search.html?only=<id>[&src=&label=]`, transparent page), animates with PIL, pipes rgb24 to ffmpeg |

1. **Gather real output**: screenshot-campaign captures, rendered frames (`-RenderTemplate`-style debug
   launch args), or new captures through the app with Argent. Downscale to ~1000 px JPGs in `photos/`.
2. **Plate and props**: generate with **Sume** (the user's choice over fal). Dry-run first, keep it to
   ~3 calls (Last Summer: $0.55):
   - plate: `google/nano-banana-pro`, 4K, **3:2**, "top-down flat-lay of an empty <surface>, <light>,
     nothing on it, no text". Crop the surface interior for both 3:2 and 2.33:1 so both assets share it.
     A 21:9 request came back as an angled table that fought the flat props; crop from the 3:2 instead.
   - props: `openai/gpt-image-2.5`, `background: transparent`, 2K, one sheet with 3–4 unbranded props
     spaced apart; split them by alpha bbox / column gaps into `kit/`.
   - App assets work too when big enough (the app's own stickers, icons); 140 px canisters were too small.
3. **Comps**: write `header.html` and `search.html`, render, look at the preview and the iPhone crop,
   fix overlaps and covered labels, repeat. Expect 3–5 passes.
4. **Video** (`build_video.py`): static layers + per-element sprites (cropped to alpha bbox), entrances
   (slide from off-table, prints "drop" from 1.18× scale with a 0.18 s fade), a hero that changes
   (Last Summer re-develops one photo through three films with a cross-fade and a screen-blended warm
   leak; Grain plays the real template frames), staggered lift-away exit, bare scene at both ends.
   15 s renders in ~15 s. Grain's variant (`~/Codes/Grain/appstore/creative/build_video.py`) uses a
   white/black difference matte for type and real app frames from the simulator.
5. **QC**: a timeline contact sheet (frames at ~0.2, 1, 2, 3.5, switch points, exit, last) and the
   iPhone header crop. Show the user en-US first; localize only after approval.
6. **Locales**: per-locale copy (headline lines, note) in a `copy.js` keyed by ASC locale, with faces
   per script (ru Baskerville, ar DecoType Naskh, hi ITF Devanagari, ja Hiragino Mincho, ko AppleMyungjo,
   zh PingFang) and `data-max` auto-shrink. Render to `creative-export/<locale>/`. Brand and film names
   stay English. Use ASC's locale codes (`it`, `tr`, `ru`, `hi`, `ja`, `ko`, …: read them from the
   version's localizations, they are not all `xx-YY`).

## Upload (`scripts/asc_creative.mjs`)
```
node ~/.agents/skills/app-sdlc/scripts/asc_creative.mjs --project <root> --version 1.5.0 --dir appstore/creative-export --dry-run
node … --project <root> --version 1.5.0 --dir appstore/creative-export en-US
node … --project <root> --version 1.5.0 --dir appstore/creative-export        # every locale folder present
```
- Reads `<root>/.asc-config.json` (keyId, issuerId, keyPath, bundleId); finds the app and the editable
  version; per locale uploads `header.png`, `search.png`, `search.mp4` (whichever exist) to
  `appAssetLibraryImages` / `appAssetLibraryVideos` (`category: CREATIVE_ASSETS`, upload operations,
  `PATCH uploaded: true`), waits for processing, then creates `appAssetLibraryPlacements`.
- Ids are kept in `<dir>/creative.json`, so a rerun skips finished uploads and placements.
- Only touches an editable version (`PREPARE_FOR_SUBMISSION` etc.). Never submits.

## Verify
- The script's final check reads every placement back with `GET /v1/appAssetLibraryPlacements/<id>`
  and expects `state: ACTIVE` (the localization has no placements relationship: that path 404s).
- Look at the version in App Store Connect once (Product Page → creative assets) for the first locale.

## Lessons
- Bash Playwright scripts get blocked; the headless-shell binary called directly with `--screenshot`
  works (`--default-background-color=00000000` for transparent layers).
- Labels in print chins get covered by the next print: stack so each chin stays visible.
- Similar-looking variants (three warm films) read as "no change" at search size; pick variants
  that differ visibly for the hero.
