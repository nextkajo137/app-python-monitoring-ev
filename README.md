# EV Charger Power Monitoring Dashboard

Dashboard monitoring daya charger mobil listrik berbasis Python Flask dan Node-RED API.

## 📌 Deskripsi Project

Project ini merupakan aplikasi monitoring penggunaan daya charger kendaraan listrik (EV Charger) secara realtime menggunakan:

* Python Flask sebagai backend
* Node-RED sebagai public API simulator
* SQLite sebagai database lokal
* HTML, CSS, dan JavaScript sebagai frontend dashboard

Aplikasi menampilkan informasi realtime seperti:

* Status charging
* Persentase baterai
* Daya charger (kW)
* Tegangan charger
* Tegangan sumber PLN
* Energi charging (kWh)
* Estimasi biaya charging
* Riwayat charging

Selain monitoring, aplikasi juga mendukung simulasi kontrol charging menggunakan tombol:

* Start
* Pause
* Reset

---

# 🏗️ Arsitektur Sistem

```text
Node-RED API
      ↓
Python Flask Backend
      ↓
SQLite Database
      ↓
Realtime Dashboard
```

---

# ⚙️ Teknologi yang Digunakan

| Teknologi           | Fungsi              |
| ------------------- | ------------------- |
| Python Flask        | Backend API         |
| Node-RED            | Simulasi Public API |
| SQLite              | Database lokal      |
| HTML/CSS/JavaScript | Frontend dashboard  |
| Chart.js            | Grafik realtime     |

---

# 📁 Struktur Folder

```text
app-python-monitoring-ev/
│
├── node-red/
│   └── ev-charger-dummy-flow.json
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       └── app.js
│
├── templates/
│   └── index.html
│
├── app.py
├── requirements.txt
├── .env
└── ev_charger.db
```

---

# 🚀 Cara Menjalankan Project

## 1. Clone Repository

```bash
git clone https://github.com/nextkajo137/app-python-monitoring-ev.git
```

Masuk ke folder project:

```bash
cd app-python-monitoring-ev
```

---

## 2. Membuat Virtual Environment

```bash
python -m venv venv
```

Aktifkan virtual environment:

### Windows

```bash
venv\Scripts\activate
```

---

## 3. Install Dependency

```bash
pip install -r requirements.txt
```

---

## 4. Menjalankan Flask Backend

```bash
python app.py
```

Jika berhasil:

```text
Running on http://127.0.0.1:5000
```

## 5. Akun Akses Default

Aplikasi sudah memiliki 3 akun **Superadmin** bawaan yang bisa langsung digunakan untuk mengelola sistem dan menerima pendaftaran user baru:
- **Username:** `superadmin1` | `superadmin2` | `superadmin3`
- **Password:** `superadmin123`

---

# 🔌 Menjalankan Node-RED

## 1. Install Node-RED

```bash
npm install -g node-red
```

---

## 2. Jalankan Node-RED

```bash
node-red
```

Jika berhasil:

```text
Server now running at http://127.0.0.1:1880/
```

---

## 3. Import Flow Node-RED

Import file:

```text
node-red/ev-charger-dummy-flow.json
```

Ke Node-RED melalui:

```text
Menu → Import
```

---

# 🌐 Endpoint API

## Flask API

| Endpoint     | Method | Fungsi                  |
| ------------ | ------ | ----------------------- |
| /            | GET    | Dashboard utama         |
| /api/live    | GET    | Data realtime dashboard |
| /api/history | GET    | Riwayat charging        |
| /api/summary | GET    | Ringkasan konsumsi      |
| /api/control | POST   | Kontrol charging        |

---

## Node-RED API

| Endpoint             | Method | Fungsi              |
| -------------------- | ------ | ------------------- |
| /api/charger/live    | GET    | Data dummy realtime |
| /api/charger/history | GET    | Riwayat charging    |
| /api/charger/summary | GET    | Ringkasan charging  |
| /api/charger/control | POST   | Kontrol charging    |

---

# 🎛️ Fitur Utama

## ✅ Monitoring Realtime

Menampilkan:

* Status charging
* Battery level
* Daya charger
* Tegangan charger
* Tegangan PLN
* Energi charging
* Estimasi biaya charging

---

## ✅ Kontrol Charging

### ▶️ Start

Mengaktifkan simulasi charging.

### ⏸ Pause

Menghentikan charging dan mengubah daya menjadi 0.

### 🔄 Reset

Mengembalikan data charging ke kondisi awal.

---

## ✅ Database SQLite

Data charging disimpan ke SQLite untuk:

* Riwayat charging
* Total energi
* Total biaya

---

# 📊 Contoh Data JSON

```json
{
  "source": "node-red-dummy",
  "status": "charging",
  "level_percent": 27.9,
  "charger_power_kw": 7.01,
  "charger_voltage_v": 389.2,
  "pln_voltage_v": 226.9
}
```

---

# 👨‍💻 Tim Pengembang

Project tugas mata kuliah Pemrograman Backend.

Tema:

Monitoring penggunaan daya charger kendaraan listrik berbasis Python dan Node-RED API.

---

# 📄 Lisensi

Project ini dibuat untuk keperluan pembelajaran dan pengembangan akademik.
