import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

from form_classifier.sources import DEFAULT_COLUMNS, open_sheet, read_config
from form_classifier.storage import Database


LOG = logging.getLogger("form-classifier")


# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAX_PATCH = (
    BASE_DIR
    / "Maxpatch"
    / "What are you listening_max.maxpat"
)
# ============================================================
# MAX/MSP
# ============================================================

def open_max_patch():
    """Open the Max/MSP patch automatically."""

    if not MAX_PATCH.exists():
        raise FileNotFoundError(
            f"Max patch tidak ditemukan:\n{MAX_PATCH}"
        )

    LOG.info("Opening Max patch...")
    LOG.info("Patch: %s", MAX_PATCH)

    result = subprocess.run(
        [
            "open",
            "-a",
            "Max",
            str(MAX_PATCH),
        ],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Gagal membuka Max/MSP."
        )

    LOG.info("Menunggu Max/MSP siap...")

    time.sleep(4)

    LOG.info("Max patch opened.")


# ============================================================
# CLASSIFICATION LOG
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
        c["LOW"],
        c["MIDDLE"],
        c["HIGH"],
        c["REVIEW"],
    )


# ============================================================
# MAIN
# ============================================================

def main(argv=None):

    parser = argparse.ArgumentParser(
        description=(
            "Google Form classification + "
            "Sensor + Max/MSP"
        )
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------------
    # WATCH
    # --------------------------------------------------------

    live = sub.add_parser(
        "watch",
        help="Pantau Google Sheets dan kirim data ke Max/MSP",
    )

    live.add_argument(
        "--config",
        default="config.json",
    )

    live.add_argument(
        "--once",
        action="store_true",
        help="Sinkronisasi satu kali kemudian berhenti",
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report = sub.add_parser(
        "report",
        help="Tampilkan klasifikasi terakhir",
    )

    report.add_argument(
        "--config",
        default="config.json",
    )

    report.add_argument(
        "--detail",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    report.add_argument(
        "--row",
        type=int,
        help="Pilih responden berdasarkan nomor baris Sheet",
    )

    # --------------------------------------------------------
    # OSC TEST
    # --------------------------------------------------------

    osc_test = sub.add_parser(
        "osc-test",
        help="Buka Max dan test LOW/MIDDLE/HIGH",
    )

    osc_test.add_argument(
        "--host",
        default="127.0.0.1",
    )

    osc_test.add_argument(
        "--port",
        type=int,
        default=8000,
    )

    # --------------------------------------------------------
    # SENSOR
    # --------------------------------------------------------

    sensor = sub.add_parser(
        "sensor",
        help="Jalankan sensor dan kirim trigger ke Max/MSP",
    )

    sensor.add_argument(
        "--max-host",
        default="127.0.0.1",
    )

    sensor.add_argument(
        "--max-port",
        type=int,
        default=8000,
    )

    sensor.add_argument(
        "--sensor-host",
        default="127.0.0.1",
    )

    sensor.add_argument(
        "--sensor-port",
        type=int,
        default=8001,
    )

    sensor.add_argument(
        "--category",
        choices=[
            "LOW",
            "MIDDLE",
            "HIGH",
            "REVIEW",
        ],
        default="LOW",
    )

    sensor.add_argument(
        "--serial",
        help=(
            "Port serial hardware, contoh "
            "/dev/cu.usbmodemXXXX"
        ),
    )

    sensor.add_argument(
        "--baud",
        type=int,
        default=115200,
    )

    # --------------------------------------------------------
    # IMPORT JSON
    # --------------------------------------------------------

    offline = sub.add_parser(
        "import-json",
        help="Test menggunakan snapshot JSON lokal",
    )

    offline.add_argument("file")

    offline.add_argument(
        "--database",
        default="data/sample.sqlite3",
    )

    offline.add_argument(
        "--output",
        default="output/sample",
    )


    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    db = None
    sheet = None

    try:

        # ====================================================
        # IMPORT JSON
        # ====================================================

        if args.command == "import-json":

            snapshot = json.loads(
                Path(args.file).read_text(
                    encoding="utf-8"
                )
            )

            source = snapshot["source"]

            db = Database(
                args.database
            )

            changes = db.sync(
                source,
                snapshot["rows"],
                snapshot.get(
                    "columns",
                    DEFAULT_COLUMNS,
                ),
            )

            summary = db.export(
                source,
                args.output,
            )

            show(
                changes,
                summary,
            )

            return 0


        # ====================================================
        # OSC TEST
        # ====================================================

        if args.command == "osc-test":

            open_max_patch()

            from form_classifier.osc import MaxOSC

            sender = MaxOSC(
                args.host,
                args.port,
            )

            LOG.info(
                "Testing Max/MSP OSC %s:%s",
                args.host,
                args.port,
            )

            for category in (
                "LOW",
                "MIDDLE",
                "HIGH",
            ):

                LOG.info(
                    "Mengirim kategori: %s",
                    category,
                )

                values = sender.send_category(
                    category,
                    0,
                    new_response=False,
                )

                LOG.info(
                    "OSC terkirim: %s",
                    values.get(
                        "/screen_time/category",
                        category,
                    ),
                )

                # beri waktu supaya tiap mode terdengar
                time.sleep(5)

            LOG.info(
                "OSC test selesai."
            )

            return 0


        # ====================================================
        # SENSOR
        # ====================================================

        if args.command == "sensor":

            # buka Max otomatis
            open_max_patch()

            from form_classifier.sensor_service import (
                SensorService,
            )

            LOG.info(
                "======================================"
            )

            LOG.info(
                "SENSOR + MAX/MSP"
            )

            LOG.info(
                "======================================"
            )

            LOG.info(
                "Max/MSP      : %s:%s",
                args.max_host,
                args.max_port,
            )

            LOG.info(
                "Sensor OSC   : %s:%s",
                args.sensor_host,
                args.sensor_port,
            )

            LOG.info(
                "Kategori     : %s",
                args.category,
            )

            LOG.info(
                "Ctrl+C untuk berhenti."
            )

            service = SensorService(
                args.max_host,
                args.max_port,
                args.sensor_host,
                args.sensor_port,
                args.category,
                args.serial,
                args.baud,
            )

            service.run()

            return 0


        # ====================================================
        # CONFIG
        # ====================================================

        config = read_config(
            args.config
        )


        # ====================================================
        # REPORT
        # ====================================================

        if args.command == "report":

            report_file = (
                Path(config["output_dir"])
                / "classification.json"
            )

            report_data = json.loads(
                report_file.read_text(
                    encoding="utf-8"
                )
            )

            summary = report_data["summary"]

            print(
                "KLASIFIKASI GOOGLE FORM | "
                + summary["generated_at"]
            )

            print(
                "Total:",
                summary["total"],
                "|",
                summary["categories"],
            )

            print(
                f"{'BARIS':<6} "
                f"{'NAMA / INISIAL':<28} "
                f"{'JAWABAN':<14} "
                "KATEGORI"
            )

            selected = [
                r
                for r in report_data["responses"]
                if args.row is None
                or r["row_number"] == args.row
            ]

            if not selected:
                raise ValueError(
                    "Tidak ada responden sesuai nomor baris."
                )

            for row in selected:

                print(
                    f"{row['row_number']:<6} "
                    f"{row['name']:<28} "
                    f"{row['screen_time_raw']:<14} "
                    f"{row['category']}"
                )

            return 0


        # ====================================================
        # WATCH GOOGLE FORM
        # ====================================================

        if args.command == "watch":

            # buka Max bila OSC digunakan
            if config.get(
                "osc_enabled",
                False,
            ):
                open_max_patch()

            sheet = open_sheet(
                config
            )

            db = Database(
                config["database"]
            )

            osc = None

            if config.get(
                "osc_enabled",
                False,
            ):

                from form_classifier.osc import MaxOSC

                osc = MaxOSC(
                    config["max_host"],
                    config["max_port"],
                )

                LOG.info(
                    "OSC Max/MSP aktif di %s:%s",
                    config["max_host"],
                    config["max_port"],
                )

            LOG.info(
                "Memantau Google Sheets setiap %ss.",
                config["poll_seconds"],
            )

            LOG.info(
                "Ctrl+C untuk berhenti."
            )

            failures = 0

            while True:

                try:

                    rows = sheet.read()

                    changes = db.sync(
                        sheet.identity,
                        rows,
                        config["columns"],
                    )

                    summary = db.export(
                        sheet.identity,
                        config["output_dir"],
                    )

                    # ----------------------------------------
                    # DATA FORM BARU → MAX/MSP
                    # ----------------------------------------

                    if osc and (
                        changes["new"]
                        or changes["updated"]
                    ):

                        try:

                            category = (
                                changes.get(
                                    "last_category"
                                )
                                or summary[
                                    "latest_response"
                                ]["category"]
                            )

                            LOG.info(
                                "Data Form → %s",
                                category,
                            )

                            osc.send_category(
                                category,
                                summary["total"],
                                new_response=bool(
                                    changes["new"]
                                ),
                            )

                        except OSError as error:

                            LOG.warning(
                                "OSC tidak tersambung ke "
                                "Max/MSP: %s",
                                error,
                            )

                    show(
                        changes,
                        summary,
                    )

                    failures = 0

                    if args.once:
                        return 0

                except Exception as error:

                    failures += 1

                    LOG.error(
                        "Sinkronisasi gagal: %s",
                        error,
                    )

                    if args.once:
                        raise

                time.sleep(
                    min(
                        60,
                        config["poll_seconds"]
                        * (
                            2
                            ** min(
                                failures,
                                5,
                            )
                        ),
                    )
                )

    except KeyboardInterrupt:

        LOG.info(
            "Sistem dihentikan."
        )

        return 0

    except Exception as error:

        LOG.error(
            "%s: %s",
            type(error).__name__,
            error,
        )

        return 1

    finally:

        if db is not None:
            db.close()

        if sheet is not None:
            sheet.close()


if __name__ == "__main__":
    sys.exit(main())