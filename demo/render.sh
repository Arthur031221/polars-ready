#!/bin/sh
set -eu
cd /home/levi/personal-oss/polars-ready
vhs demo/demo.tape
google-chrome --headless --no-sandbox --disable-gpu --hide-scrollbars --window-size=1200,675 --screenshot=assets/social-card.png file:///home/levi/personal-oss/polars-ready/demo/social-card.html >/dev/null 2>&1
