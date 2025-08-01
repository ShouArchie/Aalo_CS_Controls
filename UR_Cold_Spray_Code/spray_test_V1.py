"""
Spray Test V1
~~~~~~~~~~~~~
Executes 16 conical spray patterns ("samples") at 16 different robot poses.

Workflow:
1. Connect to the UR robot at ROBOT_IP.
2. Go to HOME joint configuration.
3. For each piece (1‒16):
     a. Move to its joint target.
     b. Run the assigned spray pattern(s) using rf.conical_motion_servoj_script().
     c. Wait until the robot is idle.
4. After the last piece: translate the TCP +100 mm in +X and +100 mm in +Y,
   pause 3 s, then return to HOME and disconnect.

Joint targets for piece1 … piece16 are TEMPORARY placeholders – replace with
measured values before production use.
"""

from __future__ import annotations

import math
import time
from typing import List, Sequence

import urx

import robot_functions as rf

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

ROBOT_IP = "192.168.0.101"  # ← update if your robot IP differs

# TCP offset
TCP_OFFSET_MM = (-278.81, 0.0, 60.3, 0.0, 0.0, 0.0)  # (x, y, z, rx, ry, rz)

LOOKAHEAD_TIME = 0.2  


def _gain_for_cycle(cycle_s: float) -> int:
    return 3000 if cycle_s <= 0.015 else 1000

# -----------------------------------------------------------------------------
# Joint targets (DEGREES) – ***PLACEHOLDERS***
# -----------------------------------------------------------------------------

HOME_DEG = [206.06, -66.96, 104.35, 232.93, 269.26, 118.75] # [201.64, -54.86, 109.85, 214.57, 269.77, 111.69]
# Pot home => 212.3, -60.18, 124.01, 205.85, 269.69, 122.34
# Dummy values; replace with real joint angles for each test piece
# Joint-angle targets captured from terminal – one set per piece
piece1_deg  = [191.483, -71.466, 112.006, 229.518, 269.213, 104.186]
piece2_deg  = [188.467, -72.609, 114.07,  228.294, 269.132, 101.131]
piece3_deg  = [185.556, -73.648, 115.875, 227.231, 269.035,  98.184]
piece4_deg  = [182.636, -74.678, 117.403, 226.474, 268.968,  95.223]
piece5_deg  = [179.035, -75.345, 118.753, 225.450, 268.920,  91.584]
piece6_deg  = [176.250, -75.901, 119.605, 224.915, 268.894,  88.767]
piece7_deg  = [173.201, -76.371, 120.448, 224.284, 268.880,  85.690]
piece8_deg  = [169.623, -76.604, 121.083, 223.531, 268.873,  82.069]
piece9_deg  = [166.799, -76.602, 121.528, 222.797, 268.886,  79.189]
piece10_deg = [163.561, -76.720, 121.717, 222.449, 268.917,  75.891]
piece11_deg = [160.268, -76.461, 121.726, 221.833, 268.966,  72.521]
piece12_deg = [157.122, -76.054, 121.358, 221.414, 269.031,  69.284]
piece13_deg = [154.355, -75.503, 120.824, 221.073, 269.125,  66.444]
piece14_deg = [151.247, -74.768, 120.221, 220.547, 269.250,  63.253]
piece15_deg = [148.207, -73.792, 119.051, 220.301, 269.429,  60.116]
piece16_deg = [145.823, -73.034, 118.053, 220.138, 269.585,  57.612]

_rad = math.radians

home = [_rad(a) for a in HOME_DEG]
piece1 = [_rad(a) for a in piece1_deg]
piece2 = [_rad(a) for a in piece2_deg]
piece3 = [_rad(a) for a in piece3_deg]
piece4 = [_rad(a) for a in piece4_deg]
piece5 = [_rad(a) for a in piece5_deg]
piece6 = [_rad(a) for a in piece6_deg]
piece7 = [_rad(a) for a in piece7_deg]
piece8 = [_rad(a) for a in piece8_deg]
piece9 = [_rad(a) for a in piece9_deg]
piece10 = [_rad(a) for a in piece10_deg]
piece11 = [_rad(a) for a in piece11_deg]
piece12 = [_rad(a) for a in piece12_deg]
piece13 = [_rad(a) for a in piece13_deg]
piece14 = [_rad(a) for a in piece14_deg]
piece15 = [_rad(a) for a in piece15_deg]
piece16 = [_rad(a) for a in piece16_deg]

pieces = [
    piece1,
    piece2,
    piece3,
    piece4,
    piece5,
    piece6,
    piece7,
    piece8,
    piece9,
    piece10,
    piece11,
    piece12,
    piece13,
    piece14,
    piece15,
    piece16,
]

# -----------------------------------------------------------------------------
# Sample definitions – one list item per piece
# Each inner list can contain 1-or-2 sweeps run in succession.
# -----------------------------------------------------------------------------

samples: List[List[dict[str, float]]] = [
    # 1. 15° tilt, 2 rev, 2.7 s/rev (cycle = 0.015)
    [dict(tilt=15, rev=2, cycle=0.015)],
    # 2. 15° tilt, 2 rev, 5.4 s/rev (cycle = 0.03)
    [dict(tilt=15, rev=2, cycle=0.03)],
    # 3. 10° tilt, 2 rev, 2.7 s/rev
    [dict(tilt=10, rev=2, cycle=0.015)],
    # 4. 10° tilt, 2 rev, 5.4 s/rev
    [dict(tilt=10, rev=2, cycle=0.03)],
    # 5. 15° tilt, 4 rev, 2.7 s/rev
    [dict(tilt=15, rev=3, cycle=0.015)],
    # 6. 15° tilt, 4 rev, 5.4 s/rev
    [dict(tilt=15, rev=3, cycle=0.03)],
    # 7. 10° tilt, 4 rev, 2.7 s/rev
    [dict(tilt=10, rev=3, cycle=0.015)],
    # 8. 10° tilt, 4 rev, 5.4 s/rev
    [dict(tilt=10, rev=3, cycle=0.03)],
    # 9. 15° → 10°, 2 rev each, 2.7 s/rev
    [dict(tilt=15, rev=2, cycle=0.015), dict(tilt=10, rev=2, cycle=0.015)],
    # 10. 15° → 10°, 2 rev each, 5.4 s/rev
    [dict(tilt=15, rev=2, cycle=0.03), dict(tilt=10, rev=2, cycle=0.03)],
    # 11. 15° → 10°, 4 rev each, 2.7 s/rev
    [dict(tilt=15, rev=3, cycle=0.015), dict(tilt=10, rev=3, cycle=0.015)],
    # 12. 15° → 10°, 4 rev each, 5.4 s/rev
    [dict(tilt=15, rev=3, cycle=0.03), dict(tilt=10, rev=3, cycle=0.03)],
    # 13. 10° → 15°, 2 rev each, 2.7 s/rev
    [dict(tilt=10, rev=2, cycle=0.015), dict(tilt=15, rev=2, cycle=0.015)],
    # 14. 10° → 15°, 2 rev each, 5.4 s/rev
    [dict(tilt=10, rev=2, cycle=0.03), dict(tilt=15, rev=2, cycle=0.03)],
    # 15. 10° → 15°, 4 rev each, 2.7 s/rev
    [dict(tilt=10, rev=3, cycle=0.015), dict(tilt=15, rev=3, cycle=0.015)],
    # 16. 10° → 15°, 4 rev each, 5.4 s/rev
    [dict(tilt=10, rev=3, cycle=0.03), dict(tilt=15, rev=3, cycle=0.03)],
]

assert len(samples) == 16, "Must have exactly 16 samples"

# -----------------------------------------------------------------------------
# Helper to execute one conical sweep
# -----------------------------------------------------------------------------

def _run_sweep(robot: urx.Robot, *, tilt: float, rev: float, cycle: float):
    """Run one conical sweep and wait for the robot to go idle."""
    steps = int(180 * rev)  # always 180 steps per revolution
    rf.conical_motion_servoj_script(
        robot,
        tilt_deg=tilt,
        revolutions=rev,
        steps=steps,
        cycle_s=cycle,
        lookahead_time=LOOKAHEAD_TIME,
        gain=2500,
        sing_tol_deg=1,
    )
    time.sleep(1.5)
    rf.wait_until_idle(robot)

# -----------------------------------------------------------------------------
# Main routine
# -----------------------------------------------------------------------------

def main():
    robot = urx.Robot(ROBOT_IP)
    try:
        # TCP offset
        rf.set_tcp_offset(robot, *TCP_OFFSET_MM)

        print("Moving to HOME …")
        rf.move_to_joint_position(robot, home, acc=1, vel=0.5)
        time.sleep(5)
        rf.translate_tcp(robot, dx_mm=75, dz_mm=-75, acc=1.5, vel=1)

        for idx, (piece_joints, sample) in enumerate(zip(pieces, samples), start=1):
            print(f"\n=== PIECE {idx} ===")
            rf.move_to_joint_position(robot, piece_joints, acc=1.5, vel=1)
            for sweep in sample:
                print(
                    f"   ↳ Sweep: tilt={sweep['tilt']}°, rev={sweep['rev']}, cycle={sweep['cycle']}"  # type: ignore[index]
                )
                _run_sweep(robot, **sweep)  # type: ignore[arg-type]
            
            rf.translate_tcp(robot, dx_mm=100, dz_mm=-50, acc=1.8, vel=1.5) # UNSURE YET. Depends on whether or not we stack pieces

        # Post-spray translation
        print("\nTranslating +100 mm in +X and +100 mm in +Y …")
        rf.translate_tcp(robot, dx_mm=100, dz_mm=-100, acc=1.5, vel=0.5)
        time.sleep(5.0)
        print("complete")

    finally:
        robot.close()
        print("✓ Robot connection closed")


if __name__ == "__main__":
    main() 