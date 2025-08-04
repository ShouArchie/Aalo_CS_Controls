import time
import sys
from typing import Optional
import math
import urx

# Import our modules
import robot_functions as rf
import urscript_paths as paths

# Configuration
ROBOT_IP = "192.168.10.205" # 192.168.10.205 # 192.168.0.101
DEFAULT_WAIT_TIME = 30  # seconds to wait for program completion

HOMETest = [math.radians(a) for a in [201.64, -54.86, 109.85, 214.57, 269.77, 111.69]]

robot = urx.Robot(ROBOT_IP)
rf.set_tcp_offset(robot, -257.81, 0, 60.3, 0, 0, 0)
# --- Move down, then MoveP back to home TCP 
rf.move_to_joint_position(robot, HOMETest, acc=0.5, vel=0.5)
# remember TCP pose of HOMETest (target of MoveP)
home_tcp = robot.getl()

# push tool 400 mm straight down so we have some distance to travel
rf.translate_tcp(robot, dy_mm= -100, dz_mm=-150, acc=0.5, vel=0.5)

initial_pose = rf.get_tcp_pose(robot)
# rf.rotate_tcp(robot, ry_deg=10, acc=0.1, vel=0.1)
final_pose = rf.get_tcp_pose(robot)

delta_rx = math.degrees(initial_pose[3]) - math.degrees(final_pose[3])
delta_ry = math.degrees(initial_pose[4]) - math.degrees(final_pose[4])
delta_rz = math.degrees(initial_pose[5]) - math.degrees(final_pose[5]) 
print(f"Delta RX,RY,RZ (deg): {delta_rx:.2f}, {delta_ry:.2f}, {delta_rz:.2f}")

# rf.set_tcp_offset(robot, -257.81, 0, 60.3, 0, -10, 0)

# Conical sweep using movej version (commented out for now)
rf.rotate_tcp(robot, ry_deg=15, acc=0.1, vel=0.1)
current_pose = rf.get_tcp_pose(robot)
time.sleep(2)
rf.conical_motion_servoj_script(
    robot,
    tilt_deg=15,
    revolutions=1.0,
    steps=180,
    cycle_s=0.015, # Steps: 180 and Cycle: 0.015
    lookahead_time=0.2,
    gain=3000,
    sing_tol_deg=1,
)
time.sleep(1.3)
rf.wait_until_idle(robot) 
print("Complete 1 ")


rf.conical_motion_servoj_script(
    robot,
    tilt_deg=10,
    revolutions=1.0,
    steps=180,
    cycle_s=0.015, # Steps: 180 and Cycle: 0.015
    lookahead_time=0.2,
    gain=1000,
    sing_tol_deg=1,
)

time.sleep(1.3)
rf.wait_until_idle(robot) 
print("Complete")
robot.close()


# Align the tool to the spray pattern
rf.translate_tcp(robot, dy_mm= 20, acc=0.5, vel=0.5)
rf.rotate_tcp(robot, ry_deg=13.5, acc=0.1, vel=0.1)

# Spray Pattern
DY_STEP = 0.050    # m  (back-and-forth along tool Y)
RY_STEP = math.radians(1.36)  # ≈0.0237 rad per incremental rotation
CYCLES = 5  # forward & reverse passes

UR_SCRIPT_TEMPLATE = f"""
def blended_spray():
    # Forward cycles
    j = 0
    while j < {iterations}:
        i = 0
        while i < {CYCLES}:
            movel(pose_trans(get_actual_tcp_pose(), p[0, -{DY_STEP}, 0, 0, 0, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, {RY_STEP}, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            movel(pose_trans(get_actual_tcp_pose(), p[0,  {DY_STEP}, 0, 0, 0, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            if i < {CYCLES} - 1:
                movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, {RY_STEP}, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            end
            i = i + 1
        end
 
        # Reverse cycles
        i = 0
        while i < {CYCLES}:
            if i > 0:
                movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, -{RY_STEP}, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            end
            movel(pose_trans(get_actual_tcp_pose(), p[0, -{DY_STEP}, 0, 0, 0, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0, 0, -{RY_STEP}, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            if i < {CYCLES} - 1:
                movel(pose_trans(get_actual_tcp_pose(), p[0,  {DY_STEP}, 0, 0, 0, 0]), a={ACC}, v={VEL}, r={BLEND_R})
            end
            i = i + 1
        end
        j = j + 1
    end
end
 
# Execute the routine
blended_spray()
"""
 