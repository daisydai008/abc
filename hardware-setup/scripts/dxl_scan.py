#!/usr/bin/env python3
"""Bus discovery for DYNAMIXEL XL330 servos: ping across all baud rates.

Default mode (deep): explicit per-ID ping at every XL330 baud rate. Finds
every servo regardless of its configured ID/baud, and works where broadcast
ping fails (multiple same-ID servos colliding). Use this to discover factory
servos (ID 1 @ 57600) or audit a fully configured arm.

--broadcast mode (fast): one broadcast ping per baud rate. 7 packets total,
but NB: broadcast ping collides when multiple servos share the bus with the
same ID — silence does NOT prove an empty bus. Only use as a quick first
glance on a bus believed to be healthy; when in doubt, run the default mode.

Usage:
  python3 dxl_scan.py [port] [max_id]      # deep scan (default /dev/ttyUSB0 40)
  python3 dxl_scan.py --broadcast [port]   # fast broadcast ping per baud
"""
import sys

from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

BAUDS = [9600, 57600, 115200, 1000000, 2000000, 3000000, 4000000]
BROADCAST_ID = 254


def open_at(port, baud):
    ph = PortHandler(port)
    try:
        if not ph.openPort() or not ph.setBaudRate(baud):
            return None
    except Exception:
        return None  # e.g. port does not exist / permission denied
    return ph


def broadcast_scan(pkt, port):
    for baud in BAUDS:
        ph = open_at(port, baud)
        if ph is None:
            print(f"{baud:>8}: port open/setbaud FAILED")
            continue
        model, res, err = pkt.ping(ph, BROADCAST_ID)
        tag = f"RESPONDED model={model}" if res == COMM_SUCCESS else "no response"
        print(f"{baud:>8}: {tag}")
        ph.closePort()
    print("\nNB: 'no response' does NOT prove an empty bus (same-ID collision). "
          "Re-run without --broadcast for a definitive answer.")


def deep_scan(pkt, port, max_id):
    found = []
    for baud in BAUDS:
        ph = open_at(port, baud)
        if ph is None:
            print(f"{baud:>8}: port FAILED")
            continue
        ph.setPacketTimeoutMillis(40)
        hits = []
        for sid in range(0, max_id + 1):
            model, res, err = pkt.ping(ph, sid)
            if res == COMM_SUCCESS:
                hits.append((sid, model))
        print(f"{baud:>8}: {hits if hits else 'none'}", flush=True)
        found.extend((baud, s, m) for s, m in hits)
        ph.closePort()
    print("\nSUMMARY:", found if found else "no servo found at any baud/ID")


def main():
    args = sys.argv[1:]
    broadcast = "--broadcast" in args
    args = [a for a in args if a != "--broadcast"]
    port = args[0] if len(args) > 0 else "/dev/ttyUSB0"
    max_id = int(args[1]) if len(args) > 1 else 40
    pkt = PacketHandler(2.0)
    if broadcast:
        broadcast_scan(pkt, port)
    else:
        deep_scan(pkt, port, max_id)


if __name__ == "__main__":
    main()
