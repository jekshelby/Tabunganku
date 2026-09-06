# CatatUang

CatatUang adalah aplikasi pencatatan keuangan pribadi berbasis Flask. Aplikasi ini membantu pengguna mencatat pemasukan dan pengeluaran, mengelola tabungan, memantau laporan keuangan, serta membaca nominal struk melalui OCR.

## Akses dan Instalasi PWA

CatatUang dapat digunakan langsung melalui versi online:

**[Buka CatatUang](https://tabunganku.onrender.com/)**

Aplikasi dapat dipasang ke home screen seperti aplikasi mobile. Pastikan membuka link menggunakan browser perangkat.

### iPhone/iPad dengan Safari

1. Buka [CatatUang](https://tabunganku.onrender.com/) melalui Safari.
2. Tekan tombol **Share**.
3. Pilih **Add to Home Screen**.
4. Tekan **Add**.
5. Buka CatatUang dari ikon yang muncul di home screen.

Video panduan instalasi PWA di iOS/Safari:

[Tonton panduan instalasi di Safari/iOS](https://youtu.be/rXzADglUEZA)

### Android dengan Chrome atau browser lain

1. Buka [CatatUang](https://tabunganku.onrender.com/) melalui Chrome.
2. Buka menu browser dengan menekan ikon tiga titik.
3. Pilih **Install app**, **Add to Home screen**, atau pilihan sejenis yang tersedia.
4. Konfirmasi dengan menekan **Install** atau **Add**.
5. Buka CatatUang dari home screen atau app drawer.

Video panduan instalasi PWA di Android/Chrome:

[Tonton panduan instalasi di Android/Chrome](https://youtu.be/VaQ8qL11bos)

## Fitur Utama

### 1. Autentikasi Pengguna

- Registrasi akun baru.
- Login menggunakan email dan password.
- Password disimpan dalam bentuk hash.
- Session login berlaku hingga 30 hari.
- Logout dari akun.
- Pengaturan akun melalui ikon profil di kanan atas.
- Edit nama dan email.
- Ganti password.

### 2. Dashboard

Dashboard menampilkan ringkasan keuangan pengguna yang sedang login:

- Saldo utama.
- Total pemasukan.
- Total pengeluaran.
- Tiga transaksi terbaru.
- Tombol cepat untuk mencatat transaksi.
- Fitur sembunyikan/tampilkan saldo.

Semua data dashboard diambil berdasarkan `user_id` dari session sehingga data antar pengguna tetap terpisah.

### 3. Pencatatan Transaksi

Pengguna dapat menambahkan transaksi dengan informasi:

- Jenis transaksi: pemasukan atau pengeluaran.
- Nominal.
- Kategori.
- Catatan.
- Tanggal otomatis dari database.

Nominal menggunakan angka rupiah bulat. Jika ada request dengan angka pecahan, sistem akan membulatkannya ke rupiah terdekat.

Transaksi juga dapat:

- Diedit.
- Dihapus.
- Difilter berdasarkan pemasukan atau pengeluaran.
- Dilihat berdasarkan kelompok tanggal.

Transaksi yang dibuat otomatis oleh sistem tabungan tidak dapat diedit atau dihapus langsung dari menu transaksi. Perubahannya harus dilakukan melalui menu Tabungan agar saldo tetap konsisten.

### 4. Tabungan

Menu Tabungan memiliki dua jenis tabungan:

#### Target & deadline

Mode ini adalah pilihan default dan membutuhkan:

- Nama tabungan.
- Target nominal.
- Deadline.

Sistem menampilkan progress berdasarkan saldo terkumpul dibandingkan target.

#### Tabungan umum

Digunakan untuk menyimpan uang tanpa target dan deadline tertentu.

- Tidak membutuhkan target nominal.
- Tidak membutuhkan deadline.
- Tidak menampilkan progress bar.
- Tetap memiliki saldo dan riwayat setor/tarik.

#### Operasi Tabungan

- Buat tabungan.
- Edit nama, target, mode, dan deadline.
- Setor saldo.
- Tarik saldo.
- Melihat riwayat aktivitas.
- Menghapus tabungan.

#### Integrasi saldo utama

Saat setor ke tabungan:

- Saldo tabungan bertambah.
- Saldo utama berkurang.
- Sistem membuat transaksi pengeluaran dengan kategori `Tabungan - Nama Tabungan`.

Saat menarik dari tabungan:

- Saldo tabungan berkurang.
- Saldo utama bertambah.
- Sistem membuat transaksi pemasukan.

Saat tabungan dihapus:

- Saldo tersisa dikembalikan ke saldo utama.
- Sistem membuat transaksi pemasukan dengan kategori `Pengembalian - Nama Tabungan`.
- Target tabungan dan riwayat mutasinya dihapus sesuai relasi database.

### 5. Report Keuangan

Menu Report menyediakan ringkasan berdasarkan periode:

- Bulanan.
- Tahunan.

Informasi yang ditampilkan:

- Total pemasukan.
- Total pengeluaran.
- Total setor tabungan.
- Total tarik tabungan.
- Arus bersih periode.
- Rincian transaksi berdasarkan kategori.
- Posisi saldo setiap tabungan.
- Insight keuangan otomatis.

Insight menggunakan aturan lokal berdasarkan data pengguna, tanpa mengirim data ke layanan AI eksternal. Insight dapat menjelaskan:

- Arus keuangan positif atau negatif.
- Selisih pemasukan dan pengeluaran.
- Kategori pengeluaran terbesar.
- Jumlah uang yang disisihkan ke tabungan.
- Target tabungan yang hampir tercapai.

### 6. Scan Struk OCR

Menu Scan dapat digunakan untuk membaca nominal dari gambar struk.

Metode input:

- Kamera perangkat.
- Galeri atau file gambar.

Alur OCR:

1. Pengguna memilih atau mengambil gambar struk.
2. Gambar dikirim ke endpoint `/api/scan-ocr`.
3. OCR.Space memproses gambar.
4. Nominal hasil pembacaan ditampilkan.
5. Nominal dapat diteruskan ke form pencatatan transaksi.

Fitur kamera membutuhkan izin kamera dari browser. OCR membutuhkan koneksi internet.

### 7. Progressive Web App

Aplikasi mendukung fitur PWA melalui:

- `manifest.json`.
- Service worker.
- Cache network-first untuk akses yang lebih baik saat koneksi tidak stabil.
- Layout mobile dengan navigasi bawah.

## Tampilan Aplikasi

### Dashboard

![Dashboard CatatUang](static/screenshots/dashboard.png)

### Transaksi

![Halaman transaksi CatatUang](static/screenshots/transaksi.png)

### Tabungan

![Menu tabungan CatatUang](static/screenshots/tabungan.png)

### Report

![Report keuangan CatatUang](static/screenshots/report.png)

### Pengaturan Akun

![Pengaturan akun CatatUang](static/screenshots/akun.png)

### Scan OCR

![Scan OCR CatatUang](static/screenshots/scan.png)

## Teknologi

- Python 3.
- Flask 3.
- PostgreSQL Neon.
- `psycopg2-binary` untuk koneksi database.
- Jinja2 untuk template HTML.
- Bootstrap Icons.
- Requests untuk komunikasi dengan OCR.Space.
- Gunicorn untuk deployment.

## Struktur Folder

```text
.
├── app.py                    # Entry point Flask dan route aplikasi
├── db.py                     # Koneksi PostgreSQL
├── setup_db.py               # Membuat tabel users dan transaksi utama
├── setup_db2.py              # Migrasi tabel tabungan dan relasinya
├── Procfile                 # Konfigurasi deployment Gunicorn
├── requirements.txt         # Dependency Python
├── features/
│   ├── auth.py              # Registrasi, login, dan pengaturan akun
│   ├── dashboard.py         # Ringkasan dan riwayat transaksi
│   ├── ocr.py               # Ekstraksi nominal struk
│   ├── pencatatan.py        # Kategori dan operasi transaksi
│   ├── report.py            # Agregasi laporan dan insight
│   └── tabungan.py          # Target, saldo, dan mutasi tabungan
├── templates/               # Template halaman Jinja2
└── static/
    ├── css/style.css        # Styling aplikasi
    ├── manifest.json        # Konfigurasi PWA
    └── service-worker.js    # Service worker PWA
```

## Struktur Database

### `users`

Menyimpan data akun pengguna.

- `id`
- `nama`
- `email`
- `password`
- `created_at`

### `transaksi`

Menyimpan pemasukan dan pengeluaran utama.

- `id`
- `user_id`
- `tanggal`
- `tipe`
- `nominal`
- `kategori`
- `catatan`
- `tabungan_id` untuk transaksi otomatis dari tabungan
- `created_at`

### `tabungan`

Menyimpan target atau tabungan umum.

- `id`
- `user_id`
- `nama`
- `target_nominal`, boleh kosong untuk tabungan umum
- `deadline`, boleh kosong untuk tabungan umum
- `status`
- `warna`
- `created_at`
- `updated_at`

### `transaksi_tabungan`

Menyimpan mutasi saldo tabungan.

- `id`
- `tabungan_id`
- `user_id`
- `tipe`: `setor` atau `tarik`
- `nominal`
- `tanggal`
- `catatan`
- `created_at`

## Instalasi Lokal

### 1. Buat virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependency

```bash
pip install -r requirements.txt
```

### 3. Buat file `.env`

Gunakan connection string PostgreSQL dari Neon:

```env
DATABASE_URL=postgresql://username:password@host/database?sslmode=require
SECRET_KEY=ganti_dengan_secret_key_yang_aman
OCR_SPACE_API_KEY=isi_dengan_api_key_ocr_space
```

Jangan commit file `.env` ke repository.

### 4. Siapkan database

Jalankan setup tabel dasar terlebih dahulu:

```bash
python setup_db.py
```

Kemudian jalankan migrasi tabungan:

```bash
python setup_db2.py
```

`setup_db2.py` bersifat idempoten sehingga aman dijalankan kembali. Script ini tidak menghapus data pengguna atau transaksi yang sudah ada.

### 5. Jalankan aplikasi

```bash
python app.py
```

Aplikasi tersedia di:

```text
http://127.0.0.1:5000
```

## Route Utama

| Route | Method | Fungsi |
|---|---|---|
| `/` | GET | Dashboard |
| `/login` | GET, POST | Login |
| `/register` | GET, POST | Registrasi |
| `/akun` | GET, POST | Kustomisasi akun |
| `/tambah` | GET, POST | Tambah transaksi |
| `/transaksi` | GET | Daftar transaksi |
| `/transaksi/<id>/edit` | GET, POST | Edit transaksi |
| `/transaksi/<id>/hapus` | POST | Hapus transaksi |
| `/tabungan` | GET, POST | Daftar dan tambah tabungan |
| `/tabungan/<id>` | GET | Detail tabungan |
| `/tabungan/<id>/edit` | GET, POST | Edit tabungan |
| `/tabungan/<id>/hapus` | POST | Hapus tabungan |
| `/tabungan/<id>/mutasi` | POST | Setor atau tarik tabungan |
| `/report` | GET | Report bulanan/tahunan |
| `/scan` | GET | Halaman scan struk |
| `/api/scan-ocr` | POST | Endpoint OCR struk |
| `/logout` | GET | Logout |

## Deployment

Aplikasi sudah menyediakan `Procfile` untuk platform yang mendukung Gunicorn:

```text
web: gunicorn app:app
```

Pastikan environment deployment memiliki:

- `DATABASE_URL` Neon PostgreSQL.
- `SECRET_KEY` yang aman.
- `OCR_SPACE_API_KEY` dari OCR.Space agar fitur scan tidak bergantung pada API key demo `helloworld`.
- Dependency dari `requirements.txt`.

## Keamanan dan Catatan

- Jangan menyimpan credential database langsung di source code.
- Jangan membagikan isi `.env` ke publik.
- Gunakan `SECRET_KEY` yang berbeda untuk production.
- Pastikan database Neon menggunakan SSL.
- Endpoint yang mengubah data dilindungi login session.
- Query transaksi dan tabungan selalu dibatasi berdasarkan `user_id`.
- OCR menggunakan layanan pihak ketiga, sehingga gambar struk dikirim ke OCR.Space.
