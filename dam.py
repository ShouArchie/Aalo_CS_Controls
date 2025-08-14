"""
Dam n Sector Wall w Azimuth Fill
Steps
(1) building a pressure dam around the hole at an oblique angle
(2) erecting a short sector wall on the upwind side
(3) filling the center with azimuth angle - hits that never dwell
 
finish with a microorbit to densify
  - get_tcp_pose, _mat_to_aa, send_urscript, wait_until_idle,
    move_to_joint_position, set_tcp_offset
 
Run:
    python dampath.py
"""
from __future__ import annotations
 
import math
import time
from typing import List, Tuple
 
import urx
from UR_Cold_Spray_Code import robot_functions as rf
 
# ---------------------- CONFIG ----------------------
ROBOT_IP = "192.168.10.205"
TCP_OFFSET_MM = (-278.81, 0.0, 60.3, 0.0, 0.0, 0.0)
 
# Home joints (replace if needed)
HOME_DEG = [206.06, -66.96, 104.35, 232.93, 269.26, 118.75]
_deg = math.radians
home = [_deg(a) for a in HOME_DEG]
 
# Controller timing
CYCLE_S = 0.015
LOOKAHEAD_S = 0.2
GAIN = 2500
SING_TOL_DEG = 1.0
 
# Process params (based on your data: VRC EXP-0044, ~100 mm/s, standoff 20 mm)
# Jet direction estimate (degrees, 0 at +X, increasing CCW). Set if you know
# where outflow is biasing the plume; used to place the sector wall upwind.
JET_THETA_DEG = 0.0       # if unknown, leave 0 — wall is still helpful
 
# Stage A: Oblique dam rings (alternate CW/CCW)
DAM_RADII_MM = [3.2, 2.4, 1.8, 1.3]
DAM_TILT_DEG = (10.0, 20.0)   # start oblique → steeper
DAM_REVS = 1.0
 
# Stage B: Sector wall (short arc on upwind side)
SECTOR_ARC_DEG = 70.0         # arc width of wall
SECTOR_RADII_MM = [2.8, 2.2, 1.6]
SECTOR_PASSES = 2             # repeat to gain height
SECTOR_TILT_DEG = (10.0, 20.0)
 
# Stage C: Random-azimuth fill (inward biased)
FILL_R_START_MM = 1.8
FILL_R_END_MM = 0.0
FILL_TURNS = 7
FILL_STEPS_PER_TURN = 220
FILL_TILT_DEG = (10.0, 20.0)
FILL_JITTER_DEG = 5.0        # random azimuth jump range
 
# Stage D: Radial spokes to stitch
SPOKES_RADIUS_MM = 2.0
SPOKES_COUNT = 7
SPOKES_PASSES = 2
SPOKES_TILT_DEG = 10.0
SPOKES_STEPS_PER_SPOKE = 95
 
# Stage E: Micro-finish
FINISH_RADIUS_MM = 0.6
FINISH_REVS = 2.0
FINISH_TILT_DEG = 1.0
 
# Motion between pieces
ACC_MOVE = 1.0
VEL_MOVE = 0.8
 
# ---------------------- Helpers ----------------------
 
def _skip_sing(phi_deg: float, tol_deg: float = SING_TOL_DEG) -> bool:
    ang = phi_deg % 360.0
    return min(abs(((ang - 90) + 180) % 360 - 180), abs(((ang - 270) + 180) % 360 - 180)) < tol_deg
 
 
def _frame_axis_angle(phi_rad: float, tilt_rad: float) -> Tuple[float, float, float]:
    """Same orientation math as your conical/servoj helper."""
    axis = (-1.0, 0.0, 0.0)
    u = (0.0, 0.0, 1.0)
    v = (0.0, 1.0, 0.0)
    cp, sp = math.cos(phi_rad), math.sin(phi_rad)
    Xx = math.cos(tilt_rad) * axis[0] + math.sin(tilt_rad) * (cp * u[0] + sp * v[0])
    Xy = math.cos(tilt_rad) * axis[1] + math.sin(tilt_rad) * (cp * u[1] + sp * v[1])
    Xz = math.cos(tilt_rad) * axis[2] + math.sin(tilt_rad) * (cp * u[2] + sp * v[2])
    mag = math.sqrt(Xx*Xx + Xy*Xy + Xz*Xz) or 1.0
    Xx, Xy, Xz = Xx/mag, Xy/mag, Xz/mag
    Zdown = (0.0, 0.0, -1.0)
    Yx = Zdown[1]*Xz - Zdown[2]*Xy
    Yy = Zdown[2]*Xx - Zdown[0]*Xz
    Yz = Zdown[0]*Xy - Zdown[1]*Xx
    magy = math.sqrt(Yx*Yx + Yy*Yy + Yz*Yz) or 1.0
    Yx, Yy, Yz = Yx/magy, Yy/magy, Yz/magy
    Zx = Xy*Yz - Xz*Yy
    Zy = Xz*Yx - Xx*Yz
    Zz = Xx*Yy - Xy*Yx
    rx, ry, rz = rf._mat_to_aa([[Xx, Yx, Zx],[Xy, Yy, Zy],[Xz, Yz, Zz]])
    return rx, ry, rz
 
 
def _servoj_pose(robot: urx.Robot, x: float, y: float, z: float, rx: float, ry: float, rz: float, lines: List[str]):
    pose = ", ".join(f"{v:.6f}" for v in [x, y, z, rx, ry, rz])
    lines.append(f"  servoj(get_inverse_kin(p[{pose}]), t={CYCLE_S}, lookahead_time={LOOKAHEAD_S}, gain={GAIN})")
    lines.append("  sync()")
 
# ---------------------- Stages ----------------------
 
def dam_rings(robot: urx.Robot):
    x0, y0, z0, *_ = rf.get_tcp_pose(robot)
    lines: List[str] = ["def dam_rings():"]
    total = len(DAM_RADII_MM)
    for i, r_mm in enumerate(DAM_RADII_MM):
        revs = DAM_REVS
        steps = int(round(180 * revs))
        tilt = math.radians(DAM_TILT_DEG[0] + (DAM_TILT_DEG[1] - DAM_TILT_DEG[0]) * (i/(max(1,total-1))))
        for k in range(steps + 1):
            phi_deg = (k / 180.0) * 360.0
            if i % 2 == 1:
                phi_deg = -phi_deg  # alternate CW/CCW
            if _skip_sing(phi_deg):
                continue
            phi = math.radians(phi_deg)
            rx, ry, rz = _frame_axis_angle(phi, tilt)
            r = r_mm / 1000.0
            x = x0 + r * math.cos(phi)
            y = y0 + r * math.sin(phi)
            _servoj_pose(robot, x, y, z0, rx, ry, rz, lines)
    lines.append("end"); lines.append("dam_rings()")
    rf.send_urscript(robot, "\n".join(lines))
 
 
def sector_wall(robot: urx.Robot):
    """Short arc on upwind side to shield the jet."""
    x0, y0, z0, *_ = rf.get_tcp_pose(robot)
    start_deg = JET_THETA_DEG - SECTOR_ARC_DEG/2.0
    end_deg = JET_THETA_DEG + SECTOR_ARC_DEG/2.0
    lines: List[str] = ["def sector_wall():"]
    for p in range(SECTOR_PASSES):
        for r_i, r_mm in enumerate(SECTOR_RADII_MM):
            tilt = math.radians(SECTOR_TILT_DEG[0] + (SECTOR_TILT_DEG[1] - SECTOR_TILT_DEG[0]) * (p/(max(1,SECTOR_PASSES-1))))
            steps = 140
            for k in range(steps + 1):
                frac = k/steps
                phi_deg = start_deg + (end_deg - start_deg) * frac
                if _skip_sing(phi_deg):
                    continue
                phi = math.radians(phi_deg)
                rx, ry, rz = _frame_axis_angle(phi, tilt)
                r = r_mm/1000.0
                x = x0 + r * math.cos(phi)
                y = y0 + r * math.sin(phi)
                _servoj_pose(robot, x, y, z0, rx, ry, rz, lines)
    lines.append("end"); lines.append("sector_wall()")
    rf.send_urscript(robot, "\n".join(lines))
 
 
def random_fill(robot: urx.Robot):
    """Inward-biased randomized azimuth strikes to bridge the hole."""
    import random
    x0, y0, z0, *_ = rf.get_tcp_pose(robot)
    total_steps = int(round(FILL_TURNS * FILL_STEPS_PER_TURN))
    lines: List[str] = ["def random_fill():"]
    rng = random.Random(42)  # deterministic
    for i in range(total_steps + 1):
        prog = i/total_steps
        r_mm = FILL_R_START_MM + (FILL_R_END_MM - FILL_R_START_MM) * prog
        base_phi_deg = prog * (FILL_TURNS * 360.0)
        jitter = rng.uniform(-FILL_JITTER_DEG, FILL_JITTER_DEG)
        phi_deg = base_phi_deg + jitter
        if _skip_sing(phi_deg):
            continue
        phi = math.radians(phi_deg)
        tilt = math.radians(FILL_TILT_DEG[0] + (FILL_TILT_DEG[1] - FILL_TILT_DEG[0]) * prog)
        rx, ry, rz = _frame_axis_angle(phi, tilt)
        r = (r_mm/1000.0)
        x = x0 + r * math.cos(phi)
        y = y0 + r * math.sin(phi)
        _servoj_pose(robot, x, y, z0, rx, ry, rz, lines)
    lines.append("end"); lines.append("random_fill()")
    rf.send_urscript(robot, "\n".join(lines))
 
 
def spokes_stitch(robot: urx.Robot):
    x0, y0, z0, *_ = rf.get_tcp_pose(robot)
    lines: List[str] = ["def spokes_stitch():"]
    tilt = math.radians(SPOKES_TILT_DEG)
    for p in range(SPOKES_PASSES):
        for s in range(SPOKES_COUNT):
            base_deg = (360.0 / SPOKES_COUNT) * s + (p % 2) * (180.0 / SPOKES_COUNT)
            steps = SPOKES_STEPS_PER_SPOKE
            for k in range(steps + 1):
                frac = k / steps
                r = (SPOKES_RADIUS_MM * (1.0 - frac))/1000.0
                phi = math.radians(base_deg)
                if _skip_sing(base_deg):
                    continue
                rx, ry, rz = _frame_axis_angle(phi, tilt)
                x = x0 + r * math.cos(phi)
                y = y0 + r * math.sin(phi)
                _servoj_pose(robot, x, y, z0, rx, ry, rz, lines)
    lines.append("end"); lines.append("spokes_stitch()")
    rf.send_urscript(robot, "\n".join(lines))
 
 
def micro_finish(robot: urx.Robot):
    x0, y0, z0, *_ = rf.get_tcp_pose(robot)
    lines: List[str] = ["def micro_finish():"]
    tilt = math.radians(FINISH_TILT_DEG)
    steps = int(round(180 * FINISH_REVS))
    for k in range(steps + 1):
        phi_deg = (k/180.0) * 360.0
        if _skip_sing(phi_deg):
            continue
        phi = math.radians(phi_deg)
        rx, ry, rz = _frame_axis_angle(phi, tilt)
        r = FINISH_RADIUS_MM/1000.0
        x = x0 + r * math.cos(phi)
        y = y0 + r * math.sin(phi)
        _servoj_pose(robot, x, y, z0, rx, ry, rz, lines)
    lines.append("end"); lines.append("micro_finish()")
    rf.send_urscript(robot, "\n".join(lines))
 
# ---------------------- Main ----------------------
 
def main():
    robot = urx.Robot(ROBOT_IP)
    try:
        rf.set_tcp_offset(robot, *TCP_OFFSET_MM)
        rf.move_to_joint_position(robot, home, acc=ACC_MOVE, vel=VEL_MOVE, wait=True)
        time.sleep(0.5)
 
        print("A) Dam rings …")
        dam_rings(robot); rf.wait_until_idle(robot)
        time.sleep(0.2)
 
        print("B) Sector wall (upwind) …")
        sector_wall(robot); rf.wait_until_idle(robot)
        time.sleep(0.2)
 
        print("C) Random-azimuth fill …")
        random_fill(robot); rf.wait_until_idle(robot)
        time.sleep(0.2)
 
        print("D) Spokes stitch …")
        spokes_stitch(robot); rf.wait_until_idle(robot)
        time.sleep(0.2)
 
        print("E) Micro-finish …")
        micro_finish(robot); rf.wait_until_idle(robot)
 
        print("✓ complete — backing off …")
        rf.translate_tcp(robot, dx_mm=100, dz_mm=-100, acc=0.8, vel=0.6)
        time.sleep(0.5)
        rf.move_to_joint_position(robot, home, acc=ACC_MOVE, vel=VEL_MOVE, wait=True)
 
    finally:
        robot.close(); print("✓ Robot connection closed")
 
 
if __name__ == "__main__":
    main()