from __future__ import annotations

import math
import time
from typing import List, Sequence

import urx
from urx.urrobot import RobotException

# Constants and Configuration
JOINT_EPS_DEG = 0.05           # joint-angle tolerance in °
POS_EPS_MM = 0.051               # linear tolerance in mm
ORI_EPS_DEG = 0.1              # orientation tolerance in °

# Converted constants
JOINT_EPS = math.radians(JOINT_EPS_DEG)
POS_EPS = POS_EPS_MM / 1000.0
ORI_EPS = math.radians(ORI_EPS_DEG)
POLL = 0.005                    
TIMEOUT = 180                 

# -----------------------------------------------------------------------------
# Robot Connection and Basic Operations
# -----------------------------------------------------------------------------

def connect_robot(ip: str) -> urx.Robot:
    """Connect to UR robot at specified IP address."""
    robot = urx.Robot(ip)
    print(f"✓ Connected to UR10 at {ip}")
    return robot

def disconnect_robot(robot: urx.Robot):
    """Safely disconnect from robot."""
    try:
        stop_linear(robot)
        robot.close()
        print("✓ Robot connection closed")
    except Exception as e:
        print(f"⚠️ Error during disconnect: {e}")

# -----------------------------------------------------------------------------
# Motion Control and Waiting Functions
# -----------------------------------------------------------------------------

def wait_until_joints(robot: urx.Robot, target: Sequence[float]) -> None:
    """Wait until robot reaches target joint configuration."""
    start = time.time()
    while True:
        cur = robot.getj()
        if max(abs(c - t) for c, t in zip(cur, target)) < JOINT_EPS:
            return
        if time.time() - start > TIMEOUT:
            print("⚠️  joint wait timeout; continuing")
            return
        time.sleep(POLL)

def get_tcp_pose(robot: urx.Robot) -> List[float]:
    """Get current TCP pose [x, y, z, rx, ry, rz]."""
    pose = robot.getl()
    if pose is None or len(pose) != 6:
        raise RuntimeError("Invalid TCP pose from robot")
    return list(map(float, pose))

def get_joint_angles(robot: urx.Robot) -> List[float]:
    """Get current joint angles [j1, j2, j3, j4, j5, j6]."""
    angles = robot.getj()
    if angles is None or len(angles) != 6:
        raise RuntimeError("Invalid joint angles from robot")
    return list(map(float, angles))


def wait_until_pose(robot: urx.Robot, target: Sequence[float]) -> None:
    """Wait until robot reaches target TCP pose."""
    start = time.time()
    def ang_err(a: float, b: float) -> float:
        diff = abs(a - b) % (2 * math.pi)
        return diff if diff <= math.pi else (2 * math.pi - diff)

    while True:
        cur = get_tcp_pose(robot)
        pos_err = max(abs(c - t) for c, t in zip(cur[:3], target[:3]))
        ori_err = max(ang_err(c, t) for c, t in zip(cur[3:], target[3:]))
        if pos_err < POS_EPS and ori_err < ORI_EPS:
            return
        if time.time() - start > TIMEOUT:
            print("⚠️  pose wait timeout; continuing")
            return
        time.sleep(POLL)

def send_movel(
    robot: urx.Robot,
    pose: Sequence[float],
    acc: float = 1.2,
    vel: float = 0.5,
    blend_mm: float = 0.0,
):
    """Send movel command with optional blend radius (mm)."""
    pose_str = ", ".join(f"{v:.6f}" for v in pose)
    r_part = f", r={blend_mm/1000.0:.4f}" if blend_mm > 0 else ""
    robot.send_program(f"movel(p[{pose_str}], a={acc}, v={vel}{r_part})")


# New helper: joint-interpolated move to pose (lets robot choose minimal joint path)

def send_movej_pose(
    robot: urx.Robot,
    pose: Sequence[float],
    acc: float = 1.2,
    vel: float = 0.5,
    blend_mm: float = 0.0,
):
    """Send movej command targeting a Cartesian pose (UR will IK to joints) with optional blend radius."""
    pose_str = ", ".join(f"{v:.6f}" for v in pose)
    r_part = f", r={blend_mm/1000.0:.4f}" if blend_mm > 0 else ""
    robot.send_program(f"movej(p[{pose_str}], a={acc}, v={vel}{r_part})")

def stop_linear(robot: urx.Robot, acc: float = 1.2):
    """Stop linear motion."""
    try:
        robot.send_program(f"stopl(a={acc})")
    except Exception:
        pass  # ignore if already stopped

def move_to_joint_position(robot: urx.Robot, joints: Sequence[float], acc: float = 1.2, vel: float = 0.5, wait: bool = True):
    """Move robot to specified joint configuration."""
    print("Moving to target joint position …")
    try:
        robot.movej(joints, acc=acc, vel=vel, wait=False)
    except RobotException as e:
        if "Robot stopped" not in str(e):
            raise
    if wait:
        wait_until_joints(robot, joints)

def send_urscript(robot: urx.Robot, script: str):
    """Send raw URScript to robot."""
    print("▶ Sending URScript program …")
    robot.send_program(script)
    print("✓ Program sent")

# -----------------------------------------------------------------------------
# TCP Configuration
# -----------------------------------------------------------------------------

def set_tcp_offset(
    robot: urx.Robot,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    z_mm: float = 0.0,
    rx_deg: float = 0.0,
    ry_deg: float = 0.0,
    rz_deg: float = 0.0,
):
    """Set TCP offset in millimeters and degrees."""
    x = x_mm / 1000.0
    y = y_mm / 1000.0
    z = z_mm / 1000.0
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)

    robot.set_tcp((x, y, z, rx, ry, rz))
    time.sleep(0.05)

    print(
        "✓ TCP offset set to "
        f"(dx={x_mm:.1f} mm, dy={y_mm:.1f} mm, dz={z_mm:.1f} mm, "
        f"rx={rx_deg:.1f}°, ry={ry_deg:.1f}°, rz={rz_deg:.1f}°)"
    )

# -----------------------------------------------------------------------------
# Orientation Math Helpers
# -----------------------------------------------------------------------------

def _aa_to_mat(rx: float, ry: float, rz: float):
    """Convert axis-angle vector to 3×3 rotation matrix."""
    theta = math.sqrt(rx * rx + ry * ry + rz * rz)
    if theta < 1e-12:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    kx, ky, kz = rx / theta, ry / theta, rz / theta
    c = math.cos(theta)
    s = math.sin(theta)
    v = 1 - c
    return [
        [kx * kx * v + c, kx * ky * v - kz * s, kx * kz * v + ky * s],
        [ky * kx * v + kz * s, ky * ky * v + c, ky * kz * v - kx * s],
        [kz * kx * v - ky * s, kz * ky * v + kx * s, kz * kz * v + c],
    ]

def _mat_mul(a, b):
    """Matrix multiplication for 3×3 matrices."""
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]

def _mat_to_aa(R):
    """Convert 3×3 rotation matrix to axis-angle vector."""
    trace = R[0][0] + R[1][1] + R[2][2]
    cos_theta = max(min((trace - 1.0) / 2.0, 1.0), -1.0)
    theta = math.acos(cos_theta)
    if theta < 1e-12:
        return (0.0, 0.0, 0.0)
    sin_theta = math.sin(theta)
    rx = (R[2][1] - R[1][2]) / (2.0 * sin_theta) * theta
    ry = (R[0][2] - R[2][0]) / (2.0 * sin_theta) * theta
    rz = (R[1][0] - R[0][1]) / (2.0 * sin_theta) * theta
    return (rx, ry, rz)

def _rot_y(angle_rad: float):
    """Rotation matrix about Y axis by angle_rad (right-hand rule)."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]

def _rot_z(angle_rad: float):
    """Rotation matrix about Z axis by angle_rad (right-hand rule)."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]

# Add new rotation helper about X axis

def _rot_x(angle_rad: float):
    """Rotation matrix about X axis by angle_rad (right-hand rule)."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]

# -----------------------------------------------------------------------------
# Advanced TCP Motion Functions
# -----------------------------------------------------------------------------

def rotate_tcp_y(robot: urx.Robot, degrees: float, acc: float = 1.2, vel: float = 0.5):
    """Rotate the tool around its own Y (green) axis by degrees."""
    pose = get_tcp_pose(robot)
    x, y, z, rx, ry, rz = pose

    # Current orientation → matrix
    R = _aa_to_mat(rx, ry, rz)

    # Incremental rotation about local Y axis
    dR = _rot_y(math.radians(degrees))

    # Compose: R_new = R * dR (apply in tool frame)
    R_new = _mat_mul(R, dR)

    # Back to axis-angle
    rx_n, ry_n, rz_n = _mat_to_aa(R_new)

    # Send motion with unchanged translation and new orientation
    new_pose = [x, y, z, rx_n, ry_n, rz_n]
    send_movel(robot, new_pose, acc, vel)
    wait_until_pose(robot, new_pose)

def rotate_tcp_z(robot: urx.Robot, degrees: float, acc: float = 1.2, vel: float = 0.5):
    """Rotate the tool around its own Z (blue) axis by degrees."""
    pose = get_tcp_pose(robot)
    x, y, z, rx, ry, rz = pose

    # Current orientation → matrix
    R = _aa_to_mat(rx, ry, rz)

    # Incremental rotation about local Z axis
    dR = _rot_z(math.radians(degrees))

    # Compose: R_new = R * dR (apply in tool frame)
    R_new = _mat_mul(R, dR)

    # Back to axis-angle
    rx_n, ry_n, rz_n = _mat_to_aa(R_new)

    # Send motion with unchanged translation and new orientation
    new_pose = [x, y, z, rx_n, ry_n, rz_n]
    send_movel(robot, new_pose, acc, vel)
    wait_until_pose(robot, new_pose)

    print(
        f"   ↳ Rotated {degrees:.1f}° about tool Y-axis (green); now Ry component = {math.degrees(ry_n):.2f}°"
    )

def rotate_tcp_x(robot: urx.Robot, degrees: float, acc: float = 1.2, vel: float = 0.5):
    """Rotate the tool around its own X (red) axis by degrees."""
    pose = get_tcp_pose(robot)
    x, y, z, rx, ry, rz = pose

    # Current orientation → matrix
    R = _aa_to_mat(rx, ry, rz)

    # Incremental rotation about local X axis
    dR = _rot_x(math.radians(degrees))

    # Compose: R_new = R * dR (apply in tool frame)
    R_new = _mat_mul(R, dR)

    # Back to axis-angle
    rx_n, ry_n, rz_n = _mat_to_aa(R_new)

    # Send motion with unchanged translation and new orientation
    new_pose = [x, y, z, rx_n, ry_n, rz_n]
    send_movel(robot, new_pose, acc, vel)
    wait_until_pose(robot, new_pose)

    print(
        f"   ↳ Rotated {degrees:.1f}° about tool X-axis (red); now Rx component = {math.degrees(rx_n):.2f}°"
    )

def translate_tcp(
    robot: urx.Robot,
    dx_mm: float = 0.0,
    dy_mm: float = 0.0,
    dz_mm: float = 0.0,
    acc: float = 1.2,
    vel: float = 0.5
):
    """Translate the TCP along its own axes by the specified millimeters."""
    if dx_mm == dy_mm == dz_mm == 0.0:
        return  # nothing to do

    # Current pose and orientation matrix
    pose = get_tcp_pose(robot)
    x, y, z, rx, ry, rz = pose
    R = _aa_to_mat(rx, ry, rz)

    # Delta vector in tool frame (→ metres)
    d_tool = [dx_mm / 1000.0, dy_mm / 1000.0, dz_mm / 1000.0]

    # Convert to base frame: d_base = R * d_tool
    d_base = [
        sum(R[i][j] * d_tool[j] for j in range(3)) for i in range(3)
    ]

    # New Cartesian position in base frame
    new_pos = [x + d_base[0], y + d_base[1], z + d_base[2]]

    new_pose = new_pos + [rx, ry, rz]
    send_movel(robot, new_pose, acc, vel)
    wait_until_pose(robot, new_pose)

    # print(
    #     f"   ↳ Translated (tool frame) Δx={dx_mm:.1f} mm, Δy={dy_mm:.1f} mm, Δz={dz_mm:.1f} mm"
    # )

# -----------------------------------------------------------------------------
# Generic incremental rotation (all three axes)
# -----------------------------------------------------------------------------

def rotate_tcp(
    robot: urx.Robot,
    rx_deg: float = 0.0,
    ry_deg: float = 0.0,
    rz_deg: float = 0.0,
    acc: float = 1.2,
    vel: float = 0.5,
):
    """Incrementally rotate the TCP about its own X, Y and Z axes.

    The rotations are applied in **X → Y → Z** order, all in the TOOL frame,
    and the TCP translation is unchanged.
    """
    if rx_deg == ry_deg == rz_deg == 0.0:
        return  # nothing to do

    pose = get_tcp_pose(robot)
    x, y, z, rx, ry, rz = pose
    R = _aa_to_mat(rx, ry, rz)

    dR_x = _rot_x(math.radians(rx_deg))
    dR_y = _rot_y(math.radians(ry_deg))
    dR_z = _rot_z(math.radians(rz_deg))

    # Apply increments in sequence (tool-frame)
    R_new = _mat_mul(_mat_mul(R, dR_x), _mat_mul(dR_y, dR_z))

    rx_n, ry_n, rz_n = _mat_to_aa(R_new)
    new_pose = [x, y, z, rx_n, ry_n, rz_n]
    send_movel(robot, new_pose, acc, vel)
    wait_until_pose(robot, new_pose)

    # print(
    #     f"   ↳ Rotated ΔRx={rx_deg:.1f}°, ΔRy={ry_deg:.1f}°, ΔRz={rz_deg:.1f}° (tool frame)"
    # )
# -----------------------------------------------------------------------------
# URScript program generation for conical sweep
# -----------------------------------------------------------------------------

def conical_motion_script(
    robot: urx.Robot,
    tilt_deg: float = 20.0,
    revolutions: float = 1.0,
    steps: int = 72,
    acc: float = 0.1,
    vel: float = 0.1,
    blend_mm: float = 1.0,
    avoid_singular: bool = True,
    sing_tol_deg: float = 2.0,
):
    """Generate and send a single URScript program that performs the conical
    sweep with constant blend radius.

    This is useful when you want the robot to execute the whole path natively
    (smooth blending, no round-trip latency).
    """

    x0, y0, z0, *_ = get_tcp_pose(robot)

    axis = (-1.0, 0.0, 0.0)
    u = (0.0, 0.0, 1.0)
    v = (0.0, 1.0, 0.0)
    theta = math.radians(tilt_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    blend_m = max(0.0, blend_mm) / 1000.0
    pts = []

    for i in range(steps + 1):
        phi = 2 * math.pi * revolutions * i / steps
        ang = math.degrees(phi) % 360
        if avoid_singular and min(abs(((ang - 90 + 180) % 360) - 180), abs(((ang - 270 + 180) % 360) - 180)) < sing_tol_deg:
            continue

        cp, sp = math.cos(phi), math.sin(phi)
        X = [cos_t*axis[0] + sin_t*(cp*u[0] + sp*v[0]),
             cos_t*axis[1] + sin_t*(cp*u[1] + sp*v[1]),
             cos_t*axis[2] + sin_t*(cp*u[2] + sp*v[2])]
        mag = math.sqrt(sum(c*c for c in X)) or 1.0
        X = [c/mag for c in X]

        Zdown = (0.0, 0.0, -1.0)
        Y = [Zdown[1]*X[2]-Zdown[2]*X[1], Zdown[2]*X[0]-Zdown[0]*X[2], Zdown[0]*X[1]-Zdown[1]*X[0]]
        mag_y = math.sqrt(sum(c*c for c in Y)) or 1.0
        Y = [c/mag_y for c in Y]
        Z = [X[1]*Y[2]-X[2]*Y[1], X[2]*Y[0]-X[0]*Y[2], X[0]*Y[1]-X[1]*Y[0]]
        R = [[X[0], Y[0], Z[0]], [X[1], Y[1], Z[1]], [X[2], Y[2], Z[2]]]
        rx, ry, rz = _mat_to_aa(R)
        pts.append([x0, y0, z0, rx, ry, rz])

    lines = ["def cone_path():"]
    prev = None
    for idx, p in enumerate(pts):
        pose_str = ", ".join(f"{v:.6f}" for v in p)
        if idx == len(pts) - 1 or blend_m == 0.0:
            # Last point or no blending requested
            lines.append(f"  movej(p[{pose_str}], a={acc}, v={vel})")
        else:
            # Limit blend radius to < half distance to next waypoint (UR requirement)
            if prev is None:
                prev = p
            dist = math.sqrt(sum((p[i]-prev[i])**2 for i in range(3)))  # metres
            max_r = 0.45 * dist  # leave some margin
            r_use = min(blend_m, max_r)
            if r_use < 1e-6:
                lines.append(f"  movej(p[{pose_str}], a={acc}, v={vel})")
            else:
                lines.append(f"  movej(p[{pose_str}], a={acc}, v={vel}, r={r_use:.4f})")
            prev = p
    lines.append("end")
    lines.append("cone_path()")

    send_urscript(robot, "\n".join(lines))

# -----------------------------------------------------------------------------
# URScript program generation with servoJ for smooth conical sweep
# -----------------------------------------------------------------------------

def conical_motion_servoj_script(
    robot: urx.Robot,
    tilt_deg: float = 20.0,
    revolutions: float = 1.0,
    steps: int = 720,
    cycle_s: float = 0.008,
    lookahead_time: float = 0.1,
    gain: int = 300,
    avoid_singular: bool = True,
    sing_tol_deg: float = 1.0,
    approach_time_s: float = None,
):
    # Get current TCP pose and orientation as starting reference
    current_pose = get_tcp_pose(robot)
    x0, y0, z0 = current_pose[0], current_pose[1], current_pose[2]
    starting_rx, starting_ry, starting_rz = current_pose[3], current_pose[4], current_pose[5]
    
    # Convert starting orientation to rotation matrix
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

    theta_tilt = math.radians(tilt_deg)

    # Build full list of poses (axis-angle) that realise the cone
    pts: list[list[float]] = []
    for i in range(steps + 1):
        phi = 2 * math.pi * revolutions * i / steps
        ang = math.degrees(phi) % 360
        if avoid_singular and min(
            abs(((ang - 90 + 180) % 360) - 180),
            abs(((ang - 270 + 180) % 360) - 180),
        ) < sing_tol_deg:
            # Skip configurations that get too close to wrist singularities
            continue

        # Create rotation axis perpendicular to starting normal direction
        # This varies around the cone to create the circular motion
        rotation_axis = [0.0, math.cos(phi), math.sin(phi)]
        
        # Normalize rotation axis
        axis_mag = math.sqrt(rotation_axis[0]*rotation_axis[0] + rotation_axis[1]*rotation_axis[1] + rotation_axis[2]*rotation_axis[2])
        if axis_mag > 1e-6:
            rotation_axis = [rotation_axis[0]/axis_mag, rotation_axis[1]/axis_mag, rotation_axis[2]/axis_mag]
        else:
            rotation_axis = [0.0, 1.0, 0.0]  # Default to Y-axis
        
        # Create rotation matrix for tilt around rotation_axis using Rodrigues formula
        cos_tilt = math.cos(theta_tilt)
        sin_tilt = math.sin(theta_tilt)
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
        
        for row in range(3):
            for col in range(3):
                for k in range(3):
                    target_rotation_matrix[row][col] += R_tilt[row][k] * starting_rotation_matrix[k][col]
        
        # Convert target rotation matrix to axis-angle for UR
        rx, ry, rz = _mat_to_aa(target_rotation_matrix)
        pts.append([x0, y0, z0, rx, ry, rz])

    # Assemble URScript program
    lines = ["def cone_servoj():"]
    for idx, p in enumerate(pts):
        pose_str = ", ".join(f"{v:.6f}" for v in p)
        # use approach_time_s for first movement if provided, regular cycle_s for others
        cycle_time_to_use = approach_time_s if (approach_time_s is not None and idx == 0) else cycle_s
        lines.append(
            f"  servoj(get_inverse_kin(p[{pose_str}]), t={cycle_time_to_use}, lookahead_time={lookahead_time}, gain={gain})"
        )
        lines.append("  sync()")
    lines.append("end")
    lines.append("cone_servoj()")

    # Send program for execution
    send_urscript(robot, "\n".join(lines))


def wait_until_idle(robot: urx.Robot, eps_rad: float = 0.005, stable_time: float = 0.15, poll: float = 0.002, timeout: float = TIMEOUT) -> None:
    start = time.time()
    last = robot.getj()
    stable_start = None
    while True:
        cur = robot.getj()
        if max(abs(c - l) for c, l in zip(cur, last)) < eps_rad:
            # joints have barely moved since last sample
            if stable_start is None:
                stable_start = time.time()
            elif time.time() - stable_start >= stable_time:
                return  # stationary long enough
        else:
            stable_start = None  # movement resumed
        if time.time() - start > timeout:
            print("⚠️  idle wait timeout; continuing")
            return
        last = cur
        time.sleep(poll)


# -----------------------------------------------------------------------------
# Spiral Cold Spray Function
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
    approach_time_s: float = 0.5,
    delta_x_mm: float = 0.0,
):

    # Get current TCP pose and orientation as starting reference
    current_pose = get_tcp_pose(robot)
    x0, y0, z0 = current_pose[0], current_pose[1], current_pose[2]
    starting_rx, starting_ry, starting_rz = current_pose[3], current_pose[4], current_pose[5]
    
    # Store starting joint angles for reliable return movement
    starting_joints = robot.getj()
    starting_joints_str = f"[{starting_joints[0]:.6f}, {starting_joints[1]:.6f}, {starting_joints[2]:.6f}, {starting_joints[3]:.6f}, {starting_joints[4]:.6f}, {starting_joints[5]:.6f}]"
    
    starting_angle_mag = math.sqrt(starting_rx*starting_rx + starting_ry*starting_ry + starting_rz*starting_rz)
    if starting_angle_mag > 1e-6:
        # Normalized axis
        start_ax = starting_rx / starting_angle_mag
        start_ay = starting_ry / starting_angle_mag  
        start_az = starting_rz / starting_angle_mag
        
        cos_theta = math.cos(starting_angle_mag)
        sin_theta = math.sin(starting_angle_mag)
        
        starting_rotation_matrix = [
            [cos_theta + start_ax*start_ax*(1-cos_theta), start_ax*start_ay*(1-cos_theta) - start_az*sin_theta, start_ax*start_az*(1-cos_theta) + start_ay*sin_theta],
            [start_ay*start_ax*(1-cos_theta) + start_az*sin_theta, cos_theta + start_ay*start_ay*(1-cos_theta), start_ay*start_az*(1-cos_theta) - start_ax*sin_theta],
            [start_az*start_ax*(1-cos_theta) - start_ay*sin_theta, start_az*start_ay*(1-cos_theta) + start_ax*sin_theta, cos_theta + start_az*start_az*(1-cos_theta)]
        ]
    else:
        starting_rotation_matrix = [[1,0,0], [0,1,0], [0,0,1]]  # Identity matrix
    
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
        rx, ry, rz = _mat_to_aa(target_rotation_matrix)

        # Spiral translation in TCP YZ plane around current center, with optional X movement
        x = x0 + (delta_x_mm / 1000.0) * frac  # interpolate X position from start to start+delta_x_mm
        y = y0 + r * math.cos(phi)
        z = z0 + r * math.sin(phi)

        pose_str = ", ".join(f"{v:.6f}" for v in [x, y, z, rx, ry, rz])
        # use approach_time_s for first movement, regular cycle_s for others
        cycle_time_to_use = approach_time_s if step == 0 else current_cycle_s
        lines.append(
            f"  servoj(get_inverse_kin(p[{pose_str}]), t={cycle_time_to_use:.6f}, lookahead_time={lookahead_s}, gain={gain})"
        )
        lines.append("  sync()")


    lines.append("# Return to starting joint position")
    lines.append(f"movej({starting_joints_str}, a=1.0, v=1.0)")
    
    lines.append("end")
    lines.append("")
    lines.append("spiral_servoj()")
    lines.append("")
    

    send_urscript(robot, "\n".join(lines))


# -----------------------------------------------------------------------------
# Custom Movement Pattern Function
# -----------------------------------------------------------------------------

def custom_rectangle_pattern(
    robot: urx.Robot,
    width_mm: float = 30.0,
    height_mm: float = 30.0,
    initial_repetitions: int = 6,
    step_size_mm: float = 1.0,
    tilt_angle_deg: float = 10.0,
    initial_velocity: float = 0.05,
    initial_acceleration: float = 0.5,
    rect_velocity: float = 0.05,
    rect_acceleration: float = 0.5,
    blend_radius_mm: float = 0.01,
    rect_repetitions: int = 2,
):
    """
    
    TCP Orientation Reference:
    -Y is right, +Y is left, X- is forward, X+ is backward, Z- is up, Z+ is down
    
    Pattern sequence:
    1. Capture initial joint position
    2. Move to starting position (down half height, left half width)
    3. Initial horizontal oscillations (right-left-right-left...)
    4. Move up step size, tilt +Ry, adjust TCP
    5. Rectangle pattern: right-up-left-up until height is covered
    6. Move left 1cm, down height, right 1cm (return to start)
    7. Repeat rectangle pattern
    8. Move back 10cm and return to initial joint position
    """
    
    # print("initial robot state")
    initial_joint_angles = get_joint_angles(robot)
    initial_tcp_pose = get_tcp_pose(robot)
    initial_tcp_offset = [-0.27568, 0.0, 0.07794, 0.0, 0.0, 0.0]  # Store original TCP offset
    
    start_x, start_y, start_z = initial_tcp_pose[0], initial_tcp_pose[1], initial_tcp_pose[2]
    start_rx, start_ry, start_rz = initial_tcp_pose[3], initial_tcp_pose[4], initial_tcp_pose[5]
    
    print(f"🔧 Starting custom rectangle pattern from: {start_x:.3f}, {start_y:.3f}, {start_z:.3f}")
    print(f"   ↳ Width: {width_mm}mm, Height: {height_mm}mm")
    print(f"   ↳ Initial repetitions: {initial_repetitions}, Step size: {step_size_mm}mm")
    print(f"   ↳ Tilt angle: {tilt_angle_deg}°, Rectangle repetitions: {rect_repetitions}")
    print(f"   ↳ Initial vel/acc: {initial_velocity}/{initial_acceleration}")
    print(f"   ↳ Rectangle vel/acc: {rect_velocity}/{rect_acceleration}")
    print(f"   ↳ Blend radius: {blend_radius_mm}mm")
    print(f"   ↳ Initial joints: [{', '.join(f'{math.degrees(j):.1f}°' for j in initial_joint_angles)}]")
    
    # Generate URScript for rectangle pattern
    print("🔧 Generating URScript for rectangle pattern...")
    
    # Convert parameters to meters
    width_m = width_mm / 1000.0
    height_m = height_mm / 1000.0
    step_m = step_size_mm / 1000.0
    blend_radius_m = blend_radius_mm / 1000.0
    tilt_rad = math.radians(tilt_angle_deg)
    base_steps = int(math.floor(height_m / step_m))
    if base_steps <= 0:
        # Edge case: requested step exceeds height. Do two rows (finish left), clamp step to not exceed height.
        num_rows = 2
        actual_step_size = min(step_m, height_m)
    else:
        num_rows = base_steps + 1  # rows = vertical transitions + 1
        if num_rows % 2 == 1:
            num_rows -= 1  # one less step so we finish on the left
        # Keep the requested step size so we do not exceed height
        actual_step_size = step_m
    
    covered_height = (num_rows - 1) * actual_step_size
    leftover_height = max(0.0, height_m - covered_height)
    print(f"   ↳ Rows: {num_rows} | step: {actual_step_size*1000:.2f}mm | covered: {covered_height*1000:.2f}mm | leftover: {leftover_height*1000:.2f}mm")
    
    # Get starting joints for URScript
    starting_joints_str = ", ".join(f"{j:.6f}" for j in initial_joint_angles)
    
    # Build URScript
    lines = []
    lines.append("# Custom Rectangle Pattern URScript")
    lines.append("def rectangle_pattern():")
    lines.append("")
    
    # Phase 1: Move to starting position (down half height, left half width)
    lines.append("  # Phase 1: Move to starting position")
    lines.append(f"  pose_start = get_actual_tcp_pose()")
    lines.append(f"  # Move down {height_m/2:.6f}m, left {width_m/2:.6f}m (TCP-relative)")
    lines.append(f"  start_corner = pose_trans(pose_start, p[0, {width_m/2:.6f}, {height_m/2:.6f}, 0, 0, 0])")
    lines.append(f"  movel(start_corner, a={initial_acceleration:.3f}, v={initial_velocity:.3f})")
    lines.append("")
    
    # Phase 2: Initial horizontal oscillations (TCP-relative, chained)
    lines.append("  # Phase 2: Initial horizontal oscillations")
    for i in range(initial_repetitions):
        # Right (negative Y) from current pose
        lines.append(f"  # Oscillation {i+1}: Right")
        lines.append(f"  current_pos = get_actual_tcp_pose()")
        lines.append(f"  right_pos = pose_trans(current_pos, p[0, -{width_m:.6f}, 0, 0, 0, 0])")
        lines.append(f"  movel(right_pos, a={initial_acceleration:.3f}, v={initial_velocity:.3f})")
        # Left (positive Y) from updated pose
        lines.append(f"  # Oscillation {i+1}: Left")
        lines.append(f"  current_pos = get_actual_tcp_pose()")
        lines.append(f"  left_pos = pose_trans(current_pos, p[0, {width_m:.6f}, 0, 0, 0, 0])")
        lines.append(f"  movel(left_pos, a={initial_acceleration:.3f}, v={initial_velocity:.3f})")
    lines.append("")
    
    # Phase 3: Move up step size and tilt (TCP-relative)
    lines.append("  # Phase 3: Move up and tilt")
    lines.append(f"  current_pos = get_actual_tcp_pose()")
    lines.append(f"  # Using TCP frame; negative Z is UP per spec.")
    lines.append(f"  up_pos = pose_trans(current_pos, p[0, 0, -{actual_step_size:.6f}, 0, 0, 0])")
    lines.append(f"  movel(up_pos, a={initial_acceleration:.3f}, v={initial_velocity:.3f})")
    lines.append("")
    lines.append(f"  # Tilt TCP +Ry {tilt_angle_deg}° (TCP-relative)")
    lines.append(f"  current_pose = get_actual_tcp_pose()")
    lines.append(f"  tilted_pose = pose_trans(current_pose, p[0, 0, 0, 0, {tilt_rad:.6f}, 0])")
    lines.append(f"  movel(tilted_pose, a=1, v=0.3)")
    lines.append("")
    
    # Phase 4: Adjust TCP offset
    lines.append("  # Phase 4: Adjust TCP offset")
    new_tcp_offset = initial_tcp_offset.copy()
    new_tcp_offset[4] = initial_tcp_offset[4] - tilt_rad
    tcp_str = ", ".join(f"{t:.6f}" for t in new_tcp_offset)
    lines.append(f"  set_tcp(p[{tcp_str}])")
    lines.append("  sleep(0.2)")
    lines.append("")
    
    # Phase 5: Rectangle pattern for each repetition (finish on left)
    for rep in range(rect_repetitions):
        lines.append(f"  # Rectangle repetition {rep + 1}")
        lines.append(f"  rect_start = get_actual_tcp_pose()")
        
        # Alternating strokes per row; ensure final row finishes on left (+Y)
        for row in range(num_rows):
            lines.append(f"  # Row {row + 1} : {'Right' if (row % 2 == 0) else 'Left'} stroke")
            lines.append(f"  current_pos = get_actual_tcp_pose()")
            if row % 2 == 0:
                lines.append(f"  next_pos = pose_trans(current_pos, p[0, -{width_m:.6f}, 0, 0, 0, 0])")
            else:
                lines.append(f"  next_pos = pose_trans(current_pos, p[0, {width_m:.6f}, 0, 0, 0, 0])")
            lines.append(f"  movel(next_pos, a={rect_acceleration:.3f}, v={rect_velocity:.3f}, r={blend_radius_m:.6f})")

            # Move up between rows (except after the last row)
            if row < num_rows - 1:
                lines.append(f"  current_pos = get_actual_tcp_pose()")
                lines.append(f"  up_pos = pose_trans(current_pos, p[0, 0, -{actual_step_size:.6f}, 0, 0, 0])")
                lines.append(f"  movel(up_pos, a={rect_acceleration:.3f}, v={rect_velocity:.3f}, r={blend_radius_m:.6f})")

        # Return sequence per request: +Y 1cm, then move down to start Z, then reset to start pose
        if rep < rect_repetitions - 1:
            lines.append(f"  # Return sequence for repetition {rep + 1}: ensure left finish, offset, descend, reset")
            lines.append(f"  current_pos = get_actual_tcp_pose()")
            lines.append(f"  left_1cm = pose_trans(current_pos, p[0, 0.01, 0, 0, 0, 0])")
            lines.append(f"  movel(left_1cm, a={rect_acceleration:.3f}, v={rect_velocity:.3f}, r={blend_radius_m:.6f})")
            lines.append(f"  current_pos = get_actual_tcp_pose()")
            lines.append(f"  dz = rect_start[2] - current_pos[2]")
            lines.append(f"  down_pos = pose_trans(current_pos, p[0, 0, dz, 0, 0, 0])")
            lines.append(f"  movel(down_pos, a={rect_acceleration:.3f}, v={rect_velocity:.3f})")
            lines.append(f"  movel(rect_start, a={rect_acceleration:.3f}, v={rect_velocity:.3f})")

        lines.append("")
    
    # Phase 6: Move back 10cm and return to initial position (TCP-relative)
    lines.append("  # Phase 6: Move back and return home")
    lines.append("  # Move back 10cm (X+ is backward)")
    lines.append("  current_pos = get_actual_tcp_pose()")
    lines.append("  back_pos = pose_trans(current_pos, p[0.1, 0, 0, 0, 0, 0])")
    lines.append("  movel(back_pos, a=1.0, v=0.5)")
    lines.append("")
    
    # Reset TCP and return to starting joints
    tcp_original_str = ", ".join(f"{t:.6f}" for t in initial_tcp_offset)
    lines.append(f"  # Reset TCP offset")
    lines.append(f"  set_tcp(p[{tcp_original_str}])")
    lines.append("  sleep(0.2)")
    lines.append("")
    lines.append(f"  # Return to starting joint position")
    lines.append(f"  movej([{starting_joints_str}], a=1.0, v=0.5)")
    lines.append("")
    
    lines.append("end")
    lines.append("")
    lines.append("rectangle_pattern()")
    
    # Send the URScript
    print("📤 Sending URScript to robot...")
    send_urscript(robot, "\n".join(lines))
    
    print("🎯 Rectangle pattern URScript sent successfully!")
