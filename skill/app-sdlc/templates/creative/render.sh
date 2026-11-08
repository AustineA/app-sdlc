#!/bin/zsh
# Renders a comp at device scale 2 with Playwright's headless shell (the same way Grain renders
# its overlays). Usage: ./render.sh header|search  ->  ../creative-export/en-US/<name>.png + preview jpg
set -e
cd "$(dirname "$0")"
NAME=$1; LOCALE=${2:-en-US}
case $NAME in header) W=1920; H=823 ;; search|layers*) W=1920; H=1280 ;; *) echo "unknown $NAME"; exit 1 ;; esac
CHROME=$(ls -d ~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell | tail -1)
OUT=../creative-export/$LOCALE; mkdir -p $OUT
"$CHROME" --headless --hide-scrollbars --force-device-scale-factor=2 --allow-file-access-from-files \
  --window-size=$W,$H --virtual-time-budget=4000 --screenshot=$OUT/$NAME.png "file://$PWD/$NAME.html?loc=$LOCALE" >/dev/null 2>&1
python3 -c "
from PIL import Image; im=Image.open('$OUT/$NAME.png').convert('RGB'); print(im.size)
im.thumbnail((1600,1600)); im.save('$OUT/$NAME-preview.jpg', quality=85)"
