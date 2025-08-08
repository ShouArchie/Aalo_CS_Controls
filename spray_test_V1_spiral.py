"""
Spray Test V1 — Spiral version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
replaces the fixed-radius conical sweeps with a spiral radius

Usage:
    python spray_test_V1_spiral.py

Adjust the PARAMS section for the robot IP, TCP, and spiral parameters.
"""
from __future__ import annotations

import math
import time
from typing import List

import urx

from UR_Cold_Spray_Code import robot_functions as rf

# -----------------------------------------------------------------------------
# PARAMS
# -----------------------------------------------------------------------------
ROBOT_IP = "192.168.10.205"   # ← set your controller IP
TCP_OFFSET_MM = (-278.81, 0.0, 60.3, 0.0, 0.0, 0.0)  # (x, y, z, rx, ry, rz)

# Home + piece joint targets (radians)
# These are the same structure as the previous V1; replace with the measured values.
HOME_DEG = [206.06, -66.96, 104.35, 232.93, 269.26, 118.75]
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

_deg = math.radians
home = [_deg(a) for a in HOME_DEG]
pieces = [[_deg(a) for a in piece] for piece in [
    piece1_deg, piece2_deg, piece3_deg, piece4_deg,
    piece5_deg, piece6_deg, piece7_deg, piece8_deg,
    piece9_deg, piece10_deg, piece11_deg, piece12_deg,
    piece13_deg, piece14_deg, piece15_deg, piece16_deg,
]]

# Default spiral parameters (tune on rig)
TILT_START_DEG = 15.0      # start a bit off-normal to avoid rebound
TILT_END_DEG   = 1       # reduce angle as you approach the center
R_START_MM     = 50.0      # outer radius of coverage
R_END_MM       = 0.0       # hit the center
REVS           = 10.0       # total revolutions from R_START → R_END
STEPS_PER_REV  = 180       # 2° step size (matches your current sampling)
CYCLE_S        = 0.015     # servoj period (≈66 Hz) - used when not using variable timing
LOOKAHEAD_S    = 0.2
GAIN           = 2500
SING_TOL_DEG   = 1.0       # skip window around 90° and 270°

# Variable cycle timing (optional - set both to None to use fixed CYCLE_S)
CYCLE_S_START  = 0.015     # starting cycle time (slower) - outer radius
CYCLE_S_END    = 0.015     # ending cycle time (faster) - inner radius

# Tilt direction control
INVERT_TILT    = False     # True = flip tilt direction (Ry- instead of Ry+)

# Optional: a second interleaved pass with a tiny phase offset
RUN_INTERLEAVED_SECOND_PASS = True
PHASE_OFFSET_DEG = 1.0     # small φ shift to bridge wedge gaps if plume is narrow

# Motion params between pieces
ACC_MOVE = 1.0
VEL_MOVE = 0.8

# Choose which piece to spray in this demo (1–16). Set to None to just use HOME.
PIECE_INDEX: int | None = 1

# -----------------------------------------------------------------------------
# Spiral generator (URScript with servoj)
# -----------------------------------------------------------------------------

def spiral_cold_spray(
    robot: urx.Robot,
    *,
    tilt_start_deg: float,
    tilt_end_deg: float,
    revs: float,
    r_start_mm: float,
    r_end_mm: float,
    steps_per_rev: int,
    cycle_s: float,
    lookahead_s: float,
    gain: int,
    sing_tol_deg: float,
    phase_offset_deg: float = 0.0,
    cycle_s_start: float = None,
    cycle_s_end: float = None,
    invert_tilt: bool = False,
):
    """Generate a radius-scheduled spiral and execute with servoj.

    - Uses current TCP XYZ as spiral center and current orientation as starting reference.
    - Keeps the singularity avoidance by skipping phases near 90°/270°.
    - Creates orientations with linearly varying angle from starting normal direction:
      tool X-axis angle varies linearly from tilt_start → tilt_end degrees.
    - If cycle_s_start and cycle_s_end are provided, interpolates cycle time
      from start to end over the whole spiral. Otherwise uses fixed cycle_s.
    - If invert_tilt is True, negates both tilt angles to flip the tilt direction.
    """
    # Get current TCP pose and orientation as starting reference
    current_pose = rf.get_tcp_pose(robot)
    x0, y0, z0 = current_pose[0], current_pose[1], current_pose[2]
    starting_rx, starting_ry, starting_rz = current_pose[3], current_pose[4], current_pose[5]
    
    # Convert starting orientation to rotation matrix to get starting normal direction
    starting_angle_mag = math.sqrt(starting_rx*starting_rx + starting_ry*starting_ry + starting_rz*starting_rz)
    if starting_angle_mag > 1e-6:
        # Normalized axis
        start_ax = starting_rx / starting_angle_mag
        start_ay = starting_ry / starting_angle_mag  
        start_az = starting_rz / starting_angle_mag
        
        # Rodrigues formula for starting rotation matrix
        cos_theta = math.cos(starting_angle_mag)
        sin_theta = math.sin(starting_angle_mag)
        
        starting_rotation_matrix = [
            [cos_theta + start_ax*start_ax*(1-cos_theta), start_ax*start_ay*(1-cos_theta) - start_az*sin_theta, start_ax*start_az*(1-cos_theta) + start_ay*sin_theta],
            [start_ay*start_ax*(1-cos_theta) + start_az*sin_theta, cos_theta + start_ay*start_ay*(1-cos_theta), start_ay*start_az*(1-cos_theta) - start_ax*sin_theta],
            [start_az*start_ax*(1-cos_theta) - start_ay*sin_theta, start_az*start_ay*(1-cos_theta) + start_ax*sin_theta, cos_theta + start_az*start_az*(1-cos_theta)]
        ]
    else:
        starting_rotation_matrix = [[1,0,0], [0,1,0], [0,0,1]]  # Identity matrix
    
    # Extract starting normal direction (tool X-axis)
    starting_normal = [starting_rotation_matrix[0][0], starting_rotation_matrix[1][0], starting_rotation_matrix[2][0]]

    # Apply tilt inversion if requested
    if invert_tilt:
        tilt_start_deg = -tilt_start_deg
        tilt_end_deg = -tilt_end_deg

    # Precompute counts
    total_steps = int(round(revs * steps_per_rev))
    
    # Determine if we're using variable cycle timing
    use_variable_cycle = cycle_s_start is not None and cycle_s_end is not None

    # Build URScript
    lines: List[str] = ["def spiral_servoj():"]

    for step in range(total_steps + 1):
        frac = step / total_steps if total_steps else 1.0
        # Linear schedules
        tilt = math.radians(tilt_start_deg + (tilt_end_deg - tilt_start_deg) * frac)
        r_mm = r_start_mm + (r_end_mm - r_start_mm) * frac
        r = r_mm / 1000.0
        
        # Calculate cycle time (variable or fixed)
        if use_variable_cycle:
            current_cycle_s = cycle_s_start + (cycle_s_end - cycle_s_start) * frac
        else:
            current_cycle_s = cycle_s

        # Phase with optional offset
        phi_deg = (step / steps_per_rev) * 360.0 + phase_offset_deg
        phi = math.radians(phi_deg)

        # Skip near 90° and 270° (wrap-safe)
        ang = (phi_deg % 360.0)
        if min(abs(((ang - 90) + 180) % 360 - 180),
               abs(((ang - 270) + 180) % 360 - 180)) < sing_tol_deg:
            continue

        # Create orientation with linearly varying angle from starting normal direction
        # Calculate target angle from starting normal (linearly interpolated)
        current_tilt_angle_rad = math.radians(tilt_start_deg + (tilt_end_deg - tilt_start_deg) * frac)
        
        # Debug: Log tilt angle for problematic cases
        if step < 5 or (invert_tilt and step < 20):
            print(f"Step {step}: frac={frac:.3f}, tilt_deg={math.degrees(current_tilt_angle_rad):.2f}")
        
        # Create rotation axis perpendicular to starting normal direction
        # Use spiral phase to create varying rotation axis direction
        rotation_axis = [
            0.0,
            math.cos(phi), 
            math.sin(phi)
        ]
        
        # Normalize rotation axis
        axis_mag = math.sqrt(rotation_axis[0]*rotation_axis[0] + rotation_axis[1]*rotation_axis[1] + rotation_axis[2]*rotation_axis[2])
        if axis_mag > 1e-6:
            rotation_axis = [rotation_axis[0]/axis_mag, rotation_axis[1]/axis_mag, rotation_axis[2]/axis_mag]
        else:
            rotation_axis = [0.0, 1.0, 0.0]  # Default to Y-axis
        
        # Create rotation matrix for tilt around rotation_axis using Rodrigues formula
        cos_tilt = math.cos(current_tilt_angle_rad)
        sin_tilt = math.sin(current_tilt_angle_rad)
        ax, ay, az = rotation_axis[0], rotation_axis[1], rotation_axis[2]
        
        R_tilt = [
            [cos_tilt + ax*ax*(1-cos_tilt), ax*ay*(1-cos_tilt) - az*sin_tilt, ax*az*(1-cos_tilt) + ay*sin_tilt],
            [ay*ax*(1-cos_tilt) + az*sin_tilt, cos_tilt + ay*ay*(1-cos_tilt), ay*az*(1-cos_tilt) - ax*sin_tilt],
            [az*ax*(1-cos_tilt) - ay*sin_tilt, az*ay*(1-cos_tilt) + ax*sin_tilt, cos_tilt + az*az*(1-cos_tilt)]
        ]
        
        # Apply rotation to starting orientation: target = R_tilt * starting_rotation_matrix
        target_rotation_matrix = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0], 
            [0.0, 0.0, 0.0]
        ]
        
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    target_rotation_matrix[i][j] += R_tilt[i][k] * starting_rotation_matrix[k][j]
        
        # Convert target rotation matrix to axis-angle for UR
        rx, ry, rz = rf._mat_to_aa(target_rotation_matrix)

        # Spiral translation in TCP YZ plane around current center
        x = x0
        y = y0 + r * math.cos(phi)
        z = z0 + r * math.sin(phi)

        pose_str = ", ".join(f"{v:.6f}" for v in [x, y, z, rx, ry, rz])
        lines.append(
            f"  servoj(get_inverse_kin(p[{pose_str}]), t={current_cycle_s:.6f}, lookahead_time={lookahead_s}, gain={gain})"
        )
        lines.append("  sync()")

    lines.append("end")
    lines.append("spiral_servoj()")

    rf.send_urscript(robot, "\n".join(lines))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    robot = urx.Robot(ROBOT_IP)
    try:
        rf.set_tcp_offset(robot, *TCP_OFFSET_MM)

        # Move to HOME
        print("Moving to HOME …")
        rf.move_to_joint_position(robot, home, acc=ACC_MOVE, vel=VEL_MOVE, wait=True)
        time.sleep(1.0)

       
        # Pass 1 (outer → inner)
        print("Starting spiral pass 1 …")
        spiral_cold_spray(
            robot,
            tilt_start_deg=TILT_START_DEG,
            tilt_end_deg=TILT_END_DEG,
            revs=REVS,
            r_start_mm=R_START_MM,
            r_end_mm=R_END_MM,
            steps_per_rev=STEPS_PER_REV,
            cycle_s=CYCLE_S,
            lookahead_s=LOOKAHEAD_S,
            gain=GAIN,
            sing_tol_deg=SING_TOL_DEG,
            phase_offset_deg=0.0,
            cycle_s_start=CYCLE_S_START,
            cycle_s_end=CYCLE_S_END,
            invert_tilt=True,
        )
        time.sleep(1.0)
        rf.wait_until_idle(robot)


    finally:
        robot.close()
        print("✓ Robot connection closed")


if __name__ == "__main__":
    main()
