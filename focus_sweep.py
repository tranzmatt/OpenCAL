#!/usr/bin/env python3
"""
focus_sweep.py — Capture still images at multiple focal distances.
Saves labeled .jpeg images to USB under a focus_sweep/ folder.

LensPosition range for Pi Camera Module 3: 0.0 (infinity) to 15.0 (~67mm)

Usage:
    python3 focus_sweep.py
"""

import time
from pathlib import Path
from picamera2 import Picamera2
from libcamera import controls

# --- Configuration ---
DIOPTER_START = 1.0
DIOPTER_END   = 15.0
DIOPTER_STEP  = 1.0
SETTLE_TIME   = 1.5   # seconds to wait after setting focus before capture
AWB_ENABLE    = False
COLOUR_GAINS  = (2.0, 1.8)
# ---------------------


def find_usb() -> Path | None:
    media = Path("/media/opencal")
    if media.exists():
        for d in sorted(media.iterdir()):
            if d.is_dir() and d.is_mount():
                return d
    return None


def main():
    usb = find_usb()
    save_dir = usb / "focus_sweep" if usb else Path("/tmp/focus_sweep")
    save_dir.mkdir(exist_ok=True)
    print(f"Saving images to: {save_dir}")

    d = DIOPTER_START
    diopters_list = []
    while d <= DIOPTER_END + 1e-9:
        diopters_list.append(round(d, 2))
        d += DIOPTER_STEP

    print(f"Capturing {len(diopters_list)} images ({DIOPTER_START} to {DIOPTER_END} diopters, step {DIOPTER_STEP})...")

    cam = Picamera2()
    still_config = cam.create_still_configuration(buffer_count=2)
    still_config["controls"]["AfMode"] = controls.AfModeEnum.Manual
    cam.configure(still_config)
    cam.start()
    time.sleep(1.0)

    if not AWB_ENABLE:
        cam.set_controls({"AwbEnable": False, "ColourGains": COLOUR_GAINS})

    for i, diopters in enumerate(diopters_list):
        mm = 1000.0 / diopters if diopters > 0 else 9999
        cam.set_controls({"LensPosition": diopters})
        time.sleep(SETTLE_TIME)

        meta = cam.capture_metadata()
        actual = meta.get("LensPosition", "N/A")

        filename = f"focus_{diopters:05.2f}diopters_{mm:.0f}mm.jpeg"
        path = save_dir / filename
        cam.capture_file(str(path))
        print(f"  [{i + 1}/{len(diopters_list)}] {diopters:.2f} diopters (~{mm:.0f}mm) | actual={actual} | {filename}")

    cam.stop()
    cam.close()
    print(f"\nDone! {len(diopters_list)} images saved to {save_dir}")


if __name__ == "__main__":
    main()
