"""Google Form classification + Sensor + Max/MSP.

Alur utama:
- watch       : sinkronisasi Google Form/Sheets -> classification.json
- sensor-test : ambil kategori Form terbaru -> simulasi sensor ON -> Max/MSP
- sensor      : jalankan SensorService menggunakan kategori Form terbaru
- osc-test    : tes routing OSC /screen_time ke Max/MSP
- report      : tampilkan hasil klasifikasi tersimpan
- import-json : impor snapshot lokal
"""

import argparse
import importlib.util
import json
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

from form_classifier.sources import DEFAULT_COLUMNS, open_sheet, read_config
from form_classifier.storage import Database


LOG = logging.getLogger("form-classifier")

BASE_DIR = Path(__file__).resolve().parent
MAX_PATCH = BASE_DIR / "Maxpatch" / "What are you listening_max.maxpat"
VALID_SOUND_CATEGORIES = {"LOW", "MIDDLE", "HIGH"}


def load_proximity_bridge_class():
    """Load ProximityOSCBridge dari sensor.py yang satu folder dengan main.py."""
    sensor_file = BASE_DIR / "sensor.py"

    if not sensor_file.exists():
        raise FileNotFoundError(
            "sensor.py tidak ditemukan:\n"
            f"{sensor_file}\n"
            "Letakkan sensor.py di folder yang sama dengan main.py."
        )

    spec = importlib.util.spec_from_file_location(
        "local_proximity_sensor",
        sensor_file,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Gagal memuat module sensor dari: {sensor_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    bridge_class = getattr(module, "ProximityOSCBridge", None)
    if bridge_class is None:
        raise ImportError(
            "Class ProximityOSCBridge tidak ditemukan di sensor.py"
        )

    return bridge_class


# ============================================================
# MAX/MSP HELPERS
# ============================================================

def open_max_patch(wait_seconds=4.0):
    """Buka patch Max/MSP yang benar dan tunggu sampai siap."""
    if not MAX_PATCH.exists():
        raise FileNotFoundError(
            "Max patch tidak ditemukan:\n"
            f"{MAX_PATCH}\n"
            "Pastikan file berada di folder Maxpatch dan namanya persis "
            "'What are you listening_max.maxpat'."
        )

    LOG.info("Opening Max patch: %s", MAX_PATCH)

    result = subprocess.run(
        ["open", "-a", "Max", str(MAX_PATCH)],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError("Gagal membuka Max/MSP")

    LOG.info("Menunggu Max siap %.1f detik...", wait_seconds)
    time.sleep(wait_seconds)
    LOG.info("Max patch siap.")


def send_screen_time_state(host, port, state):
    """Kirim kategori ke Max/MSP.

    LOW    -> /screen_time Low
    MIDDLE -> /screen_time Middle
    HIGH   -> /screen_time High
    STOP   -> /screen_time Stop

    Max:
      [udpreceive 8002]
              |
      [route /screen_time]
              |
      [route Low Middle High Stop]
    """
    from pythonosc.udp_client import SimpleUDPClient

    mapping = {
        "LOW": "Low",
        "MIDDLE": "Middle",
        "HIGH": "High",
        "STOP": "Stop",
    }

    key = str(state).strip().upper()
    if key not in mapping:
        raise ValueError(f"State OSC tidak valid: {state}")

    value = mapping[key]
    client = SimpleUDPClient(host, port)
    client.send_message("/screen_time", value)
    LOG.info("OSC -> /screen_time %s -> %s:%s", value, host, port)
    return value


# ============================================================
# DATA / REPORT HELPERS
# ============================================================

def show(changes, summary):
    c = summary["categories"]
    LOG.info(
        "Baru=%s diperbarui=%s dihapus=%s tetap=%s | "
        "Total=%s LOW=%s MIDDLE=%s HIGH=%s REVIEW=%s",
        changes["new"],
        changes["updated"],
        changes["removed"],
        changes["unchanged"],
        summary["total"],
        c.get("LOW", 0),
        c.get("MIDDLE", 0),
        c.get("HIGH", 0),
        c.get("REVIEW", 0),
    )


def report_path_from_config(config):
    return Path(config["output_dir"]) / "classification.json"


def load_report(config):
    report_file = report_path_from_config(config)
    if not report_file.exists():
        raise FileNotFoundError(
            f"Data klasifikasi belum tersedia: {report_file}\n"
            "Jalankan dulu: python3 main.py watch --once"
        )

    return json.loads(report_file.read_text(encoding="utf-8"))


def latest_category_from_report(report_data):
    """Ambil kategori responden terbaru secara defensif."""
    # Beberapa versi exporter menyimpan latest_response di summary.
    summary = report_data.get("summary", {})
    latest = summary.get("latest_response")

    # Beberapa versi dapat menyimpannya di top-level.
    if not latest:
        latest = report_data.get("latest_response")

    # Fallback: respons terakhir di list.
    if not latest:
        responses = report_data.get("responses", [])
        if responses:
            latest = responses[-1]

    if not latest:
        raise ValueError("Belum ada respons Google Form yang dapat digunakan.")

    category = str(latest.get("category", "")).strip().upper()
    if not category:
        raise ValueError("Respons terbaru tidak memiliki kategori.")

    return category, latest


def sync_form_once(config, log_summary=True):
    """Sinkronisasi Google Sheet satu kali dan simpan classification.json.

    log_summary=False dipakai oleh mode sensor agar terminal tidak dipenuhi
    baris "Baru=0 ... Total=..." setiap polling.
    """
    sheet = None
    db = None
    try:
        sheet = open_sheet(config)
        db = Database(config["database"])

        rows = sheet.read()
        changes = db.sync(sheet.identity, rows, config["columns"])
        summary = db.export(sheet.identity, config["output_dir"])

        if log_summary:
            show(changes, summary)

        return changes, summary
    finally:
        if db is not None:
            db.close()
        if sheet is not None:
            sheet.close()


def get_latest_form_category(config, refresh=True):
    """Ambil kategori Form terbaru; refresh Sheet dulu jika diminta.

    Jika refresh gagal tetapi cache classification.json tersedia, cache tetap
    dipakai agar tester masih dapat berjalan.
    """
    if refresh:
        try:
            LOG.info("Mengambil data Google Form terbaru...")
            sync_form_once(config, log_summary=True)
        except Exception as error:
            LOG.warning(
                "Refresh Google Form gagal (%s). Mencoba data tersimpan...",
                error,
            )

    report_data = load_report(config)
    category, latest = latest_category_from_report(report_data)
    return category, latest


# ============================================================
# CLI
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        description="Google Form + Sensor + Max/MSP"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # WATCH
    live = sub.add_parser(
        "watch",
        help="Pantau Google Sheets dan simpan klasifikasi terbaru",
    )
    live.add_argument("--config", default="config.json")
    live.add_argument(
        "--once",
        action="store_true",
        help="Sinkronisasi satu kali lalu berhenti",
    )

    # REPORT
    report = sub.add_parser(
        "report",
        help="Tampilkan klasifikasi terakhir",
    )
    report.add_argument("--config", default="config.json")
    report.add_argument("--detail", action="store_true", help=argparse.SUPPRESS)
    report.add_argument("--row", type=int)

    # OSC TEST
    osc_test = sub.add_parser(
        "osc-test",
        help="Tes routing OSC Python -> Max/MSP",
    )
    osc_test.add_argument("--host", default="127.0.0.1")
    osc_test.add_argument("--port", type=int, default=8002)
    osc_test.add_argument(
        "--hold",
        type=float,
        default=3.0,
        help="Jeda antar LOW/MIDDLE/HIGH (default 3 detik)",
    )
    osc_test.add_argument(
        "--no-open-max",
        action="store_true",
        help="Jangan buka patch Max otomatis",
    )

    # SENSOR REAL
    sensor = sub.add_parser(
        "sensor",
        help="Jalankan sensor menggunakan kategori Google Form terbaru",
    )
    sensor.add_argument("--config", default="config.json")
    sensor.add_argument("--max-host", default="127.0.0.1")
    sensor.add_argument("--max-port", type=int, default=8002)
    sensor.add_argument("--sensor-host", default="0.0.0.0")
    sensor.add_argument("--sensor-port", type=int, default=8001)
    sensor.add_argument(
        "--category",
        choices=["LOW", "MIDDLE", "HIGH", "REVIEW"],
        default=None,
        help="Override manual kategori. Jika kosong, ambil dari Google Form terbaru.",
    )
    sensor.add_argument("--serial")
    sensor.add_argument("--baud", type=int, default=115200)
    sensor.add_argument(
        "--cached",
        action="store_true",
        help="Jangan refresh Google Form; gunakan classification.json tersimpan",
    )
    sensor.add_argument(
        "--no-open-max",
        action="store_true",
        help="Jangan buka patch Max otomatis",
    )

    # SENSOR TEST (SIMULASI SENSOR ON)
    sensor_test = sub.add_parser(
        "sensor-test",
        help="Data Form terbaru -> simulasi sensor ON -> Max/MSP",
    )
    sensor_test.add_argument("--config", default="config.json")
    sensor_test.add_argument("--max-host", default="127.0.0.1")
    sensor_test.add_argument("--max-port", type=int, default=8002)
    sensor_test.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Durasi sensor dianggap aktif (default 30 detik)",
    )
    sensor_test.add_argument(
        "--cached",
        action="store_true",
        help="Jangan refresh Google Form; gunakan classification.json tersimpan",
    )
    sensor_test.add_argument(
        "--no-open-max",
        action="store_true",
        help="Jangan buka patch Max otomatis",
    )

    # IMPORT JSON
    offline = sub.add_parser(
        "import-json",
        help="Import snapshot JSON lokal",
    )
    offline.add_argument("file")
    offline.add_argument("--database", default="data/sample.sqlite3")
    offline.add_argument("--output", default="output/sample")

    return parser


# ============================================================
# COMMAND HANDLERS
# ============================================================

def handle_import_json(args):
    snapshot = json.loads(Path(args.file).read_text(encoding="utf-8"))
    source = snapshot["source"]

    db = Database(args.database)
    try:
        changes = db.sync(
            source,
            snapshot["rows"],
            snapshot.get("columns", DEFAULT_COLUMNS),
        )
        summary = db.export(source, args.output)
        show(changes, summary)
    finally:
        db.close()

    return 0


def handle_osc_test(args):
    if not args.no_open_max:
        open_max_patch()

    for category in ("LOW", "MIDDLE", "HIGH"):
        LOG.info("OSC TEST -> %s", category)
        send_screen_time_state(args.host, args.port, category)
        time.sleep(max(0.0, args.hold))

    LOG.info("OSC TEST -> STOP")
    send_screen_time_state(args.host, args.port, "STOP")
    LOG.info("OSC test selesai.")
    return 0


def handle_report(args):
    config = read_config(args.config)
    report_data = load_report(config)
    summary = report_data["summary"]

    print("KLASIFIKASI GOOGLE FORM | " + summary["generated_at"])
    print("Total:", summary["total"], "|", summary["categories"])
    print(f"{'BARIS':<6} {'NAMA / INISIAL':<28} {'JAWABAN':<14} KATEGORI")

    responses = report_data.get("responses", [])
    selected = [
        row
        for row in responses
        if args.row is None or row.get("row_number") == args.row
    ]

    if not selected:
        raise ValueError("Tidak ada responden yang sesuai.")

    for row in selected:
        print(
            f"{row.get('row_number', ''):<6} "
            f"{str(row.get('name', '')):<28} "
            f"{str(row.get('screen_time_raw', '')):<14} "
            f"{row.get('category', '')}"
        )

    return 0


def handle_watch(args):
    config = read_config(args.config)
    sheet = None
    db = None

    try:
        sheet = open_sheet(config)
        db = Database(config["database"])

        LOG.info("Memantau Google Sheets setiap %ss.", config["poll_seconds"])
        LOG.info("Kategori Form disimpan untuk digunakan oleh sensor.")

        failures = 0

        while True:
            try:
                rows = sheet.read()
                changes = db.sync(sheet.identity, rows, config["columns"])
                summary = db.export(sheet.identity, config["output_dir"])
                show(changes, summary)

                # Baca kembali report agar kompatibel dengan bentuk exporter berbeda.
                try:
                    report_data = load_report(config)
                    category, latest = latest_category_from_report(report_data)
                    LOG.info(
                        "DATA FORM TERBARU -> %s%s",
                        category,
                        f" | {latest.get('name', '')}" if latest.get("name") else "",
                    )
                except Exception as error:
                    LOG.warning("Belum dapat membaca data terbaru: %s", error)

                failures = 0
                if args.once:
                    return 0

            except Exception as error:
                failures += 1
                LOG.error("Sinkronisasi gagal: %s", error)
                if args.once:
                    raise

            time.sleep(
                min(
                    60,
                    config["poll_seconds"] * (2 ** min(failures, 5)),
                )
            )

    finally:
        if db is not None:
            db.close()
        if sheet is not None:
            sheet.close()


def handle_sensor_test(args):
    """Tester end-to-end: Form -> kategori -> simulasi sensor -> Max."""
    config = read_config(args.config)
    category, latest = get_latest_form_category(
        config,
        refresh=not args.cached,
    )

    LOG.info("======================================")
    LOG.info("TEST DATA FORM + SENSOR + MAX/MSP")
    LOG.info("======================================")
    LOG.info("DATA FORM TERBARU -> %s", category)

    if latest.get("name"):
        LOG.info("RESPONDEN TERBARU -> %s", latest.get("name"))

    if not args.no_open_max:
        open_max_patch()

    if category == "REVIEW":
        LOG.warning("Kategori REVIEW tidak memiliki mode sound. Mengirim STOP.")
        send_screen_time_state(args.max_host, args.max_port, "STOP")
        return 0

    if category not in VALID_SOUND_CATEGORIES:
        raise ValueError(f"Kategori Form tidak dapat digunakan untuk sound: {category}")

    LOG.info("SENSOR TEST = ACTIVE")
    send_screen_time_state(args.max_host, args.max_port, category)

    LOG.info(
        "Mode %s aktif selama %.1f detik. Max yang melakukan looping audio.",
        category,
        args.duration,
    )

    try:
        time.sleep(max(0.0, args.duration))
    finally:
        LOG.info("SENSOR TEST = INACTIVE")
        send_screen_time_state(args.max_host, args.max_port, "STOP")
        LOG.info("STOP dikirim ke Max/MSP.")

    return 0


def handle_sensor(args):
    """Google Form -> Max/MSP, dikontrol proximity sensor dari HP Android.

    Android mengirim OSC ke Python port 8001:
      /proximity 0  -> NEAR
      /proximity 5  -> FAR

    Python meneruskan nilai yang sama ke Max/MSP port 8002:
      /proximity 0  -> Max mendeteksi NEAR
      /proximity 5  -> Max mendeteksi FAR

    Mode final:
      Google Form -> Max berjalan independen dari proximity.
      NEAR/FAR hanya diteruskan ke Max sebagai /proximity.
      Sensor HP tidak lagi memblokir queue Google Form.

    Mapping sound TIDAK berubah:
      LOW    -> Notification LOW saja
      MIDDLE -> Notification MIDDLE + Vibration
      HIGH   -> Notification HIGH + Vibration + Alarm

    Urutan responden tetap mengikuti Google Form dan setelah responden
    terakhir selesai akan kembali ke PLAY #1.
    """
    import queue
    from pythonosc.udp_client import SimpleUDPClient
    ProximityOSCBridge = load_proximity_bridge_class()

    GAP_SECONDS = 60.0
    NEAR_THRESHOLD = 1.0  # app Android: 0 = NEAR, 5 = FAR

    config = read_config(args.config)

    if not args.cached:
        LOG.info("Sinkronisasi awal Google Form...")
        try:
            sync_form_once(config, log_summary=False)
        except Exception as error:
            LOG.warning(
                "Sinkronisasi awal Google Form gagal (%s). "
                "Mencoba classification.json tersimpan...",
                error,
            )

    report_data = load_report(config)
    responses = report_data.get("responses", [])

    if not responses:
        raise ValueError("Belum ada respons Google Form.")

    def response_key(row):
        row_number = row.get("row_number")
        if row_number not in (None, ""):
            return f"row:{row_number}"

        timestamp = (
            row.get("timestamp")
            or row.get("submitted_at")
            or row.get("created_at")
            or ""
        )
        return json.dumps(
            [
                timestamp,
                row.get("name", ""),
                row.get("screen_time_raw", ""),
                row.get("category", ""),
            ],
            ensure_ascii=False,
            default=str,
        )

    def sort_rows(rows):
        def key(row):
            try:
                return (0, int(row.get("row_number")))
            except (TypeError, ValueError):
                return (
                    1,
                    str(
                        row.get("timestamp")
                        or row.get("submitted_at")
                        or row.get("created_at")
                        or ""
                    ),
                )
        return sorted(rows, key=key)

    if not args.no_open_max:
        open_max_patch()

    client = SimpleUDPClient(args.max_host, args.max_port)

    sound_labels = {
        "LOW": "Notification LOW SAJA",
        "MIDDLE": "Notification MIDDLE + Vibration",
        "HIGH": "Notification HIGH + Vibration + Alarm",
    }

    def send_stop():
        client.send_message("/screen_time", "Stop")
        LOG.info("MAX <- /screen_time Stop")

    def trigger_category(category):
        osc_value = {
            "LOW": "Low",
            "MIDDLE": "Middle",
            "HIGH": "High",
        }[category]

        client.send_message("/screen_time", osc_value)
        LOG.info("MAX <- /screen_time %s", osc_value)

    play_queue = queue.Queue()
    stop_event = threading.Event()
    seen_responses = set()

    # ============================================================
    # PROXIMITY OSC SERVER: HP -> sensor.py :8001 -> MAX :8002
    # ============================================================
    def on_proximity_state(value, is_near):
        """Status proximity dari sensor.py. Form playback tetap independen."""
        LOG.info("")
        LOG.info(
            ">>> HP PROXIMITY = %s | raw=%.3f",
            "NEAR" if is_near else "FAR",
            value,
        )
        LOG.info(
            ">>> MAX PROXIMITY = %s | /proximity %.3f",
            "NEAR" if is_near else "FAR",
            value,
        )
        LOG.info(">>> FORM PLAYBACK TETAP BERJALAN INDEPENDEN")

    proximity_bridge = ProximityOSCBridge(
        sensor_host=args.sensor_host,
        sensor_port=args.sensor_port,
        max_host=args.max_host,
        max_port=args.max_port,
        near_threshold=NEAR_THRESHOLD,
        on_state=on_proximity_state,
    )
    proximity_bridge.start()

    # Data awal sesuai urutan row Form.
    loop_rows = []
    initial_count = 0

    for row in sort_rows(responses):
        key = response_key(row)
        seen_responses.add(key)

        category = str(row.get("category", "")).strip().upper()
        if category not in VALID_SOUND_CATEGORIES:
            continue

        play_queue.put(row)
        loop_rows.append(row)
        initial_count += 1

    LOG.info("")
    LOG.info("======================================")
    LOG.info("HP PROXIMITY + FORM -> MAX")
    LOG.info("======================================")
    LOG.info("RESPONDEN AWAL : %s", initial_count)
    LOG.info("SENSOR.PY OSC   : %s:%s", args.sensor_host, args.sensor_port)
    LOG.info("ANDROID -> PY   : /proximity 0 = NEAR | /proximity 5 = FAR")
    LOG.info(
        "PYTHON -> MAX   : /proximity 0..5 -> %s:%s",
        args.max_host,
        args.max_port,
    )
    LOG.info("STATUS FORM     : AKTIF LANGSUNG (tidak menunggu proximity HP)")
    LOG.info("JEDA RESPONDEN  : %.1f detik", GAP_SECONDS)
    LOG.info("LOW             : /screen_time Low -> Notification LOW saja")
    LOG.info("MIDDLE          : /screen_time Middle -> Notification + Vibration")
    LOG.info("HIGH            : /screen_time High -> Notification + Vibration + Alarm")
    LOG.info("LOOP            : PLAY terakhir selesai -> kembali PLAY #1")
    LOG.info("======================================")
    LOG.info("")

    send_stop()

    def playback_worker():
        sequence_number = 0

        while not stop_event.is_set():
            try:
                row = play_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                category = str(row.get("category", "")).strip().upper()
                if category not in VALID_SOUND_CATEGORIES:
                    continue

                sequence_number += 1

                name = str(row.get("name", "")).strip() or "(tanpa nama)"
                row_number = row.get("row_number")

                LOG.info("")
                LOG.info("======================================")
                LOG.info("PLAY #%s", sequence_number)
                LOG.info("NAMA     : %s", name)
                if row_number not in (None, ""):
                    LOG.info("FORM ROW : %s", row_number)
                LOG.info("CATEGORY : %s", category)
                LOG.info("SOUND    : %s", sound_labels[category])
                LOG.info("FORM     : SEND LANGSUNG KE MAX")
                LOG.info("======================================")

                trigger_category(category)

                # Pertahankan durasi existing: 60 detik per responden.
                # Proximity HP tidak menghentikan atau memblokir timer ini.
                if stop_event.wait(GAP_SECONDS):
                    break

                send_stop()

            finally:
                play_queue.task_done()

                # Sesudah responden terakhir kembali ke PLAY #1.
                if play_queue.empty() and loop_rows and not stop_event.is_set():
                    LOG.info("")
                    LOG.info("======================================")
                    LOG.info("PLAY TERAKHIR SELESAI -> KEMBALI KE PLAY #1")
                    LOG.info("======================================")

                    sequence_number = 0

                    for loop_row in loop_rows:
                        play_queue.put(loop_row)

    playback_thread = threading.Thread(
        target=playback_worker,
        name="form-proximity-playback",
        daemon=True,
    )
    playback_thread.start()

    def refresh_form_loop():
        interval = max(1.0, float(config.get("poll_seconds", 5)))
        LOG.info(
            "LIVE FORM aktif: cek respons baru setiap %.1f detik.",
            interval,
        )

        while not stop_event.wait(interval):
            try:
                if not args.cached:
                    sync_form_once(config, log_summary=False)

                current_report = load_report(config)
                current_rows = sort_rows(current_report.get("responses", []))

                for row in current_rows:
                    key = response_key(row)
                    if key in seen_responses:
                        continue

                    seen_responses.add(key)

                    category = str(row.get("category", "")).strip().upper()
                    if category not in VALID_SOUND_CATEGORIES:
                        continue

                    # Tambahkan data baru ke queue dan juga daftar loop berikutnya.
                    loop_rows.append(row)
                    play_queue.put(row)

                    LOG.info(
                        "FORM BARU MASUK QUEUE -> #%s %s | %s | pending=%s",
                        row.get("row_number"),
                        str(row.get("name", "")).strip() or "(tanpa nama)",
                        category,
                        play_queue.qsize(),
                    )

            except Exception as error:
                LOG.warning("Live Form gagal: %s", error)

    refresh_thread = threading.Thread(
        target=refresh_form_loop,
        name="form-live-refresh",
        daemon=True,
    )
    refresh_thread.start()

    try:
        while True:
            time.sleep(1.0)

    finally:
        stop_event.set()
        send_stop()

        proximity_bridge.stop()

        playback_thread.join(timeout=2.0)
        refresh_thread.join(timeout=2.0)
        return 0


# ============================================================
# MAIN
# ============================================================

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        if args.command == "import-json":
            return handle_import_json(args)

        if args.command == "osc-test":
            return handle_osc_test(args)

        if args.command == "report":
            return handle_report(args)

        if args.command == "watch":
            return handle_watch(args)

        if args.command == "sensor-test":
            return handle_sensor_test(args)

        if args.command == "sensor":
            return handle_sensor(args)

        parser.error(f"Command tidak dikenal: {args.command}")
        return 2

    except KeyboardInterrupt:
        LOG.info("Sistem dihentikan.")
        # Saat tester / sensor dihentikan, coba kirim STOP agar metro Max tidak terus berjalan.
        try:
            if hasattr(args, "max_host") and hasattr(args, "max_port"):
                send_screen_time_state(args.max_host, args.max_port, "STOP")
        except Exception:
            pass
        return 0

    except Exception as error:
        LOG.error("%s: %s", type(error).__name__, error)
    return 1


if __name__ == "__main__":
    sys.exit(main())
