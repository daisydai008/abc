#!/usr/bin/env python3
"""Configure one DYNAMIXEL XL330-M077-T at a time: set servo ID and 4M baudrate.

Alternative to Dynamixel Wizard 2.0 GUI. Works on macOS and Linux with
`pip install dynamixel-sdk` (pure Python + pyserial).

ABC firmware requirements (verified against abc/deploy/robot/leaders/gello_leader.py):
  - Protocol 2.0 (XL330 factory default)
  - Baudrate 4_000_000 (hard-coded in GelloLeaderNode)
  - IDs: left arm 20-26, right arm 30-36 (gtwy_config in deploy/robot/config.py)

Usage — connect ONE servo (via U2D2 + powered hub), then e.g.:
  python3 set_servo_ids.py --port /dev/tty.usbserial-FTAAMOEB --id 20
  python3 set_servo_ids.py --port /dev/ttyUSB0 --id 21

Motor order per assembly guide: M0 base .. M6 handle/trigger.
Suggested mapping: ID 20/30 -> M0 (base), ..., ID 26/36 -> M6 (trigger).
"""
import argparse
import sys

from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

# XL330 control table (Protocol 2.0 EEPROM area — torque must be OFF to write)
ADDR_ID = 7
ADDR_BAUDRATE = 8
ADDR_TORQUE_ENABLE = 64
BAUD_CODE_4M = 6  # 0:9600 1:57600 2:115200 3:1M 4:2M 5:3M 6:4M
BROADCAST_ID = 254
FACTORY_BAUD = 57_600
TARGET_BAUD = 4_000_000


def open_port(port: str, baud: int):
    ph = PortHandler(port)
    if not ph.openPort():
        sys.exit(f"Failed to open {port}")
    if not ph.setBaudRate(baud):
        sys.exit(f"Failed to set baud {baud}")
    return ph


def find_servos(ph, pkt):
    """Scan IDs 0-252 with a short timeout; return [(id, model), ...].

    NB: a READ to the broadcast address (254) gets no reply in Protocol 2.0
    (only PING/WRITE-type instructions are broadcastable), so discovering the
    current ID via broadcast read does not work — scan explicit IDs instead.
    """
    ph.setPacketTimeoutMillis(40)
    hits = []
    for sid in range(0, 253):
        model, result, error = pkt.ping(ph, sid)
        if result == COMM_SUCCESS:
            hits.append((sid, model))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="U2D2 serial port")
    ap.add_argument("--id", type=int, required=True, help="new servo ID (20-26 / 30-36)")
    ap.add_argument("--scan-baud", type=int, default=FACTORY_BAUD,
                    help="baud the servo currently speaks (factory 57600)")
    ap.add_argument("--skip-baud", action="store_true",
                    help="only set ID, keep current baudrate")
    args = ap.parse_args()
    if not (0 <= args.id <= 252):
        sys.exit("ID must be 0-252")

    pkt = PacketHandler(2.0)

    # --- phase 1: talk to the servo at its current baud ---
    ph = open_port(args.port, args.scan_baud)
    found = find_servos(ph, pkt)
    if len(found) > 1:
        factory = [f for f in found if f[0] == 1]
        if factory:
            # incremental chain mode: already-configured servos stay on the bus,
            # the one factory servo (ID 1) is the new segment to configure
            print(f"Bus has {len(found)} servos {found}; targeting the factory one (ID 1).")
            found = factory
        else:
            ph.closePort()
            sys.exit(f"Multiple servos on the bus: {found}. Connect exactly ONE "
                     "(or add new servos one at a time along the chain).")
    if not found:
        ph.closePort()
        sys.exit(f"No servo responded at {args.scan_baud} baud on {args.port}. "
                 "Connect exactly ONE servo; try --scan-baud 4000000 if already configured.")
    old_id, model = found[0]
    print(f"Found servo: ID={old_id} model={model} @ {args.scan_baud} baud")

    # torque off so EEPROM is writable
    pkt.write1ByteTxRx(ph, old_id, ADDR_TORQUE_ENABLE, 0)

    if old_id != args.id:
        res, err = pkt.write1ByteTxRx(ph, old_id, ADDR_ID, args.id)
        if res != COMM_SUCCESS or err:
            sys.exit(f"ID write failed: {pkt.getTxRxResult(res)} err={err}")
        print(f"ID {old_id} -> {args.id}")

    if not args.skip_baud:
        res, err = pkt.write1ByteTxRx(ph, args.id, ADDR_BAUDRATE, BAUD_CODE_4M)
        if res != COMM_SUCCESS or err:
            sys.exit(f"Baud write failed: {pkt.getTxRxResult(res)} err={err}")
        print("Baudrate -> 4M (code 6)")
    ph.closePort()

    # --- phase 2: verify at 4M ---
    verify_baud = args.scan_baud if args.skip_baud else TARGET_BAUD
    ph = open_port(args.port, verify_baud)
    model, res, err = pkt.ping(ph, args.id)
    if res != COMM_SUCCESS:
        sys.exit(f"Verification failed at {verify_baud} baud")
    cur_id, res, _ = pkt.read1ByteTxRx(ph, args.id, ADDR_ID)
    cur_baud_code, _, _ = pkt.read1ByteTxRx(ph, args.id, ADDR_BAUDRATE)
    print(f"OK: ID={cur_id} model={model} baud_code={cur_baud_code} @ {verify_baud}")
    ph.closePort()
    print("Done. Label this servo and move to the next one.")


if __name__ == "__main__":
    main()
