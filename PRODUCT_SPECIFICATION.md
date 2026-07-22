# Product Specification: AqiqahOn

## 1. Overview

**Nama Produk:** AqiqahOn  
**Versi:** 1.1
**Platform:** Web Application (Responsive)  
**URL Produksi:** aqiqahon.sahabataqiqah.co.id  
**Deskripsi:** Sistem manajemen bisnis end-to-end untuk perusahaan layanan aqiqah "Sahabat Aqiqah", mencakup pemesanan, keuangan, dan manajemen data master.

---

## 2. Tech Stack

### Backend

| Komponen         | Teknologi                              | Versi  |
| ---------------- | -------------------------------------- | ------ |
| Framework        | Django                                 | 4.2    |
| Bahasa           | Python                                 | 3.11.3 |
| Database         | MySQL                                  | -      |
| ORM              | Django ORM                             | -      |
| PDF Generator    | ReportLab, xhtml2pdf, PyPDF2           | -      |
| Export Excel     | xlwt (.xls), xlsxwriter (.xlsx)        | -      |
| Rich Text        | TinyMCE                                | -      |
| Phone Validation | django-phonenumber-field, phonenumbers | -      |
| Audit Trail      | django-crum                            | -      |
| Session Timeout  | django-auto-logout                     | -      |
| Device Detection | django-user-agents                     | -      |
| Image Processing | Pillow                                 | -      |

### Frontend

| Komponen         | Teknologi                       | Versi  |
| ---------------- | ------------------------------- | ------ |
| CSS Framework    | Bootstrap                       | 5.3    |
| UI Design        | Soft UI Dashboard (Argon-based) | -      |
| JavaScript       | jQuery                          | 3.6    |
| Date/Time Picker | jQuery UI                       | 1.12   |
| Data Tables      | DataTables                      | 1.13.5 |
| Icons            | Font Awesome, Nucleo Icons      | -      |
| Notifications    | Notyf                           | -      |
| Dark Mode        | Custom CSS                      | -      |

---

## 3. User Roles & Access Control

### 3.1 Authentication

- Login menggunakan `user_id` + password (bukan email)
- `USERNAME_FIELD = 'user_id'`
- Auto-logout setelah 15 menit tidak aktif (via `django-auto-logout`)
- Cache control pada halaman login (`no_cache, must_revalidate, no_store`)

### 3.2 Role-Based Access Control (RBAC)

- Permission per menu: `add`, `edit`, `delete` (boolean flags)
- Decorator `@role_required(allowed_roles='MENU_ID')` pada setiap view
- Superuser bypass semua pengecekan RBAC
- Menu yang tidak diakses akan tersembunyi/di-disable di sidebar

### 3.3 Menu RBAC IDs

| Menu ID       | Keterangan          |
| ------------- | ------------------- |
| USER          | Manajemen Pengguna  |
| AREA-SALES    | Manajemen Cabang    |
| PROMO         | Manajemen Promo     |
| POSITION      | Manajemen Posisi    |
| MENU          | Manajemen Menu      |
| CUISINE       | Manajemen Masakan   |
| EQUIPMENT     | Manajemen Pelengkap |
| CATEGORY      | Manajemen Kategori  |
| PACKAGE       | Manajemen Paket     |
| REGION        | Manajemen Region    |
| CUSTOMER      | Manajemen Pelanggan |
| FORM          | Form Pemesanan      |
| ORDER         | Pesanan             |
| ORDER-ARCHIVE | Arsip Pesanan       |
| CASH-IN       | Uang Masuk          |

---

## 4. Feature Modules

### 4.1 Transaksi (Transactions)

#### 4.1.1 Form Pemesanan

**Endpoint:** `GET /form/`  
**Akses:** Menu `FORM`  
**Fitur:**

- Menampilkan daftar semua cabang (AreaSales)
- Setiap cabang memiliki URL form pemesanan unik: `/order/new/<area_id>/`

#### 4.1.2 Pemesanan (Orders)

**Endpoint Publik:** `/order/new/<area_id>/` (tanpa login)  
**Endpoint Internal:** `/order/<branch>/<date>/`

**Fitur Pemesanan Publik (Customer):**

- Form pemesanan publik yang dapat diakses per cabang
- Input data pelanggan:
  - Nama lengkap (`customer_name`)
  - Telepon utama & alternatif (`customer_phone`, `customer_phone2`)
  - Email (`customer_email`)
  - Alamat lengkap (`customer_address`, `customer_district`, `customer_city`, `customer_province`)
- Input data anak (`OrderChild`):
  - Nama anak (`child_name`)
  - Tanggal lahir (`child_birth`)
  - Jenis kelamin (`child_sex`: L/P)
  - Nama ayah (`child_father`)
  - Nama ibu (`child_mother`)
- Pilihan paket (`OrderPackage`):
  - Kategori paket
  - Jenis paket (jantan/betina)
  - Kuantitas (`quantity`)
  - Komposisi: nasi, masakan utama, sub masakan, side cuisine 1-5, minuman, tas, box, souvenir
  - Addon (item tambahan dengan harga per unit)
  - Souvenir per paket (`OrderPackageSouvenir`)
- Pilihan sisa makanan (`OrderLeftoverFood`)
- Informasi tambahan:
  - Promo (`promo`, `promo_nominal`)
  - Gunakan foto (`use_photo`)
  - Disaksikan (`witnessed`)
  - Sumber informasi (`info_source`)
  - Catatan pesanan (`order_note`)
- Status awal: `PENDING`
- `entry_by` di-set `'customer'` untuk semua record pesanan

**Fitur Internal (Staff/CS):**

- Lihat daftar pesanan dengan filter cabang dan tanggal
- Pencarian berdasarkan: `order_id`, `customer_name`, `cs`, `regional__area_name`, `order_status`
- Pagination otomatis
- Status pesanan: `PENDING`, `DRAFT`, `CONFIRMED`, `DP`, `LUNAS`, `BATAL`
- CS dapat mengubah pesanan via endpoint `cs/update` dan `cs/package/update`
- CS dapat menambah anak dan paket via endpoint `cs/child/add` dan `cs/package/add`
- Konfirmasi pesanan: `/order/confirm/<id>/` dan `/order/confirm/update/<id>/`
- Submit pesanan: `/order/submit/<id>/`
- Batalkan pesanan: `/order/cancel/<id>/`

**Kalkulasi Otomatis (di `save()` method):**

- `pending_payment = total_order - down_payment - discount`
- `total_price = (quantity * unit_price) + extra_price` (per paket)

#### 4.1.3 Arsip (Archive)

**Endpoint:** `/order/archive/<branch>/<date>/`  
**Akses:** Menu `ORDER-ARCHIVE`  
**Fitur:**

- Menampilkan pesanan dengan `delivery_date < hari ini - 90 hari`
- Filter: semua pesanan selesai/dibatalkan (kecuali `PENDING`)
- Pencarian dan pagination

#### 4.1.4 Dokumen PDF

**Endpoint:**

- Invoice: `/order/invoice/<id>/`
- BAP: `/order/bap/<id>/`
- Checklist: `/order/checklist/<id>/`

**Detail Invoice:**

- Header dengan data cabang dan logo
- Data pelanggan dan anak
- Tabel paket: nama paket, jumlah, harga satuan, total
- Rincian komposisi per paket (nasi, masakan, pelengkap, dll)
- Sub Total, Diskon, DP, Jumlah Tertagih
- Syarat & Ketentuan (pengiriman, jam tiba, jam acara, catatan)
- Tanda tangan digital

**Detail BAP:**

- Checklist item per paket
- Rincian komposisi (nasi, masakan utama, sub, side 1-5, other, addon, minuman, sertifikat, tas, souvenir)
- Sisa masakan olahan daging dan tulangan

### 4.2 Keuangan (Finance)

#### 4.2.1 Uang Masuk (Cash In / Payments)

**Endpoint:** `/cashin/`  
**Akses:** Menu `CASH-IN`

**Fitur:**

- Daftar semua pembayaran dengan pencarian
- Tambah pembayaran: `/cashin/add/<order_id>/<msg>/`
  - Pilih pesanan (hanya yang `order_status` = `DP` atau `CONFIRMED` dan `pending_payment > 0`)
  - Jenis pembayaran (`cashin_type`)
  - Nominal (`cashin_amount`)
  - Catatan (`cashin_note`)
  - Nama bank (`bank`)
  - Upload bukti pembayaran (`evidence`, file upload ke `cashin/`)
- Update pembayaran: `/cashin/update/<id>/<msg>/`
  - Validasi: nominal tidak boleh melebihi `pending_payment`
  - Dapat mengubah target pesanan
- Hapus bukti: `/cashin/remove-evidence/<id>/`
- Hapus pembayaran: `/cashin/delete/<id>/`
- Auto-sync file ke production server (saat `DEBUG=False`)

---

# 4.3 Order Schedule (Jadwal Pesanan)

## Overview

Modul **Order Schedule** merupakan pusat operasional yang mengelola seluruh aktivitas setelah pesanan dikonfirmasi hingga pesanan selesai dikirim kepada pelanggan.

Modul ini berfungsi sebagai penghubung antara:

- Order
- Produksi Dapur
- Packing
- Pengiriman
- Monitoring Operasional

Setiap Order yang berstatus **CONFIRMED** akan secara otomatis menghasilkan satu data **Order Schedule**.

---

# User Roles

| Role              | Permission        |
| ----------------- | ----------------- |
| Superuser         | Full Access       |
| Customer Service  | View, Add, Edit   |
| Admin Operasional | Full Access       |
| Kepala Dapur      | View              |
| Driver            | View Own Schedule |

RBAC Menu ID

```
ORDER-SCHEDULE
```

---

# Menu

```
Transaksi
    Order
    Jadwal Pesanan
    Arsip
```

---

# Endpoint

| Method | URL                           |
| ------ | ----------------------------- |
| GET    | /schedule/                    |
| GET    | /schedule/view/<id>/          |
| GET    | /schedule/calendar/           |
| GET    | /schedule/kitchen/            |
| GET    | /schedule/delivery/           |
| POST   | /schedule/update/<id>/        |
| POST   | /schedule/change-status/<id>/ |
| POST   | /schedule/assign-driver/<id>/ |
| POST   | /schedule/reschedule/<id>/    |
| GET    | /schedule/export/             |
| GET    | /schedule/report/daily/       |
| GET    | /schedule/report/kitchen/     |
| GET    | /schedule/report/driver/      |

---

# Features

- Daily Schedule
- Calendar View
- Kitchen View
- Delivery View
- Driver Assignment
- Vehicle Assignment
- Production Schedule
- Packing Schedule
- Delivery Schedule
- Dashboard
- Production Summary
- Goat Summary
- Cuisine Summary
- Equipment Summary
- Timeline
- Reminder
- Notification
- Export Excel
- Print Daily Schedule

---

# Schedule Status

| Status      | Description       |
| ----------- | ----------------- |
| UNSCHEDULED | Belum dijadwalkan |
| SCHEDULED   | Sudah dijadwalkan |
| COOKING     | Sedang produksi   |
| PACKING     | Sedang packing    |
| READY       | Siap dikirim      |
| ON DELIVERY | Sedang dikirim    |
| COMPLETED   | Selesai           |
| CANCELLED   | Dibatalkan        |

---

# Schedule List

Default Filter

- Hari Ini

Filter

- Delivery Date
- Event Date
- Customer
- Driver
- Status
- Region
- Branch
- Goat Type

Columns

| Field         |
| ------------- |
| Delivery Date |
| Delivery Time |
| Event Time    |
| Invoice       |
| Customer      |
| Package       |
| Goat Type     |
| Total Box     |
| Driver        |
| Status        |

---

# Detail Schedule

## General Information

- Order Number
- Invoice Number
- Customer
- Branch
- Region
- Address
- Phone
- Event Time
- Delivery Time

---

## Package Information

| Field         |
| ------------- |
| Package       |
| Goat Type     |
| Goat Quantity |
| Total Box     |

---

## Production

| Field             |
| ----------------- |
| Production Start  |
| Production Finish |
| Packing Start     |
| Packing Finish    |

---

## Delivery

| Field           |
| --------------- |
| Driver          |
| Vehicle         |
| Departure Time  |
| ETA             |
| Delivery Status |

---

# Dashboard

## Operational Dashboard

Widget

- Today's Orders
- Unscheduled
- Cooking
- Packing
- Ready
- On Delivery
- Completed

---

## Kitchen Dashboard

Widget

- Total Goats
- Total Rice
- Total Box (termasuk jumlah Addon dengan Tipe Pelengkap "Box Paket")
- Total Bags
- Total Souvenirs

## Dashboard Recap

Widget

- Recap Masakan: Menampilkan daftar masakan yang sudah dipesan (total > 0), termasuk item Addon dengan Tipe Pelengkap "Masakan"
- Recap Menu Olahan: Menampilkan daftar menu olahan yang sudah dipesan (total > 0), termasuk item Addon dengan Tipe Pelengkap "Olahan Dan Pendamping"
- Recap Box Items: Menampilkan daftar item box yang sudah dipesan (total > 0), termasuk item Addon dengan Tipe Pelengkap "Kemasan Dan Souvenir"
- Rekap Dekorasi: Menampilkan jumlah Qty Paket dengan Dashboard "Dekorasi", dikelompokkan berdasarkan jenis kelamin anak (Laki-Laki / Perempuan)
- Rekap Paket Nasi Box: Menampilkan jumlah Qty Paket dengan Dashboard "Nasi Box"
- Rekap Paket Kambing: Menampilkan rincian Jumlah Porsi menu Daging dan Olahan dari Paket dengan Dashboard "Paket Kambing"
- Rekap Kambing Guling: Menampilkan rincian Jumlah Jenis Kambing (GoatType) dan Tipe (Jantan/Betina) berdasarkan Order Package pada hari yang dipilih

### Konvensi Warna Badge

- `bg-gradient-primary` (biru): digunakan untuk badge angka utama dan label Daging
- `bg-gradient-dark` (hitam): digunakan sebagai pengganti `bg-gradient-info`, untuk badge angka sekunder dan label Olahan
- `bg-gradient-success` (hijau): badge status Selesai
- `bg-gradient-warning` (kuning): badge status Pending
- `bg-gradient-danger` (merah): badge status Batal

---

## Driver Dashboard

Widget

- Today's Delivery
- Tomorrow Delivery
- Delivery History

---

# Production Summary

Automatically generated from Order Packages.

## Goat Summary

| Goat Type | Qty |
| --------- | --- |
| A         | xx  |
| B         | xx  |
| C         | xx  |
| D         | xx  |
| Istimewa  | xx  |
| Istimewa+ | xx  |
| Super     | xx  |
| Super+    | xx  |

---

## Cuisine Summary

Automatically grouped by Cuisine.

Example

| Cuisine  | Qty |
| -------- | --- |
| Sate     | xx  |
| Gulai    | xx  |
| Tongseng | xx  |
| Rendang  | xx  |

---

## Equipment Summary

| Item     | Qty |
| -------- | --- |
| Box      | xx  |
| Bag      | xx  |
| Souvenir | xx  |

### Tipe Pelengkap

Field `tipe` pada model Equipment menentukan ke mana item Addon akan ditampilkan di Dashboard:

| Tipe Pelengkap | Penempatan di Dashboard |
| --- | --- |
| Kemasan Dan Souvenir | Card "Kemasan Dan Souvenir" |
| Masakan | Card "Rekap Masakan" |
| Olahan Dan Pendamping | Card "Rekap Menu Olahan + Pendamping" |
| Box Paket | Ditambahkan ke Total Box di Dashboard Produksi |

---

# Reminder

Reminder will appear when:

- Driver is empty.
- Schedule is overdue.
- Packing not completed.
- Delivery time has passed.
- Status is still Scheduled.

---

# Notification

Sidebar

```
Order Schedule (8)
```

Badge shows

- UNSCHEDULED
- OVERDUE

---

# Database

## Model OrderSchedule

| Field             | Type                  |
| ----------------- | --------------------- |
| schedule_id       | BigAutoField          |
| order             | FK → Order            |
| delivery_date     | DateField             |
| delivery_time     | TimeField             |
| event_time        | TimeField             |
| production_start  | DateTimeField         |
| production_finish | DateTimeField         |
| packing_start     | DateTimeField         |
| packing_finish    | DateTimeField         |
| driver            | FK User               |
| vehicle           | FK Vehicle (nullable) |
| status            | CharField             |
| notes             | TextField             |
| entry_date        | DateTimeField         |
| entry_by          | CharField             |
| update_date       | DateTimeField         |
| update_by         | CharField             |

---

## Model OrderScheduleHistory

| Field      | Type             |
| ---------- | ---------------- |
| history_id | BigAutoField     |
| schedule   | FK OrderSchedule |
| old_status | CharField        |
| new_status | CharField        |
| remark     | TextField        |
| entry_date | DateTimeField    |
| entry_by   | CharField        |

---

# Master Goat Type

Tambahkan Master baru.

Menu

```
Master Data
    Jenis Kambing
```

Model

## GoatType

| Field          | Type          |
| -------------- | ------------- |
| goat_type_id   | CharField(20) |
| goat_type_name | CharField(50) |
| display_order  | IntegerField  |
| active         | BooleanField  |

Sample Data

| Code | Name      |
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

# Master Package Changes

Tambahkan field baru.

| Field     | Type          |
| --------- | ------------- |
| goat_type | FK → GoatType |

Business Rules

- Wajib diisi.
- Menjadi default ketika Package dipilih.

---

# Order Package Changes

Tambahkan field baru.

| Field     | Type          |
| --------- | ------------- |
| goat_type | FK → GoatType |

Business Rules

- Nilai default berasal dari Package.
- Customer Service dapat melakukan override.
- Perubahan tidak memengaruhi Master Package.
- Nilai pada Order Package digunakan sebagai snapshot historis.

---

# Business Flow

```
Customer Order

↓

PENDING

↓

CONFIRMED

↓

Create Order Schedule

↓

UNSCHEDULED

↓

Assign Driver

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

# Business Rules

## Auto Create

Ketika Order menjadi

```
CONFIRMED
```

Sistem otomatis membuat Order Schedule.

---

## Driver Validation

Satu Driver tidak boleh memiliki dua pengiriman pada waktu yang sama.

---

## Production Validation

Delivery Time harus lebih besar daripada Production Finish.

---

## Packing Validation

Status READY hanya dapat dipilih apabila Packing telah selesai.

---

## Completion Validation

Status COMPLETED hanya dapat dipilih apabila Delivery telah selesai.

---

## Goat Type Validation

- Goat Type wajib diisi.
- Goat Type mengikuti nilai pada Order Package.
- Rekap produksi menggunakan Goat Type dari Order Package.
- Perubahan Goat Type di Master Package tidak mengubah Order yang sudah dibuat.

---

# Export

Format

- Excel
- PDF

Laporan

- Daily Schedule
- Kitchen Summary
- Driver Schedule
- Goat Summary
- Cuisine Summary
- Equipment Summary

---

# Performance Requirements

- Mendukung minimal 10.000 Schedule aktif.
- DataTables menggunakan Server-side Processing.
- Waktu pencarian maksimal 2 detik.
- Mendukung export hingga 50.000 baris.

---

# Security

- Role Based Access Control.
- Audit Trail.
- Soft Delete (opsional).
- Log seluruh perubahan status.
- Log perubahan Driver.
- Log perubahan Goat Type.

---

# Audit Trail

Semua perubahan berikut wajib dicatat.

- Driver
- Vehicle
- Delivery Time
- Production Time
- Packing Time
- Goat Type
- Status
- Notes

Audit Trail meliputi:

- Tanggal
- User
- Nilai Lama
- Nilai Baru
- Catatan

---

# Future Enhancement

- Calendar Drag & Drop
- Google Maps API
- GPS Tracking
- WhatsApp Notification
- Proof of Delivery (POD)
- Upload Foto Serah Terima
- Digital Signature
- Mobile Driver App
- Route Optimization
- Kitchen Display Dashboard
- Kitchen TV Mode

---

## 5. Data Master (Master Data)

### 5.1 Pengguna (Users)

**Endpoint:** `/master/user/`  
**Akses:** Menu `USER`  
**Fitur:**

- Daftar semua pengguna (raw SQL JOIN dengan Position)
- Tambah pengguna (`FormUser` - extends `UserCreationForm`)
  - User ID, Nama, Email, Posisi, Tanda Tangan (upload)
  - Password & Konfirmasi Password
- Lihat pengguna (`FormUserView` - readonly)
  - Kelola permission menu (checkbox per menu)
  - Kelola akses area/cabang
  - Kelola posisi
- Update pengguna
- Hapus pengguna
- Hapus tanda tangan: `/master/user/remove-signature/<id>/`
- Ganti password: `/master/user/change-password/`
- Set password user lain: `/master/user/set-password/<id>/`
- Lihat area user: `/master/user-area/view/<id>/`

### 5.2 Pelanggan (Customers)

**Endpoint:** `/master/customer/`  
**Akses:** Menu `CUSTOMER`  
**Model Fields:**
| Field | Tipe | Keterangan |
|---|---|---|
| customer_id | BigAutoField | PK |
| customer_name | CharField(200) | Nama pelanggan |
| customer_address | CharField(200) | Alamat |
| customer_district | CharField(50) | Kecamatan |
| customer_city | CharField(50) | Kota |
| customer_province | CharField(50) | Provinsi |
| customer_phone | CharField(50) | Telepon utama |
| customer_phone2 | CharField(50) | Telepon alternatif |
| customer_email | CharField(50) | Email |

**Fitur:**

- CRUD pelanggan
- Detail anak per pelanggan (`CustomerDetail`):
  - Nama anak, tanggal lahir, jenis kelamin, ayah, ibu
  - Unique constraint: `customer + child_name`

### 5.3 Cabang (Area/Branch)

**Endpoint:** `/master/area-sales/`  
**Akses:** Menu `AREA-SALES`  
**Model Fields:**
| Field | Tipe | Keterangan |
|---|---|---|
| area_id | CharField(50) | PK (auto uppercase) |
| area_name | CharField(50) | Nama cabang |
| manager | CharField(50) | Nama manajer |
| bank_account | CharField(200) | Rekening bank |
| address | CharField(200) | Alamat |
| district | CharField(50) | Kecamatan |
| city | CharField(50) | Kota |
| postal_code | CharField(10) | Kode pos |
| form | CharField(200) | URL form pemesanan |

**Fitur:**

- CRUD cabang
- Hubungan cabang-user (`AreaUser`): unique constraint `area + user`
- Hubungan cabang-distributor (`AreaSalesDetail`)
- Method `get_area_sales_children()`: mengambil semua detail

### 5.4 Posisi (Positions)

**Endpoint:** `/master/position/`  
**Akses:** Menu `POSITION`  
**Model:** `Position`
| Field | Tipe | Keterangan |
|---|---|---|
| position_id | CharField(3) | PK (max 3 karakter, auto uppercase) |
| position_name | CharField(50) | Nama posisi |

### 5.5 Menu

**Endpoint:** `/master/menu/`  
**Akses:** Menu `MENU`  
**Model:** `Menu`
| Field | Tipe | Keterangan |
|---|---|---|
| menu_id | CharField(50) | PK (auto uppercase) |
| menu_name | CharField(50) | Nama menu |
| menu_remark | CharField(200) | Keterangan |

### 5.6 Permission (Auth)

**Endpoint:** `/master/auth/update/<user_id>/<menu_id>/`  
**Model:** `Auth`
| Field | Tipe | Keterangan |
|---|---|---|
| user | FK → User | Pengguna |
| menu | FK → Menu | Menu |
| add | BooleanField | Izin tambah |
| edit | BooleanField | Izin ubah |
| delete | BooleanField | Izin hapus |

**Unique Constraint:** `user + menu`

### 5.7 Masakan (Cuisines)

**Endpoint:** `/master/cuisine/`  
**Akses:** Menu `CUISINE`  
**Model:** `Cuisine`
| Field | Tipe | Keterangan |
|---|---|---|
| cuisine_id | CharField(50) | PK (auto uppercase) |
| cuisine_name | CharField(50) | Nama masakan |

### 5.8 Pelengkap (Equipment)

**Endpoint:** `/master/equipment/`  
**Akses:** Menu `EQUIPMENT`  
**Model:** `Equipment`
| Field | Tipe | Keterangan |
|---|---|---|
| equipment_id | CharField(50) | PK (auto uppercase) |
| equipment_name | CharField(50) | Nama item |

### 5.9 Kategori (Categories)

**Endpoint:** `/master/category/`  
**Akses:** Menu `CATEGORY`  
**Model:** `Category`
| Field | Tipe | Keterangan |
|---|---|---|
| category_id | CharField(50) | PK (auto uppercase) |
| category_name | CharField(100) | Nama kategori |
| active | BooleanField | Status aktif |

### 5.10 Paket (Packages)

**Endpoint:** `/master/package/`  
**Akses:** Menu `PACKAGE`  
**Model:** `Package`
| Field | Tipe | Keterangan |
|---|---|---|
| package_id | CharField(50) | PK (auto uppercase) |
| package_name | CharField(50) | Nama paket |
| category | FK → Category | Kategori |
| promo | BooleanField | Flag promo |
| active | BooleanField | Status aktif |
| male_price | DecimalField(12,0) | Harga jantan |
| female_price | DecimalField(12,0) | Harga betina |
| box | IntegerField | Jumlah box |
| quantity | IntegerField | Kuantitas |
| type | CharField(10) | Tipe paket |

**Komposisi Paket (per komponen):**
| Model | Relasi | Fields | Unique Constraint |
|---|---|---|---|
| Rice | Package → Cuisine | extra_price, default | package + cuisine |
| MainCuisine | Package → Cuisine | extra_price, default | package + cuisine |
| SubCuisine | Package → Cuisine | extra_price, default | package + cuisine |
| SideCuisine1-5 | Package → Cuisine | extra_price, default | package + cuisine |
| Bag | Package → Equipment | extra_price, default | package + equipment |
| Beverage | Package → Equipment | extra_price, default | package + equipment |
| Pack (Box) | Package → Equipment | extra_price, default | package + equipment |
| Souvenir | Package → Equipment | extra_price, default | package + equipment |
| Other | Package → Equipment | extra_price, default | package + equipment |
| Addon | Package → Equipment | extra_price, default | package + equipment |

**Endpoint Komposisi:**

- View: `/master/package-<tipe>/<package_id>/`
- Update: `/master/package-<tipe>/update/<package_id>/<item_id>/`
- Delete: `/master/package-<tipe>/delete/<package_id>/<item_id>/`

### 5.11 Promo

**Endpoint:** `/master/promo/`  
**Akses:** Menu `PROMO`  
**Model:** `Promo`
| Field | Tipe | Keterangan |
|---|---|---|
| promo_id | BigAutoField | PK |
| promo_name | CharField(200) | Nama promo |
| promo_limit | DecimalField(12,0) | Batas nominal |

**Model:** `PromoDetail`
| Field | Tipe | Keterangan |
|---|---|---|
| promo | FK → Promo | Promo |
| gift | CharField(50) | Nama hadiah |
| nominal | DecimalField(12,0) | Nominal |

**Unique Constraint:** `promo + gift`

### 5.12 Region

**Endpoint:** `/master/region/`  
**Akses:** Menu `REGION`  
**Model:** `Region`
| Field | Tipe | Keterangan |
|---|---|---|
| region_id | CharField(50) | PK (auto uppercase) |
| region_name | CharField(50) | Nama region |

**Model:** `RegionDetail`
| Field | Tipe | Keterangan |
|---|---|---|
| region | FK → Region | Region |
| area | FK → AreaSales | Cabang |

**Unique Constraint:** `region + area`

### 5.13 Box Type

**Model:** `BoxType`
| Field | Tipe | Keterangan |
|---|---|---|
| box_type_id | BigAutoField | PK |
| box_type_name | CharField(50) | Nama tipe box |

---

## 6. Database Schema (30 Models)

### Core Entities

| Model    | PK Type               | Keterangan                             |
| -------- | --------------------- | -------------------------------------- |
| User     | CharField (`user_id`) | Pengguna kustom (extends AbstractUser) |
| Position | CharField (3 chars)   | Posisi karyawan                        |
| Menu     | CharField             | Menu sistem untuk RBAC                 |
| Auth     | BigAutoField          | Pemetaan user-menu permission          |

### Organization

| Model        | Keterangan             |
| ------------ | ---------------------- |
| AreaSales    | Cabang/area            |
| AreaUser     | Peta user-akses cabang |
| Region       | Wilayah geografis      |
| RegionDetail | Peta region-cabang     |
| BoxType      | Tipe box               |

### Product Catalog

| Model          | Keterangan                 |
| -------------- | -------------------------- |
| Category       | Kategori paket             |
| Package        | Paket aqiqah               |
| Cuisine        | Item makanan               |
| Equipment      | Item non-makanan           |
| Rice           | Komposisi nasi per paket   |
| MainCuisine    | Masakan utama per paket    |
| SubCuisine     | Sub masakan per paket      |
| SideCuisine1-5 | Side cuisine 1-5 per paket |
| Bag            | Tas per paket              |
| Beverage       | Minuman per paket          |
| Pack           | Box per paket              |
| Souvenir       | Souvenir per paket         |
| Other          | Item lain per paket        |
| Addon          | Addon per paket            |
| Promo          | Kampanye promosi           |
| PromoDetail    | Detail hadiah promo        |

### Customer & Orders

| Model                | Keterangan                 |
| -------------------- | -------------------------- |
| Customer             | Data pelanggan             |
| CustomerDetail       | Data anak pelanggan        |
| Order                | Pesanan utama              |
| OrderChild           | Anak dalam pesanan         |
| OrderPackage         | Paket dalam pesanan        |
| OrderLeftoverFood    | Sisa makanan               |
| OrderPackageSouvenir | Souvenir per paket pesanan |
| OrderPackageAddon    | Addon per paket pesanan    |
| CashIn               | Pembayaran                 |

---

## 7. Business Logic

### 7.1 Pricing Logic

- Harga paket: `male_price` (jantan) dan `female_price` (betina)
- Setiap opsi masakan/pelengkap memiliki:
  - `extra_price`: harga tambahan
  - `default`: flag pilihan default
- Total paket: `total_price = (quantity × unit_price) + extra_price`
- Total pesanan: `pending_payment = total_order - down_payment - discount`

### 7.2 Order Processing Flow

1. Pelanggan mengakses URL cabang (`/order/new/<area_id>/`)
2. Mengisi data pelanggan (nama, telepon, email, alamat)
3. Menambah data anak (nama, tanggal lahir, jenis kelamin, orang tua)
4. Memilih paket dengan komposisi (masakan, pelengkap, kuantitas, jenis kambing)
5. Sistem menghitung: harga dasar + harga ekstra + harga addon
6. Pesanan tersimpan dengan status `PENDING`, `entry_by = 'customer'`
7. Staf mengkonfirmasi → `CONFIRMED`
8. Staf dapat memodifikasi via CS update (`/order/cs/update/`)
9. Pembayaran dicatat melalui modul Cash In
10. Invoice/BAP/checklist dicetak sebagai PDF

### 7.3 Order Status Flow

```
PENDING → DRAFT → CONFIRMED → DP → LUNAS
                                   ↘ BATAL
```

| Status      | Keterangan                                       | Trigger                                                                             |
| ----------- | ------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `PENDING`   | Status default saat pesanan dibuat               | Default dari model                                                                  |
| `DRAFT`     | Pesanan sudah disubmit oleh customer             | `order_submit()`                                                                    |
| `CONFIRMED` | Pesanan dikonfirmasi staf / belum ada pembayaran | `order_confirmed()` atau `_refresh_order_payment_status()` saat `down_payment == 0` |
| `DP`        | Sudah ada pembayaran (DP), masih ada sisa        | `_refresh_order_payment_status()` saat `down_payment > 0` dan `pending_payment > 0` |
| `LUNAS`     | Lunas (sudah dibayar penuh)                      | `_refresh_order_payment_status()` saat `pending_payment == 0`                       |
| `BATAL`     | Pesanan dibatalkan                               | `order_cancel()` oleh staf/CS                                                       |

**Logic `_refresh_order_payment_status()`:**

```python
if order.pending_payment == 0:
    order.order_status = 'LUNAS'
else:
    if order.down_payment == 0:
        order.order_status = 'CONFIRMED'
    else:
        order.order_status = 'DP'
```

**Arsip pesanan mengecualikan:** `PENDING` dan `BATAL` (untuk CS juga mengecualikan `BATAL`)

### 7.4 Notification System

- Hitung jumlah pesanan dengan status `draft` (lowercase) yang `delivery_date >= hari ini - 90 hari`
- Ditampilkan sebagai badge pada sidebar menu Transaksi
- Filter berdasarkan area user yang login

---

## 8. URL Patterns (120+ Routes)

### Authentication

| Endpoint      | View             | Keterangan            |
| ------------- | ---------------- | --------------------- |
| `/login/`     | `login_view`     | Halaman login         |
| `/logout/`    | `logout`         | Logout                |
| `/forbidden/` | `forbidden_view` | Halaman akses ditolak |

### Home

| Endpoint | View   | Keterangan      |
| -------- | ------ | --------------- |
| `/`      | `home` | Dashboard utama |

### Master Data (CRUD lengkap untuk setiap entitas)

| Prefix                | Entity    |
| --------------------- | --------- |
| `/master/user/`       | Pengguna  |
| `/master/area-sales/` | Cabang    |
| `/master/promo/`      | Promo     |
| `/master/position/`   | Posisi    |
| `/master/menu/`       | Menu      |
| `/master/cuisine/`    | Masakan   |
| `/master/equipment/`  | Pelengkap |
| `/master/category/`   | Kategori  |
| `/master/package/`    | Paket     |
| `/master/region/`     | Region    |
| `/master/customer/`   | Pelanggan |

### Orders

| Endpoint                                       | View              | Keterangan       |
| ---------------------------------------------- | ----------------- | ---------------- |
| `/order/new/<area_id>/`                        | `order_add`       | Form publik      |
| `/order/<branch>/<date>/`                      | `order_index`     | Daftar pesanan   |
| `/order/view/<id>/<cat>/<pack>/<type>/<crud>/` | `order_view`      | Detail pesanan   |
| `/order/update/<id>/`                          | `order_update`    | Update pesanan   |
| `/order/confirm/<id>/`                         | `order_confirm`   | Konfirmasi       |
| `/order/submit/<id>/`                          | `order_submit`    | Submit           |
| `/order/cancel/<id>/`                          | `order_cancel`    | Batalkan         |
| `/order/confirmed/<id>/`                       | `order_confirmed` | Tandai confirmed |
| `/order/archive/<branch>/<date>/`              | `order_archive`   | Arsip            |
| `/order/invoice/<id>/`                         | `order_invoice`   | Cetak Invoice    |
| `/order/bap/<id>/`                             | `order_bap`       | Cetak BAP        |
| `/order/checklist/<id>/`                       | `order_checklist` | Cetak Checklist  |

### Cash In

| Endpoint                        | View              | Keterangan        |
| ------------------------------- | ----------------- | ----------------- |
| `/cashin/`                      | `cashin_index`    | Daftar pembayaran |
| `/cashin/add/<order_id>/<msg>/` | `cashin_add`      | Tambah pembayaran |
| `/cashin/view/<id>/`            | `cashin_view`     | Detail pembayaran |
| `/cashin/update/<id>/<msg>/`    | `cashin_update`   | Update pembayaran |
| `/cashin/remove-evidence/<id>/` | `remove_evidence` | Hapus bukti       |
| `/cashin/delete/<id>/`          | `cashin_delete`   | Hapus pembayaran  |

---

## 9. UI/UX Specification

### 9.1 Layout System

| Layout     | Template                       | Kegunaan                         |
| ---------- | ------------------------------ | -------------------------------- |
| Base       | `layouts/base.html`            | Sidebar + Nav + Content + Footer |
| Fullscreen | `layouts/base-fullscreen.html` | Halaman login                    |
| Form       | `layouts/base-form.html`       | Halaman form                     |

### 9.2 Navigation

- Sidebar vertikal (collapsible pada mobile via `django-user_agents`)
- Tiga bagian utama: Transaksi, Keuangan, Data Master
- Visibilitas menu berdasarkan role pengguna (RBAC)
- Badge notifikasi pada sidebar (jumlah pesanan `draft`)
- SVG icons untuk setiap menu

### 9.3 Components

| Komponen            | Pustaka                         | Kegunaan                                       |
| ------------------- | ------------------------------- | ---------------------------------------------- |
| DataTables          | jQuery DataTables 1.13.5        | Tabel interaktif dengan search/sort/pagination |
| Form Controls       | Bootstrap 5 (`form-control-sm`) | Input form berukuran kecil                     |
| Datepicker          | jQuery UI Datepicker            | Input tanggal dengan validasi `min`/`max`      |
| Timepicker          | Custom                          | Input waktu                                    |
| Rich Text Editor    | TinyMCE                         | Konten program (full toolbar)                  |
| Toast Notifications | Notyf                           | Notifikasi info/success/warning/danger         |
| File Upload         | Bootstrap File Input            | Upload tanda tangan, bukti pembayaran          |
| Pagination          | Django Paginator                | Navigasi halaman data                          |

### 9.4 Responsive Design

- Deteksi mobile via `django-user_agents`
- **Mobile Sidebar**: Hidden by default on mobile (< 992px), toggle via hamburger menu button, slide in/out animation with backdrop overlay
- **Sidebar Close**: Close button (X) visible on mobile, hidden on desktop
- **Mobile Reminder**: Reminder dropdown centered on modal overlay with scroll lock on body
- Sidebar z-index kondisional untuk mobile
- Grid responsif Bootstrap 5
- Form controls menggunakan ukuran kecil (`form-control-sm`)

### 9.5 Mobile UI Features

- **Mobile Sidebar Behavior**: 
  - Sidebar hidden by default on screens < 992px
  - Toggle via hamburger button in navigation bar
  - Backdrop overlay when sidebar is open (click to close)
  - Close button (X) on top of sidebar
  - Smooth slide animation (0.3s ease-in-out)
  - Body scroll lock when sidebar is open

- **Mobile Reminder Behavior**:
  - Reminder dropdown centered on viewport
  - Backdrop overlay (semi-transparent black)
  - Scroll lock on main content when reminder is open
  - Close on backdrop click or notification click

- **Mobile Navigation**:
  - Hamburger menu button visible only on mobile (< 992px)
  - Desktop toggle button hidden on mobile
  - Notification badge visible on mobile

### 9.5 Template Files (78 templates)

| Kategori   | Jumlah | Contoh                                                                                                                                                                                             |
| ---------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Layouts    | 3      | base.html, base-form.html, base-fullscreen.html                                                                                                                                                    |
| Includes   | 7      | sidebar.html, navigation.html, footer.html, scripts.html                                                                                                                                           |
| Accounts   | 1      | login.html                                                                                                                                                                                         |
| Home/Index | 1      | index.html                                                                                                                                                                                         |
| User       | 5      | user_index, user_add, user_view, user_change_password, user_set_password                                                                                                                           |
| Area Sales | 3      | area_sales_index, area_sales_add, area_sales_view                                                                                                                                                  |
| Position   | 3      | position_index, position_add, position_view                                                                                                                                                        |
| Menu       | 3      | menu_index, menu_add, menu_view                                                                                                                                                                    |
| Cuisine    | 3      | cuisine_index, cuisine_add, cuisine_view                                                                                                                                                           |
| Equipment  | 3      | equipment_index, equipment_add, equipment_view                                                                                                                                                     |
| Category   | 3      | category_index, category_add, category_view                                                                                                                                                        |
| Package    | 3      | package_index, package_add, package_view                                                                                                                                                           |
| Region     | 3      | region_index, region_add, region_view                                                                                                                                                              |
| Customer   | 3      | customer_index, customer_add, customer_view                                                                                                                                                        |
| Promo      | 3      | promo_index, promo_add, promo_view                                                                                                                                                                 |
| Order      | 10     | order_index, order_add, order_view, order_update, order_confirm, order_confirm_update, order_child_add, order_child_update, order_package_add, order_package_update, order_archive, order_thankyou |
| Cash In    | 3      | cashin_index, cashin_add, cashin_view                                                                                                                                                              |
| Form       | 1      | form_index                                                                                                                                                                                         |
| Error      | 3      | page-403, page-404, page-500, forbidden                                                                                                                                                            |
| Lainnya    | 5      | icons, tables, map, profile, register                                                                                                                                                              |

---

## 10. Security

| Aspek            | Implementasi                                                                  |
| ---------------- | ----------------------------------------------------------------------------- |
| Authentication   | User ID + Password (bukan email)                                              |
| Session Timeout  | Auto-logout 15 menit (`django-auto-logout`)                                   |
| RBAC             | Permission per menu (`add`/`edit`/`delete`) via `Auth` model                  |
| CSRF Protection  | Django CSRF middleware                                                        |
| Audit Trail      | `entry_date`, `entry_by`, `update_date`, `update_by` (auto via `django-crum`) |
| Cache Control    | Login page: `no_cache, must_revalidate, no_store`                             |
| Password Hashing | Django default (PBKDF2)                                                       |
| Input Validation | Django Form validation + custom validators                                    |
| File Upload      | Validasi tipe file, penyimpanan terpisah                                      |

---

## 11. Export & Reports

| Format | Fungsi              | Kegunaan                           |
| ------ | ------------------- | ---------------------------------- |
| PDF    | `order_invoice()`   | Surat tagihan dengan rincian paket |
| PDF    | `order_bap()`       | Berita Acara Penerimaan            |
| PDF    | `order_checklist()` | Checklist item per paket           |

**Detail Invoice PDF:**

- Header: Logo, data cabang, nomor invoice
- Data pelanggan: nama, telepon, email, alamat
- Data anak: nama, tanggal lahir
- Tabel paket: nama, jumlah, harga satuan, total
- Rincian komposisi per paket
- Sub Total, Diskon (+Promo), DP, Jumlah Tertagih
- Syarat & Ketentuan
- Tanda tangan digital

---

## 12. Email Integration

- SMTP backend: `mail.ksisolusi.com:465` (SSL)
- Fungsi: `send_email(_subject, _msg, _recipient)` di `apps/mail.py`
- Menggunakan `django.core.mail.send_mail`
- `from_email` dari `settings.EMAIL_HOST_USER`

---

## 13. Audit Trail Pattern

Setiap model memiliki field:

```python
entry_date = models.DateTimeField(null=True)
entry_by = models.CharField(max_length=50, null=True)
update_date = models.DateTimeField(null=True, blank=True, auto_now=True)
update_by = models.CharField(max_length=50, null=True, blank=True)
```

**Logic di `save()` method:**

```python
if not self.entry_date:
    self.entry_date = timezone.now()
    self.entry_by = get_current_user().user_id
self.update_date = timezone.now()
self.update_by = get_current_user().user_id
```

---

## 14. Environment Configuration

### Settings (`core/settings.py`)

| Variable           | Default                            | Keterangan                 |
| ------------------ | ---------------------------------- | -------------------------- |
| SECRET_KEY         | env var / fallback                 | Kunci rahasia Django       |
| DEBUG              | `True`                             | Mode debug                 |
| ALLOWED_HOSTS      | localhost, 192.168.0.13, 127.0.0.1 | Host yang diizinkan        |
| AUTH_USER_MODEL    | `apps.User`                        | Model user kustom          |
| LOGIN_REDIRECT_URL | `home`                             | Redirect setelah login     |
| LANGUAGE_CODE      | `id`                               | Bahasa Indonesia           |
| TIME_ZONE          | `Asia/Jakarta`                     | Zona waktu                 |
| USE_TZ             | `False`                            | Nonaktifkan timezone-aware |
| AUTO_LOGOUT        | 15 (menit)                         | Durasi auto-logout         |

### Database

| Setting | Lokal                      | Produksi                   |
| ------- | -------------------------- | -------------------------- |
| ENGINE  | `django.db.backends.mysql` | `django.db.backends.mysql` |
| NAME    | `aqiqahon`                 | `sahabataqiqah_aqiqahon`   |
| HOST    | `localhost`                | via `DATABASE_URL`         |
| PORT    | `3306`                     | -                          |

### Email

| Setting             | Nilai                                         |
| ------------------- | --------------------------------------------- |
| EMAIL_BACKEND       | `django.core.mail.backends.smtp.EmailBackend` |
| EMAIL_HOST          | `mail.ksisolusi.com`                          |
| EMAIL_PORT          | `465`                                         |
| EMAIL_USE_SSL       | `True`                                        |
| EMAIL_HOST_USER     | (env var)                                     |
| EMAIL_HOST_PASSWORD | (env var)                                     |

---

## 15. Deployment

| Komponen              | Status                        |
| --------------------- | ----------------------------- |
| WSGI Server           | Gunicorn (commented out)      |
| Static Files          | WhiteNoise (commented out)    |
| Environment Variables | python-dotenv (commented out) |
| Database              | MySQL                         |
| Static URL            | `/apps/static/`               |
| Media URL             | `/apps/media/`                |

---

## 16. Seed Data

- **File:** `apps/fixtures/setup_data.json`
- **Cara load:** `python manage.py loaddata setup_data.json`
- Berisi data awal untuk setup aplikasi (menu, posisi, dll)

---

## 17. Known Limitations

1. **Single-file architecture:** Semua 30 models, 1260+ baris forms, dan 6900+ baris views dalam satu file masing-masing
2. **Raw SQL:** Beberapa view menggunakan `connection.cursor()` dengan raw SQL untuk query JOIN kompleks
3. **Tidak ada REST API:** Hanya server-rendered (DRF di-comment di requirements)
4. **Admin Django tidak aktif:** `admin.py` kosong, tidak ada model yang terdaftar
5. **Tidak ada automated tests:** `tests.py` kosong
6. **File sync manual:** Deploy ke production dilakukan manual via file copy
7. **Tidak ada approval workflow:** Fitur approval multi-level belum diimplementasikan

---

## 18. File Structure

```
aqiqahon/
├── core/                          # Konfigurasi Django
│   ├── settings.py                # Pengaturan utama
│   ├── urls.py                    # URL root
│   ├── wsgi.py                    # WSGI entry point
│   └── asgi.py                    # ASGI entry point
├── apps/                          # Aplikasi utama
│   ├── models.py                  # 30 models (1032 baris)
│   ├── views.py                   # ~120 view functions (6928 baris)
│   ├── urls.py                    # 120+ URL patterns (253 baris)
│   ├── forms.py                   # 50+ form classes (1260 baris)
│   ├── mail.py                    # Utilitas email
│   ├── notifications.py           # Hitung notifikasi pesanan
│   ├── validators.py              # Validator kustom
│   ├── host.py                    # Base URL constant
│   ├── templates/                 # 78 template HTML
│   ├── static/                    # CSS, JS, fonts, images
│   ├── templatetags/              # Custom template filters
│   ├── media/                     # File upload
│   └── fixtures/                  # Seed data
├── authentication/                # Aplikasi autentikasi
│   ├── views.py                   # Login, forbidden view
│   ├── forms.py                   # LoginForm
│   └── decorators.py              # @role_required
├── manage.py
└── requirements.txt               # 25 dependencies
```

---

_Document updated from codebase analysis on July 19, 2026_
