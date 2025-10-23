import time
import numpy as np
from constants import POLICY_CONTROL_PERIOD
from real_env import RealEnv

env = RealEnv()
env.reset()
env.close()