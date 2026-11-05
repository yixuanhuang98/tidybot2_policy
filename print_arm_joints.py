# Prints the Kinova arm's measured joint positions online.
#
# This is a read-only monitor: it opens its own Kortex session and only queries
# measured joint angles. It does not change the servoing/control mode, so it is
# safe to run while the arm is being moved by gamepad or while arm_server.py is
# running (it does not use TorqueControlledArm, which enforces a single
# instance).
#
# Usage: python print_arm_joints.py [--hz 20] [--log joints.csv]

import argparse
import time
import numpy as np
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from kinova import DeviceConnection


def wrap_deg(angles_deg):
    """Wrap angles to [-180, 180) degrees."""
    return (angles_deg + 180.0) % 360.0 - 180.0


def main():
    parser = argparse.ArgumentParser(description='Print Kinova joint positions online')
    parser.add_argument('--hz', type=float, default=20.0, help='Print rate in Hz')
    parser.add_argument('--log', type=str, default=None, help='Optional CSV file to append samples to')
    args = parser.parse_args()

    period = 1.0 / args.hz
    log_file = open(args.log, 'w') if args.log else None
    if log_file:
        log_file.write('t,' + ','.join(f'q{i + 1}_deg' for i in range(7)) + ',' + ','.join(f'q{i + 1}_rad' for i in range(7)) + '\n')

    with DeviceConnection.createTcpConnection() as router:
        base = BaseClient(router)
        print('Streaming joint positions (deg and rad). Press Ctrl+C to stop.')
        t0 = time.time()
        try:
            while True:
                loop_start = time.time()
                joint_angles = base.GetMeasuredJointAngles().joint_angles
                q_deg = wrap_deg(np.array([j.value for j in joint_angles]))
                q_rad = np.deg2rad(q_deg)
                elapsed = time.time() - t0
                deg_str = ' '.join(f'{v:9.3f}' for v in q_deg)
                rad_str = ' '.join(f'{v:9.4f}' for v in q_rad)
                print(f'\r[{elapsed:7.2f}s] deg = [{deg_str}]  rad = [{rad_str}]', end='', flush=True)
                if log_file:
                    log_file.write(f'{elapsed:.4f},' + ','.join(f'{v:.5f}' for v in q_deg) + ',' + ','.join(f'{v:.6f}' for v in q_rad) + '\n')
                time.sleep(max(0.0, period - (time.time() - loop_start)))
        except KeyboardInterrupt:
            print()
        finally:
            if log_file:
                log_file.close()


if __name__ == '__main__':
    main()
