#!/usr/bin/env python3
"""Verify an assembled GELLO leader arm: ping all 7 servos at 4M and stream joint angles.

Run on the Linux workstation (or any machine with `pip install dynamixel-sdk`),
with the arm's U2D2 plugged in and the 5V hub powered. Does NOT enable torque —
pure read-only check, safe to run with the arm in any pose.

Mirrors abc/deploy/robot/leaders/gello_leader.py conventions:
  raw = (position / 2048 - 1) * pi   (radians)

Usage:
  python3 verify_leader.py --port /dev/serial/by-id/usb-FTDI_... --ids 20 21 22 23 24 25 26
"""
import argparse
import sys
import time

from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

ADDR_PRESENT_POSITION = 132  # 4 bytes, Protocol 2.0
BAUD = 4_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--ids", type=int, nargs="+", default=list(range(20, 27)))
    ap.add_argument("--duration", type=float, default=5.0,
                    help="seconds to stream readings (0 = single snapshot)")
    args = ap.parse_args()

    ph = PortHandler(args.port)
    pkt = PacketHandler(2.0)
    if not ph.openPort() or not ph.setBaudRate(BAUD):
        sys.exit(f"Failed to open {args.port} @ {BAUD}")

    # ping pass
    ok = True
    for i in args.ids:
        model, res, err = pkt.ping(ph, i)
        status = f"model={model}" if res == COMM_SUCCESS else f"FAIL ({pkt.getTxRxResult(res)})"
        print(f"ID {i:3d}: {status}")
        ok &= res == COMM_SUCCESS
    if not ok:
        sys.exit("Some servos missing — check IDs (set_servo_ids.py), baud=4M, wiring, 5V power.")

    # stream pass
    import math
    t0 = time.time()
    print("\nM0..M6 raw joint angles (rad):")
    while True:
        vals = []
        for i in args.ids:
            pos, res, err = pkt.read4ByteTxRx(ph, i, ADDR_PRESENT_POSITION)
            vals.append((pos / 2048 - 1) * math.pi if res == COMM_SUCCESS else float("nan"))
        print("  " + " ".join(f"{v:+.3f}" for v in vals))
        if args.duration <= 0 or time.time() - t0 > args.duration:
            break
        time.sleep(0.1)
    ph.closePort()
    print("\nMove each joint by hand and confirm the matching column changes.")


if __name__ == "__main__":
    main()
