# 📋 Logbook Catatan Perkembangan Aplikasi EV Charger Monitoring

Dokumen ini mencatat riwayat pembaruan fungsional dan teknis aplikasi **EV Charger Power Monitoring Dashboard** secara bertahap pertanggal pengembangan (tanggal terbaru berada di paling atas).

---

## 📌 Logbook Entry: Monitoring Realtime Per-User, History Auto-Save 100%, Validasi Profil & Stabilitas Database

- **Tanggal**: 19 Juli 2026
- **Author**: Rizki Abdul Rozaq

### Rangkuman Pembaruan Teknis:

1. **Monitoring Realtime Per-User (Independensi Akun)**
   - Mengubah arsitektur *live state* dari sistem global tunggal menjadi sistem terisolasi per akun pengguna.
   - Setiap pengguna yang login memiliki tingkat baterai (%), daya pengisian (kW), status pengisian (*Sedang Charging*, *Pause*, *Standby*), dan biaya siklus aktif sendiri secara independen.
   - Tindakan Start, Pause, dan Reset yang dilakukan oleh satu akun tidak akan merusak atau mengganggu sesi pengisian pengguna lain yang sedang aktif.

2. **Penyimpanan Otomatis Siklus Charging (Auto-Save 100% / Completion)**
   - Menyempurnakan pemicu pencatatan riwayat charging otomatis saat tingkat baterai mencapai 100%, saat status pengisian berganti ke *idle/completed*, atau saat siklus di-reset oleh simulator.
   - Menghubungkan id akun pengguna yang aktif dengan setiap entri charging otomatis maupun manual sehingga data riwayat tersimpan permanen tanpa hilang.

3. **Isolasi Ringkasan Konsumsi Biaya & Total kWh Per Akun**
   - Mengisolasikan perhitungan Total Biaya Konsumsi, Total kWh Charging, dan Jumlah Siklus Selesai pada dashboard pengguna.
   - Pengguna biasa hanya melihat total akumulasi pemakaian dari akun mereka sendiri, sedangkan role Admin/Superadmin tetap dapat memantau total agregat seluruh sistem.

4. **Umpan Balik Visual Validasi Form Profil**
   - Menambahkan komponen notifikasi peringatan visual (*alert box*) bergaya cyber-glassmorphism pada dashboard.
   - Menampilkan pesan kesalahan langsung saat pengguna salah memasukkan password saat ini, memasukkan username yang sudah terpakai, atau membuat password baru yang kurang dari 6 karakter/tidak cocok.

5. **Optimasi Stabilitas & Penguncian Database SQLite**
   - Mengaktifkan mode *Write-Ahead Logging* (WAL) pada database SQLite untuk mendukung akses simultan antara pembacaan (*reading*) dan penulisan (*writing*) tanpa saling mengunci (*non-blocking*).
   - Menambahkan konfigurasi *busy timeout* dan *connection timeout* 30 detik serta penanganan penciptaan state aman (*INSERT OR IGNORE*) guna mencegah terjadinya kesalahan `database is locked` saat banyak permintaan API berjalan secara bersamaan.

---

## 📌 Logbook Entry: Sistem Autentikasi dan Manajemen Pengguna

- **Tanggal**: 18 Juli 2026
- **Author**: Rizki Abdul Rozaq

### Rangkuman Pembaruan Teknis:

1. **Sistem Autentikasi (Login & Register)**
   - Menambahkan desain UI terpisah untuk halaman Login dan Register.
   - Menambahkan validasi pada form registrasi (anti-kosong, pencocokan ketikan *password* dan *konfirmasi password*).
   - Menerapkan pengamanan *hashing* pada *password* di *database* agar aman (tidak disimpan sebagai *plain-text*).

2. **Jenjang Role Akses (Hak Akses)**
   Aplikasi membagi hak pengguna menjadi 3 tingkatan (Role):
   - **Superadmin**: Role tertinggi. Sistem secara otomatis membuat (seeding) **3 akun superadmin tetap** (`superadmin1`, `superadmin2`, `superadmin3`). Superadmin bisa mengelola dan memodifikasi status akun bertipe *User* maupun *Admin*.
   - **Admin**: Pengelola stasiun *charging*. Memiliki izin untuk mengendalikan alat (Start/Pause) dan hak untuk menyetujui akun bertipe *User*.
   - **User**: Hanya pemantau biasa (tombol kontrol Start/Pause disembunyikan dari layarnya).

3. **Sistem *Approval* (Persetujuan Pendaftaran)**
   - Saat pendaftar (*Admin* atau *User*) baru menyelesaikan registrasi, akun mereka secara otomatis berada dalam status **Pending**. 
   - Pemilik akun tidak akan bisa *login* sebelum disetujui (di-*Approve*) secara manual oleh pengelola melalui halaman Kontrol. Sistem akan menolak akses login mereka dengan pesan "Akun belum disetujui".

4. **Fitur Suspend (*Activate / Deactivate*)**
   - Fitur pemblokiran yang mengizinkan Admin/Superadmin mencabut paksa hak login dari suatu akun yang sebelumnya sudah disetujui.
   - Berguna untuk me-nonaktifkan akun (misalnya karyawan yang sudah resign) secara sementara atau permanen tanpa menghapus rekam jejak (riwayat histori) datanya.

5. **Halaman "Kontrol User"**
   - Halaman panel manajemen pengguna khusus untuk Admin & Superadmin.
   - Menampilkan tabel berisi: Username, Role, Waktu Login Terakhir, Status *Approval*, dan Status *Active*.
   - Menyediakan tombol-tombol aksi kontrol: **Approve**, **Activate/Deactivate**, dan **Hapus Akun** (lengkap dengan *pop-up* validasi peringatan agar mencegah akun tidak sengaja terhapus).
   - Menerapkan batasan hierarki: Admin tidak bisa menghapus/mengedit akun Superadmin.

6. **Halaman "Profil Saya"**
   - Tersedia form profil terintegrasi pada UI dasbor (berbasis navigasi *Single Page Application*).
   - Pengguna bisa mengubah nama **Username** (dengan sistem validasi *backend* agar tidak ada nama yang bentrok di *database*).
   - Pengguna dapat mengubah **Password** baru, namun sistem akan selalu mewajibkan pengetikan ulang *password lama* terlebih dahulu demi alasan keamanan.

7. **Proteksi Keamanan Rute (Endpoint Security)**
   - Menyematkan fungsi *decorator* khusus (`@login_required`, `@admin_required`, `@superadmin_required`) pada setiap *logic* perutean API/Halaman web.
   - Memblokir tindakan peretasan URL (*bypass*). Pengguna yang tidak punya akses / belum login tidak akan bisa mengakses tombol kontrol (Start/Pause) di alat atau menghapus data pengguna.
   - Sistem juga mendata jejak terakhir *login* pengguna (`last_login_at`).

8. **Integrasi Antarmuka (SPA UI Integration)**
   - Halaman Kontrol User dan Profil digabungkan langsung (tanpa perlu reload halaman penuh) ke dalam komponen antar-muka Dashboard bergaya *Glassmorphism*. 
   - Semua form tindakan pengguna akan secara otomatis merespons (via URL fragment / argumen) agar layar mengembalikan pengguna tepat ke halaman Tab di mana mereka bertindak.
