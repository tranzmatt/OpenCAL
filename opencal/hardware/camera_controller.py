import time
from typing import final
from pathlib import Path
from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from libcamera import controls  # pyright: ignore

from opencal.utils.config import CameraConfig


@final
class CameraController:
    def __init__(self, config: CameraConfig):
        """Initialize the CameraController with configuration from a JSON file."""

        # TODO: remove unneccessary config
        self.cam_type = config.type
        self.camera_index = config.index
        self.save_path = Path(config.save_path)

        self.capture = None
        self._stream_thread = None
        self.streaming = False
        self._record_thread = None
        self._recording = False
        self.writer = None
        self.record_file = None
        self._proc = None
        self._raw_file = None
        self.fps = 20
        self.recording = False

        self._focus_diopters: float = 9.5  # ~105mm focal distance
        self._awb_enable: bool = config.awb_enable
        self._colour_gains: tuple[float, float] = config.colour_gains

        try:
            self.picam = Picamera2()
            self.still_config = self.picam.create_still_configuration(buffer_count=2)
            self.video_config = self.picam.create_video_configuration()
            self.picam.configure(self.still_config)
        except Exception as e:
            self.picam = None
            print("WARNING: No camera connected, camera functionality disabled.")

    def start_camera(self, preview: bool = False):
        """Start the camera and begin streaming if requested.

        Args:
            preview (bool): Whether to show a preview of the camera feed.
        """
        if not self.picam:
            print("WARNING: No camera connected, cannot start camera.")
            return
        if self.picam.started:
            return

        if preview:
            config = self.picam.create_preview_configuration()
            self.picam.configure(config)
            # self.picam.start_preview(Preview.QT)

        self.picam.start()
        self._apply_controls()

    def capture_image(self, save_path: Path | None = None) -> bool:
        if not self.picam:
            print("WARNING: No camera connected, cannot capture image.")
            return False

        try:
            if not self.picam.started:
                self.start_camera(preview=True)

            if save_path is None:
                save_path = self.save_path / "capture.jpeg"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            self.picam.switch_mode_and_capture_file(self.still_config, save_path)
            return True
        except Exception as e:
            print(f"ERROR: Image capture failed: {e}")
            return False

    def _apply_controls(self):
        """Apply focus and white balance after every camera start/reconfigure."""
        self.picam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": self._focus_diopters})
        if self._awb_enable:
            self.picam.set_controls({"AwbEnable": True})
        else:
            self.picam.set_controls({"AwbEnable": False, "ColourGains": self._colour_gains})

    def set_focus(self, diopters: float):
        """Turns off autofocus and sets a manual focal distance in diopters (m^-1)"""
        if not self.picam:
            print("WARNING: No camera connected, cannot start camera.")
            return
        self._focus_diopters = diopters
        self.picam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": diopters})

    def activate_autofocus(self):
        if not self.picam:
            print("WARNING: No camera connected, cannot start camera.")
            return
        self.picam.set_controls({"AfMode": controls.AfModeEnum.Continuous})

    def start_recording(self, file: Path):
        if not self.picam:
            print("WARNING: No camera connected, cannot start camera.")
            return
        if self.picam.started:
            self.picam.stop()
        video_config = self.picam.create_video_configuration(main={"size": (1920, 1080)})
        video_config["controls"]["AfMode"] = controls.AfModeEnum.Manual
        self.picam.configure(video_config)
        encoder = H264Encoder()
        self.picam.start_recording(encoder=encoder, output=str(file))
        time.sleep(0.5)  # wait for pipeline to fully initialize before locking controls
        self._apply_controls()
        print("DEBUG: starting recording")
        self._recording = True

    def stop_recording(self):
        if not self.picam:
            return
        if self._recording:
            print("DEBUG: stopping recording")
            self.picam.stop_recording()

    def stop_camera(self):
        """Stop the camera and release resources."""
        if not self.picam:
            return
        self.picam.stop()


if __name__ == "__main__":
    from opencal.utils.config import Config

    cfg = Config()
    cam = CameraController(cfg.camera)  # Create an instance of the CameraController
    cam.cam_type = "rpi"  # Set camera type to Raspberry Pi (or "usb")
    print("Recording... Press Ctrl+C to stop.")

    time.sleep(10)  # Record for 5 seconds

    cam.stop_all()  # Stop all operations
