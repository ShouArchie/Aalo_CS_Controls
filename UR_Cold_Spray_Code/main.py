import time
import sys
import math

# Third-party helpers ---------------------------------------------------------
try:
    import keyboard  # Listen for global hot-keys
except ImportError:
    print("❌  The 'keyboard' package is required. Install it via:  pip install keyboard")
    sys.exit(1)

import urx

# Project modules -------------------------------------------------------------
import robot_functions as rf

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

ROBOT_IP = "192.168.0.101"  # ← change to suit your network
ACC = 0.1                    # linear / angular acceleration
VEL = 0.1                    # linear / angular velocity
STEP_MM = 1.0               # incremental translation per key-press in mm
HOME_DEG = [206.06, -66.96, 104.35, 232.93, 269.26, 118.75] # [204.96, -66.96, 105.48, 231.08, 269.76, 117.43]
HOME_RAD = [math.radians(a) for a in HOME_DEG]
# Temporary Cartesian HOME pose (x, y, z, rx, ry, rz) – update with real values
HOME_POSE = [943.72, 500.8, 219.86, 0.071, 3.126, -0.015]  # TODO: measure and enter actual HOME TCP pose

# Joint-based HOME move (existing behaviour)
def go_home():
    """Move robot to the predefined HOME joint configuration (joint move)."""
    print("Moving to HOME joint configuration …")
    rf.move_to_joint_position(robot, HOME_RAD, acc=ACC, vel=VEL)
    print("✓ Reached HOME joint configuration")


def go_home_l():
    """Move linearly (movel) to the HOME Cartesian pose using low speed."""
    print("Moving linearly to HOME pose …")
    rf.send_movel(robot, HOME_POSE, acc=ACC, vel=VEL)
    rf.wait_until_pose(robot, HOME_POSE)
    print("✓ Reached HOME pose (movel)")


TCP_OFFSET_MM = (-277.81, 0.0, 60.3, 0.0, 0.0, 0.0)
# -----------------------------------------------------------------------------
# Robot connection
# -----------------------------------------------------------------------------

print("Connecting to robot …")
robot = urx.Robot(ROBOT_IP)
print(f"✓ Connected to UR robot at {ROBOT_IP}\n")
rf.set_tcp_offset(robot, *TCP_OFFSET_MM)
# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def move_tcp(dx: float = 0.0, dy: float = 0.0, dz: float = 0.0):
    """Translate TCP in its own coordinate frame by the given millimetres."""
    rf.translate_tcp(robot, dx_mm=dx, dy_mm=dy, dz_mm=dz, acc=ACC, vel=VEL)


def rotate_ry_sequence(angle_deg: float):
    """Rotate around local Y-axis, wait, print joints, rotate back."""
    # First rotation
    rf.rotate_tcp(robot, ry_deg=angle_deg, acc=ACC, vel=VEL)
    time.sleep(1.0)
    # Report joint angles in degrees for readability
    print("joint angles:", [round(math.degrees(j), 3) for j in robot.getj()])
    # Return to original orientation
    rf.rotate_tcp(robot, ry_deg=-angle_deg, acc=ACC, vel=VEL)


def print_joints():
    print("joint angles:", [round(math.degrees(j), 3) for j in robot.getj()])
    time.sleep(1)

# -----------------------------------------------------------------------------
# Key-bindings
# -----------------------------------------------------------------------------

keyboard.add_hotkey('d', lambda: move_tcp(dy=-STEP_MM))     # D → −Y  (−1 mm)
keyboard.add_hotkey('a', lambda: move_tcp(dy=STEP_MM))      # A → +Y  (+1 mm)
keyboard.add_hotkey('w', lambda: move_tcp(dz=-STEP_MM))     # W → −Z  (−1 mm)
keyboard.add_hotkey('s', lambda: move_tcp(dz=STEP_MM))      # S → +Z  (+1 mm)
keyboard.add_hotkey('n', lambda: move_tcp(dx=-STEP_MM))    # ↑ → −X  (−1 mm)
keyboard.add_hotkey('m', lambda: move_tcp(dx=STEP_MM))   # ↓ → +X  (+1 mm)

keyboard.add_hotkey('1', lambda: rotate_ry_sequence(15))  # 1 → −15° Ry sequence
keyboard.add_hotkey('2', lambda: rotate_ry_sequence(10))
keyboard.add_hotkey('3', lambda: print_joints())  # 2 → −10° Ry sequence
keyboard.add_hotkey('l', go_home_l)                       # L → HOME via movel
keyboard.add_hotkey('h', go_home)                          # H → HOME joint pose

# -----------------------------------------------------------------------------
# Clean-up & main loop
# -----------------------------------------------------------------------------

def _cleanup_exit():
    """Safely close the robot connection and exit the program."""
    print("\nExiting – closing robot connection …")
    try:
        robot.close()
    finally:
        sys.exit(0)

# Esc terminates the program
keyboard.add_hotkey('esc', _cleanup_exit)

print("Controls ready (press Esc to quit):")
print("  D →  −1 mm in Y")
print("  A →  +1 mm in Y")
print("  W →  −1 mm in Z")
print("  S →  +1 mm in Z")
print("  ↑ →  −1 mm in X")
print("  ↓ →  +1 mm in X")
print("  1 →  Rotate Ry by −15°, wait 1 s, print joints, rotate back")
print("  2 →  Rotate Ry by −10°, wait 1 s, print joints, rotate back")
print("  L →  Move linearly to HOME TCP pose (placeholder)")
print("  H →  Move to HOME joint position")
print("  Esc → Quit program\n")

# Block forever until Esc triggers _cleanup_exit
keyboard.wait()
