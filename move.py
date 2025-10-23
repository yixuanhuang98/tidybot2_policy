import time
import numpy as np
from constants import POLICY_CONTROL_PERIOD
from real_env import RealEnv

env = RealEnv()
env.reset()

# base_movement
for _ in range(100):
    obs = env.get_obs()
    action = {
        'base_pose': np.array([-0.2, 0, 0]),
        'arm_pos': obs['arm_pos'],
        'arm_quat': obs['arm_quat'],
        'gripper_pos': obs['gripper_pos'],
    }
    env.step(action)
    print([(k, v.shape) if v.ndim == 3 else (k, v) for (k, v) in obs.items()])
    time.sleep(POLICY_CONTROL_PERIOD)  # Note: Not precise

env.close()