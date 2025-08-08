import math
import matplotlib.pyplot as plt
import urx
import time
import numpy as np
from typing import List, Tuple

# Import parameters from the main spiral script (we'll use some of these)
from spray_test_V1_spiral import (
    ROBOT_IP, TCP_OFFSET_MM, home
)

# Import robot functions
from UR_Cold_Spray_Code import robot_functions as rf

# Conical motion parameters
TILT_DEG = 10.0              # cone angle
REVOLUTIONS = 4.0            # number of full rotations
STEPS = 180                  # steps per revolution (1° each)
CYCLE_S = 0.03              # base cycle time
LOOKAHEAD_TIME = 0.015         # lookahead time
GAIN = 3000                   # servoj gain
AVOID_SINGULAR = True        # avoid singularities
SING_TOL_DEG = 1.0          # singularity tolerance

def capture_robot_conical_positions(robot: urx.Robot) -> Tuple[List[Tuple[float, float, float]], List[float], List[float]]:
    """Capture actual robot TCP positions during conical execution."""
    
    positions = []
    angles_from_start = []  # Orientation difference from starting position
    
    # Read the starting position AND orientation BEFORE generating the conical code
    print("Reading robot starting position and orientation...")
    starting_pose = rf.get_tcp_pose(robot)
    x0, y0, z0 = starting_pose[0], starting_pose[1], starting_pose[2]
    starting_rx, starting_ry, starting_rz = starting_pose[3], starting_pose[4], starting_pose[5]
    print(f"Starting position: X={x0:.6f}, Y={y0:.6f}, Z={z0:.6f}")
    print(f"Starting orientation: Rx={np.degrees(starting_rx):.2f}°, Ry={np.degrees(starting_ry):.2f}°, Rz={np.degrees(starting_rz):.2f}°")
    
    # Convert starting orientation to rotation matrix for later comparison
    starting_angle_mag = np.sqrt(starting_rx*starting_rx + starting_ry*starting_ry + starting_rz*starting_rz)
    if starting_angle_mag > 1e-6:
        # Normalized axis
        start_ax, start_ay, start_az = starting_rx/starting_angle_mag, starting_ry/starting_angle_mag, starting_rz/starting_angle_mag
        
        # Rodrigues formula for starting rotation matrix
        cos_theta = np.cos(starting_angle_mag)
        sin_theta = np.sin(starting_angle_mag)
        
        starting_rotation_matrix = np.array([
            [cos_theta + start_ax*start_ax*(1-cos_theta), start_ax*start_ay*(1-cos_theta) - start_az*sin_theta, start_ax*start_az*(1-cos_theta) + start_ay*sin_theta],
            [start_ay*start_ax*(1-cos_theta) + start_az*sin_theta, cos_theta + start_ay*start_ay*(1-cos_theta), start_ay*start_az*(1-cos_theta) - start_ax*sin_theta],
            [start_az*start_ax*(1-cos_theta) - start_ay*sin_theta, start_az*start_ay*(1-cos_theta) + start_ax*sin_theta, cos_theta + start_az*start_az*(1-cos_theta)]
        ])
    else:
        starting_rotation_matrix = np.eye(3)  # Identity matrix for no rotation
    
    # Store the starting position as our first point
    positions.append((x0, y0, z0))
    
    # Calculate theoretical angles for comparison
    theoretical_angles = []
    total_steps = STEPS + 1
    
    # For conical motion, the angle from normal should be constant at TILT_DEG
    for step in range(total_steps):
        theoretical_angles.append(TILT_DEG)  # Constant tilt angle
    
    # Store starting angle (should be 0° since we're comparing to starting orientation)
    angles_from_start.append(0.0)
    
    # Generate CORRECTED conical motion that maintains constant angle from starting orientation
    lines: List[str] = ["def cone_servoj():"]
    
    # Convert starting orientation to rotation matrix for reference
    theta_tilt = math.radians(TILT_DEG)
    
    for i in range(STEPS + 1):
        phi = 2 * math.pi * REVOLUTIONS * i / STEPS
        ang = math.degrees(phi) % 360
        
        if AVOID_SINGULAR and min(
            abs(((ang - 90 + 180) % 360) - 180),
            abs(((ang - 270 + 180) % 360) - 180),
        ) < SING_TOL_DEG:
            # Skip configurations that get too close to wrist singularities
            continue
        
        # Create rotation that maintains constant angle from starting orientation
        # Method: Rotate around axis perpendicular to starting orientation
        
        # Define rotation axis in the YZ plane (perpendicular to starting tool direction)
        rotation_axis = np.array([0, np.cos(phi), np.sin(phi)])
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
        
        # Create rotation matrix for the tilt
        cos_tilt = np.cos(theta_tilt)
        sin_tilt = np.sin(theta_tilt)
        
        # Rodrigues rotation formula to create rotation matrix
        K = np.array([
            [0, -rotation_axis[2], rotation_axis[1]],
            [rotation_axis[2], 0, -rotation_axis[0]],
            [-rotation_axis[1], rotation_axis[0], 0]
        ])
        
        R_tilt = np.eye(3) + sin_tilt * K + (1 - cos_tilt) * np.dot(K, K)
        
        # Apply this rotation to the starting orientation
        target_rotation = R_tilt @ starting_rotation_matrix
        
        # Convert back to axis-angle for UR
        rx, ry, rz = rf._mat_to_aa(target_rotation.tolist())
        
        pose_str = ", ".join(f"{v:.6f}" for v in [x0, y0, z0, rx, ry, rz])
        
        # Use slower timing for visualization (3x slower)
        slow_cycle_s = CYCLE_S * 3
        lines.append(
            f"  servoj(get_inverse_kin(p[{pose_str}]), t={slow_cycle_s:.6f}, lookahead_time={LOOKAHEAD_TIME}, gain={GAIN})"
        )
        lines.append("  sync()")
    
    lines.append("end")
    lines.append("cone_servoj()")
    
    # Execute the conical motion and capture positions
    print("Executing conical motion and capturing positions...")
    rf.send_urscript(robot, "\n".join(lines))
    
    # Capture positions during execution
    start_time = time.time()
    timeout = 300  # 5 minute timeout for slow motion
    last_joints = None
    stationary_count = 0
    
    # Give the program a moment to start
    time.sleep(0.5)
    
    while True:
        try:
            # Get current TCP position and orientation
            current_pose = rf.get_tcp_pose(robot)
            current_pos = (current_pose[0], current_pose[1], current_pose[2])
            positions.append(current_pos)
            
            # Get current joint positions for movement detection
            current_joints = robot.getj()
            
            # Calculate orientation difference from starting position (conical angle)
            rx, ry, rz = current_pose[3], current_pose[4], current_pose[5]
            
            # Convert current orientation to rotation matrix
            current_angle_mag = np.sqrt(rx*rx + ry*ry + rz*rz)
            if current_angle_mag > 1e-6:
                # Normalized axis
                ax, ay, az = rx/current_angle_mag, ry/current_angle_mag, rz/current_angle_mag
                
                # Rodrigues formula for current rotation matrix
                cos_theta = np.cos(current_angle_mag)
                sin_theta = np.sin(current_angle_mag)
                
                current_rotation_matrix = np.array([
                    [cos_theta + ax*ax*(1-cos_theta), ax*ay*(1-cos_theta) - az*sin_theta, ax*az*(1-cos_theta) + ay*sin_theta],
                    [ay*ax*(1-cos_theta) + az*sin_theta, cos_theta + ay*ay*(1-cos_theta), ay*az*(1-cos_theta) - ax*sin_theta],
                    [az*ax*(1-cos_theta) - ay*sin_theta, az*ay*(1-cos_theta) + ax*sin_theta, cos_theta + az*az*(1-cos_theta)]
                ])
            else:
                current_rotation_matrix = np.eye(3)  # Identity matrix for no rotation
            
            # Calculate the rotation difference between starting and current orientations
            # R_diff = R_current * R_starting^T
            rotation_diff = current_rotation_matrix @ starting_rotation_matrix.T
            
            # Extract the angle from the rotation difference matrix
            # trace(R) = 1 + 2*cos(theta), so theta = arccos((trace(R) - 1) / 2)
            trace = np.trace(rotation_diff)
            
            # Add debug info for first few samples
            if len(positions) <= 3:
                print(f"Debug sample {len(positions)}: trace={trace:.6f}")
            
            # Clamp trace to avoid numerical issues
            trace = np.clip(trace, -1, 3)  # trace should be between -1 and 3 for rotation matrices
            angle_from_normal_rad = np.arccos(np.clip((trace - 1) / 2, -1, 1))
            angle_from_normal_deg = np.degrees(angle_from_normal_rad)
            
            angles_from_start.append(angle_from_normal_deg)
            
            # Print progress every 25 samples
            if len(positions) % 25 == 0:
                print(f"Captured {len(positions)} points, angle: {angle_from_normal_deg:.1f}°")
            
            # Check if robot joints are still moving (better for conical motion)
            if last_joints is not None:
                # Calculate joint movement (sum of absolute differences)
                joint_movement = sum(abs(a - b) for a, b in zip(current_joints, last_joints))
                if joint_movement < 0.0001:  # Less than 0.0001 radians (~0.006°) total joint movement
                    stationary_count += 1
                else:
                    stationary_count = 0
                    
                # Debug info for movement detection
                if stationary_count > 100:
                    print(f"Low joint movement detected: {joint_movement:.8f} rad, stationary for {stationary_count} samples")
            
            last_joints = current_joints
            
            # Check if robot joints stopped moving for too long
            if stationary_count > 150:  # 3 seconds of no joint movement
                print(f"Robot joints appear to have stopped moving after {stationary_count} stationary samples")
                break
            
            # Check if robot is idle (motion complete)
            try:
                if not robot.is_program_running():
                    print("Robot program finished")
                    break
            except:
                # In simulation, this might not work reliably
                pass
                
            # Check timeout
            if time.time() - start_time > timeout:
                print("Timeout reached during conical execution")
                break
                
            time.sleep(0.02)  # 50Hz sampling rate
            
        except Exception as e:
            print(f"Error capturing position: {e}")
            break
    
    print(f"Captured {len(positions)} positions and {len(angles_from_start)} angles")
    return positions, angles_from_start, theoretical_angles

def plot_conical():
    """Connect to robot, execute conical motion, and plot actual positions."""
    
    print("Connecting to robot...")
    robot = urx.Robot(ROBOT_IP)
    
    try:
        # Set TCP offset
        rf.set_tcp_offset(robot, *TCP_OFFSET_MM)
        
        # Move to HOME position
        print("Moving to HOME position...")
        rf.move_to_joint_position(robot, home, acc=1.0, vel=0.8, wait=True)
        time.sleep(1.0)
        
        # Apply 10 degree rotation around tool Y-axis from home
        print("Rotating around tool Y-axis by 10 degrees from home position...")
        
        # Get current TCP pose for comparison
        home_pose = rf.get_tcp_pose(robot)
        print(f"Home TCP orientation: Rx={math.degrees(home_pose[3]):.2f}°, Ry={math.degrees(home_pose[4]):.2f}°, Rz={math.degrees(home_pose[5]):.2f}°")
        
        # Use robot_functions rotate_tcp_y function
        # rf.rotate_tcp_y(robot, 10.0, acc=1.0, vel=0.8)
        # time.sleep(1.0)
        
        # Show the new TCP orientation after rotation
        rotated_pose = rf.get_tcp_pose(robot)
        print(f"Rotated TCP orientation: Rx={math.degrees(rotated_pose[3]):.2f}°, Ry={math.degrees(rotated_pose[4]):.2f}°, Rz={math.degrees(rotated_pose[5]):.2f}°")
        
        # Capture conical motion from this rotated starting position
        print("Executing conical motion from rotated starting position...")
        positions, angles, theoretical_angles = capture_robot_conical_positions(robot)
        
    finally:
        robot.close()
        print("Robot connection closed")
    
    # Separate coordinates
    x_coords, y_coords, z_coords = zip(*positions)
    
    # Create 2x2 plots for conical motion analysis
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: XY view (top view)
    ax1.plot(x_coords, y_coords, 'b-', linewidth=2, label='Conical Path')
    ax1.scatter(x_coords, y_coords, c='purple', s=20, alpha=0.6, label='Captured Points', zorder=5)
    ax1.plot(x_coords[0], y_coords[0], 'go', markersize=8, label='Start')
    ax1.plot(x_coords[-1], y_coords[-1], 'ro', markersize=8, label='End')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_title('XY Plane View (Top View) - Should be circular')
    ax1.grid(True)
    ax1.legend()
    ax1.axis('equal')
    
    # Plot 2: XZ view (side view)
    ax2.plot(x_coords, z_coords, 'b-', linewidth=2, label='Conical Path')
    ax2.scatter(x_coords, z_coords, c='purple', s=20, alpha=0.6, label='Captured Points', zorder=5)
    ax2.plot(x_coords[0], z_coords[0], 'go', markersize=8, label='Start')
    ax2.plot(x_coords[-1], z_coords[-1], 'ro', markersize=8, label='End')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Z (m)')
    ax2.set_title('XZ Plane View - Z should be constant (apex)')
    ax2.grid(True)
    ax2.legend()
    
    # Plot 3: YZ view (side view)
    ax3.plot(y_coords, z_coords, 'b-', linewidth=2, label='Conical Path')
    ax3.scatter(y_coords, z_coords, c='purple', s=20, alpha=0.6, label='Captured Points', zorder=5)
    ax3.plot(y_coords[0], z_coords[0], 'go', markersize=8, label='Start')
    ax3.plot(y_coords[-1], z_coords[-1], 'ro', markersize=8, label='End')
    ax3.set_xlabel('Y (m)')
    ax3.set_ylabel('Z (m)')
    ax3.set_title('YZ Plane View - Z should be constant (apex)')
    ax3.grid(True)
    ax3.legend()
    
    # Plot 4: Conical Angle from Starting Position
    time_points = list(range(len(angles)))
    ax4.plot(time_points, angles, 'b-', linewidth=2, label='Actual Conical Angle')
    ax4.scatter(time_points, angles, c='purple', s=20, alpha=0.6, label='Measured Points')
    ax4.plot(range(len(theoretical_angles)), theoretical_angles, 'g--', linewidth=2, label='Theoretical (constant)')
    ax4.set_xlabel('Sample Number')
    ax4.set_ylabel('Conical Angle from Start (degrees)')
    ax4.set_title(f'Tool Orientation Difference from Home (Expected: {TILT_DEG}°)')
    ax4.grid(True)
    ax4.legend()
    
    plt.tight_layout()
    
    # Print statistics
    print(f"\nConical Motion Parameters:")
    print(f"  Robot IP: {ROBOT_IP}")
    print(f"  Tilt angle: {TILT_DEG}°")
    print(f"  Revolutions: {REVOLUTIONS}")
    print(f"  Total captured points: {len(positions)}")
    print(f"  X range: {min(x_coords):.6f} to {max(x_coords):.6f}")
    print(f"  Y range: {min(y_coords):.6f} to {max(y_coords):.6f}")
    print(f"  Z range: {min(z_coords):.6f} to {max(z_coords):.6f} (variation: {max(z_coords)-min(z_coords):.6f})")
    print(f"  Angle range: {min(angles):.2f}° to {max(angles):.2f}° (expected: {TILT_DEG}°)")
    print(f"  Angle std dev: {np.std(angles):.2f}°")
    
    plt.show()

if __name__ == "__main__":
    plot_conical()