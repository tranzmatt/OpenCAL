#!/usr/bin/env python3
"""
focus_sweep_video.py — Record short video clips at multiple focal distances.
Saves labeled .h264 clips to USB under a focus_sweep_video/ folder.

LensPosition range for Pi Camera Module 3: 0.0 (infinity) to 15.0 (~67mm)

Usage:
    python3 focus_sweep_video.py
"""

import time
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from libcamera import controls

# --- Configuration ---
DIOPTER_START = 1.0   # near infinity (~1000mm)
DIOPTER_END   = 15.0  # closest focus (~67mm)
DIOPTER_STEP  = 1.0
CLIP_DURATION = 2.0   # seconds per clip
SETTLE_TIME   = 1.5   # seconds to wait after setting focus before recording
AWB_ENABLE    = False
COLOUR_GAINS  = (2.0, 1.8)  # matches config.json
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
    if usb is None:
        print("ERROR: No USB drive found. Insert a USB drive and try again.")
        return

    save_dir = usb / "focus_sweep_video"
    save_dir.mkdir(exist_ok=True)
    print(f"Saving clips to: {save_dir}")

    d = DIOPTER_START
    diopters_list = []
    while d <= DIOPTER_END + 1e-9:
        diopters_list.append(round(d, 2))
        d += DIOPTER_STEP

    print(f"Recording {len(diopters_list)} clips ({DIOPTER_START} to {DIOPTER_END} diopters, step {DIOPTER_STEP})...")

    for i, diopters in enumerate(diopters_list):
        mm = 1000.0 / diopters if diopters > 0 else 9999
        filename = f"focus_{diopters:05.2f}diopters_{mm:.0f}mm.h264"
        path = save_dir / filename

        cam = Picamera2()
        config = cam.create_video_configuration(main={"size": (1920, 1080)})
        config["controls"]["AfMode"] = controls.AfModeEnum.Manual
        cam.configure(config)
        cam.start()
        time.sleep(0.5)

        cam.set_controls({"LensPosition": diopters})
        if AWB_ENABLE:
            cam.set_controls({"AwbEnable": True})
        else:
            cam.set_controls({"AwbEnable": False, "ColourGains": COLOUR_GAINS})
        time.sleep(SETTLE_TIME)

        meta = cam.capture_metadata()
        actual = meta.get("LensPosition", "N/A")
        cam.start_recording(H264Encoder(), output=str(path))
        time.sleep(CLIP_DURATION)
        cam.stop_recording()
        cam.close()
        print(f"  [{i + 1}/{len(diopters_list)}] {diopters:.2f} diopters (~{mm:.0f}mm) | actual={actual} | {filename}")

    print(f"\nDone! {len(diopters_list)} clips saved to {save_dir}")
    print("Convert to mp4:  ffmpeg -i clip.h264 -c copy clip.mp4")


if __name__ == "__main__":
    main()
