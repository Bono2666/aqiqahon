# Product Requirements Document (PRD)

## AqiqahOn — Sistem Manajemen & Pemesanan Aqiqah Online

---

## 1. Gambaran Umum

| Item                 | Detail                                 |
| -------------------- | -------------------------------------- |
| **Nama Produk**      | AqiqahOn                               |
| **Domain Produksi**  | sahabataqiqah.co.id                    |
| **Platform**         | Web Application (Server-Side Rendered) |
| **Framework**        | Django 4.2 / Python 3.11               |
| **Database**         | MySQL                                  |
| **Bahasa UI**        | Indonesia (id)                         |
| **Timezone**         | Asia/Jakarta                           |
| **Mobile Detection** | django-user-agents                     |

AqiqahOn adalah **sistem manajemen bisnis aqiqah** (layanan penyembelihan & pengolahan hewan aqiqah) yang menyediakan:

1. **Panel Admin** — untuk staff internal mengelola pesanan, data master, keuangan, dan approval
2. **Formulir Pemesanan Publik** — untuk pelanggan melakukan pemesanan online via link yang dibagikan

---

## 2. Pengguna & Peran

### 2.1 Daftar Peran

| Peran                     | Kode Menu  | Deskripsi                                        |
| ------------------------- | ---------- | ------------------------------------------------ |
| **Superuser**             | —          | Akses penuh ke seluruh sistem                    |
| **Admin/User**            | `USER`     | Mengelola data pengguna, posisi, menu, otorisasi |
| **Manajer Area**          | `AREA`     | Mengelola cabang/area penjualan                  |
| **CS (Customer Service)** | `ORDER`    | Mengelola & mengupdate pesanan pelanggan         |
| **Keuangan**              | `CASH-IN`  | Mengelola penerimaan uang (cash-in)              |
| **Promo**                 | `PROMO`    | Mengelola promosi dan hadiah                     |
| **Pelanggan**             | `CUSTOMER` | Mengelola data pelanggan                         |
| **Regional**              | `REGION`   | Mengelompokkan area penjualan                    |

### 2.2 Sistem Otorisasi

- **Login**: Menggunakan `user_id` + password
- **RBAC (Role-Based Access Control)**: Per-level menu dengan permission `add`, `edit`, `delete`
- **Auto-Logout**: Sesi berakhir setelah **15 menit** tidak aktif
- **Dekorator**: `@role_required(allowed_roles='...')` membatasi akses per view
- **Area Assignment**: User dapat di-assign ke beberapa area penjualan (`AreaUser`)

---

## 3. Fitur Utama

### 3.1 Autentikasi & Manajemen Sesi

| Fitur           | Detail                               |
| --------------- | ------------------------------------ |
| Login           | `user_id` + password, session-based  |
| Auto-logout     | 15 menit idle → redirect ke login    |
| Change password | User mengubah password sendiri       |
| Set password    | Admin mengatur password user lain    |
| Cache control   | Halaman login tidak di-cache browser |

### 3.2 Manajemen Pesanan (Transaksi)

#### 3.2.1 Alur Pemesanan (Customer Flow)

```
Form Publik → Input Data Anak → Pilih Paket → Konfirmasi → Submit (DRAFT)
```

**Langkah 1 — Formulir Publik** (`/order/new/<area_id>/`)

- Tersedia via link per area: `http://sahabataqiqah.co.id/order/new/<AREA_ID>/`
- Pelanggan mengisi: nama, telepon, email, alamat, kota, provinsi, tanggal pengiriman, waktu kedatangan

**Langkah 2 — Data Anak Aqiqah** (`/order/child/add/<id>/`)

- Nama anak, tanggal lahir, jenis kelamin (L/P), nama ayah, nama ibu
- Bisa menambah multiple anak dalam satu pesanan
- Validasi: tanggal lahir tidak boleh melebihi hari ini

**Langkah 3 — Pilih Paket** (`/order/package/add/<id>/`)

- Pilih kategori → pilih paket → konfigurasi paket:
  - **Jenis Hewan**: Jantan / Betina (menentukan harga)
  - **Jumlah (Qty)**: jumlah porsi/kambing
  - **Jenis Kotak**: pilihan box type
  - **Masakan Utama**: Main Cuisine (dengan extra price jika upgrade)
  - **Sub Masakan**: Sub Cuisine
  - **Side Masakan 1–5**: hingga 5 pilihan side cuisine
  - **Beras**: pilihan jenis beras
  - **Tas**: pilihan tas
  - **Minuman**: pilihan beverage
  - **Souvenir**: pilihan souvenir
  - **Addon**: item tambahan dengan harga & kuantitas
- **Auto-calculated**:
  - `total_price = (qty × unit_price) + extra_price`
  - `extra_price` dihitung dari semua upgrade (cuisine, rice, bag, box, beverage)
- Bisa menambah multiple paket dalam satu pesanan

**Langkah 4 — Konfirmasi** (`/order/confirm/<id>/`)

- Review data lengkap: data anak, paket, harga
- Pilih promo (jika memenuhi syarat minimum transaksi)
- Centang: perlu foto?, disaksikan?, sumber info
- Input catatan pesanan

**Langkah 5 — Submit** → Status berubah: `PENDING` → `DRAFT`

#### 3.2.2 Status Pesanan

| Status      | Keterangan                                        |
| ----------- | ------------------------------------------------- |
| `PENDING`   | Pesanan baru, belum disubmit                      |
| `DRAFT`     | Pesanan berhasil disubmit, menunggu konfirmasi CS |
| `CONFIRMED` | Pesanan dikonfirmasi CS                           |
| `DP`        | Pesanan sudah dibayar sebagian (Down Payment)     |
| `LUNAS`     | Pesanan lunas dibayar                             |
| `ARCHIVED`  | Pesanan selesai & diarsipkan                      |
| `BATAL`     | Pesanan dibatalkan                                |

#### 3.2.3 Manajemen Pesanan (CS Flow)

- **Lihat Daftar Pesanan**: `/order/<branch>/<date>/` (filter per cabang & tanggal)
- **Detail Pesanan**: `/order/view/<id>/...`
- **Update Data Anak**: Tambah/edit/hapus anak dari sisi CS
- **Update Paket**: Mengubah konfigurasi paket dari sisi CS
- **Konfirmasi Pesanan**: `/order/confirm/<id>/` → status `CONFIRMED`
- **Batal Pesanan**: `/order/cancel/<id>/` → status `BATAL`
- **Arsip Pesanan**: `/order/archive/<branch>/<date>/`

#### 3.2.4 Nomor Urut & ID Pesanan

- **Seq Number**: Auto-increment per tahun (format: `00001`)
- **Order ID**: `INV-1{seq}/{area_id}/SA/{bulan}/{tahun}` (contoh: `INV-100001/AB1/SA/07/2026`)

### 3.3 Manajemen Data Master

#### 3.3.1 Pengguna (`/master/user/`)

| Field       | Tipe          | Keterangan           |
| ----------- | ------------- | -------------------- |
| `user_id`   | Char(50) PK   | Identifier login     |
| `username`  | Char(50)      | Nama tampilan        |
| `email`     | Email         | Email                |
| `position`  | FK → Position | Jabatan              |
| `signature` | Image         | Tanda tangan digital |
| `password`  | —             | Password terenkripsi |

**Fitur**:

- CRUD lengkap (add, view, update, delete)
- Upload & hapus tanda tangan digital
- Assign menu permission (add/edit/delete per menu)
- Assign area penjualan
- Change password & set password

#### 3.3.2 Pelanggan (`/master/customer/`)

| Field               | Tipe            | Keterangan         |
| ------------------- | --------------- | ------------------ |
| `customer_id`       | BigAutoField PK | Auto-generated     |
| `customer_name`     | Char(200)       | Nama pelanggan     |
| `customer_address`  | Char(200)       | Alamat             |
| `customer_district` | Char(50)        | Kecamatan          |
| `customer_city`     | Char(50)        | Kota               |
| `customer_province` | Char(50)        | Provinsi           |
| `customer_phone`    | Char(50)        | Telepon utama      |
| `customer_phone2`   | Char(50)        | Telepon alternatif |
| `customer_email`    | Char(50)        | Email              |

**Detail Anak** (`CustomerDetail`):

- `child_name`, `child_birth`, `child_sex`, `child_father`, `child_mother`
- Unique constraint: `(customer, child_name)`

**Catatan**: Pelanggan juga **auto-created** saat pesanan dikonfirmasi CS.

#### 3.3.3 Cabang/Area Penjualan (`/master/area-sales/`)

| Field          | Tipe        | Keterangan                                 |
| -------------- | ----------- | ------------------------------------------ |
| `area_id`      | Char(50) PK | Kode area (auto-uppercase)                 |
| `area_name`    | Char(50)    | Nama cabang                                |
| `manager`      | Char(50)    | User ID manager (position ASM)             |
| `bank_account` | Char(200)   | Rekening bank                              |
| `address`      | Char(200)   | Alamat kantor                              |
| `district`     | Char(50)    | Kecamatan                                  |
| `city`         | Char(50)    | Kota                                       |
| `postal_code`  | Char(10)    | Kode pos                                   |
| `form`         | Char(200)   | URL form pemesanan publik (auto-generated) |

**Catatan**: URL form otomatis dibuat: `{base_url}/order/new/{area_id}/`

#### 3.3.4 Posisi (`/master/position/`)

| Field           | Tipe       | Keterangan                 |
| --------------- | ---------- | -------------------------- |
| `position_id`   | Char(3) PK | Kode jabatan (max 3 digit) |
| `position_name` | Char(50)   | Nama jabatan               |

Contoh: `ASM` (Area Sales Manager)

#### 3.3.5 Menu & Otorisasi (`/master/menu/`)

**Menu**:
| Field | Tipe | Keterangan |
|-------|------|------------|
| `menu_id` | Char(50) PK | Kode menu |
| `menu_name` | Char(50) | Nama menu |
| `menu_remark` | Char(200) | Keterangan |

**Auth (Permission)**:
| Field | Tipe | Keterangan |
|-------|------|------------|
| `user` | FK → User | Pengguna |
| `menu` | FK → Menu | Menu |
| `add` | Boolean | Izin tambah |
| `edit` | Boolean | Izin ubah |
| `delete` | Boolean | Izin hapus |

Unique constraint: `(user, menu)`

#### 3.3.6 Masakan (`/master/cuisine/`)

| Field          | Tipe        | Keterangan                    |
| -------------- | ----------- | ----------------------------- |
| `cuisine_id`   | Char(50) PK | Kode masakan (auto-uppercase) |
| `cuisine_name` | Char(50)    | Nama masakan                  |

#### 3.3.7 Pelengkap/Equipment (`/master/equipment/`)

| Field            | Tipe        | Keterangan     |
| ---------------- | ----------- | -------------- |
| `equipment_id`   | Char(50) PK | Kode equipment |
| `equipment_name` | Char(50)    | Nama item      |

Digunakan untuk: tas, minuman, souvenir, box, dll.

#### 3.3.8 Kategori (`/master/category/`)

| Field           | Tipe        | Keterangan    |
| --------------- | ----------- | ------------- |
| `category_id`   | Char(50) PK | Kode kategori |
| `category_name` | Char(50)    | Nama kategori |

#### 3.3.9 Paket (`/master/package/`)

| Field          | Tipe          | Keterangan                  |
| -------------- | ------------- | --------------------------- |
| `package_id`   | Char(50) PK   | Kode paket (auto-uppercase) |
| `package_name` | Char(50)      | Nama paket                  |
| `category`     | FK → Category | Kategori                    |
| `promo`        | Boolean       | Memenuhi syarat promo       |
| `active`       | Boolean       | Aktif/tidak                 |
| `male_price`   | Decimal(12,0) | Harga kambing jantan        |
| `female_price` | Decimal(12,0) | Harga kambing betina        |
| `box`          | Integer       | Jumlah box per porsi        |
| `quantity`     | Integer       | Default kuantitas           |
| `type`         | Char(10)      | Tipe paket                  |

**Relasi Paket** (tabel penghubung dengan extra_price & default):

| Model            | Relasi              | Keterangan        |
| ---------------- | ------------------- | ----------------- |
| `Rice`           | package ↔ cuisine   | Pilihan beras     |
| `MainCuisine`    | package ↔ cuisine   | Masakan utama     |
| `SubCuisine`     | package ↔ cuisine   | Sub masakan       |
| `SideCuisine1–5` | package ↔ cuisine   | 5 side masakan    |
| `Bag`            | package ↔ equipment | Pilihan tas       |
| `Beverage`       | package ↔ equipment | Pilihan minuman   |
| `Souvenir`       | package ↔ equipment | Pilihan souvenir  |
| `Pack`           | package ↔ equipment | Pilihan box/kotak |
| `Other`          | package ↔ equipment | Item lainnya      |
| `Addon`          | package ↔ equipment | Item tambahan     |

Setiap relasi memiliki field:

- `extra_price`: Harga tambahan jika dipilih
- `default`: Apakah ini pilihan default

### 3.4 Manajemen Keuangan (Cash-In)

#### 3.4.1 Pencatatan Uang Masuk (`/cashin/`)

| Field           | Tipe            | Keterangan                  |
| --------------- | --------------- | --------------------------- |
| `cashin_id`     | BigAutoField PK | Auto-generated              |
| `order`         | FK → Order      | Pesanan terkait             |
| `cashin_date`   | DateTime        | Tanggal pembayaran          |
| `cashin_type`   | Char(50)        | Jenis pembayaran (DP/Lunas) |
| `cashin_amount` | Decimal(12,0)   | Jumlah pembayaran           |
| `cashin_note`   | Char(200)       | Catatan                     |
| `bank`          | Char(50)        | Bank pengirim               |
| `evidence`      | File            | Bukti transfer (foto)       |

**Fitur**:

- Upload bukti transfer (foto)
- Validasi: jumlah pembayaran tidak boleh melebihi `pending_payment`
- Pindah pesanan antar order
- Auto-refresh status pesanan setelah pembayaran:
  - `pending_payment == 0` → `LUNAS`
  - `down_payment == 0` → `CONFIRMED`
  - selain itu → `DP`

#### 3.4.2 Kalkulasi Harga

```
total_order = Σ(total_price per paket) + Σ(total_price addon) - promo_nominal
pending_payment = total_order - down_payment - discount
down_payment = Σ(cashin_amount)
```

**PPN**: 11% (PPN Indonesia terkini)

### 3.5 Sistem Notifikasi

- **Draft Orders**: Menampilkan jumlah pesanan draft yang perlu ditindaklanjuti
- Filter: area sesuai assignment user + status `draft` + delivery_date ≥ 90 hari yang lalu
- Ditampilkan sebagai badge di sidebar/navigation

### 3.6 Dokumen PDF

#### 3.6.1 Invoice (`/order/invoice/<id>/`)

Komponen Invoice:

- Logo perusahaan
- Data cabang (alamat, telepon, website)
- No. referensi (order ID)
- Tanggal invoice & tanggal pengiriman
- Data pemesan (nama, telepon, alamat)
- Tabel detail: Produk | Deskripsi | Qty | Harga Satuan | Jumlah
- Sub Total, Diskon, DP, Jumlah Tertagih
- Watermark "LUNAS" jika status LUNAS
- Tanda tangan: GA, Kurir
- Keterangan & Checklist

#### 3.6.2 BAP (Berita Acara Pemeriksaan) (`/order/bap/<id>/`)

Format serupa Invoice dengan komponen tambahan:

- Rincian biaya per item
- Total, diskon, promo, DP
- Tanda tangan: Customer, GA

#### 3.6.3 Checklist (`/order/checklist/<id>/`)

Checklist Form untuk driver & checker:

- Data pesanan (invoice, nama, tanggal delivery)
- Checklist item: beras, masakan utama, sub, side 1-5, other, addon, minuman, sertifikat, tas, souvenir, promo, BAP & kwitansi
- Kolom: DI ISI OLEH DRIVER | DI ISI OLEH CHECKER
- Kolom catatan & tanda tangan

### 3.7 Fitur Promo

| Field         | Tipe            | Keterangan                       |
| ------------- | --------------- | -------------------------------- |
| `promo_id`    | BigAutoField PK | ID promo                         |
| `promo_name`  | Char(200)       | Nama promo                       |
| `promo_limit` | Decimal(12,0)   | Minimum transaksi untuk eligible |

**PromoDetail**:
| Field | Tipe | Keterangan |
|-------|------|------------|
| `promo` | FK → Promo | Promo induk |
| `gift` | Char(50) | Nama hadiah |
| `nominal` | Decimal(12,0) | Nilai potongan |

**Logika Promo**:

1. Cek apakah ada paket dengan flag `promo=True` dalam pesanan
2. Cek apakah total transaksi memenuhi minimum `promo_limit`
3. Pilih promo dengan `promo_limit` tertinggi yang masih terpenuhi
4. Potongan diterapkan ke `promo_nominal` pada order

### 3.8 Jadwal Pesanan (Calendar View)

| Item | Detail |
|------|--------|
| Route | `/jadwal/` |
| API | `/jadwal/events/` |
| Library | FullCalendar.js v6.x (CDN) |
| Default View | DayGrid Month (kalender bulanan) |
| Filter | Cabang, Status |
| Aksi | Lihat Detail, Invoice PDF, BAP PDF, Checklist PDF |
| Sidebar | Section Transaksi → Jadwal |
| Role | `ORDER` (sama dengan Pemesanan) |

**Fitur**:

- **Tampilan Kalender**: Menampilkan pesanan berdasarkan tanggal pengiriman (`delivery_date`)
- **3 View Mode**: Month, Week, Day (dapat beralih via toolbar)
- **Filter Real-time**:
  - Cabang: Filter berdasarkan area penjualan
  - Status: DRAFT, CONFIRMED, DP, LUNAS, BATAL, atau semua
- **Klik Event**: Muncul modal detail pesanan dengan info lengkap
- **Aksi dari Modal**:
  - **Lihat Detail**: Navigasi ke halaman detail pesanan
  - **Invoice**: Generate/download PDF Invoice
  - **BAP**: Generate/download PDF BAP
  - **Checklist**: Generate/download PDF Checklist

**Color Legend (Status)**:

| Status | Warna | Keterangan |
|--------|-------|------------|
| `DRAFT` | Kuning `#ffc107` | Pesanan draft |
| `CONFIRMED` | Biru `#17a2b8` | Sudah dikonfirmasi |
| `DP` | Oranye `#fd7e14` | Bayar sebagian |
| `LUNAS` | Hijau `#28a745` | Lunas dibayar |
| `BATAL` | Merah `#dc3545` | Dibatalkan |
| `ARCHIVED` | Abu `#6c757d` | Terarsip |

**API Endpoint**:

```
GET /jadwal/events/?start=2026-07-01&end=2026-07-31&branch=all&status=all
```

Response (FullCalendar JSON format):
```json
[
  {
    "id": "INV-100001/AB1/SA/07/2026",
    "title": "Budi Santoso (Cabang AB1)",
    "start": "2026-07-15T00:00:00",
    "color": "#28a745",
    "extendedProps": {
      "order_id": "INV-100001/AB1/SA/07/2026",
      "customer_name": "Budi Santoso",
      "area_name": "Cabang AB1",
      "status": "LUNAS",
      "total_order": "3500000",
      "cs": "Siti",
      "time_arrival": "08:00 - 10:00"
    }
  }
]
```

### 3.9 Export Data

- **Excel (.xls)**: Menggunakan `xlwt`
- **Excel (.xlsx)**: Menggunakan `xlsxwriter`
- **Import/Export**: `django-import-export` dengan `tablib`

# 3.14 Jadwal Pesanan (Order Schedule)

## 3.14.1 Latar Belakang

Saat ini proses operasional setelah pesanan dikonfirmasi masih dilakukan menggunakan file Microsoft Excel sebagai media penjadwalan produksi dan pengantaran. Kondisi ini menimbulkan beberapa kendala, antara lain:

- Jadwal pesanan tersebar di beberapa file.
- Rekap kebutuhan dapur dilakukan secara manual.
- Tidak ada monitoring status produksi secara real-time.
- Penugasan driver dilakukan secara manual.
- Potensi pesanan terlewat cukup tinggi.
- Sulit mengetahui kapasitas produksi harian.
- Sulit mengetahui total kebutuhan kambing, nasi, box, souvenir, dan perlengkapan setiap hari.

Oleh karena itu diperlukan sebuah modul **Jadwal Pesanan (Order Schedule)** yang menjadi pusat pengelolaan aktivitas operasional mulai dari pesanan dikonfirmasi hingga selesai dikirim kepada pelanggan.

---

# 3.14.2 Tujuan

Modul Jadwal Pesanan bertujuan untuk:

- Mengelola seluruh jadwal produksi.
- Mengelola jadwal pengantaran.
- Menghasilkan rekap kebutuhan dapur secara otomatis.
- Membantu kepala dapur merencanakan produksi.
- Membantu admin operasional mengatur driver.
- Mengurangi risiko pesanan terlewat.
- Menampilkan dashboard operasional harian.
- Menampilkan rekap kebutuhan kambing berdasarkan **Jenis Kambing**.

---

# 3.14.3 Ruang Lingkup

Modul ini mencakup:

- Jadwal Produksi
- Jadwal Packing
- Jadwal Pengantaran
- Assignment Driver
- Assignment Kendaraan
- Monitoring Status
- Dashboard Operasional
- Dashboard Produksi
- Dashboard Driver
- Rekap Produksi
- Rekap Masakan
- Rekap Perlengkapan
- Rekap Jenis Kambing

---

# 3.14.4 User Roles

| Role              | Hak Akses           |
| ----------------- | ------------------- |
| Superuser         | Full Access         |
| Customer Service  | View, Add, Edit     |
| Admin Operasional | Full Access         |
| Kepala Dapur      | View Produksi       |
| Driver            | View Jadwal Sendiri |

---

# 3.14.5 Menu

```
Transaksi
    Order
    Jadwal Pesanan
    Arsip
```

Permission ID

```
ORDER-SCHEDULE
```

---

# 3.14.6 Workflow

```
Order

↓

CONFIRMED

↓

Auto Create Jadwal Pesanan

↓

UNSCHEDULED

↓

SCHEDULED

↓

COOKING

↓

PACKING

↓

READY

↓

ON DELIVERY

↓

COMPLETED
```

---

# 3.14.7 Status Jadwal

| Status      | Keterangan        |
| ----------- | ----------------- |
| UNSCHEDULED | Belum dijadwalkan |
| SCHEDULED   | Sudah dijadwalkan |
| COOKING     | Sedang produksi   |
| PACKING     | Sedang packing    |
| READY       | Siap dikirim      |
| ON DELIVERY | Sedang dikirim    |
| COMPLETED   | Pesanan selesai   |
| CANCELLED   | Dibatalkan        |

---

# 3.14.8 Daftar Jadwal

Default Filter

- Hari Ini

Filter

- Cabang
- Region
- Driver
- Customer
- Status
- Delivery Date
- Event Date
- Jenis Kambing

Kolom

| Kolom              |
| ------------------ |
| Tanggal Pengiriman |
| Jam Pengiriman     |
| Jam Acara          |
| Nomor Invoice      |
| Customer           |
| Paket              |
| **Jenis Kambing**  |
| Jumlah Box         |
| Area               |
| Driver             |
| Status             |

---

# 3.14.9 Detail Jadwal

## Informasi Umum

- Nomor Order
- Nomor Invoice
- Customer
- Cabang
- Area
- Alamat
- Telepon
- Jam Acara
- Jam Pengiriman
- Driver
- Kendaraan
- Catatan

## Informasi Paket

| Field             | Keterangan     |
| ----------------- | -------------- |
| Paket             | Nama Paket     |
| **Jenis Kambing** | Grade Kambing  |
| Qty Kambing       | Jumlah Kambing |
| Total Box         | Total Box      |

---

## Produksi

Field

- Mulai Produksi
- Estimasi Selesai
- Mulai Packing
- Estimasi Packing Selesai

---

## Pengiriman

Field

- Driver
- Kendaraan
- Jam Berangkat
- ETA
- Status Pengiriman

---

# 3.14.10 Rekap Produksi

Sistem menghasilkan rekap otomatis.

## Rekap Jenis Kambing

| Jenis Kambing | Qty |
| ------------- | --- |
| A             | xx  |
| B             | xx  |
| C             | xx  |
| D             | xx  |
| Istimewa      | xx  |
| Istimewa+     | xx  |
| Super         | xx  |
| Super+        | xx  |

Rekap ini digunakan sebagai dasar pembelian kambing setiap hari.

---

## Rekap Box

| Item     | Qty |
| -------- | --- |
| Box      | xx  |
| Tas      | xx  |
| Souvenir | xx  |

---

## Rekap Masakan

| Masakan  | Qty |
| -------- | --- |
| Sate     | xx  |
| Gulai    | xx  |
| Tongseng | xx  |
| Rendang  | xx  |

---

## Rekap Side Dish

| Item    | Qty |
| ------- | --- |
| Sambal  | xx  |
| Kerupuk | xx  |
| Acar    | xx  |

---

# 3.14.11 Dashboard

Dashboard menampilkan informasi:

- Pesanan Hari Ini
- Belum Dijadwalkan
- Sedang Produksi
- Sedang Packing
- Siap Kirim
- Dalam Pengiriman
- Selesai

---

# 3.14.12 Dashboard Produksi

Widget

- Total Kambing
- Total Box


Widget Rekap Jenis Kambing

- Grade A
- Grade B
- Grade C
- Grade D
- Istimewa
- Istimewa+
- Super
- Super+
- Total Type Kambing

---

# 3.14.13 Dashboard Driver

Driver hanya melihat:

- Jadwal Hari Ini
- Jadwal Besok
- Riwayat Pengiriman

---

# 3.14.14 Reminder

Reminder muncul apabila:

- Driver belum ditentukan.
- Jadwal hari ini belum diproses.
- Packing belum selesai.
- Pengiriman terlambat.
- Status masih Scheduled tetapi jam sudah lewat.

---

# 3.14.15 Business Rules

## Auto Create

Ketika Order berubah menjadi

```
CONFIRMED
```

Sistem otomatis membuat data Jadwal Pesanan.

Status awal

```
UNSCHEDULED
```

---

## Assignment Driver

Satu driver tidak boleh memiliki dua pengiriman pada waktu yang sama.

---

## Produksi

Jam Pengiriman tidak boleh lebih awal daripada Estimasi Produksi Selesai.

---

## Packing

Status READY hanya dapat dipilih apabila proses packing selesai.

---

## Pengiriman

Status COMPLETED hanya dapat dipilih apabila Driver telah melakukan konfirmasi selesai.

---

## Jenis Kambing

Setiap Paket wajib memiliki **Jenis Kambing** sebagai acuan produksi.

Pilihan Jenis Kambing:

- A
- B
- C
- D
- Istimewa
- Istimewa+
- Super
- Super+

Business Rules:

- Jenis Kambing default diambil dari Master Paket.
- Customer Service dapat mengubah Jenis Kambing pada saat Order dibuat atau diubah.
- Perubahan hanya berlaku pada Order tersebut.
- Perubahan tidak mengubah Master Paket.
- Rekap Produksi menggunakan Jenis Kambing yang tersimpan pada Order, bukan pada Master Paket.

---

# 3.14.16 Perubahan Master Paket

Tambahkan field baru pada Master Paket.

| Field     | Tipe          | Keterangan            |
| --------- | ------------- | --------------------- |
| goat_type | FK → GoatType | Jenis Kambing Default |

Field ini digunakan sebagai nilai default ketika Paket dipilih pada Order.

---

# 3.14.17 Master Jenis Kambing

Tambahkan Master Data baru.

```
Master Data
    Jenis Kambing
```

| Field          | Tipe        | Keterangan         |
| -------------- | ----------- | ------------------ |
| goat_type_id   | Char(20)    | Primary Key        |
| goat_type_name | Varchar(50) | Nama Jenis Kambing |
| display_order  | Integer     | Urutan Tampil      |
| active         | Boolean     | Status Aktif       |

Contoh Data

| Kode | Nama      |
| ---- | --------- |
| A    | Grade A   |
| B    | Grade B   |
| C    | Grade C   |
| D    | Grade D   |
| IST  | Istimewa  |
| IST+ | Istimewa+ |
| SUP  | Super     |
| SUP+ | Super+    |

---

# 3.14.18 Notifikasi

Sidebar

```
Jadwal Pesanan (12)
```

Badge menampilkan jumlah:

- UNSCHEDULED
- OVERDUE

---

# 3.14.19 Future Enhancement

Versi berikutnya akan mendukung:

- Drag & Drop Calendar
- Google Maps Integration
- GPS Tracking
- Mobile Driver
- Proof of Delivery
- Upload Foto
- Digital Signature
- WhatsApp Notification
- Optimasi Rute Pengiriman

---

# 3.14.20 Acceptance Criteria

- Jadwal otomatis dibuat ketika Order dikonfirmasi.
- Rekap produksi dihitung otomatis.
- Rekap Jenis Kambing dihitung otomatis.
- Driver dapat ditentukan.
- Jadwal dapat diubah.
- Dashboard menampilkan kondisi operasional secara real-time.
- Tidak ada bentrok jadwal driver.
- Jenis Kambing tampil pada Jadwal Pesanan.
- Jenis Kambing digunakan sebagai dasar rekap produksi.
- Dapat diekspor ke Excel.
- Dapat dicetak sebagai Jadwal Harian.

---

## 4. Arsitektur Teknis

### 4.1 Tech Stack

```
Backend:       Django 4.2 / Python 3.11
Database:      MySQL (via pymysql)
Frontend:      Bootstrap 5 + Soft UI Dashboard (Argon Design System)
JavaScript:    jQuery + DataTables
PDF Engine:    ReportLab + xhtml2pdf + PyPDF2
Rich Editor:   TinyMCE
Charts:        Chart.js (tersedia, belum aktif)
Email:         SMTP via mail.ksisolusi.com
```

### 4.2 Key Libraries

| Library                    | Versi | Fungsi                          |
| -------------------------- | ----- | ------------------------------- |
| `django`                   | 5.0.6 | Core framework                  |
| `pillow`                   | —     | Image processing                |
| `pymysql`                  | —     | MySQL adapter                   |
| `django-crum`              | —     | Current request user middleware |
| `phonenumbers`             | —     | Phone validation                |
| `django-phonenumber-field` | —     | Phone field                     |
| `dj-database-url`          | —     | DB URL parsing (production)     |
| `django-import-export`     | —     | Data import/export              |
| `django-auto-logout`       | —     | Session timeout                 |
| `pytz`                     | —     | Timezone handling               |
| `xlwt`                     | —     | Excel .xls generation           |
| `xlsxwriter`               | —     | Excel .xlsx generation          |
| `django-mathfilters`       | —     | Template math filters           |
| `reportlab`                | —     | PDF generation                  |
| `pypdf2`                   | —     | PDF merging                     |
| `xhtml2pdf`                | —     | HTML to PDF                     |
| `requests`                 | —     | HTTP requests                   |
| `django-tinymce`           | —     | Rich text editor                |
| `django-user-agents`       | —     | Mobile/device detection         |

### 4.3 Struktur Proyek

```
aqiqahon/
├── manage.py                    # Django management
├── requirements.txt             # Dependencies
├── core/                        # Konfigurasi Django
│   ├── settings.py              # Settings utama
│   ├── urls.py                  # Root URL routing
│   ├── wsgi.py                  # WSGI entry point
│   └── asgi.py                  # ASGI entry point
├── apps/                        # Modul aplikasi utama
│   ├── models.py                # 50+ model database (~1032 baris)
│   ├── views.py                 # View functions (~6928 baris)
│   ├── urls.py                  # URL routing (~317 baris)
│   ├── forms.py                 # Django forms (~1260 baris)
│   ├── mail.py                  # Email utility
│   ├── host.py                  # Base URL config
│   ├── notifications.py         # Notifikasi pesanan
│   ├── validators.py            # Custom validators
│   ├── media/                   # Upload files
│   ├── static/                  # Static assets
│   ├── staticfiles/             # Collected static
│   ├── templates/               # HTML templates
│   │   ├── accounts/            # Login page
│   │   ├── layouts/             # Base layouts
│   │   ├── includes/            # Reusable components
│   │   └── home/                # 80+ page templates
│   └── templatetags/            # Custom template filters
├── authentication/              # Modul autentikasi
│   ├── views.py                 # Login/logout views
│   ├── decorators.py            # Role-based decorator
│   └── forms.py                 # Login form
└── venv/                        # Virtual environment
```

### 4.4 Konfigurasi Database

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'aqiqahon',
        'USER': 'root',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
# Production: menggunakan DATABASE_URL environment variable
```

### 4.5 Konfigurasi Keamanan

```python
AUTO_LOGOUT = {
    'IDLE_TIME': timedelta(minutes=15),
    'REDIRECT_TO_LOGIN_IMMEDIATELY': True,
}
# SECRET_KEY dari environment variable
# DEBUG dikontrol via environment variable
```

---

## 5. Struktur Database (50+ Models)

### 5.1 Entity Inti

| Model          | PK                         | Keterangan                        |
| -------------- | -------------------------- | --------------------------------- |
| `User`         | `user_id` (Char)           | Custom user, extends AbstractUser |
| `Position`     | `position_id` (Char(3))    | Jabatan                           |
| `Menu`         | `menu_id` (Char)           | Menu sistem                       |
| `Auth`         | Auto (Unique: user+menu)   | Permission per menu               |
| `Channel`      | `channel_id` (Char(5))     | Saluran penjualan                 |
| `Distributor`  | `distributor_id` (Char)    | Distributor + kode SAP            |
| `AreaSales`    | `area_id` (Char)           | Cabang/area penjualan             |
| `AreaUser`     | Auto (Unique: area+user)   | Assignment user ke area           |
| `Region`       | `region_id` (Char)         | Pengelompokan region              |
| `RegionDetail` | Auto (Unique: region+area) | Detail region-area                |
| `Division`     | —                          | Divisi organisasi                 |

### 5.2 Pelanggan

| Model            | PK                                 | Keterangan            |
| ---------------- | ---------------------------------- | --------------------- |
| `Customer`       | `customer_id` (BigAutoField)       | Data pelanggan        |
| `CustomerDetail` | Auto (Unique: customer+child_name) | Detail anak pelanggan |

### 5.3 Katalog Paket

| Model            | Relasi              | Keterangan              |
| ---------------- | ------------------- | ----------------------- |
| `Cuisine`        | —                   | Daftar masakan          |
| `Equipment`      | —                   | Daftar equipment        |
| `Category`       | —                   | Kategori paket          |
| `Package`        | FK → Category       | Paket aqiqah            |
| `Rice`           | Package ↔ Cuisine   | Pilihan beras per paket |
| `MainCuisine`    | Package ↔ Cuisine   | Masakan utama per paket |
| `SubCuisine`     | Package ↔ Cuisine   | Sub masakan per paket   |
| `SideCuisine1–5` | Package ↔ Cuisine   | Side masakan per paket  |
| `Bag`            | Package ↔ Equipment | Tas per paket           |
| `Beverage`       | Package ↔ Equipment | Minuman per paket       |
| `Souvenir`       | Package ↔ Equipment | Souvenir per paket      |
| `Pack`           | Package ↔ Equipment | Box/kotak per paket     |
| `Other`          | Package ↔ Equipment | Item lain per paket     |
| `Addon`          | Package ↔ Equipment | Addon per paket         |

### 5.4 Pesanan

| Model                  | PK                                         | Keterangan              |
| ---------------------- | ------------------------------------------ | ----------------------- |
| `Order`                | `order_id` (Char)                          | Pesanan utama           |
| `OrderChild`           | Auto (Unique: order+child_name)            | Data anak dalam pesanan |
| `OrderPackage`         | Auto (Unique: order+package)               | Paket dalam pesanan     |
| `OrderPackageSouvenir` | Auto (Unique: order+package+equipment)     | Souvenir pesanan        |
| `OrderPackageAddon`    | Auto (Unique: order+package+equipment)     | Addon pesanan           |
| `OrderLeftoverFood`    | Auto (Unique: order+package+leftover_food) | Sisa makanan            |

### 5.5 Keuangan

| Model            | PK                         | Keterangan            |
| ---------------- | -------------------------- | --------------------- |
| `CashIn`         | `cashin_id` (BigAutoField) | Pencatatan pembayaran |
| `Budget`         | —                          | Anggaran              |
| `BudgetDetail`   | —                          | Detail anggaran       |
| `BudgetRelease`  | —                          | Pelepasan anggaran    |
| `BudgetApproval` | —                          | Approval anggaran     |

### 5.6 Approval & Workflow

| Model             | Keterangan               |
| ----------------- | ------------------------ |
| `Proposal`        | Proposal bisnis          |
| `ProposalRelease` | Pelepasan proposal       |
| `ProposalMatrix`  | Matrix approval proposal |
| `Program`         | Program kerja            |
| `ProgramRelease`  | Pelepasan program        |
| `ProgramMatrix`   | Matrix approval program  |
| `Claim`           | Klaim                    |
| `ClaimRelease`    | Pelepasan klaim          |
| `ClaimMatrix`     | Matrix approval klaim    |
| `CL`              | Claim List               |
| `CLRelease`       | Pelepasan CL             |
| `CLMatrix`        | Matrix approval CL       |
| `CLDetail`        | Detail CL                |

### 5.7 Lainnya

| Model              | Keterangan                 |
| ------------------ | -------------------------- |
| `Promo`            | Promosi                    |
| `PromoDetail`      | Detail hadiah promo        |
| `Closing`          | Periode penutupan keuangan |
| `IncrementalSales` | Penjualan incremental      |
| `ProjectedCost`    | Proyeksi biaya             |
| `UploadLog`        | Log upload file            |
| `BoxType`          | Tipe box                   |

### 5.8 Audit Trail

Semua model menggunakan field:

- `entry_date` — Waktu pembuatan record
- `entry_by` — User yang membuat record
- `update_date` — Waktu update terakhir
- `update_by` — User yang terakhir mengupdate

Auto-tracking via `crum.get_current_user()` di method `save()`.

---

## 6. Route Lengkap

### 6.1 Autentikasi

| Route         | View             | Deskripsi     |
| ------------- | ---------------- | ------------- |
| `/login/`     | `login_view`     | Halaman login |
| `/logout/`    | Django built-in  | Logout        |
| `/forbidden/` | `forbidden_view` | Akses ditolak |

### 6.2 Home

| Route | View   | Deskripsi                         |
| ----- | ------ | --------------------------------- |
| `/`   | `home` | Dashboard dengan notifikasi draft |

### 6.3 Data Master

| Route Prefix                           | View                      | Deskripsi                  |
| -------------------------------------- | ------------------------- | -------------------------- |
| `/master/user/`                        | `user_index`              | Daftar pengguna            |
| `/master/user/add/`                    | `user_add`                | Tambah pengguna            |
| `/master/user/view/<id>/`              | `user_view`               | Detail pengguna + auth     |
| `/master/user/update/<id>/`            | `user_update`             | Edit pengguna              |
| `/master/user/delete/<id>/`            | `user_delete`             | Hapus pengguna             |
| `/master/user/change-password/`        | `change_password`         | Ganti password             |
| `/master/user/set-password/<id>/`      | `set_password`            | Atur password user lain    |
| `/master/user-area/view/<id>/`         | `user_area_view`          | Kelola area user           |
| `/master/area-sales/`                  | `area_sales_index`        | Daftar cabang              |
| `/master/area-sales/add/`              | `area_sales_add`          | Tambah cabang              |
| `/master/area-sales/view/<id>/`        | `area_sales_view`         | Detail cabang              |
| `/master/area-sales/update/<id>/`      | `area_sales_update`       | Edit cabang                |
| `/master/area-sales/delete/<id>/`      | `area_sales_delete`       | Hapus cabang               |
| `/master/position/`                    | `position_index`          | Daftar posisi              |
| `/master/position/add/`                | `position_add`            | Tambah posisi              |
| `/master/position/view/<id>/`          | `position_view`           | Detail posisi              |
| `/master/position/update/<id>/`        | `position_update`         | Edit posisi                |
| `/master/position/delete/<id>/`        | `position_delete`         | Hapus posisi               |
| `/master/menu/`                        | `menu_index`              | Daftar menu                |
| `/master/menu/add/`                    | `menu_add`                | Tambah menu                |
| `/master/menu/view/<id>/`              | `menu_view`               | Detail menu                |
| `/master/menu/update/<id>/`            | `menu_update`             | Edit menu                  |
| `/master/menu/delete/<id>/`            | `menu_delete`             | Hapus menu                 |
| `/master/cuisine/`                     | `cuisine_index`           | Daftar masakan             |
| `/master/cuisine/add/`                 | `cuisine_add`             | Tambah masakan             |
| `/master/cuisine/view/<id>/`           | `cuisine_view`            | Detail masakan             |
| `/master/cuisine/update/<id>/`         | `cuisine_update`          | Edit masakan               |
| `/master/cuisine/delete/<id>/`         | `cuisine_delete`          | Hapus masakan              |
| `/master/equipment/`                   | `equipment_index`         | Daftar equipment           |
| `/master/equipment/add/`               | `equipment_add`           | Tambah equipment           |
| `/master/equipment/view/<id>/`         | `equipment_view`          | Detail equipment           |
| `/master/equipment/update/<id>/`       | `equipment_update`        | Edit equipment             |
| `/master/equipment/delete/<id>/`       | `equipment_delete`        | Hapus equipment            |
| `/master/category/`                    | `category_index`          | Daftar kategori            |
| `/master/category/add/`                | `category_add`            | Tambah kategori            |
| `/master/category/view/<id>/`          | `category_view`           | Detail kategori            |
| `/master/category/update/<id>/`        | `category_update`         | Edit kategori              |
| `/master/category/delete/<id>/`        | `category_delete`         | Hapus kategori             |
| `/master/package/`                     | `package_index`           | Daftar paket               |
| `/master/package/add/`                 | `package_add`             | Tambah paket               |
| `/master/package/view/<id>/`           | `package_view`            | Detail paket               |
| `/master/package/update/<id>/`         | `package_update`          | Edit paket                 |
| `/master/package/delete/<id>/`         | `package_delete`          | Hapus paket                |
| `/master/package-rice/<id>/`           | `package_rice_view`       | Kelola beras paket         |
| `/master/package-maincuisine/<id>/`    | —                         | Kelola masakan utama paket |
| `/master/package-subcuisine/<id>/`     | `package_subcuisine_view` | Kelola sub masakan paket   |
| `/master/package-sidecuisine1-5/<id>/` | —                         | Kelola side masakan paket  |
| `/master/package-beverage/<id>/`       | `package_beverage_view`   | Kelola minuman paket       |
| `/master/package-bag/<id>/`            | `package_bag_view`        | Kelola tas paket           |
| `/master/package-box/<id>/`            | `package_box_view`        | Kelola box paket           |
| `/master/package-souvenir/<id>/`       | `package_souvenirs_view`  | Kelola souvenir paket      |
| `/master/package-addon/<id>/`          | `package_addon_view`      | Kelola addon paket         |
| `/master/channel/`                     | `channel_index`           | Daftar channel             |
| `/master/channel/add/`                 | `channel_add`             | Tambah channel             |
| `/master/channel/view/<id>/`           | `channel_view`            | Detail channel             |
| `/master/channel/update/<id>/`         | `channel_update`          | Edit channel               |
| `/master/channel/delete/<id>/`         | `channel_delete`          | Hapus channel              |
| `/master/closing-period/`              | `closing_index`           | Daftar closing period      |
| `/master/closing-period/add/`          | `closing_add`             | Tambah closing period      |
| `/master/closing-period/view/<id>/`    | `closing_view`            | Detail closing period      |
| `/master/closing-period/update/<id>/`  | `closing_update`          | Edit closing period        |
| `/master/closing-period/delete/<id>/`  | `closing_delete`          | Hapus closing period       |
| `/master/division/`                    | `division_index`          | Daftar divisi              |
| `/master/division/add/`                | `division_add`            | Tambah divisi              |
| `/master/division/view/<id>/`          | `division_view`           | Detail divisi              |
| `/master/division/update/<id>/`        | `division_update`         | Edit divisi                |
| `/master/division/delete/<id>/`        | `division_delete`         | Hapus divisi               |
| `/master/region/`                      | `region_index`            | Daftar region              |
| `/master/region/add/`                  | `region_add`              | Tambah region              |
| `/master/region/view/<id>/`            | `region_view`             | Detail region              |
| `/master/region/update/<id>/`          | `region_update`           | Edit region                |
| `/master/region/delete/<id>/`          | `region_delete`           | Hapus region               |
| `/master/customer/`                    | `customer_index`          | Daftar pelanggan           |
| `/master/customer/add/`                | `customer_add`            | Tambah pelanggan           |
| `/master/customer/view/<id>/`          | `customer_view`           | Detail pelanggan           |
| `/master/customer/update/<id>/`        | `customer_update`         | Edit pelanggan             |
| `/master/customer/delete/<id>/`        | `customer_delete`         | Hapus pelanggan            |
| `/master/promo/`                       | `promo_index`             | Daftar promo               |
| `/master/promo/add/`                   | `promo_add`               | Tambah promo               |
| `/master/promo/view/<id>/`             | `promo_view`              | Detail promo               |
| `/master/promo/update/<id>/`           | `promo_update`            | Edit promo                 |
| `/master/promo/delete/<id>/`           | `promo_delete`            | Hapus promo                |
| `/master/distributor/`                 | `distributor_index`       | Daftar distributor         |

### 6.4 Transaksi (Pesanan)

| Route                                                             | View                      | Deskripsi                   |
| ----------------------------------------------------------------- | ------------------------- | --------------------------- |
| `/order/new/<area_id>/`                                           | `order_add`               | Form pemesanan publik       |
| `/order/update/<id>/`                                             | `order_update`            | Edit data pesanan           |
| `/order/child/add/<id>/<add>/`                                    | `order_child_add`         | Tambah anak                 |
| `/order/child/update/<id>/<child>/<add>/`                         | `order_child_update`      | Edit anak                   |
| `/order/child/delete/<id>/<child>/`                               | `order_child_delete`      | Hapus anak                  |
| `/order/child/cs/update/<id>/<child>/`                            | `order_child_cs_update`   | CS edit anak                |
| `/order/child/cs/delete/<id>/<child>/`                            | `order_child_cs_delete`   | CS hapus anak               |
| `/order/package/add/<id>/<cat>/<pack>/<type>/<add>/`              | `order_package_add`       | Tambah paket                |
| `/order/package/update/<id>/<package>/<cat>/<pack>/<type>/<add>/` | `order_package_update`    | Edit paket                  |
| `/order/package/delete/<id>/<package>/`                           | `order_package_delete`    | Hapus paket                 |
| `/order/package/cs/update/<id>/<cat>/<pack>/<type>/`              | `order_package_cs_update` | CS edit paket               |
| `/order/package/cs/delete/<id>/<pack>/`                           | `order_package_cs_delete` | CS hapus paket              |
| `/order/confirm/update/<id>/`                                     | `order_confirm_update`    | Edit konfirmasi             |
| `/order/confirm/<id>/`                                            | `order_confirm`           | Review konfirmasi           |
| `/order/submit/<id>/`                                             | `order_submit`            | Submit pesanan              |
| `/order/cancel/<id>/`                                             | `order_cancel`            | Batalkan pesanan            |
| `/order/confirmed/<id>/`                                          | `order_confirmed`         | Konfirmasi pesanan          |
| `/order/<branch>/<date>/`                                         | `order_index`             | Daftar pesanan              |
| `/order/view/<id>/<cat>/<pack>/<type>/<crud>/`                    | `order_view`              | Detail pesanan              |
| `/order/archive/<branch>/<date>/`                                 | `order_archive`           | Pesanan arsip               |
| `/order/cs/update/<id>/<cat>/<pack>/<type>/`                      | `order_cs_update`         | CS update pesanan           |
| `/order/cs/child/add/<id>/`                                       | `order_cs_child_add`      | CS tambah anak              |
| `/order/cs/package/add/<id>/<cat>/<pack>/<type>/`                 | `order_cs_package_add`    | CS tambah paket             |
| `/form/`                                                          | `form_index`              | Daftar form untuk dibagikan |

### 6.5 Keuangan

| Route                           | View              | Deskripsi         |
| ------------------------------- | ----------------- | ----------------- |
| `/cashin/`                      | `cashin_index`    | Daftar uang masuk |
| `/cashin/add/<id>/<msg>/`       | `cashin_add`      | Tambah pembayaran |
| `/cashin/view/<id>/`            | `cashin_view`     | Detail pembayaran |
| `/cashin/update/<id>/<msg>/`    | `cashin_update`   | Edit pembayaran   |
| `/cashin/remove-evidence/<id>/` | `remove_evidence` | Hapus bukti       |
| `/cashin/delete/<id>/`          | `cashin_delete`   | Hapus pembayaran  |

### 6.6 Klaim & Approval

| Route                                             | View                    | Deskripsi            |
| ------------------------------------------------- | ----------------------- | -------------------- |
| `/claim/<tab>/`                                   | `claim_index`           | Daftar klaim         |
| `/claim/add/<area>/<distributor>/<program>/`      | `claim_add`             | Tambah klaim         |
| `/claim/view/<tab>/<id>/`                         | `claim_view`            | Detail klaim         |
| `/claim/update/<tab>/<id>/`                       | `claim_update`          | Edit klaim           |
| `/claim/delete/<tab>/<id>/`                       | `claim_delete`          | Hapus klaim          |
| `/claim_release/`                                 | `claim_release_index`   | Daftar release klaim |
| `/claim_release/view/<id>/<is_revise>/`           | `claim_release_view`    | Detail release       |
| `/claim_release/update/<id>/`                     | `claim_release_update`  | Edit release         |
| `/claim_release/approve/<id>/`                    | `claim_release_approve` | Approve klaim        |
| `/claim_release/return/<id>/`                     | `claim_release_return`  | Return klaim         |
| `/claim_release/reject/<id>/`                     | `claim_release_reject`  | Reject klaim         |
| `/claim_archive/`                                 | `claim_archive_index`   | Klaim arsip          |
| `/matrix/claim/`                                  | `claim_matrix_index`    | Matrix klaim         |
| `/matrix/claim/view/<id>/<channel>/`              | `claim_matrix_view`     | Detail matrix        |
| `/matrix/claim/update/<id>/<channel>/<approver>/` | `claim_matrix_update`   | Edit matrix          |
| `/matrix/claim/delete/<id>/<channel>/<arg>/`      | `claim_matrix_delete`   | Hapus matrix         |
| `/claim_print/<id>/`                              | `claim_print`           | Cetak klaim          |

### 6.7 Dokumen PDF

| Route                    | View              | Deskripsi              |
| ------------------------ | ----------------- | ---------------------- |
| `/order/invoice/<id>/`   | `order_invoice`   | Generate Invoice PDF   |
| `/order/bap/<id>/`       | `order_bap`       | Generate BAP PDF       |
| `/order/checklist/<id>/` | `order_checklist` | Generate Checklist PDF |

### 6.8 Jadwal Pesanan

| Route                | View            | Deskripsi                           |
| -------------------- | --------------- | ----------------------------------- |
| `/jadwal/`           | `jadwal_index`  | Halaman kalender jadwal pesanan     |
| `/jadwal/events/`    | `jadwal_events` | API JSON untuk data event kalender  |

---

## 7. Spesifikasi non-Fungsi

### 7.1 Keamanan

| Aspek               | Implementasi                                                         |
| ------------------- | -------------------------------------------------------------------- |
| Autentikasi         | Session-based, user_id + password                                    |
| Otorisasi           | RBAC per menu dengan flag add/edit/delete                            |
| Session Timeout     | 15 menit idle → auto-logout                                          |
| CSRF Protection     | Django CSRF middleware                                               |
| Password Validation | Django built-in validators (similarity, min length, common, numeric) |
| SQL Injection       | Django ORM + parameterized queries                                   |
| File Upload         | Validasi tipe file                                                   |

### 7.2 Audit

| Aspek            | Implementasi                            |
| ---------------- | --------------------------------------- |
| Create Tracking  | `entry_date`, `entry_by` auto-filled    |
| Update Tracking  | `update_date`, `update_by` auto-updated |
| User Attribution | `crum.get_current_user()`               |

### 7.3 Responsive Design

| Aspek            | Implementasi                                                                 |
| ---------------- | ---------------------------------------------------------------------------- |
| Mobile Detection | `django-user-agents`                                                         |
| UI Framework     | Bootstrap 5 + Soft UI Dashboard                                              |
| DataTables       | Tabel interaktif dengan search, sort, pagination                             |
| Mobile Sidebar   | Sidebar hidden by default, toggle via hamburger menu, slide animation        |
| Mobile Reminder  | Reminder dropdown centered on modal overlay, scroll lock on body             |
| Sidebar Close    | Close button (X) visible on mobile, hidden on desktop                        |

### 7.4 Performa

| Aspek         | Implementasi                                      |
| ------------- | ------------------------------------------------- |
| Raw SQL       | Digunakan untuk query kompleks (JOIN multi-table) |
| Paginator     | Django Paginator (25 item/halaman default)        |
| Static Files  | `collectstatic` untuk production                  |
| Cache Control | Header no-cache pada halaman login                |

### 7.5 Deployment

| Aspek         | Implementasi                                |
| ------------- | ------------------------------------------- |
| WSGI          | `core.wsgi` (Gunicorn-ready)                |
| Database      | MySQL (localhost) / `DATABASE_URL` env var  |
| Debug Mode    | `DEBUG` env var (default: True)             |
| Allowed Hosts | `ALLOWED_HOSTS` env var                     |
| Media Files   | `apps/media/` (upload ke production server) |
| Static Files  | `apps/staticfiles/` (collected)             |

### 7.6 Email

| Aspek   | Implementasi                            |
| ------- | --------------------------------------- |
| Backend | SMTP (`django.core.mail.backends.smtp`) |
| Host    | `mail.ksisolusi.com`                    |
| Port    | 465 (SSL)                               |
| Fungsi  | Notifikasi approval, pengiriman email   |

---

## 8. Validasi Data

### 8.1 Validasi Tanggal

| Field           | Aturan                           |
| --------------- | -------------------------------- |
| `delivery_date` | Tidak boleh kurang dari hari ini |
| `child_birth`   | Tidak boleh melebihi hari ini    |

### 8.2 Validasi Uniqueness

| Model                  | Unique Constraint               |
| ---------------------- | ------------------------------- |
| `AreaUser`             | (area, user)                    |
| `Auth`                 | (user, menu)                    |
| `CustomerDetail`       | (customer, child_name)          |
| `OrderChild`           | (order, child_name)             |
| `OrderPackage`         | (order, package)                |
| `OrderPackageSouvenir` | (order, package, equipment)     |
| `OrderPackageAddon`    | (order, package, equipment)     |
| `OrderLeftoverFood`    | (order, package, leftover_food) |
| `Rice`                 | (package, cuisine)              |
| `MainCuisine`          | (package, cuisine)              |
| `SubCuisine`           | (package, cuisine)              |
| `SideCuisine1-5`       | (package, cuisine)              |
| `Bag`                  | (package, equipment)            |
| `Beverage`             | (package, equipment)            |
| `Souvenir`             | (package, equipment)            |
| `Pack`                 | (package, equipment)            |
| `Other`                | (package, equipment)            |
| `Addon`                | (package, equipment)            |
| `PromoDetail`          | (promo, gift)                   |
| `RegionDetail`         | (region, area)                  |

---

## 9. Formulir & Input

### 9.1 Widget

| Widget                      | Penggunaan                           |
| --------------------------- | ------------------------------------ |
| `form-control-sm`           | Semua input fields                   |
| `form-select-sm`            | Dropdown selects                     |
| `DateInput` (type=date)     | Tanggal pengiriman, tanggal lahir    |
| `NumberInput` (no-spinners) | Harga, kuantitas                     |
| `FileInput`                 | Upload bukti, tanda tangan, proposal |
| `TinyMCE`                   | Editor rich text (konten program)    |
| `PasswordInput`             | Password fields                      |
| `EmailInput`                | Email fields                         |

### 9.2 Mixin Validasi

| Mixin                              | Fungsi                                 |
| ---------------------------------- | -------------------------------------- |
| `OrderDeliveryDateValidationMixin` | Validasi tanggal pengiriman ≥ hari ini |
| `OrderChildBirthValidationMixin`   | Validasi tanggal lahir ≤ hari ini      |

---

## 10. Template & UI

### 10.1 Struktur Template

```
templates/
├── accounts/
│   └── login.html              # Halaman login
├── layouts/                    # Base templates
├── includes/
│   ├── sidebar.html            # Sidebar navigasi
│   ├── navigation.html         # Top navigation
│   └── footer.html             # Footer
└── home/
    ├── index.html              # Dashboard
    ├── user_*.html             # CRUD user (8+ files)
    ├── area_sales_*.html       # CRUD area sales
    ├── position_*.html         # CRUD position
    ├── menu_*.html             # CRUD menu
    ├── cuisine_*.html          # CRUD cuisine
    ├── equipment_*.html        # CRUD equipment
    ├── category_*.html         # CRUD category
    ├── package_*.html          # CRUD package + detail views
    ├── promo_*.html            # CRUD promo
    ├── region_*.html           # CRUD region
    ├── channel_*.html          # CRUD channel
    ├── division_*.html         # CRUD division
    ├── closing_*.html          # CRUD closing period
    ├── distributor_*.html      # CRUD distributor
    ├── customer_*.html         # CRUD customer
    ├── order_*.html            # Order flow (20+ files)
    ├── cashin_*.html           # Cash-in flow
    ├── claim_*.html            # Claim flow
    ├── jadwal_index.html        # Kalender jadwal pesanan
    └── forbidden.html          # Halaman akses ditolak
```

### 10.2 Sidebar Navigation

| Section         | Menu                                                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Transaksi**   | Pemesanan, Form, Arsip, **Jadwal**                                                                                                          |
| **Keuangan**    | Uang Masuk                                                                                                                                  |
| **Klaim**       | Klaim, Klaim Release, Klaim Archive, Matrix                                                                                                 |
| **Data Master** | Pengguna, Pelanggan, Cabang, Posisi, Menu, Masakan, Pelengkap, Kategori, Paket, Promo, Region, Channel, Divisi, Distributor, Closing Period |

---

## 11. Status Saat Ini

Aplikasi **fully functional** dengan fitur:

- Pemesanan aqiqah online via link publik
- Manajemen data master lengkap (16+ modul CRUD)
- Pencatatan keuangan dengan bukti transfer
- Proses approval multi-level (klaim, proposal, program)
- Generate dokumen PDF (Invoice, BAP, Checklist)
- Sistem notifikasi draft pesanan
- Export data ke Excel
- **Mobile-responsive sidebar** (slide in/out, overlay backdrop)
- **Mobile reminder dropdown** (centered modal, scroll lock)
- Auto-logout 15 menit
- Audit trail lengkap

---

_Document updated: 19 Juli 2026_
_Version: 2.1_
_Based on codebase analysis of AqiqahOn application_
