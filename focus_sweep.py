#!/usr/bin/env python3
"""
focus_sweep.py — Capture images at multiple focal distances to find optimal focus.
Saves labeled images to USB drive under a focus_sweep/ folder.

Usage:
    python3 focus_sweep.py
"""

import time
from pathlib import Path
from picamera2 import Picamera2
from libcamera import controls

# --- Configuration ---
FOCUS_START_MM = 30.0  # nearest focal distance to test (mm)
FOCUS_END_MM   = 50.0  # farthest focal distance to test (mm)
FOCUS_STEP_MM  = 2.5   # step size (mm)
SETTLE_TIME    = 1.0   # seconds to wait after focusing before capture
AWB_ENABLE     = False
COLOUR_GAINS   = (2.0, 1.8)  # (red_gain, blue_gain) — matches config.json
# ---------------------


def mm_to_diopters(mm: float) -> float:
    return 1000.0 / mm


def find_usb() -> Path | None:
    media = Path("/media/opencal")
    if media.exists():
        for d in sorted(media.iterdir()):
            if d.is_dir() and d.is_mount():
                return d
    return None


def main():
    usb = find_usb()
    if usb is None:
        print("ERROR: No USB drive found. Insert a USB drive and try again.")
        return

    save_dir = usb / "focus_sweep"
    save_dir.mkdir(exist_ok=True)
    print(f"Saving images to: {save_dir}")

    cam = Picamera2()
    still_config = cam.create_still_configuration(buffer_count=2)
    cam.configure(still_config)
    cam.start()
    time.sleep(1.0)  # warm up

    # Apply white balance matching config.json settings
    if AWB_ENABLE:
        cam.set_controls({"AwbEnable": True})
    else:
        cam.set_controls({"AwbEnable": False, "ColourGains": COLOUR_GAINS})

    mm = FOCUS_START_MM
    distances = []
    while mm <= FOCUS_END_MM + 1e-9:
        distances.append(round(mm, 2))
        mm += FOCUS_STEP_MM

    print(f"Capturing {len(distances)} images ({FOCUS_START_MM}mm to {FOCUS_END_MM}mm, every {FOCUS_STEP_MM}mm)...")

    for mm in distances:
        diopters = mm_to_diopters(mm)
        cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": diopters})
        time.sleep(SETTLE_TIME)

        filename = f"focus_{mm:05.1f}mm_{diopters:.2f}diopters.jpeg"
        path = save_dir / filename
        cam.capture_file(str(path))
        print(f"  [{distances.index(mm) + 1}/{len(distances)}] {filename}")

    cam.stop()
    print(f"\nDone! {len(distances)} images saved to {save_dir}")
    print(f"Convert winning mm to diopters: 1000 / mm  (e.g. 100mm = 10.0 diopters)")


if __name__ == "__main__":
    main()
