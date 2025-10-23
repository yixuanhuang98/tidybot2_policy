import time
import numpy as np
from constants import POLICY_CONTROL_PERIOD
from real_env import RealEnv

env = RealEnv()
env.reset()
try:
    for _ in range(100):
        action = {
            'base_pose': np.array([-0.2, 0, 0]),
            'arm_pos': np.array([0.55, 0.0, 0.4]),
            'arm_quat': np.array([1, 0, 0, 0]),
            'gripper_pos': np.array([1]),
        }
        env.step(action)
        obs = env.get_obs()
        print([(k, v.shape) if v.ndim == 3 else (k, v) for (k, v) in obs.items()])
        time.sleep(POLICY_CONTROL_PERIOD)  # Note: Not precise
finally:
    env.close()