# Sistem sensor Python -> Max/MSP

Sensor bridge dijalankan dengan:

```sh
python3 main.py sensor --category HIGH
```

Untuk Arduino/ESP32 melalui USB serial:

```sh
python3 main.py sensor --category HIGH --serial /dev/cu.usbmodemXXXX --baud 115200
```

Board mengirim satu baris setiap pembacaan, misalnya:

```json
{"proximity": 0.73, "touch": 1, "held": 0}
```

Format CSV `0.73,1,0` juga diterima. Nilai proximity harus sudah dinormalisasi 0.0 (jauh) sampai 1.0 (sangat dekat). Python melakukan validasi dan membatasi nilai ke rentang tersebut.

Default port:

- Python menerima sensor di UDP `127.0.0.1:8001`.
- Python mengirim kontrol dan trigger ke Max/MSP di UDP `127.0.0.1:8000`.

Python menerima pesan berikut dari aplikasi sensor/ponsel/simulator lain:

```text
/sensor/proximity 0.0..1.0
/sensor/touch 0|1
/sensor/held 0|1
/sensor/category LOW|MIDDLE|HIGH|REVIEW
```

Contoh tes dari Max atau aplikasi OSC lain:

```text
/sensor/category HIGH
/sensor/proximity 0.85
/sensor/touch 1
```

Setelah proximity + touch bertahan 0,6 detik, Python masuk `HELD`. Python mengirim state dan parameter ke Max setiap 100 ms:

```text
/proximity
/interaction/state
/touch
/held
/risk
/notification/intensity
/vibration/intensity
/alarm/intensity
/news/negative_mix
/news/positive_mix
/news/intensity
/news/density
/audio/master_intensity
```

Trigger audio dikirim sebagai pulsa `1`:

```text
/notification/trigger 1
/vibration/trigger 1
/alarm/trigger 1
```

Policy otomatis:

- LOW: notification.
- MIDDLE: notification + vibration.
- HIGH: notification + vibration + alarm.
- Proximity `VERY_NEAR` mempercepat notification.
- HELD memicu seluruh jenis yang diizinkan kategori.
- Proximity mengendalikan risk, news mix, intensity, dan density.

Max/MSP harus tetap melakukan playback, gain, crossfade, EQ, reverb, delay, granular, glitch, dan output speaker. Python hanya mengirim angka, simbol, dan trigger. Patching audio tidak dipindahkan ke Python.

Sensor fisik belum dapat dibaca Python tanpa sumber hardware. Pilih satu input: serial Arduino/ESP32 dengan opsi `--serial`, atau perangkat lain yang mengirim alamat OSC `/sensor/...` ke port 8001. UI ponsel belum diperlukan.

Jika sensor berada di komputer lain, jalankan Python dengan `--sensor-host 0.0.0.0` dan kirim ke alamat LAN komputer Python. Jika Max berada di komputer lain, isi `--max-host` dengan alamat LAN komputer Max.
