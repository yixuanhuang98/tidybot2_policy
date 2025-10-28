# Author: Jimmy Wu
# Date: October 2024
#
# This RPC server allows other processes to communicate with the mobile base
# low-level controller, which runs in its own, dedicated real-time process.
#
# Note: Operations that are not time-sensitive should be run in a separate,
# non-real-time process to avoid interfering with the low-level control and
# causing latency spikes.

import time
from multiprocessing.managers import BaseManager as MPBaseManager
from base_controller import Vehicle
from constants import BASE_RPC_HOST, BASE_RPC_PORT, RPC_AUTHKEY
from base_server import BaseManager

if __name__ == '__main__':
    import numpy as np
    from constants import POLICY_CONTROL_PERIOD
    manager = BaseManager(address=(BASE_RPC_HOST, BASE_RPC_PORT), authkey=RPC_AUTHKEY)
    manager.connect()
    base = manager.Base()
    try:
        base.reset()
        for i in range(50):
            base.execute_action({'base_pose': np.array([(i / 50) * 0.5, 0.0, 0.0])})
            print(base.get_state())
            time.sleep(POLICY_CONTROL_PERIOD)  # Note: Not precise
    finally:
        base.close()
