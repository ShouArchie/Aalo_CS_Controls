"""
Path Test
~~~~~~~~~
Moves the UR robot through HOME and all 16 piece joint configurations that
were captured in *spray_test_V1.py*.  Each transition uses low-speed
parameters (acc = 0.1, vel = 0.1) and the script waits for the robot to
settle at every target before proceeding.

Usage:
    python path_test.py

Press the hardware Emergency-Stop or power-cycle the controller at any time
if unexpected motion occurs.
"""
from __future__ import annotations

import math
import time
import urx

import robot_functions as rf
import spray_test_V1 as st

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

ROBOT_IP = "192.168.0.101"  # Update if needed
ACC = 0.1                    # Joint/Cartesian acceleration
VEL = 0.1                    # Joint/Cartesian velocity

# TCP offset identical to main.py – adjust if your setup differs.
TCP_OFFSET_MM = (-272.81, 0.0, 60.3, 0.0, 0.0, 0.0)

# -----------------------------------------------------------------------------
# Main routine
# -----------------------------------------------------------------------------

def main():
    robot = urx.Robot(ROBOT_IP)
    try:
        # Configure TCP
        rf.set_tcp_offset(robot, *TCP_OFFSET_MM)

        # Build ordered list of joint-angle targets (already in radians)
        targets = [st.home] + st.pieces  # type: ignore[attr-defined]
        names = ["HOME"] + [f"piece{i}" for i in range(1, len(st.pieces) + 1)]  # type: ignore[attr-defined]

        for name, joints in zip(names, targets, strict=True):
            rf.translate_tcp(robot, dx_mm=100, dz_mm=-100, acc= 0.1, vel=0.1)
            print(f"\n→ Moving to {name} …")
            deg_list = [round(math.degrees(j), 3) for j in joints]
            print("   Target (deg):", deg_list)
            rf.move_to_joint_position(robot, joints, acc=ACC, vel=VEL, wait=True)
            print("   ✓ Reached", name)
            time.sleep(1.0)  # brief dwell between poses


        print("\n✓ Path test complete – returning to HOME …")
        rf.translate_tcp(robot, dx_mm=300, dz_mm=-300, acc= 0.1, vel=0.1)
        rf.move_to_joint_position(robot, st.home, acc=ACC, vel=VEL, wait=True)

    finally:
        robot.close()
        print("✓ Robot connection closed")


if __name__ == "__main__":
    main() 