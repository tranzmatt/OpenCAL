#!/usr/bin/env python3
"""
focus_final_test.py — Capture one still and one video clip at chosen focus values.

Usage:
    python3 focus_final_test.py
"""

import time
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from libcamera import controls

PHOTO_DIOPTERS = 10.0   # ~100mm — best from still sweep
VIDEO_DIOPTERS = [9.0, 10.0]  # ~111mm and ~100mm — compare both
COLOUR_GAINS   = (2.0, 1.8)


def find_usb() -> Path | None:
    media = Path("/media/opencal")
    if media.exists():
        for d in sorted(media.iterdir()):
            if d.is_dir() and d.is_mount():
                return d
    return None


def main():
    usb = find_usb()
    save_dir = usb / "focus_final" if usb else Path("/tmp/focus_final")
    save_dir.mkdir(exist_ok=True)
    print(f"Saving to: {save_dir}\n")

    # --- Still photo ---
    print(f"[Photo] {PHOTO_DIOPTERS} diopters (~{1000/PHOTO_DIOPTERS:.0f}mm)")
    cam = Picamera2()
    still_config = cam.create_still_configuration(buffer_count=2)
    still_config["controls"]["AfMode"] = controls.AfModeEnum.Manual
    cam.configure(still_config)
    cam.start()
    time.sleep(1.0)
    cam.set_controls({"LensPosition": PHOTO_DIOPTERS,
                      "AwbEnable": False, "ColourGains": COLOUR_GAINS})
    time.sleep(1.5)
    meta = cam.capture_metadata()
    print(f"  actual LensPosition: {meta.get('LensPosition', 'N/A')}")
    photo_path = save_dir / f"photo_{PHOTO_DIOPTERS}diopters.jpeg"
    cam.capture_file(str(photo_path))
    cam.stop()
    cam.close()
    print(f"  Saved: {photo_path.name}\n")

    # --- Video clips ---
    for d in VIDEO_DIOPTERS:
        print(f"[Video] {d} diopters (~{1000/d:.0f}mm)")
        cam = Picamera2()
        video_config = cam.create_video_configuration(main={"size": (1920, 1080)})
        video_config["controls"]["AfMode"] = controls.AfModeEnum.Manual
        cam.configure(video_config)
        cam.start()
        time.sleep(0.5)
        cam.set_controls({"LensPosition": d,
                          "AwbEnable": False, "ColourGains": COLOUR_GAINS})
        time.sleep(1.5)
        meta = cam.capture_metadata()
        print(f"  actual LensPosition: {meta.get('LensPosition', 'N/A')}")
        video_path = save_dir / f"video_{d}diopters.h264"
        cam.start_recording(H264Encoder(), output=str(video_path))
        time.sleep(5.0)
        cam.stop_recording()
        cam.close()
        print(f"  Saved: {video_path.name}\n")

    print("\nDone!")


if __name__ == "__main__":
    main()
