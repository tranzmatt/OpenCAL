#!/usr/bin/env python3
"""
focus_test.py — Tests multiple strategies to apply manual focus in video mode.
Prints actual LensPosition from metadata for each attempt.
Target: 33.33 diopters (30mm). If successful, LensPosition should read ~33.33.

Usage:
    python3 focus_test.py
"""

import time
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from libcamera import controls

TARGET_DIOPTERS = 33.33
WB_CONTROLS = {"AwbEnable": False, "ColourGains": (2.0, 1.8)}


def read_lens(cam, label):
    meta = cam.capture_metadata()
    lp = meta.get("LensPosition", "N/A")
    af = meta.get("AfMode", "N/A")
    print(f"  {label}: LensPosition={lp}  AfMode={af}")
    return lp


# ---------------------------------------------------------------------------
# Strategy 1: full-res raw stream to enable PDAF, controls set after start
# ---------------------------------------------------------------------------
def strategy_1():
    print("\n[Strategy 1] Full-res raw (4608x2592) to enable PDAF")
    cam = Picamera2()
    cam.configure(cam.create_video_configuration(
        main={"size": (1920, 1080)},
        raw={"size": (4608, 2592)},
    ))
    cam.start()
    time.sleep(1.0)
    cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": TARGET_DIOPTERS})
    cam.set_controls(WB_CONTROLS)
    time.sleep(1.0)
    read_lens(cam, "after set_controls")
    cam.stop()
    cam.close()


# ---------------------------------------------------------------------------
# Strategy 2: set AfMode first, wait, then set LensPosition separately
# ---------------------------------------------------------------------------
def strategy_2():
    print("\n[Strategy 2] Separate AfMode then LensPosition calls")
    cam = Picamera2()
    cam.configure(cam.create_video_configuration(
        main={"size": (1920, 1080)},
        raw={"size": (4608, 2592)},
    ))
    cam.start()
    time.sleep(1.0)
    cam.set_controls({"AfMode": controls.AfModeEnum.Manual})
    time.sleep(0.5)
    cam.set_controls({"LensPosition": TARGET_DIOPTERS})
    cam.set_controls(WB_CONTROLS)
    time.sleep(1.0)
    read_lens(cam, "after separate calls")
    cam.stop()
    cam.close()


# ---------------------------------------------------------------------------
# Strategy 3: same as 2 but with much longer settle time (3s)
# ---------------------------------------------------------------------------
def strategy_3():
    print("\n[Strategy 3] Longer settle time (3s)")
    cam = Picamera2()
    cam.configure(cam.create_video_configuration(
        main={"size": (1920, 1080)},
        raw={"size": (4608, 2592)},
    ))
    cam.start()
    time.sleep(1.0)
    cam.set_controls({"AfMode": controls.AfModeEnum.Manual})
    time.sleep(1.0)
    cam.set_controls({"LensPosition": TARGET_DIOPTERS})
    time.sleep(3.0)
    read_lens(cam, "after 3s settle")
    cam.stop()
    cam.close()


# ---------------------------------------------------------------------------
# Strategy 4: default video config (no raw), separate calls — baseline
# ---------------------------------------------------------------------------
def strategy_4():
    print("\n[Strategy 4] Default video config (no raw), separate calls — baseline")
    cam = Picamera2()
    cam.configure(cam.create_video_configuration())
    cam.start()
    time.sleep(1.0)
    cam.set_controls({"AfMode": controls.AfModeEnum.Manual})
    time.sleep(0.5)
    cam.set_controls({"LensPosition": TARGET_DIOPTERS})
    time.sleep(1.0)
    read_lens(cam, "after set_controls")
    cam.stop()
    cam.close()


# ---------------------------------------------------------------------------
# Strategy 5: set focus in still mode, switch_mode to video without stopping
# ---------------------------------------------------------------------------
def strategy_5():
    print("\n[Strategy 5] Set focus in still mode, then switch_mode to video")
    from pathlib import Path
    usb = next((d for d in sorted(Path("/media/opencal").iterdir()) if d.is_mount()), None)
    out = str((usb or Path("/tmp")) / "strategy5_test.h264")

    cam = Picamera2()
    still_config = cam.create_still_configuration(buffer_count=2)
    video_config = cam.create_video_configuration(main={"size": (1920, 1080)})

    cam.configure(still_config)
    cam.start()
    time.sleep(1.0)

    cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": TARGET_DIOPTERS})
    cam.set_controls(WB_CONTROLS)
    time.sleep(1.5)  # let lens physically move
    read_lens(cam, "still mode after set_controls")

    # Switch to video without stopping — lens stays in position
    cam.switch_mode(video_config)
    time.sleep(0.5)
    read_lens(cam, "video mode after switch_mode")

    cam.start_recording(H264Encoder(), output=out)
    time.sleep(2.0)
    read_lens(cam, "video mode while recording")
    cam.stop_recording()
    cam.close()
    print(f"  Saved clip to {out}")


# ---------------------------------------------------------------------------
# Strategy 6: embed controls in config dict before configure() — IPA starts in manual
# ---------------------------------------------------------------------------
def strategy_6():
    print("\n[Strategy 6] Controls embedded in config dict before configure()")
    cam = Picamera2()
    config = cam.create_video_configuration(main={"size": (1920, 1080)})
    config["controls"]["AfMode"] = controls.AfModeEnum.Manual
    config["controls"]["LensPosition"] = TARGET_DIOPTERS
    cam.configure(config)
    cam.start()
    time.sleep(1.0)
    read_lens(cam, "after start")
    cam.stop()
    cam.close()


# ---------------------------------------------------------------------------
# Strategy 7: call set_controls BEFORE cam.start() — queued as startup controls
# ---------------------------------------------------------------------------
def strategy_7():
    print("\n[Strategy 7] set_controls before cam.start()")
    cam = Picamera2()
    cam.configure(cam.create_video_configuration(main={"size": (1920, 1080)}))
    cam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": TARGET_DIOPTERS})
    cam.start()
    time.sleep(1.0)
    read_lens(cam, "after start")
    cam.stop()
    cam.close()


# ---------------------------------------------------------------------------
# Strategy 8: AfMode=Manual in config dict, then LensPosition set AFTER start
# Also records a 3s clip so you can visually verify focus changed
# ---------------------------------------------------------------------------
def strategy_8():
    print("\n[Strategy 8] AfMode in config dict, LensPosition set after start + record clip")
    from pathlib import Path
    usb = next((d for d in sorted(Path("/media/opencal").iterdir()) if d.is_mount()), None)
    out = str((usb or Path("/tmp")) / "strategy8_test.h264")

    cam = Picamera2()
    config = cam.create_video_configuration(main={"size": (1920, 1080)})
    config["controls"]["AfMode"] = controls.AfModeEnum.Manual
    cam.configure(config)
    cam.start()
    time.sleep(0.5)

    read_lens(cam, "before LensPosition")
    cam.set_controls({"LensPosition": TARGET_DIOPTERS})
    cam.set_controls(WB_CONTROLS)
    time.sleep(1.5)
    read_lens(cam, "after LensPosition + 1.5s")

    cam.start_recording(H264Encoder(), output=out)
    time.sleep(3.0)
    read_lens(cam, "while recording")
    cam.stop_recording()
    cam.close()
    print(f"  Saved clip to {out} — compare focus visually against default (15 diopters / 67mm)")


if __name__ == "__main__":
    print(f"Testing manual focus in video mode. Target: {TARGET_DIOPTERS} diopters (30mm)")
    print("LensPosition should read ~33.33 if controls are being applied.\n")
    strategy_8()
    print("\nDone.")
