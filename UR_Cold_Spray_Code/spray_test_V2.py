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
TCP_OFFSET_10MM = (-272.81, 0.0, 60.3, 0.0, 0.0, 0.0)  # 15mm
TCP_OFFSET_20MM = (-277.81, 0.0, 60.3, 0.0, 0.0, 0.0) # 20mm

LOOKAHEAD_TIME = 0.2  


def _gain_for_cycle(cycle_s: float) -> int:
    return 3000 if cycle_s <= 0.015 else 1000

# -----------------------------------------------------------------------------
# Joint targets (DEGREES) – ***PLACEHOLDERS***
# -----------------------------------------------------------------------------

HOME_DEG = [204.67, -66.96, 105.05, 231.5, 269.66, 116.81] # [201.64, -54.86, 109.85, 214.57, 269.77, 111.69]
# Pot home => 212.3, -60.18, 124.01, 205.85, 269.69, 122.34
# Dummy values; replace with real joint angles for each test piece
# Joint-angle targets captured from terminal – one set per piece
piece1_deg  = [189.956, -72.44,  102.261, 254.329, 273.084, 102.006]
piece2_deg  = [187.366, -73.602, 103.765, 254.066, 272.386,  99.451]
piece3_deg  = [184.817, -74.772, 109.349, 244.754, 271.073,  97.072]
piece4_deg  = [182.02,  -75.851, 110.497, 244.691, 270.545,  94.277]
piece5_deg  = [178.56,  -76.414, 107.765, 252.95,  269.981,  90.815]
piece6_deg  = [176.117, -77.058, 108.429, 252.882, 269.319,  88.427]
piece7_deg  = [173.074, -77.674, 113.06,  243.782, 268.88,   85.344]
piece8_deg  = [169.687, -78.121, 113.552, 243.573, 268.252,  81.95]
piece9_deg  = [167.349, -77.929, 110.049, 251.658, 266.929,  79.812]
piece10_deg = [164.434, -78.052, 110.12,  251.418, 266.147,  76.937]
piece11_deg = [161.383, -77.925, 110.015,  251.078, 265.355,  73.916]
piece12_deg = [158.434, -77.503, 109.633, 250.666, 264.606,  70.994]
piece13_deg = [155.355, -77.298, 112.95,  242.111, 265.762,  67.539]
piece14_deg = [152.541, -76.534, 112.151, 241.863, 265.319,  64.7]
piece15_deg = [149.475, -75.663, 110.834, 241.981, 264.857,  61.589]
piece16_deg = [147.317, -74.837, 109.679, 242.05,  264.545,  59.405]

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
    # 2. 15° tilt, 2 rev, 5.4 s/rev (cycle = 0.0475)
    [dict(tilt=15, rev=2, cycle=0.0475)],
    # 3. 10° tilt, 2 rev, 2.7 s/rev
    [dict(tilt=10, rev=2, cycle=0.015)],
    # 4. 10° tilt, 2 rev, 5.4 s/rev
    [dict(tilt=10, rev=2, cycle=0.0475)],
    # 5. 15° tilt, 4 rev, 2.7 s/rev
    [dict(tilt=15, rev=4, cycle=0.015)],
    # 6. 15° tilt, 4 rev, 5.4 s/rev
    [dict(tilt=15, rev=4, cycle=0.0475)],
    # 7. 10° tilt, 4 rev, 2.7 s/rev
    [dict(tilt=10, rev=4, cycle=0.015)],
    # 8. 10° tilt, 4 rev, 5.4 s/rev
    [dict(tilt=10, rev=4, cycle=0.0475)],
    # 9. 15° → 10°, 2 rev each, 2.7 s/rev
    [dict(tilt=15, rev=2, cycle=0.015), dict(tilt=10, rev=2, cycle=0.015)],
    # 10. 15° → 10°, 2 rev each, 5.4 s/rev
    [dict(tilt=15, rev=2, cycle=0.0475), dict(tilt=10, rev=2, cycle=0.0475)],
    # 11. 15° → 10°, 4 rev each, 2.7 s/rev
    [dict(tilt=15, rev=4, cycle=0.015), dict(tilt=10, rev=4, cycle=0.015)],
    # 12. 15° → 10°, 4 rev each, 5.4 s/rev
    [dict(tilt=15, rev=4, cycle=0.0475), dict(tilt=10, rev=4, cycle=0.0475)],
    # 13. 10° → 15°, 2 rev each, 2.7 s/rev
    [dict(tilt=10, rev=2, cycle=0.015), dict(tilt=15, rev=2, cycle=0.015)],
    # 14. 10° → 15°, 2 rev each, 5.4 s/rev
    [dict(tilt=10, rev=2, cycle=0.0475), dict(tilt=15, rev=2, cycle=0.0475)],
    # 15. 10° → 15°, 4 rev each, 2.7 s/rev
    [dict(tilt=10, rev=4, cycle=0.015), dict(tilt=15, rev=4, cycle=0.015)],
    # 16. 10° → 15°, 4 rev each, 5.4 s/rev
    [dict(tilt=10, rev=4, cycle=0.0475), dict(tilt=15, rev=4, cycle=0.0475)],
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
        rf.move_to_joint_position(robot, home, acc=1, vel=0.8)
        time.sleep(5)

        for idx, (piece_joints, sample) in enumerate(zip(pieces, samples), start=1):
            print(f"\n=== PIECE {idx} ===")
            rf.move_to_joint_position(robot, piece_joints, acc=1, vel=0.5)
            for sweep in sample:
                print(
                    f"   ↳ Sweep: tilt={sweep['tilt']}°, rev={sweep['rev']}, cycle={sweep['cycle']}"  # type: ignore[index]
                )
                _run_sweep(robot, **sweep)  # type: ignore[arg-type]
            
            rf.translate_tcp(robot, dx_mm=75, dz_mm=-75, acc=1.5, vel=1) # UNSURE YET. Depends on whether or not we stack pieces

        # Post-spray translation
        print("\nTranslating +100 mm in +X and +100 mm in +Y …")
        rf.translate_tcp(robot, dx_mm=100, dz_mm=-100, acc=0.5, vel=0.5)
        time.sleep(5.0)
        print("complete")

    finally:
        robot.close()
        print("✓ Robot connection closed")


if __name__ == "__main__":
    main() 