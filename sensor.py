"""Hard-forward Android proximity OSC -> Max/MSP.

Android -> Python:
    UDP 8001
    /proximity 0.0 = NEAR
    /proximity 5.0 = FAR

Python -> Max:
    UDP 8002
    /proximity <same float>
"""

import argparse
import logging
import socket
import struct
import threading
import time

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

LOG = logging.getLogger("proximity-sensor")


def _osc_pad(data: bytes) -> bytes:
    data += b"\x00"
    while len(data) % 4:
        data += b"\x00"
    return data


def build_osc_float(address: str, value: float) -> bytes:
    return (
        _osc_pad(address.encode("utf-8"))
        + _osc_pad(b",f")
        + struct.pack(">f", float(value))
    )


class ProximityOSCBridge:
    def __init__(
        self,
        sensor_host: str = "0.0.0.0",
        sensor_port: int = 8002,
        max_host: str = "127.0.0.1",
        max_port: int = 8002,
        near_threshold: float = 1.0,
        on_state=None,
    ):
        self.sensor_host = sensor_host
        self.sensor_port = int(sensor_port)
        self.max_host = max_host
        self.max_port = int(max_port)
        self.near_threshold = float(near_threshold)
        self.on_state = on_state

        self._dispatcher = Dispatcher()
        self._dispatcher.map("/proximity", self._on_proximity)

        self._server = None
        self._thread = None

    def _forward_raw_osc(self, value: float) -> int:
        packet = build_osc_float("/proximity", value)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            return sock.sendto(packet, (self.max_host, self.max_port))
        finally:
            sock.close()

    def _on_proximity(self, address, *values):
        if not values:
            LOG.warning("PROXIMITY diterima tanpa nilai.")
            return

        try:
            raw_value = float(values[0])
        except (TypeError, ValueError):
            LOG.warning("Nilai proximity tidak valid: %r", values[0])
            return

        value = max(0.0, min(5.0, raw_value))
        is_near = value <= self.near_threshold

        LOG.info("HP -> PYTHON /proximity %.3f", value)

        try:
            sent = self._forward_raw_osc(value)
            LOG.info(
                "HARD SEND -> MAX /proximity %.3f -> %s:%s | %d bytes",
                value, self.max_host, self.max_port, sent
            )
        except Exception:
            LOG.exception(
                "GAGAL HARD SEND /proximity %.3f -> %s:%s",
                value, self.max_host, self.max_port
            )
            return

        if self.on_state is not None:
            try:
                self.on_state(value, is_near)
            except Exception:
                LOG.exception("Error pada callback proximity.")

    def start(self):
        if self._server is not None:
            return

        self._server = ThreadingOSCUDPServer(
            (self.sensor_host, self.sensor_port),
            self._dispatcher,
        )

        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="android-proximity-osc",
            daemon=True,
        )
        self._thread.start()

        LOG.info("PROXIMITY SERVER aktif -> %s:%s", self.sensor_host, self.sensor_port)
        LOG.info("HARD FORWARD MAX     -> %s:%s", self.max_host, self.max_port)

    def stop(self):
        if self._server is None:
            return

        self._server.shutdown()
        self._server.server_close()

        if self._thread is not None:
            self._thread.join(timeout=2.0)

        self._server = None
        self._thread = None
        LOG.info("PROXIMITY SERVER berhenti.")


def main():
    parser = argparse.ArgumentParser(
        description="Android proximity :8001 -> hard-forward Max :8002"
    )
    parser.add_argument("--sensor-host", default="0.0.0.0")
    parser.add_argument("--sensor-port", type=int, default=8001)
    parser.add_argument("--max-host", default="127.0.0.1")
    parser.add_argument("--max-port", type=int, default=8002)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    bridge = ProximityOSCBridge(
        sensor_host=args.sensor_host,
        sensor_port=args.sensor_port,
        max_host=args.max_host,
        max_port=args.max_port,
    )
    bridge.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()


if __name__ == "__main__":
    main()
