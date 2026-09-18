"""Sensor service final: satu responden, satu kategori, sound terpisah.

Tidak ada lagi satu pesan kategori yang "digabung".

LOW:
  /sound/notification_low 1

MIDDLE:
  /sound/notification_middle 1
  /sound/vibration 1

HIGH:
  /sound/notification_high 1
  /sound/vibration 1
  /sound/alarm 1

FAR:
  /sound/stop 1

Loop Python:
  LOW    random 15-20 detik
  MIDDLE random 10-15 detik
  HIGH   random 5-10 detik
"""

import random
import threading
from collections import deque

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient


VALID_CATEGORIES = {"LOW", "MIDDLE", "HIGH"}

LOOP_INTERVALS = {
    "LOW": (15.0, 20.0),
    "MIDDLE": (10.0, 15.0),
    "HIGH": (5.0, 10.0),
}

SOUND_LABELS = {
    "LOW": "Notification LOW SAJA",
    "MIDDLE": "Notification MIDDLE + Vibration",
    "HIGH": "Notification HIGH + Vibration + Alarm",
}


class SensorService:
    def __init__(
        self,
        max_host,
        max_port,
        sensor_host,
        sensor_port,
        category=None,
        serial=None,
        baud=115200,
    ):
        self.max_host = max_host
        self.max_port = int(max_port)
        self.max = SimpleUDPClient(self.max_host, self.max_port)

        self.sensor_host = sensor_host
        self.sensor_port = int(sensor_port)
        self.serial = serial
        self.baud = baud

        self._lock = threading.Lock()
        self.pending = deque()

        self.sensor_active = False
        self.active_response = None

        self._loop_stop = threading.Event()
        self._loop_thread = None

    @staticmethod
    def _validate_category(category):
        value = str(category).strip().upper()
        if value not in VALID_CATEGORIES:
            raise ValueError(f"Kategori sensor tidak valid: {value}")
        return value

    def enqueue_response(self, category, respondent="", row_number=None):
        category = self._validate_category(category)

        item = {
            "category": category,
            "respondent": respondent or "",
            "row_number": row_number,
        }

        with self._lock:
            self.pending.append(item)
            return len(self.pending)

    def _pop_next_response(self):
        with self._lock:
            if not self.pending:
                return None, 0

            item = self.pending.popleft()
            return item, len(self.pending)

    # ========================================================
    # MAX SOUND TRIGGERS - BENAR-BENAR TERPISAH
    # ========================================================

    def _send_low(self):
        self.max.send_message("/sound/notification_low", 1)
        print("MAX <- /sound/notification_low 1")
        print("SOUND -> Notification LOW SAJA")

    def _send_middle(self):
        self.max.send_message("/sound/notification_middle", 1)
        self.max.send_message("/sound/vibration", 1)

        print("MAX <- /sound/notification_middle 1")
        print("MAX <- /sound/vibration 1")
        print("SOUND -> Notification MIDDLE + Vibration")

    def _send_high(self):
        self.max.send_message("/sound/notification_high", 1)
        self.max.send_message("/sound/vibration", 1)
        self.max.send_message("/sound/alarm", 1)

        print("MAX <- /sound/notification_high 1")
        print("MAX <- /sound/vibration 1")
        print("MAX <- /sound/alarm 1")
        print("SOUND -> Notification HIGH + Vibration + Alarm")

    def _trigger_category(self, category, loop_number):
        print("")
        print(f"TRIGGER #{loop_number} | CATEGORY = {category}")

        if category == "LOW":
            self._send_low()
        elif category == "MIDDLE":
            self._send_middle()
        elif category == "HIGH":
            self._send_high()

    def _send_stop(self):
        self.max.send_message("/sound/stop", 1)
        print("MAX <- /sound/stop 1")
        print("SOUND -> STOP ALL")

    # ========================================================
    # LOOP
    # ========================================================

    def _sound_loop(self, category, respondent):
        min_seconds, max_seconds = LOOP_INTERVALS[category]
        loop_number = 2

        while not self._loop_stop.is_set():
            delay = random.uniform(min_seconds, max_seconds)

            print(
                f"NEXT {category} TRIGGER -> {delay:.1f}s | "
                f"{respondent or '(tanpa nama)'}"
            )

            if self._loop_stop.wait(delay):
                break

            with self._lock:
                still_active = self.sensor_active
                active = self.active_response
                same_response = (
                    active is not None
                    and active.get("category") == category
                )

            if not still_active or not same_response:
                break

            self._trigger_category(category, loop_number)
            loop_number += 1

    def _start_loop(self, category, respondent):
        self._loop_stop.set()

        old_thread = self._loop_thread
        if (
            old_thread is not None
            and old_thread.is_alive()
            and old_thread is not threading.current_thread()
        ):
            old_thread.join(timeout=1.0)

        self._loop_stop = threading.Event()

        self._loop_thread = threading.Thread(
            target=self._sound_loop,
            args=(category, respondent),
            name=f"sound-loop-{category.lower()}",
            daemon=True,
        )
        self._loop_thread.start()

    # ========================================================
    # SENSOR
    # ========================================================

    def activate(self):
        with self._lock:
            if self.sensor_active:
                return
            self.sensor_active = True

        item, pending_count = self._pop_next_response()

        if item is None:
            print("")
            print("======================================")
            print("SENSOR NEAR")
            print("QUEUE KOSONG")
            print("TIDAK ADA SOUND")
            print("======================================")
            self._send_stop()
            return

        with self._lock:
            self.active_response = item

        category = item["category"]
        respondent = item.get("respondent", "") or "(tanpa nama)"
        row_number = item.get("row_number")
        min_seconds, max_seconds = LOOP_INTERVALS[category]

        print("")
        print("======================================")
        print("HANYA 1 RESPONDEN AKTIF")
        print("======================================")
        print(f"NAMA          : {respondent}")

        if row_number not in (None, ""):
            print(f"FORM ROW      : {row_number}")

        print(f"KATEGORI      : {category}")
        print(f"SOUND         : {SOUND_LABELS[category]}")
        print(
            f"LOOP          : random "
            f"{min_seconds:.0f}-{max_seconds:.0f} detik"
        )
        print(f"SISA QUEUE    : {pending_count}")
        print("======================================")

        # Trigger pertama langsung.
        self._trigger_category(category, 1)

        # Loop kategori YANG SAMA selama sensor masih NEAR.
        self._start_loop(category, respondent)

    def deactivate(self):
        with self._lock:
            if not self.sensor_active:
                return

            self.sensor_active = False
            self.active_response = None

        self._loop_stop.set()

        thread = self._loop_thread
        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=1.0)

        print("")
        print("======================================")
        print("SENSOR FAR")
        print("STOP RESPONDEN AKTIF")
        print("SIAP RESPONDEN BERIKUTNYA")
        print("======================================")

        self._send_stop()

    @staticmethod
    def _is_near(value):
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            text = value.strip().lower()

            if text in {"near", "active", "on", "true"}:
                return True
            if text in {"far", "inactive", "off", "false"}:
                return False

            try:
                value = float(text)
            except ValueError:
                return None

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None

        return numeric <= 0.5

    def handle_proximity(self, address, *args):
        if not args:
            return

        value = args[0]
        print(f"SENSOR OSC -> {address} | value={value}")

        near = self._is_near(value)

        if near is None:
            print(f"Value proximity tidak dikenali: {value}")
            return

        if near:
            self.activate()
        else:
            self.deactivate()

    @staticmethod
    def debug_sensor(address, *args):
        print(f"OSC SENSOR RAW -> {address} {args}")

    def run(self):
        print("")
        print("======================================")
        print("SENSOR SERVICE - ONE RESPONDENT ONLY")
        print("======================================")
        print(f"Listen sensor OSC : {self.sensor_host}:{self.sensor_port}")
        print("LOW    -> Notification LOW SAJA")
        print("MIDDLE -> Notification MIDDLE + Vibration")
        print("HIGH   -> Notification HIGH + Vibration + Alarm")
        print("1x NEAR = hanya 1 responden")
        print("FAR     = STOP + responden berikutnya")
        print("======================================")

        self._send_stop()

        dispatcher = Dispatcher()

        for address in (
            "/proximity",
            "/sensor/proximity",
            "/sensors/proximity",
            "/proximity/value",
        ):
            dispatcher.map(address, self.handle_proximity)

        dispatcher.set_default_handler(self.debug_sensor)

        server = ThreadingOSCUDPServer(
            (self.sensor_host, self.sensor_port),
            dispatcher,
        )

        print(
            f"\n✓ Sensor OSC server aktif pada "
            f"{self.sensor_host}:{self.sensor_port}"
        )

        try:
            server.serve_forever()
        finally:
            self._loop_stop.set()
            self._send_stop()
            server.shutdown()
            server.server_close()
            print("Max -> STOP")
