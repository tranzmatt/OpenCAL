#!/usr/bin/env python3
"""
focus_sweep_video.py — Record short video clips at multiple focal distances.
Saves labeled .h264 clips to USB under a focus_sweep_video/ folder.

Usage:
    python3 focus_sweep_video.py
"""

import time
from pathlib import Path
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from libcamera import controls

# --- Configuration ---
FOCUS_START_MM = 30.0
FOCUS_END_MM   = 50.0
FOCUS_STEP_MM  = 2.5
CLIP_DURATION  = 2.0   # seconds per clip
SETTLE_TIME    = 1.0   # seconds to wait after setting focus before recording
AWB_ENABLE     = False
COLOUR_GAINS   = (2.0, 1.8)  # matches config.json
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

    save_dir = usb / "focus_sweep_video"
    save_dir.mkdir(exist_ok=True)
    print(f"Saving clips to: {save_dir}")

    cam = Picamera2()
    video_config = cam.create_video_configuration()
    cam.configure(video_config)
    encoder = H264Encoder()

    mm = FOCUS_START_MM
    distances = []
    while mm <= FOCUS_END_MM + 1e-9:
        distances.append(round(mm, 2))
        mm += FOCUS_STEP_MM

    print(f"Recording {len(distances)} clips ({FOCUS_START_MM}mm to {FOCUS_END_MM}mm, every {FOCUS_STEP_MM}mm)...")

    for i, mm in enumerate(distances):
        diopters = mm_to_diopters(mm)
        filename = f"focus_{mm:05.1f}mm_{diopters:.2f}diopters.h264"
        path = save_dir / filename

        cam.start_recording(encoder=encoder, output=str(path))
        time.sleep(0.5)  # let pipeline initialize

        # Lock focus and white balance
        cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": diopters})
        if AWB_ENABLE:
            cam.set_controls({"AwbEnable": True})
        else:
            cam.set_controls({"AwbEnable": False, "ColourGains": COLOUR_GAINS})

        time.sleep(SETTLE_TIME)  # let lens settle before recording counts
        time.sleep(CLIP_DURATION)

        cam.stop_recording()
        print(f"  [{i + 1}/{len(distances)}] {filename}")

    print(f"\nDone! {len(distances)} clips saved to {save_dir}")
    print("Convert to mp4 for playback:  ffmpeg -i clip.h264 -c copy clip.mp4")


if __name__ == "__main__":
    main()
