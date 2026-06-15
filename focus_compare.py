#!/usr/bin/env python3
"""
focus_compare.py — Record two video clips to compare focus distances.
  - Clip A: 9 diopters (~111mm) — best from video sweep
  - Clip B: 15 diopters (~67mm) — what photos were actually using (clamped max)

Usage:
    python3 focus_compare.py
"""

import time
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from libcamera import controls

CLIP_DURATION = 3.0
SETTLE_TIME   = 1.5
COLOUR_GAINS  = (2.0, 1.8)

CLIPS = [
    (9.0,  "A_9diopters_111mm"),
    (15.0, "B_15diopters_67mm"),
]


def find_usb() -> Path | None:
    media = Path("/media/opencal")
    if media.exists():
        for d in sorted(media.iterdir()):
            if d.is_dir() and d.is_mount():
                return d
    return None


def record_clip(diopters: float, label: str, save_dir: Path):
    filename = f"{label}.h264"
    path = save_dir / filename

    cam = Picamera2()
    config = cam.create_video_configuration(main={"size": (1920, 1080)})
    config["controls"]["AfMode"] = controls.AfModeEnum.Manual
    cam.configure(config)
    cam.start()
    time.sleep(0.5)

    cam.set_controls({"LensPosition": diopters})
    cam.set_controls({"AwbEnable": False, "ColourGains": COLOUR_GAINS})
    time.sleep(SETTLE_TIME)

    meta = cam.capture_metadata()
    actual = meta.get("LensPosition", "N/A")
    print(f"  Recording {label} | requested={diopters} actual={actual}")

    cam.start_recording(H264Encoder(), output=str(path))
    time.sleep(CLIP_DURATION)
    cam.stop_recording()
    cam.close()
    print(f"  Saved: {filename}")


def main():
    usb = find_usb()
    save_dir = usb / "focus_compare" if usb else Path("/tmp/focus_compare")
    save_dir.mkdir(exist_ok=True)
    print(f"Saving to: {save_dir}\n")

    for diopters, label in CLIPS:
        record_clip(diopters, label, save_dir)

    print("\nDone! Compare A vs B to see which is sharper for your setup.")


if __name__ == "__main__":
    main()
