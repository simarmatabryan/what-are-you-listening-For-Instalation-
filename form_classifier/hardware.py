"""Serial hardware input for Arduino/ESP32 style sensor boards."""

import json
import threading


class SerialSensor:
    """Read newline-delimited JSON or proximity,touch,held CSV samples."""
    def __init__(self, device, baud=115200, on_sample=None):
        import serial
        self.device = device
        self.baud = int(baud)
        self.on_sample = on_sample
        self._stop = threading.Event()
        self._serial = serial.Serial(device, self.baud, timeout=1)
        self._thread = threading.Thread(target=self._read, daemon=True)

    @staticmethod
    def parse(line):
        line = line.strip()
        if not line:
            return None
        try:
            data = json.loads(line)
            return float(data['proximity']), bool(data.get('touch', 0)), bool(data.get('held', 0))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            parts = [part.strip() for part in line.split(',')]
            if not parts:
                return None
            return (float(parts[0]), bool(int(parts[1])) if len(parts) > 1 else False,
                    bool(int(parts[2])) if len(parts) > 2 else False)

    def start(self):
        self._thread.start()

    def _read(self):
        while not self._stop.is_set():
            raw = self._serial.readline()
            if not raw:
                continue
            try:
                sample = self.parse(raw.decode('utf-8', errors='strict'))
                if sample and self.on_sample:
                    self.on_sample(*sample)
            except (UnicodeError, ValueError, KeyError, TypeError):
                continue

    def close(self):
        self._stop.set()
        self._serial.close()
