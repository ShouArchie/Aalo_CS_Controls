#!/usr/bin/env python3

import argparse
import csv
import math
import sys
import threading
import time
from datetime import datetime

import cv2
import matplotlib.pyplot as plt
import numpy as np
import serial
from matplotlib import animation, patches
from matplotlib.backend_bases import MouseButton
from mpl_toolkits.axes_grid1 import make_axes_locatable

import irpythermal
import utils

# TODO(frans): We should get rid of those
# ruff: noqa: PTH123           # use Path.open
# ruff: noqa: ANN201,ANN001    # type annotations
# ruff: noqa: DTZ005           # timezone missing
# ruff: noqa: RUF005           # tuple / list concatenation
# ruff: noqa: D100,D101,D103   # documentation missing
# ruff: noqa: PLR0915          # too many statements
# ruff: noqa: C901             # function too complex
# ruff: noqa: PLR0912          # too many branches
# ruff: noqa: FIX002           # fix instead of TODO
# ruff: noqa: ERA001           # commented out code
# ruff: noqa: SIM105,S110,E722 # exceptions

# see https://matplotlib.org/tutorials/colors/colormaps.html
CMAP_NAMES = [
    "inferno",
    "plasma",
    "coolwarm",
    "cividis",
    "jet",
    "nipy_spectral",
    "binary",
    "gray",
    "tab10",
]


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Thermal Camera Viewer")
    parser.add_argument(
        "-r", "--rawcam", action="store_true", help="use the raw camera"
    )
    parser.add_argument(
        "-d", "--device", type=str, help="use the camera at camera_path"
    )
    parser.add_argument(
        "-o",
        "--offset",
        type=float,
        help="set a fixed offset for the temperature data",
    )

    # lock in thermometry options (all of these are requred)
    parser.add_argument(
        "-l",
        "--lockin",
        type=float,
        help=(
            "enable lock-in thermometry with the given frequency (in Hz),"
            " ideally several times smaller than the camera fps"
        ),
    )
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        help=(
            "set the serial port for the power supply control (will send 1 to turn on"
            " the load, 0 to turn it off new line terminated) at 115200 baud"
        ),
    )
    parser.add_argument(
        "-i",
        "--integration",
        type=float,
        help="set the integration time for the lock-in thermometry (in seconds)",
    )
    parser.add_argument(
        "file", nargs="?", type=str, help="use the emulator with the data in file.npy"
    )
    return parser.parse_args()


args = parse_arguments()


class AppState:
    def __init__(self, args: argparse.Namespace) -> None:
        """Set up a default application state."""
        self.fps = 40
        self.exposure = {
            "auto": True,
            "auto_type": "ends",  # 'center' or 'ends'
            "T_min": 0.0,
            "T_max": 50.0,
            "T_margin": 2.0,
        }
        self.draw_temp = True

        # Choose the camera class
        self.camera: irpythermal.Camera
        self.lockin = False

        if args.file and args.file.endswith(".npy"):
            self.camera = irpythermal.CameraEmulator(args.file)
        else:
            camera_kwargs = {}
            if args.rawcam:
                camera_kwargs["camera_raw"] = True
            if args.device:
                camera_path = args.device
                cv2_cam = cv2.VideoCapture(camera_path)
                camera_kwargs["video_dev"] = cv2_cam
            if args.offset:
                camera_kwargs["fixed_offset"] = args.offset

            if args.lockin:
                self.lockin = True
                self.draw_temp = False
                # check if all lock-in thermometry options are provided
                if not args.port or not args.integration:
                    print(
                        "Error: lock-in thermometry also requires --port and"
                        " --integration options"
                    )
                    sys.exit(1)

                self.fequency = args.lockin
                self.port = args.port
                self.integration = args.integration

            self.camera = irpythermal.Camera(**camera_kwargs)

        self.cmaps_idx = 1

        # matplotlib.rcParams['toolbar'] = 'None'

        # temporary fake frame
        self.frame = np.full((self.camera.height, self.camera.width), 25.0)
        self.quad_frame = np.full((self.camera.height, self.camera.width), 0.0)
        self.in_phase_frame = np.full((self.camera.height, self.camera.width), 0.0)
        self.lut = None  # will be defined later
        self.start_skips = 2
        self.is_capturing = False
        self.lock = threading.Lock()
        self.lock_in_thread = None

        if self.lockin:
            self.fig, self.axes = plt.subplots(nrows=2, ncols=2, layout="tight")
            axes = self.axes
            self.ax = axes[0][0]
            self.im = axes[0][0].imshow(self.frame, cmap=CMAP_NAMES[self.cmaps_idx])
            im_in_phase = axes[0][1].imshow(self.frame, cmap=CMAP_NAMES[self.cmaps_idx])
            im_quadrature = axes[1][1].imshow(
                self.frame, cmap=CMAP_NAMES[self.cmaps_idx]
            )
            axes[0][0].set_title("Live")
            axes[0][1].set_title("In-phase")
            axes[1][1].set_title("Quadrature")
            divider = make_axes_locatable(axes[0][0])
            divider_in_phase = make_axes_locatable(axes[0][1])
            divider_quadrature = make_axes_locatable(axes[1][1])
            cax = divider.append_axes("right", size="5%", pad=0.05)
            cax_in_phase = divider_in_phase.append_axes("right", size="5%", pad=0.05)
            cax_quadrature = divider_quadrature.append_axes(
                "right", size="5%", pad=0.05
            )
            plt.colorbar(self.im, cax=cax)
            self.cbar_in_phase = plt.colorbar(im_in_phase, cax=cax_in_phase)
            self.cbar_quadrature = plt.colorbar(im_quadrature, cax=cax_quadrature)

            axes[1][0].axis("off")
            status_text = """
        Frame: -,
        Time: -/-,
        Load: -,
        Frequency: -Hz,
        Integration Time: -s
        Serial Port: -
        """
            self.status_text_obj = axes[1][0].text(
                0.05,
                0.95,
                status_text,
                verticalalignment="top",
                horizontalalignment="left",
                transform=axes[1][0].transAxes,
                fontsize=12,
                color="black",
            )

        else:
            self.fig = plt.figure()
            self.ax = plt.gca()
            self.im = self.ax.imshow(self.frame, cmap=CMAP_NAMES[self.cmaps_idx])
            divider = make_axes_locatable(self.ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(self.im, cax=cax)

        try:
            self.fig.canvas.set_window_title("Thermal Camera")
        except:
            # does not work on windows
            pass

        self.annotations = utils.Annotations(self.ax, patches)
        self.temp_annotations = {
            "std": {"Tmin": "lightblue", "Tmax": "red", "Tcenter": "yellow"},
            "user": {},
        }

        # Add the patch to the Axes
        self.roi = ((0, 0), (0, 0))

        self.paused = False
        self.update_colormap = True
        self.diff = {
            "enabled": False,
            "annotation_enabled": False,
            "frame": np.zeros(self.frame.shape),
        }

        self.csv_filename = None
        self.mouse_action_pos = (0, 0)
        self.mouse_action = None


app_state = AppState(args)


def log_annotations_to_csv(annotation_frame) -> None:
    anns_data = []
    for ann_type in ["std", "user"]:
        for ann_name in app_state.temp_annotations[ann_type]:
            pos = app_state.annotations.get_pos(ann_name)
            val = round(app_state.annotations.get_val(ann_name, annotation_frame), 2)
            anns_data += [pos[0], pos[1], val]  # store each position and value
    if app_state.csv_filename is not None:
        with open(app_state.csv_filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now()] + anns_data)


def get_lockin_frame(freq, port, integration):
    """
    Perform all of the lock-in thermometry operations.

    Returns the in-phase and quadrature frames after the integration time is up, while
    controlling the load via serial communication based on the period of the signal.
    """
    try:
        ser = serial.Serial(port, 115200)  # Open the serial port
    except serial.SerialException as exc:
        print(f"Error: could not open serial port {port} ({exc})")
        sys.exit(1)

    start_time = time.time()
    in_phase_sum = np.zeros((app_state.camera.height, app_state.camera.width))
    quadrature_sum = np.zeros((app_state.camera.height, app_state.camera.width))
    total_frames = 0

    # Calculate the period of the signal
    period = 1.0 / freq
    half_period = period / 2.0  # Toggle every half period
    load_on = True  # Track whether the load is on or off
    last_toggle_time = start_time  # Track the last time we toggled the load

    while (time.time() - start_time) < integration:
        current_time = time.time() - start_time  # Time since the loop started
        ret, raw_frame = app_state.camera.read()
        info, lut = app_state.camera.info()

        app_state.frame = app_state.camera.convert_to_frame(raw_frame, lut)

        if not ret:
            print("Error: could not read frame from camera")
            sys.exit(1)

        total_frames += 1

        # if(total_frames % 10 == 0):
        # print(f'Frame: {total_frames}, Time: {current_time:.2f}/{integration:.2f}')
        if True:
            app_state.status_text = f"""
Frame: {total_frames},
Time: {current_time:.2f}/{integration:.2f},
Load: {load_on},
Frequency: {freq:.2f}Hz,
Integration Time: {integration:.2f}s
Serial Port: {port}
"""

        # Check if a half period has passed (i.e., time to toggle the load)
        if current_time - (last_toggle_time - start_time) >= half_period:
            # Toggle the load state
            if load_on:
                ser.write(b"0\n")  # Send 0 to turn the load off
                load_on = False
            else:
                ser.write(b"1\n")  # Send 1 to turn the load on
                load_on = True

            # print(f'Load state: {load_on}, Time: {current_time}')  # debugging

            # Update the last toggle time
            last_toggle_time += half_period

        # Calculate the phase angle based on the current time and frequency
        phase = 2 * math.pi * freq * current_time

        # Calculate sine and cosine factors
        sin_weight = 2 * math.sin(phase)
        cos_weight = -2 * math.cos(phase)

        # print(f"time: {current_time}, phase: {phase}"
        #       f", sin: {sin_weight}, cos: {cos_weight} , load: {load_on}")

        # Multiply the frame by sin and cos to get in-phase and quadrature components
        in_phase = raw_frame * sin_weight
        quadrature = raw_frame * cos_weight

        # Accumulate the sums
        in_phase_sum += in_phase
        quadrature_sum += quadrature

        if not app_state.is_capturing:
            break

    ser.write(b"0\n")
    ser.close()

    # After integration time, normalize by the total frames (optional)
    in_phase_sum /= total_frames
    quadrature_sum /= total_frames

    return in_phase_sum, quadrature_sum


def capture_lock_in():
    while app_state.is_capturing:
        in_phase, quad = get_lockin_frame(
            app_state.fequency, app_state.port, app_state.integration
        )
        if in_phase is not None and quad is not None:
            with app_state.lock:
                app_state.in_phase_frame = in_phase
                app_state.quad_frame = quad


def start_capture():
    app_state.is_capturing = True
    thread = threading.Thread(target=capture_lock_in)
    thread.start()
    return thread


def stop_capture(thread):
    app_state.is_capturing = False
    if thread is not None:
        thread.join()


def animate_func(_frame: int) -> None:
    if app_state.lockin and app_state.start_skips > 0:
        app_state.frame = app_state.camera.get_frame()
        app_state.start_skips -= 1
    elif app_state.lockin:
        if not app_state.is_capturing:
            app_state.lock_in_thread = start_capture()
        # in_phase_frame, quad_frame = get_lockin_frame(fequency, port, integration)
    else:
        app_state.frame = app_state.camera.get_frame()

    if not app_state.paused:
        if app_state.diff["enabled"]:
            show_frame = app_state.frame - app_state.diff["frame"]
        else:
            show_frame = app_state.frame

        if app_state.diff["annotation_enabled"]:
            annotation_frame = app_state.frame - app_state.diff["frame"]
        else:
            annotation_frame = app_state.frame

        app_state.im.set_array(show_frame)
        if app_state.lockin:
            app_state.im_in_phase.set_array(app_state.in_phase_frame)
            app_state.im_quadrature.set_array(app_state.quad_frame)

        app_state.annotations.update(
            app_state.temp_annotations, annotation_frame, app_state.draw_temp
        )

        if app_state.exposure["auto"]:
            app_state.update_colormap = utils.autoExposure(
                app_state.update_colormap, app_state.exposure, show_frame
            )

        # TODO: deal with saving the lock in stuff to a file
        log_annotations_to_csv(annotation_frame)

        if app_state.update_colormap:
            app_state.im.set_clim(
                app_state.exposure["T_min"], app_state.exposure["T_max"]
            )
            app_state.fig.canvas.draw_idle()  # force update all, even with blit=True
            app_state.update_colormap = False
            return []

        if app_state.lockin:
            # adjust the color limits for the in-phase and quadrature frames
            app_state.im_in_phase.set_clim(
                np.min(app_state.in_phase_frame), np.max(app_state.in_phase_frame)
            )
            app_state.im_quadrature.set_clim(
                np.min(app_state.quad_frame), np.max(app_state.quad_frame)
            )
            new_status_text = app_state.status_text
            app_state.status_text_obj.set_text(new_status_text)
            return [
                app_state.im,
                app_state.im_in_phase,
                app_state.im_quadrature,
                app_state.status_text_obj,
            ] + app_state.annotations.get()

    return [app_state.im] + app_state.annotations.get()


def print_help():
    print("""keys:
    'h'      - help
    'q'      - quit
    ' '      - pause, resume
    'd'      - set diff
    'x','c'  - enable/disable diff, enable/disable annotation diff
    'f'      - full screen
    'u'      - calibrate
    't'      - draw min, max, center temperature
    'e'      - remove user temperature annotations
    'w'      - save to file date.png
    'r'      - save raw data to file date.npy
    'v'      - record annotations data to file date.csv
    ',', '.' - change color map
    'a', 'z' - auto exposure on/off, auto exposure type
    'k', 'l' - set the thermal range to normal/high (supported by T2S+/T2L)
    left, right, up, down - set exposure limits

mouse:
    left  button - add Region Of Interest (ROI)
    right button - add user temperature annotation
""")


FILE_NAME_FORMAT = "%Y-%m-%d_%H-%M-%S"


# keyboard
def press(event):
    if event.key == "h":
        print_help()
    if event.key == " ":
        app_state.paused ^= True
        print("paused:", app_state.paused)
    if event.key == "d":
        app_state.diff["frame"] = app_state.frame
        app_state.diff["annotation_enabled"] = app_state.diff["enabled"] = True
        print("set   diff")
    if event.key == "x":
        app_state.diff["enabled"] ^= True
        print("enable diff:", app_state.diff["enabled"])
    if event.key == "c":
        app_state.diff["annotation_enabled"] ^= True
        print("enable annotation diff:", app_state.diff["annotation_enabled"])
    if event.key == "t":
        app_state.draw_temp ^= True
        print("draw temp:", app_state.draw_temp)
    if event.key == "e":
        print("removing user annotations: ", len(app_state.temp_annotations["user"]))
        app_state.annotations.remove(app_state.temp_annotations["user"])
    if event.key == "u":
        print("calibrate")
        app_state.camera.calibrate()
    if event.key == "a":
        app_state.exposure["auto"] ^= True
        print(
            "auto exposure:",
            app_state.exposure["auto"],
            ", type:",
            app_state.exposure["auto_type"],
        )
    if event.key == "z":
        types = ["center", "ends"]
        app_state.exposure["auto_type"] = types[
            types.index(app_state.exposure["auto_type"]) - 1
        ]
        print(
            "auto exposure:",
            app_state.exposure["auto"],
            ", type:",
            app_state.exposure["auto_type"],
        )
    if event.key == "w":
        filename = time.strftime(FILE_NAME_FORMAT) + ".png"
        plt.savefig(filename)
        print("saved to:", filename)
    if event.key == "r":
        filename = time.strftime(FILE_NAME_FORMAT) + ".npy"
        np.save(
            filename,
            app_state.camera.frame_raw_u16.reshape(
                app_state.camera.height + 4, app_state.camera.width
            ),
        )
        print("saved to:", filename)
    if event.key == "v":
        if app_state.csv_filename is None:
            csv_filename = time.strftime(FILE_NAME_FORMAT) + ".csv"
            with open(csv_filename, "w", newline="") as f:
                header = ["time"]
                header += [
                    f"{a} {x}"
                    for a in app_state.temp_annotations["std"]
                    for x in ["x", "y", "val"]
                ]  # t, tmin x, tmin y, tmin val, etc
                header += [
                    f"Point{i} {x}"
                    for i, key in enumerate(app_state.temp_annotations["user"].keys())
                    for x in ["x", "y", "val"]
                ]
                csv.writer(f).writerow(header)
            print("Annotation recording started in:", csv_filename)
        else:
            print("Annotation recording  saved  in:", csv_filename)
            csv_filename = None

    if event.key in [",", "."]:
        if event.key == ".":
            app_state.cmaps_idx = (app_state.cmaps_idx + 1) % len(CMAP_NAMES)
        else:
            app_state.cmaps_idx = (app_state.cmaps_idx - 1) % len(CMAP_NAMES)
        print("color map:", CMAP_NAMES[app_state.cmaps_idx])
        app_state.im.set_cmap(CMAP_NAMES[app_state.cmaps_idx])
        app_state.update_colormap = True
    if event.key in ["k", "l"]:
        if event.key == "k":
            app_state.camera.temperature_range_normal()
        else:
            app_state.camera.temperature_range_high()
        # this takes care of calibration as well
        app_state.camera.wait_for_range_application()
        app_state.update_colormap = True
    if event.key in ["left", "right", "up", "down"]:
        app_state.exposure["auto"] = False
        t_cent = int((app_state.exposure["T_min"] + app_state.exposure["T_max"]) / 2)
        d = int(app_state.exposure["T_max"] - t_cent)
        if event.key == "up":
            t_cent += app_state.exposure["T_margin"] / 2
        if event.key == "down":
            t_cent -= app_state.exposure["T_margin"] / 2
        if event.key == "left":
            d -= app_state.exposure["T_margin"] / 2
        if event.key == "right":
            d += app_state.exposure["T_margin"] / 2
        d = max(d, app_state.exposure["T_margin"])
        app_state.exposure["T_min"] = t_cent - d
        app_state.exposure["T_max"] = t_cent + d
        print(
            "auto exposure off, T_min:",
            app_state.exposure["T_min"],
            "T_cent:",
            t_cent,
            "T_max:",
            app_state.exposure["T_max"],
        )
        app_state.update_colormap = True


def onclick(event):
    if event.inaxes == app_state.ax:
        pos = (int(event.xdata), int(event.ydata))
        if event.button == MouseButton.RIGHT:
            print("add user temperature annotation at pos:", pos)
            app_state.temp_annotations["user"][pos] = "white"
        if event.button == MouseButton.LEFT:
            if utils.inRoi(app_state.annotations.roi, pos, app_state.frame.shape):
                app_state.mouse_action = "move_roi"
                app_state.mouse_action_pos = (
                    app_state.annotations.roi[0][0] - pos[0],
                    app_state.annotations.roi[0][1] - pos[1],
                )
            else:
                app_state.mouse_action = "create_roi"
                app_state.mouse_action_pos = pos
                app_state.annotations.set_roi((pos, (0, 0)))


def onmotion(event):
    if event.inaxes == app_state.ax and event.button == MouseButton.LEFT:
        pos = (int(event.xdata), int(event.ydata))
        if app_state.mouse_action == "create_roi":
            w, h = (
                pos[0] - app_state.mouse_action_pos[0],
                pos[1] - app_state.mouse_action_pos[1],
            )
            app_state.roi = (app_state.mouse_action_pos, (w, h))
            app_state.annotations.set_roi(app_state.roi)
        if app_state.mouse_action == "move_roi":
            app_state.roi = (
                (
                    pos[0] + app_state.mouse_action_pos[0],
                    pos[1] + app_state.mouse_action_pos[1],
                ),
                app_state.annotations.roi[1],
            )
            app_state.annotations.set_roi(app_state.roi)


def main() -> None:
    _keep_me_anim = animation.FuncAnimation(
        app_state.fig, animate_func, interval=1000 / app_state.fps, blit=True
    )
    app_state.fig.canvas.mpl_connect("button_press_event", onclick)
    app_state.fig.canvas.mpl_connect("motion_notify_event", onmotion)
    app_state.fig.canvas.mpl_connect("key_press_event", press)

    print_help()
    plt.show()
    stop_capture(app_state.lock_in_thread)
    app_state.camera.release()


if __name__ == "__main__":
    main()
