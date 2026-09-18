# Klasifikasi respons Google Form di Python

Program terminal yang membaca respons Form dari Google Sheets, mengklasifikasikan screen time setiap responden, dan memperbarui hasil ketika respons bertambah. Tidak ada UI ponsel, sensor, atau pemutar audio di proyek ini.

## Langsung jalankan

Python 3.10 atau lebih baru. Setelah clone repository, siapkan konfigurasi untuk Sheet yang dapat dibaca melalui akses anonim:

```sh
git clone https://github.com/simarmatabryan/what-are-you-listening.git
cd what-are-you-listening
cp config.public.example.json config.json
```

Isi `spreadsheet_id` dan `gid` tab tujuan di `config.json`, lalu jalankan:

```sh
python3 main.py watch
```

Konfigurasi lokal yang sudah ada tidak perlu disalin ulang. `config.json`, kredensial, dan data responden tidak disertakan dalam repository. Untuk Sheet privat, gunakan petunjuk service account di bawah.

Program mengambil data setiap 5 detik. Biarkan terminal dan komputer tetap aktif. Ctrl+C menghentikan pemantauan; jalankan perintah yang sama untuk melanjutkan. Ini proses lokal, bukan layanan cloud atau tugas yang berjalan saat komputer mati.

Contoh output:

```text
Baru=30 diperbarui=0 dihapus=0 tetap=0 | Total=30 LOW=1 MIDDLE=9 HIGH=20 REVIEW=0
Baru=0 diperbarui=0 dihapus=0 tetap=30 | Total=30 LOW=1 MIDDLE=9 HIGH=20 REVIEW=0
```

Untuk satu kali pengambilan atau melihat hasil terakhir:

```sh
python3 main.py watch --once
python3 main.py report
```

Mode saat ini hanya memerlukan pustaka bawaan Python, jadi tidak perlu `pip install`. Mode service account opsional memerlukan `requirements.txt`.

## Aturan klasifikasi

| Jawaban Google Form | Kategori |
|---|---|
| `< 3 Jam` | LOW |
| `3 - 6 Jam` | MIDDLE |
| `> 6 Jam` | HIGH |
| Kosong atau format tidak dikenal | REVIEW |

Angka pasti juga didukung: <3 LOW; 3 sampai 6 inklusif MIDDLE; >6 HIGH, dengan validasi 0–24 jam. Spasi, huruf besar, koma desimal, dan variasi tanda dash ditangani.

Ini klasifikasi berbasis aturan screen time, bukan prediksi ML. Jawaban rentang **tidak diubah menjadi angka jam perkiraan**: `exact_hours` bernilai null. Umur, nama, dan aplikasi tidak menentukan kategori screen time. Hasil hanya berisi identitas dan kategori screen time; umur dan aplikasi tidak dianalisis. Kategori ini tidak menyimpulkan kondisi psikologis responden.

## Hasil yang disimpan

- `data/live.sqlite3`: respons, kategori, dan riwayat perubahan persisten.
- `output/live/classification.json`: satu snapshot berisi seluruh respons dan ringkasan konsisten.
- `output/live/summary.json`: total, jumlah/persentase kategori, respons pada baris terakhir, dan waktu sinkronisasi berhasil terakhir.

Gunakan `classification.json` sebagai sumber tunggal bila program lain membutuhkan ringkasan dan detail dari snapshot yang sama. Penulisan setiap file memakai temporary file + replace untuk mencegah pembacaan file setengah jadi. Kedua file terpisah tidak ditulis dalam satu transaksi bersama. Jika terjadi kegagalan jaringan, hasil sukses terakhir tetap tersedia; periksa `generated_at` untuk mengetahui kesegarannya.

Nama dan jawaban responden disimpan lokal dalam data/output; folder tersebut, kredensial, dan konfigurasi pribadi diabaikan Git. Database `sample` dan `live` dipisahkan agar uji sampel tidak menggandakan data live.

## Respons terus bertambah

1. Setiap polling membaca seluruh tab, termasuk baris tambahan.
2. Identitas penyimpanan adalah sumber Sheet + nomor baris. Dua respons dengan timestamp sama tetap disimpan masing-masing.
3. Baris yang belum tersimpan dicatat sebagai `new`.
4. Baris yang berubah dihitung ulang sebagai `updated`, bukan menambah total.
5. Baris yang sama dilewati sebagai `unchanged`, termasuk setelah restart.
6. Baris kosong/dihapus ditandai tidak aktif; data dan riwayat lamanya tidak dihapus dari database.
7. Header yang berubah ditolak sebelum sinkronisasi agar kolom yang salah tidak diam-diam diklasifikasikan.
8. Koneksi gagal dicoba ulang dengan jeda bertahap hingga 60 detik. Hasil lama tetap bisa dibaca.

Jalankan satu proses watcher untuk database/output yang sama. Untuk tab respons Form yang hanya bertambah, identitas per baris stabil. Jika tab disortir atau baris disisipkan, posisi yang berubah dicatat sebagai pembaruan; ini **bukan ID responden permanen**. Gunakan tab respons asli tanpa menyortirnya untuk riwayat respons yang stabil. Total/kategori akhir mengikuti snapshot tab saat itu. Jangan mengubah `mode`/`gid` pada database yang sama bila ingin menjaga kesinambungan identitas; gunakan database baru untuk sumber berbeda.

Polling ekspor Google mungkin mengalami jeda pembaruan/cache; 5 detik adalah interval pemeriksaan, bukan jaminan data Form muncul dalam 5 detik.

## Konfigurasi

`config.json` menentukan spreadsheet dan tab tujuan (`gid` dari URL Google Sheets). `columns` memakai indeks dari 0: Timestamp, Nama, Umur, Screen time, Apps. `expected_headers` menjaga susunan tersebut. Lokasi database/output diartikan relatif terhadap lokasi file konfigurasi.

Jika akses anonim Sheet nantinya ditutup, gunakan mode private tanpa membuat Sheet publik:

1. Aktifkan Google Sheets API pada Google Cloud.
2. Buat service account, unduh JSON kredensial ke `credentials.json`.
3. Bagikan Sheet sebagai Viewer kepada email service account.
4. Salin `config.example.json` ke `config-private.json` dan isi `spreadsheet_id`, `sheet_name`, serta `credentials_file`.
5. Pasang dependensi dan jalankan:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py watch --config config-private.json
```

Scope API hanya `spreadsheets.readonly`; program tidak menulis ke Form atau Sheet. `public_csv` tidak memerlukan kredensial. Verifikasi HTTPS tetap aktif; pada instalasi Python macOS tanpa CA bundle bawaan, program memakai CA sistem `/etc/ssl/cert.pem` jika tersedia.

## Pengujian

```sh
python3 -m unittest discover -s tests -v
```

Snapshot respons lokal tidak dibagikan ke GitHub. Pengujian mencakup label asli Form, batas kategori, format tidak valid, respons tambahan, restart tanpa duplikat, revisi, penghapusan, perlindungan header, ekspor, dan pemulihan setelah jaringan gagal. Sampel tambahan hanya dibuat di database tes, tidak dikirim ke Google Form.

Struktur utama: `main.py` untuk CLI; `form_classifier/classification.py` untuk aturan; `sources.py` untuk Google Sheets; `storage.py` untuk database dan output.

Sensor bridge Python → Max/MSP ada di [SENSOR_MAXMSP.md](SENSOR_MAXMSP.md). Jalankan `python3 main.py sensor --category HIGH` untuk menerima `/sensor/proximity`, `/sensor/touch`, dan `/sensor/held` di port 8001 lalu mengirim state, risk, mix, intensity, serta trigger audio ke Max di port 8000. Untuk hardware Arduino/ESP32 gunakan `--serial /dev/cu.usbmodemXXXX --baud 115200`. UI ponsel belum diperlukan.

Aplikasi Android native untuk Samsung A51 ada di folder `android/`. Build dari Android Studio, masukkan IP komputer Python, lalu tekan `Connect sensor`. Aplikasi mengirim sensor proximity/touch langsung ke Python melalui OSC UDP; aplikasi tidak memuat atau memainkan audio.

## Lihat kategori per responden

```sh
python3 main.py report
python3 main.py report --row 2
```

Tampilan hanya berisi baris, nama/inisial, jawaban durasi, dan LOW/MIDDLE/HIGH (atau REVIEW jika durasi tidak dikenal). Opsi lama `--detail` tetap diterima, tetapi menampilkan tabel sederhana yang sama. Hasil aktif JSON tidak lagi menyertakan kelompok umur atau jenis aplikasi. Riwayat database sebelumnya dipertahankan; polling pertama memperbarui format hasil lama tanpa menambah jumlah responden.

## OSC ke Max/MSP

Watcher mengirim kontrol OSC ke `127.0.0.1:8000` setiap ada respons baru atau baris yang berubah. Python hanya mengirim data klasifikasi: `/screen_time/category` (`Low`/`Middle`/`High`/`Review` untuk mengikuti route pada patch Max yang disediakan), `/screen_time/low`, `/screen_time/middle`, `/screen_time/high`, `/system/new_response 1`, dan `/system/response_count`.

Atur `osc_enabled`, `max_host`, dan `max_port` di `config.json`. Di Max/MSP, gunakan `udpreceive 8000`, decoder OSC, lalu route alamat tersebut. Jika Max/MSP belum berjalan, klasifikasi Google Sheets tetap berjalan dan data tetap disimpan; pesan OSC akan dicoba lagi saat ada respons/perubahan berikutnya. Python tidak memuat atau memainkan audio.

Untuk tes koneksi tanpa membaca Google Sheets:

```sh
python3 main.py osc-test
```

Max akan menerima urutan `Low`, `Middle`, `High`. Jalankan perintah ini setelah patch dibuka dan audio engine Max aktif.
# python
# python3
