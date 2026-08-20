# App tour reel

`app-tour.mp4` — a 15s portrait (1080x1920) reel that pans through the five app
screens in order: Home → Food → Grocery → Pharmacy → Cart.

## Rebuilding it

    python3 tools/stitch_video.py media/screens media/app-tour.mp4 --seconds 3.5 --fade 0.6

The stitcher reads every image in the folder **sorted by filename**, so the
`01-`…`05-` prefixes set the running order. Tall images get a slow vertical pan
(the whole screen is seen); anything that fits the frame gets a gentle push-in.
Segments are joined with crossfades and the reel fades in from / out to black.

Requires `pip install pillow`, plus `ffmpeg` on PATH or `pip install imageio-ffmpeg`.

## Swapping in real screenshots

Drop your own PNGs into `media/screens/`, keeping the numeric prefixes for
ordering, and re-run the command above. Nothing else needs to change.

## About the current frames

The images in `media/screens/` are **rebuilt mockups**, rendered from
`src/screens.html` via headless Chromium (`src/shoot.py`), not the original
screenshots. Layout, copy, and colour match the source designs; the food and
product photography is stood in for with gradient tiles, since the photos
themselves were not available to the build.
