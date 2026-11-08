# Creative assets starter (from Last Summer, 2026-11-08)

Copy into `<project>/appstore/creative/`, then replace the look: `desk.css` tokens and font, the plate
(`kit/plate-header.jpg`, `kit/plate-search.jpg`), props in `kit/`, photos in `photos/`, the copy in both
comps and the `PIECES`/`HERO`/`SWITCHES` timeline in `build_video.py`. Element ids in `search.html` are
what `build_video.py` animates; keep them in sync. See `references/creative-assets.md`.

    ./render.sh header && ./render.sh search      # ../creative-export/en-US/{header,search}.png + previews
    python3 build_video.py                        # ../creative-export/en-US/search.mp4 + frame JPGs
