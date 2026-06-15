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

        cam = Picamera2()
        cam.configure(cam.create_video_configuration(main={"size": (2304, 1296)}))
        cam.start()
        time.sleep(0.5)

        # Set focus and WB while camera is running but not yet recording
        cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": diopters})
        if AWB_ENABLE:
            cam.set_controls({"AwbEnable": True})
        else:
            cam.set_controls({"AwbEnable": False, "ColourGains": COLOUR_GAINS})
        time.sleep(SETTLE_TIME)  # let lens physically move before recording starts

        # Check what the camera actually reports before recording
        metadata = cam.capture_metadata()
        actual_lens = metadata.get("LensPosition", "N/A")
        actual_af   = metadata.get("AfMode", "N/A")
        print(f"  [{i + 1}/{len(distances)}] target={diopters:.2f} diopters | actual LensPosition={actual_lens} AfMode={actual_af}")

        # Start encoder on already-running camera — lens stays in position
        cam.start_recording(H264Encoder(), output=str(path))
        time.sleep(CLIP_DURATION)

        cam.stop_recording()
        cam.close()
        print(f"             saved: {filename}")

    print(f"\nDone! {len(distances)} clips saved to {save_dir}")
    print("Convert to mp4 for playback:  ffmpeg -i clip.h264 -c copy clip.mp4")


if __name__ == "__main__":
    main()
