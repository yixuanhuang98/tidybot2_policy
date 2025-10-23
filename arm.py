import time
import math
import numpy as np
from enum import Enum
from constants import POLICY_CONTROL_PERIOD
from real_env import RealEnv


class PickState(Enum):
    APPROACH = "approach"
    LOWER = "lower"
    GRASP = "grasp"
    LIFT = "lift"
    RETURN_HOME = "return_home"


class GraspController:
    # Manipulation parameters (from mp_policy.py)
    ROBOT_BASE_HEIGHT = 0.48
    PICK_APPROACH_HEIGHT_OFFSET = 0.25
    PICK_LOWER_DIST = 0.08
    PICK_LIFT_DIST = 0.28
    
    # Grasping parameters
    GRASP_SUCCESS_THRESHOLD = 0.7
    GRASP_PROGRESS_THRESHOLD = 0.3
    GRASP_TIMEOUT_S = 3.0
    
    # Target object position (you can modify this)
    TARGET_OBJECT_POS = np.array([0.5, 0, 0.1])  # Example: 1m forward, 0.5m right, 0.8m high
    
    def __init__(self):
        self.grasp_state = None
        self.grasp_start_time = None
        self.initial_gripper_pos = None
        
    def reset(self):
        """Reset the grasp controller state"""
        self.grasp_state = None
        self.grasp_start_time = None
        self.initial_gripper_pos = None
        
    def step(self, obs):
        """Execute one step of the grasping behavior"""
        # Extract current state
        base_pose = obs['base_pose']
        arm_pos = obs['arm_pos'] 
        arm_quat = obs['arm_quat']
        gripper_pos = obs['gripper_pos']
        
        # Initialize grasp state if not set
        if self.grasp_state is None:
            self.grasp_state = PickState.APPROACH
            print("Starting grasping sequence...")
        
        # Define default targets to hold current pose
        target_arm_pos = arm_pos.copy()
        target_arm_quat = arm_quat.copy()
        target_gripper_pos = gripper_pos.copy()
        
        # Calculate object position relative to robot base
        object_3d_pos = self.TARGET_OBJECT_POS
        
        # Calculate global position difference with approach height
        global_diff = np.array([
            object_3d_pos[0] - base_pose[0],
            object_3d_pos[1] - base_pose[1], 
            object_3d_pos[2] + self.PICK_APPROACH_HEIGHT_OFFSET - self.ROBOT_BASE_HEIGHT
        ])
        
        # Transform to base's local coordinate frame (account for base rotation)
        base_angle = base_pose[2]
        cos_angle = math.cos(-base_angle)  # Negative for inverse rotation
        sin_angle = math.sin(-base_angle)
        
        object_relative_pos = np.array([
            cos_angle * global_diff[0] - sin_angle * global_diff[1],
            sin_angle * global_diff[0] + cos_angle * global_diff[1],
            global_diff[2]  # Z component unchanged
        ])
        
        print(f"Base angle: {base_pose[2]:.3f} rad ({math.degrees(base_pose[2]):.1f} deg)")
        print(f"Object global pos: {object_3d_pos}")
        print(f"Current arm pos: {arm_pos}")
        print(f"Position error: {np.linalg.norm(arm_pos - object_relative_pos):.4f}m")
        print(f"Grasp state: {self.grasp_state}")
        
        # Gripper orientation pointing downward
        downward_quat = np.array([1.0, 0.0, 0.0, 0.0])
        
        if self.grasp_state == PickState.APPROACH:
            # Step 1: Position arm well above object with open gripper (safe approach)
            target_arm_pos = object_relative_pos
            target_arm_quat = downward_quat
            target_gripper_pos = np.array([0.0])  # Gripper open
            
            print(f"Step 1: Positioning arm above object with open gripper")
            if np.allclose(arm_pos, target_arm_pos, atol=0.03):  # 3cm tolerance
                self.grasp_state = PickState.LOWER
                print("Arm positioned above object, moving to lower approach")
        
        elif self.grasp_state == PickState.LOWER:
            # Step 2: Lower gripper closer to object for precise grasping
            target_arm_pos = object_relative_pos.copy()
            target_arm_pos[2] -= self.PICK_LOWER_DIST  # Lower by 8cm for closer approach
            target_arm_quat = downward_quat
            target_gripper_pos = np.array([0.0])  # Gripper open
            
            print(f"Step 2: Lowering gripper for precise approach... target: {target_arm_pos[2]:.3f}, current: {arm_pos[2]:.3f}")
            if np.allclose(arm_pos, target_arm_pos, atol=0.02):  # 2cm tolerance
                self.grasp_state = PickState.GRASP
                print("Gripper lowered to grasping position, closing gripper")
        
        elif self.grasp_state == PickState.GRASP:
            # Step 3: Close gripper to grasp
            target_arm_pos = object_relative_pos.copy()
            target_arm_pos[2] -= self.PICK_LOWER_DIST  # Maintain lowered position
            target_arm_quat = downward_quat
            target_gripper_pos = np.array([1.0])  # Close gripper
            
            print(f"Step 3: Closing gripper... current position: {gripper_pos[0]:.3f}")
            
            # Initialize grasp attempt tracking
            if self.grasp_start_time is None:
                self.grasp_start_time = time.time()
                self.initial_gripper_pos = gripper_pos[0]
                print(f"Started grasp attempt, initial gripper pos: {self.initial_gripper_pos:.3f}")
            
            # Check for successful grasp (multiple criteria)
            gripper_closed_enough = gripper_pos[0] > self.GRASP_SUCCESS_THRESHOLD
            gripper_progress = (gripper_pos[0] - self.initial_gripper_pos) > self.GRASP_PROGRESS_THRESHOLD
            grasp_timeout = (time.time() - self.grasp_start_time) > self.GRASP_TIMEOUT_S
            
            if gripper_closed_enough or gripper_progress or grasp_timeout:
                if gripper_closed_enough or gripper_progress:
                    print(f"Grasp successful! Gripper pos: {gripper_pos[0]:.3f}, progress: {gripper_pos[0] - self.initial_gripper_pos:.3f}")
                else:
                    print(f"Grasp timeout reached, proceeding with current grip: {gripper_pos[0]:.3f}")
                
                self.grasp_state = PickState.LIFT
                # Clean up tracking variables
                self.grasp_start_time = None
                self.initial_gripper_pos = None
                print("Moving to lift phase!")
        
        elif self.grasp_state == PickState.LIFT:
            # Step 4: Lift object from the grasping position
            lifted_pos = object_relative_pos.copy()
            lifted_pos[2] += (self.PICK_LIFT_DIST - self.PICK_LOWER_DIST)  # Net lift
            target_arm_pos = lifted_pos
            target_arm_quat = downward_quat
            target_gripper_pos = np.array([1.0])  # Gripper closed
            
            print(f"Step 4: Lifting object... target height: {target_arm_pos[2]:.3f}, current: {arm_pos[2]:.3f}")
            if np.allclose(arm_pos, target_arm_pos, atol=0.05):  # 5cm tolerance
                print("Object lifted successfully! Now returning to home position.")
                self.grasp_state = PickState.RETURN_HOME
        
        elif self.grasp_state == PickState.RETURN_HOME:
            # Step 5: Return arm to home position
            arm_home_pos = np.array([0.14322269, 0.0, 0.20784938])
            arm_home_quat = np.array([0.707, 0.707, 0, 0])
            
            target_arm_pos = arm_home_pos
            target_arm_quat = arm_home_quat 
            target_gripper_pos = np.array([1.0])  # Gripper closed
            
            print(f"Step 5: Returning to home position... target: {target_arm_pos}, current: {arm_pos}")
            if np.allclose(arm_pos, target_arm_pos, atol=0.05):  # 5cm tolerance
                print("Arm returned to home position! Grasping sequence complete.")
                return None  # Signal completion
        
        # Create action from targets
        action = {
            'base_pose': base_pose.copy(),  # Keep base stationary
            'arm_pos': target_arm_pos,
            'arm_quat': target_arm_quat,
            'gripper_pos': target_gripper_pos,
        }
        return action


# Main execution
def main():
    env = RealEnv()
    env.reset()
    
    # Create grasp controller
    grasp_controller = GraspController()
    
    print("Starting grasping behavior...")
    print(f"Target object position: {grasp_controller.TARGET_OBJECT_POS}")
    
    # Execute grasping behavior
    for step_count in range(1000):  # Maximum 1000 steps for safety
        obs = env.get_obs()
        
        # Get action from grasp controller
        action = grasp_controller.step(obs)
        
        if action is None:
            print("Grasping sequence completed successfully!")
            break
            
        # Execute action
        env.step(action)
        print(f"Step {step_count}: Executed action")
        print([(k, v.shape) if hasattr(v, 'ndim') and v.ndim == 3 else (k, v) for (k, v) in obs.items() if k not in ['base_image', 'wrist_image']])
        
        time.sleep(POLICY_CONTROL_PERIOD)  # Note: Not precise
    
    env.close()
    print("Grasping behavior script completed.")


if __name__ == "__main__":
    main()
