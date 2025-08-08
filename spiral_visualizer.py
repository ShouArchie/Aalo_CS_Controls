import math
import matplotlib.pyplot as plt
import urx
import time
import numpy as np
from typing import List, Tuple

# Import parameters from the main spiral script
from spray_test_V1_spiral import (
    ROBOT_IP, TCP_OFFSET_MM, TILT_START_DEG, TILT_END_DEG, R_START_MM, R_END_MM, 
    REVS, STEPS_PER_REV, SING_TOL_DEG, CYCLE_S, LOOKAHEAD_S, GAIN,
    CYCLE_S_START, CYCLE_S_END, home
)

# Import robot functions
from UR_Cold_Spray_Code import robot_functions as rf

def capture_robot_spiral_positions(robot: urx.Robot, invert_tilt: bool = False) -> Tuple[List[Tuple[float, float, float]], List[float]]:
    """Capture actual robot TCP positions during spiral execution."""
    
    positions = []
    angles_from_start = []  # Orientation difference from starting position
    
    # Read the starting position AND orientation BEFORE generating the spiral code
    print("Reading robot starting position and orientation...")
    starting_pose = rf.get_tcp_pose(robot)
    x0, y0, z0 = starting_pose[0], starting_pose[1], starting_pose[2]
    starting_rx, starting_ry, starting_rz = starting_pose[3], starting_pose[4], starting_pose[5]
    print(f"Starting position: X={x0:.6f}, Y={y0:.6f}, Z={z0:.6f}")
    print(f"Starting orientation: Rx={np.degrees(starting_rx):.2f}°, Ry={np.degrees(starting_ry):.2f}°, Rz={np.degrees(starting_rz):.2f}°")
    
    # Convert starting orientation to rotation matrix and extract tool X-axis (normal direction)
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
    
    # Extract the starting tool X-axis direction (this becomes our fixed normal direction)
    starting_normal_direction = starting_rotation_matrix[:, 0]  # First column = X-axis
    print(f"Starting normal direction (tool X-axis): [{starting_normal_direction[0]:.3f}, {starting_normal_direction[1]:.3f}, {starting_normal_direction[2]:.3f}]")
    
    # Store the starting position as our first point
    positions.append((x0, y0, z0))
    
    # Calculate theoretical angles for comparison
    theoretical_angles = []
    total_steps = int(round(REVS * STEPS_PER_REV / 4))  # Same as in spiral generation
    
    tilt_start_deg_local = TILT_START_DEG
    tilt_end_deg_local = TILT_END_DEG
    if invert_tilt:
        tilt_start_deg_local = -tilt_start_deg_local
        tilt_end_deg_local = -tilt_end_deg_local
    
    for step in range(total_steps + 1):
        frac = step / total_steps if total_steps else 1.0
        theoretical_tilt_deg = tilt_start_deg_local + (tilt_end_deg_local - tilt_start_deg_local) * frac
        theoretical_angles.append(abs(theoretical_tilt_deg))  # Store absolute angle from normal
    
    # Store starting angle (should be 0° since we're comparing to starting orientation)
    angles_from_start.append(0.0)
    
    # Determine if we're using variable cycle timing
    use_variable_cycle = CYCLE_S_START is not None and CYCLE_S_END is not None
    
    # Precompute counts - reduce steps for faster visualization
    total_steps = int(round(REVS * STEPS_PER_REV / 4))  # 1/4 the normal steps for testing
    
    # Build URScript with position capture
    lines: List[str] = ["def spiral_servoj():"]
    
    for step in range(total_steps + 1):
        frac = step / total_steps if total_steps else 1.0
        # Linear schedules
        tilt = math.radians(tilt_start_deg_local + (tilt_end_deg_local - tilt_start_deg_local) * frac)
        r_mm = R_START_MM + (R_END_MM - R_START_MM) * frac
        r = r_mm / 1000.0
        
        # Calculate cycle time (variable or fixed) - SLOW for visualization
        if use_variable_cycle:
            current_cycle_s = (CYCLE_S_START + (CYCLE_S_END - CYCLE_S_START) * frac) * 3  # 3x slower
        else:
            current_cycle_s = CYCLE_S * 3  # 3x slower for better visualization
        
        # Phase with optional offset
        phi_deg = (step / STEPS_PER_REV) * 360.0
        phi = math.radians(phi_deg)
        
        # Skip near 90° and 270° (wrap-safe)
        ang = (phi_deg % 360.0)
        if min(abs(((ang - 90) + 180) % 360 - 180),
               abs(((ang - 270) + 180) % 360 - 180)) < SING_TOL_DEG:
            continue
        
        # Tool-axis frame construction
        axis = (-1.0, 0.0, 0.0)
        u = (0.0, 0.0, 1.0)
        v = (0.0, 1.0, 0.0)
        cp, sp = math.cos(phi), math.sin(phi)
        X = [
            math.cos(tilt) * axis[0] + math.sin(tilt) * (cp * u[0] + sp * v[0]),
            math.cos(tilt) * axis[1] + math.sin(tilt) * (cp * u[1] + sp * v[1]),
            math.cos(tilt) * axis[2] + math.sin(tilt) * (cp * u[2] + sp * v[2]),
        ]
        # Normalize X
        mag = math.sqrt(sum(c * c for c in X)) or 1.0
        X = [c / mag for c in X]
        
        Zdown = (0.0, 0.0, -1.0)
        Y = [
            Zdown[1] * X[2] - Zdown[2] * X[1],
            Zdown[2] * X[0] - Zdown[0] * X[2],
            Zdown[0] * X[1] - Zdown[1] * X[0],
        ]
        mag_y = math.sqrt(sum(c * c for c in Y)) or 1.0
        Y = [c / mag_y for c in Y]
        Z = [X[1] * Y[2] - X[2] * Y[1], X[2] * Y[0] - X[0] * Y[2], X[0] * Y[1] - X[1] * Y[0]]
        
        # Axis-angle for UR
        rx, ry, rz = rf._mat_to_aa([
            [X[0], Y[0], Z[0]],
            [X[1], Y[1], Z[1]],
            [X[2], Y[2], Z[2]],
        ])
        
        # Spiral translation in TCP YZ plane around current center
        x = x0
        y = y0 + r * math.cos(phi)
        z = z0 + r * math.sin(phi)
        
        pose_str = ", ".join(f"{v:.6f}" for v in [x, y, z, rx, ry, rz])
        lines.append(
            f"  servoj(get_inverse_kin(p[{pose_str}]), t={current_cycle_s:.6f}, lookahead_time={LOOKAHEAD_S}, gain={GAIN})"
        )
        lines.append("  sync()")
    
    lines.append("end")
    lines.append("spiral_servoj()")
    
    # Execute the spiral and capture positions
    print("Executing spiral and capturing positions...")
    rf.send_urscript(robot, "\n".join(lines))
    
    # Capture positions during execution
    start_time = time.time()
    timeout = 300  # 5 minute timeout for slow spiral
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
            
            # Calculate angle between current tool X-axis and starting normal direction
            rx, ry, rz = current_pose[3], current_pose[4], current_pose[5]
            
            # Convert current orientation to rotation matrix to get current tool X-axis
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
                
                # Extract current tool X-axis direction
                current_tool_x_axis = current_rotation_matrix[:, 0]  # First column = X-axis
            else:
                current_tool_x_axis = np.array([1, 0, 0])  # Default X-axis for no rotation
            
            # Calculate angle between current tool X-axis and starting normal direction
            dot_product = np.dot(current_tool_x_axis, starting_normal_direction)
            # Clamp dot product to avoid numerical issues with arccos
            dot_product = np.clip(dot_product, -1.0, 1.0)
            angle_from_normal_rad = np.arccos(dot_product)
            angle_from_normal_deg = np.degrees(angle_from_normal_rad)
            
            # Add debug info for first few samples
            if len(positions) <= 3:
                print(f"Debug sample {len(positions)}: current_tool_x=[{current_tool_x_axis[0]:.3f}, {current_tool_x_axis[1]:.3f}, {current_tool_x_axis[2]:.3f}], angle={angle_from_normal_deg:.2f}°")
            
            angles_from_start.append(angle_from_normal_deg)
            
            # Print progress every 25 samples
            if len(positions) % 25 == 0:
                print(f"Captured {len(positions)} points, angle: {angle_from_normal_deg:.1f}°")
            
            # Check if robot joints are still moving (better for both spiral and conical motion)
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
            
            # Check if robot is idle (spiral complete)
            try:
                if not robot.is_program_running():
                    print("Robot program finished")
                    break
            except:
                # In simulation, this might not work reliably
                pass
                
            # Check timeout
            if time.time() - start_time > timeout:
                print("Timeout reached during spiral execution")
                break
                
            time.sleep(0.02)  # 50Hz sampling rate
            
        except Exception as e:
            print(f"Error capturing position: {e}")
            break
    
    print(f"Captured {len(positions)} positions and {len(angles_from_start)} angles")
    return positions, angles_from_start, theoretical_angles

def plot_spiral(run_both_orientations=False):
    """Connect to robot, execute spiral, and plot actual positions."""
    
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
        
        # Capture normal tilt spiral from this rotated starting position
        print("Executing normal tilt spiral from rotated starting position...")
        points_normal, angles_normal, theoretical_angles_normal = capture_robot_spiral_positions(robot, invert_tilt=False)
        
        points_inverted = []
        angles_inverted = []
        theoretical_angles_inverted = []
        if run_both_orientations:
            # Wait and move back to home
            time.sleep(2.0)
            rf.move_to_joint_position(robot, home, acc=1.0, vel=0.8, wait=True)
            time.sleep(1.0)
            
            # Capture inverted tilt spiral
            print("Executing inverted tilt spiral...")
            points_inverted, angles_inverted, theoretical_angles_inverted = capture_robot_spiral_positions(robot, invert_tilt=True)
        
    finally:
        robot.close()
        print("Robot connection closed")
    
    # Separate coordinates for normal spiral
    x_normal, y_normal, z_normal = zip(*points_normal)
    
    if points_inverted:
        x_inverted, y_inverted, z_inverted = zip(*points_inverted)
        # Create 2x3 plots when we have both orientations (add angle plots)
        fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(2, 3, figsize=(18, 10))
        
        # Plot 1: YZ view (Normal)
        ax1.plot(y_normal, z_normal, 'b-', linewidth=2, label='Normal Tilt')
        ax1.scatter(y_normal, z_normal, c='purple', s=10, alpha=0.6, label='Captured Points')
        ax1.plot(y_normal[0], z_normal[0], 'go', markersize=8, label='Start')
        ax1.plot(y_normal[-1], z_normal[-1], 'ro', markersize=8, label='End')
        ax1.set_xlabel('Y (m)')
        ax1.set_ylabel('Z (m)')
        ax1.set_title('YZ Plane View (Normal Tilt)')
        ax1.grid(True)
        ax1.legend()
        ax1.axis('equal')
        
        # Plot 2: YZ view (Inverted)
        ax2.plot(y_inverted, z_inverted, 'r-', linewidth=2, label='Inverted Tilt Path')
        ax2.scatter(y_inverted, z_inverted, c='purple', s=20, alpha=0.6, label='Captured Points', zorder=5)
        ax2.plot(y_inverted[0], z_inverted[0], 'go', markersize=8, label='Start')
        ax2.plot(y_inverted[-1], z_inverted[-1], 'ro', markersize=8, label='End')
        ax2.set_xlabel('Y (m)')
        ax2.set_ylabel('Z (m)')
        ax2.set_title('YZ Plane View (Inverted Tilt)')
        ax2.grid(True)
        ax2.legend()
        ax2.axis('equal')
        
        # Plot 3: Angle from Starting Normal Direction
        time_normal = list(range(len(angles_normal)))
        ax3.plot(time_normal, angles_normal, 'b-', linewidth=2, label='Tool X-axis vs Starting Normal')
        ax3.scatter(time_normal, angles_normal, c='purple', s=10, alpha=0.6, label='Measured Points')
        ax3.plot(range(len(theoretical_angles_normal)), theoretical_angles_normal, 'g--', linewidth=2, label='Theoretical')
        ax3.set_xlabel('Sample Number')
        ax3.set_ylabel('Angle from Starting Normal (degrees)')
        ax3.set_title('Tool X-axis Angle from Starting Normal - Normal Tilt')
        ax3.grid(True)
        ax3.legend()
        
        # Plot 4: XZ view
        ax4.plot(x_normal, z_normal, 'b-', linewidth=2, label='Normal Tilt Path')
        ax4.scatter(x_normal, z_normal, c='purple', s=10, alpha=0.6, label='Captured Points')
        ax4.plot(x_normal[0], z_normal[0], 'go', markersize=8, label='Start')
        ax4.plot(x_normal[-1], z_normal[-1], 'ro', markersize=8, label='End')
        ax4.set_xlabel('X (m)')
        ax4.set_ylabel('Z (m)')
        ax4.set_title('XZ Plane View (Normal) - X should be constant')
        ax4.grid(True)
        ax4.legend()
        
        # Plot 5: Angle from Starting Normal Direction (Inverted Tilt)
        time_inverted = list(range(len(angles_inverted)))
        ax5.plot(time_inverted, angles_inverted, 'r-', linewidth=2, label='Tool X-axis vs Starting Normal')
        ax5.scatter(time_inverted, angles_inverted, c='darkmagenta', s=10, alpha=0.6, label='Measured Points')
        ax5.plot(range(len(theoretical_angles_inverted)), theoretical_angles_inverted, 'g--', linewidth=2, label='Theoretical')
        ax5.set_xlabel('Sample Number')
        ax5.set_ylabel('Angle from Starting Normal (degrees)')
        ax5.set_title('Tool X-axis Angle from Starting Normal - Inverted Tilt')
        ax5.grid(True)
        ax5.legend()
        
        # Plot 6: Both overlayed
        ax6.plot(y_normal, z_normal, 'b-', linewidth=2, label='Normal Tilt', alpha=0.7)
        ax6.plot(y_inverted, z_inverted, 'r-', linewidth=2, label='Inverted Tilt', alpha=0.7)
        ax6.scatter(y_normal, z_normal, c='purple', s=8, alpha=0.4, label='Normal Points')
        ax6.scatter(y_inverted, z_inverted, c='darkmagenta', s=8, alpha=0.4, label='Inverted Points')
        ax6.plot(y_normal[0], z_normal[0], 'go', markersize=8, label='Start')
        ax6.plot(y_normal[-1], z_normal[-1], 'ko', markersize=8, label='End')
        ax6.set_xlabel('Y (m)')
        ax6.set_ylabel('Z (m)')
        ax6.set_title('YZ Plane - Both Orientations')
        ax6.grid(True)
        ax6.legend()
        ax6.axis('equal')
        
    else:
        # Create 1x3 plots when we only have normal orientation (add angle plot)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))
        
        # Plot 1: YZ view
        ax1.plot(y_normal, z_normal, 'b-', linewidth=2, label='Actual Robot Path')
        ax1.scatter(y_normal, z_normal, c='purple', s=20, alpha=0.6, label='Captured Points', zorder=5)
        ax1.plot(y_normal[0], z_normal[0], 'go', markersize=8, label='Start')
        ax1.plot(y_normal[-1], z_normal[-1], 'ro', markersize=8, label='End')
        ax1.set_xlabel('Y (m)')
        ax1.set_ylabel('Z (m)')
        ax1.set_title('YZ Plane View - Actual Robot Spiral Path')
        ax1.grid(True)
        ax1.legend()
        ax1.axis('equal')
        
        # Plot 2: XZ view
        ax2.plot(x_normal, z_normal, 'b-', linewidth=2, label='Actual Robot Path')
        ax2.scatter(x_normal, z_normal, c='purple', s=20, alpha=0.6, label='Captured Points', zorder=5)
        ax2.plot(x_normal[0], z_normal[0], 'go', markersize=8, label='Start')
        ax2.plot(x_normal[-1], z_normal[-1], 'ro', markersize=8, label='End')
        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Z (m)')
        ax2.set_title('XZ Plane View - X should be constant')
        ax2.grid(True)
        ax2.legend()
        
        # Plot 3: Angle from Starting Normal Direction
        time_normal = list(range(len(angles_normal)))
        ax3.plot(time_normal, angles_normal, 'b-', linewidth=2, label='Tool X-axis vs Starting Normal')
        ax3.scatter(time_normal, angles_normal, c='purple', s=20, alpha=0.6, label='Measured Points')
        ax3.plot(range(len(theoretical_angles_normal)), theoretical_angles_normal, 'g--', linewidth=2, label='Theoretical')
        ax3.set_xlabel('Sample Number')
        ax3.set_ylabel('Angle from Starting Normal (degrees)')
        ax3.set_title('Tool X-axis Angle from Starting Normal')
        ax3.grid(True)
        ax3.legend()
    
    plt.tight_layout()
    
    # Print statistics
    print(f"\nSpiral Parameters:")
    print(f"  Robot IP: {ROBOT_IP}")
    print(f"  Revolutions: {REVS}")
    print(f"  Start radius: {R_START_MM} mm")
    print(f"  End radius: {R_END_MM} mm")
    print(f"  Total captured points: {len(points_normal)}")
    if points_inverted:
        print(f"  Total inverted points: {len(points_inverted)}")
    print(f"  X range: {min(x_normal):.6f} to {max(x_normal):.6f} (variation: {max(x_normal)-min(x_normal):.6f})")
    print(f"  Y range: {min(y_normal):.3f} to {max(y_normal):.3f}")
    print(f"  Z range: {min(z_normal):.3f} to {max(z_normal):.3f}")
    
    plt.show()

if __name__ == "__main__":
    plot_spiral(run_both_orientations=True)