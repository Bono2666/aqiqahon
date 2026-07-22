# Product Specification: AqiqahOn

## 1. Overview

**Nama Produk:** AqiqahOn  
**Versi:** 1.0  
**Platform:** Web Application (Responsive)  
**URL Produksi:** aqiqahon.sahabataqiqah.co.id  
**Deskripsi:** Sistem manajemen bisnis end-to-end untuk perusahaan layanan aqiqah "Sahabat Aqiqah", mencakup pemesanan, keuangan, manajemen data master, dan workflow approval multi-level.

---

## 2. Tech Stack

### Backend
| Komponen | Teknologi |
|---|---|
| Framework | Django 5.0.6 |
| Bahasa | Python 3.11.3 |
| Database | MySQL |
| ORM | Django ORM |
| PDF Generator | ReportLab, xhtml2pdf, PyPDF2 |
| Export | xlwt (.xls), xlsxwriter (.xlsx) |
| Rich Text | TinyMCE |

### Frontend
| Komponen | Teknologi |
|---|---|
| CSS Framework | Bootstrap 5.3 |
| UI Design | Soft UI Dashboard (Argon-based) |
| JavaScript | jQuery 3.6, jQuery UI 1.12 |
| Data Tables | DataTables 1.13.5 |
| Icons | Font Awesome, Nucleo Icons |
| Notifications | Notyf |
| Charts | Chart.js |
| Dark Mode | Custom CSS |

---

## 3. User Roles & Access Control

### Role-Based Access Control (RBAC)
- User login menggunakan `user_id` + password
- Auto-logout setelah 15 menit tidak aktif
- Permission per menu: View, Add, Edit, Delete
- Superuser bypass semua pengecekan RBAC

### Role Types
| Role | Keterangan |
|---|---|
| Admin | Akses penuh ke semua modul |
| Manager | Akses approval & monitoring |
| CS (Customer Service) | Mengelola pesanan & update |
| Marketing | Membuat proposal & program |
| Finance | Mengelola keuangan & klaim |
| Staff | Akses terbatas sesuai penugasan |

---

## 4. Feature Modules

### 4.1 Transaksi (Transactions)

#### 4.1.1 Pemesanan (Orders)
**Endpoint:** `/order/new/<area_id>/` (public URL per cabang)

**Fitur:**
- Form pemesanan publik yang dapat diakses per cabang
- Input data pelanggan (nama, telepon, email, alamat)
- Input data anak (nama, tanggal lahir, jenis kelamin, ayah, ibu)
- Pilihan paket dengan komposisi:
  - Nasi (dengan harga ekstra & default)
  - Masakan utama
  - Masakan sampingan 1-5
  - Minuman
  - Tas
  - Box
  - Souvenir
  - Item lainnya
  - Addon
- Pilihan jenis kambing (jantan/betina)
- Kuantitas pesanan
- Manajemen sisa makanan (leftover food)
- Status pesanan: `DRAFT` → `PENDING` → `CONFIRMED` / `CANCELLED`
- Kalkulasi otomatis: `pending_payment = total_order - down_payment - discount`
- Kalkulasi paket: `total_price = (quantity * unit_price) + extra_price`

**Dokumen PDF:**
- Invoice (Surat Tagihan)
- BAP (Berita Acara Penerimaan)
- Checklist

#### 4.1.2 Arsip (Archive)
- Daftar pesanan selesai/dibatalkan
- Filter berdasarkan cabang dan rentang tanggal

### 4.2 Keuangan (Finance)

#### 4.2.1 Uang Masuk (Cash In / Payments)
**Fitur:**
- Pencatatan pembayaran terhadap pesanan
- Jenis pembayaran: transfer, cash, dll
- Upload bukti pembayaran (file attachment)
- Pencatatan nama bank
- Nominal pembayaran
- Fungsi hapus bukti

### 4.3 Data Master (Master Data)

#### 4.3.1 Pengguna (Users)
- CRUD pengguna dengan tanda tangan digital
- Penugasan posisi (position)
- Konfigurasi permission per menu (add/edit/delete)
- Penugasan akses area/cabang
- Ganti password

#### 4.3.2 Pelanggan (Customers)
- Database pelanggan dengan data:
  - Nama, alamat, telepon, email
  - Data anak (nama, tanggal lahir, jenis kelamin, ayah, ibu)
- Satu pelanggan dapat memiliki多个 anak

#### 4.3.3 Cabang (Area/Branch)
- Manajemen cabang dengan data:
  - ID, nama, manajer (posisi ASM)
  - Rekening bank
  - Alamat lengkap (kecamatan, kota, kode pos)
- URL form pemesanan unik per cabang
- Hubungan cabang-distributor
- Hubungan cabang-channel

#### 4.3.4 Menu & Posisi
- Manajemen menu sistem untuk RBAC
- Manajemen posisi karyawan

#### 4.3.5 Produk & Paket
| Komponen | Keterangan |
|---|---|
| Kategori | Kategori paket dengan status aktif/nonaktif |
| Paket | Paket aqiqah (harga jantan/betina, kuantitas box/kambing) |
| Masakan | Item makanan |
| Pelengkap | Item non-makanan (tas, minuman, souvenir, box) |
| Promo | Kampanye promosi dengan batas nominal dan detail hadiah |

#### 4.3.6 Distributor & Region
- Distributor/pemasok dengan kode SAP
- Region geografis yang membawahi多个 cabang
- Division organisasi

### 4.4 Approval Workflows

#### 4.4.1 Budget Management
- Alokasi budget per area/distributor/bulan
- Breakdown budget per channel (dengan persentase)
- Tracking: amount + upping = total, balance = total - proposed
- Multi-level approval workflow

#### 4.4.2 Proposal System
- Proposal marketing dengan:
  - Proyeksi penjualan incremental
  - Proyeksi biaya
  - Kalkulasi ROI
- Multi-level approval matrix

#### 4.4.3 Program System
- Pelacakan eksekusi program
- Workflow approval

#### 4.4.4 Claim System
- Klaim invoice dengan:
  - Kalkulasi pajak otomatis (11% PPN)
  - Total = total_claim + tax
- Multi-level approval matrix
- Release dan arsip klaim

#### 4.4.5 Claim List (CL)
- Konsolidasi daftar klaim
- Workflow approval

### 4.5 Closing Period
- Penutupan periode untuk dokumen keuangan

---

## 5. Database Models (50+ Models)

### Core Entities
| Model | Keterangan | Primary Key |
|---|---|---|
| User | Pengguna kustom | user_id (CharField) |
| Position | Posisi karyawan | position_id (3 chars) |
| Menu | Menu sistem untuk RBAC | menu_id |
| Auth | Pemetaan user-menu permission | Auto (BigAutoField) |

### Organization
| Model | Keterangan |
|---|---|
| AreaSales | Cabang/area dengan manajer, alamat, rekening bank |
| AreaChannel | Peta area-channel |
| AreaSalesDetail | Peta cabang-distributor |
| AreaUser | Peta user-akses cabang |
| Distributor | Distributor/pemasok |
| Channel | Sales channel |
| Region | Wilayah geografis |
| Division | Divisi organisasi |

### Product & Order
| Model | Keterangan |
|---|---|
| Category | Kategori paket |
| Package | Paket aqiqah (harga jantan/betina) |
| Cuisine | Item makanan |
| Equipment | Item non-makanan |
| Rice, MainCuisine, SubCuisine, SideCuisine1-5 | Komposisi paket |
| Beverage, Bag, Pack, Souvenir, Other, Addon | Komposisi paket |
| Promo, PromoDetail | Promosi |
| Customer, CustomerDetail | Pelanggan & anak |
| Order, OrderChild, OrderPackage | Pesanan |
| OrderPackageSouvenir, OrderPackageAddon | Detail paket pesanan |
| OrderLeftoverFood | Sisa makanan |
| CashIn | Pembayaran |

### Approval Workflows
| Model | Keterangan |
|---|---|
| Budget, BudgetDetail | Alokasi budget |
| BudgetRelease, BudgetApproval | Approval budget |
| Proposal, ProposalRelease, ProposalMatrix | Proposal marketing |
| IncrementalSales, ProjectedCost | Proyeksi |
| Program, ProgramRelease, ProgramMatrix | Program |
| Claim, ClaimRelease, ClaimMatrix | Klaim invoice |
| CL, CLDetail, CLRelease | Daftar klaim konsolidasi |
| Closing | Penutupan periode |

---

## 6. Business Logic

### 6.1 Pricing Logic
- Harga paket: `male_price` dan `female_price`
- Setiap opsi masakan/pelengkap memiliki `extra_price` dan flag `default`
- Total paket: `total_price = (quantity * unit_price) + extra_price`
- Total pesanan: `pending_payment = total_order - down_payment - discount`

### 6.2 Order Processing Flow
1. Pelanggan mengakses URL cabang (`/order/new/<area_id>/`)
2. Mengisi data pelanggan (nama, telepon, email, alamat)
3. Menambah data anak (nama, tanggal lahir, jenis kelamin, orang tua)
4. Memilih paket dengan komposisi (masakan, pelengkap, kuantitas, jenis kambing)
5. Sistem menghitung: harga dasar + harga ekstra + harga addon
6. Pesanan tersimpan dengan status `DRAFT`
7. Pelanggan konfirmasi → `CONFIRMED`
8. Staf dapat memodifikasi via CS update
9. Pembayaran dicatat melalui modul Cash In
10. Invoice/BAP/checklist dicetak sebagai PDF

### 6.3 Approval Workflow
- Multi-level approval matrix (ProposalMatrix, ProgramMatrix, ClaimMatrix, CLMatrix)
- Konfigurable: sequence, position, limit per approver
- Actions: approve, revise, return, reject
- Email notifikasi pada event approval
- Catatan untuk aksi revise/return/reject
- Tracking status cetak dan notifikasi

---

## 7. UI/UX Specification

### 7.1 Layout
- **Base Layout**: Sidebar + Navigation + Content + Footer
- **Fullscreen Layout**: Untuk halaman login
- **Form Layout**: Untuk halaman form

### 7.2 Navigation
- Sidebar vertikal (collapsible pada mobile)
- Tiga bagian utama: Transaksi, Keuangan, Data Master
- Visibilitas menu berdasarkan role pengguna
- Badge notifikasi pada menu Transaksi (jumlah pesanan draft)
- SVG icons untuk setiap menu

### 7.3 Components
| Komponen | Keterangan |
|---|---|
| DataTables | Tabel interaktif dengan search/sort/pagination |
| Form Controls | Bootstrap 5 form controls (ukuran kecil) |
| Datepicker | jQuery UI datepicker untuk input tanggal |
| Timepicker | Timepicker untuk input waktu |
| Rich Text Editor | TinyMCE untuk konten program |
| Toast Notifications | Notyf (info, success, warning, danger) |
| File Upload | Upload tanda tangan, bukti pembayaran, proposal |

### 7.4 Dark Mode
- Support dark mode via custom CSS
- Toggle tersedia di UI

### 7.5 Responsive Design
- Deteksi mobile via django-user_agents
- Sidebar z-index kondisional untuk mobile
- Grid responsif Bootstrap 5

---

## 8. Security

| Aspek | Implementasi |
|---|---|
| Authentication | User ID + Password |
| Session Timeout | Auto-logout 15 menit |
| RBAC | Permission per menu (add/edit/delete) |
| CSRF Protection | Django CSRF middleware |
| Audit Trail | entry_date, entry_by, update_date, update_by (auto via django-crum) |
| HTTPS | SSL (port 465 untuk email) |

---

## 9. Export & Reports

| Format | Kegunaan |
|---|---|
| PDF | Invoice, BAP, Checklist |
| Excel (.xls) | Export data |
| Excel (.xlsx) | Export data |

---

## 10. Email Integration

- SMTP backend: `mail.ksisolusi.com:465` (SSL)
- Notifikasi approval workflow
- Utility: `apps/mail.py`

---

## 11. Environment Configuration

| Variable | Keterangan |
|---|---|
| SECRET_KEY | Kunci rahasia Django |
| DEBUG | Mode debug (default: True) |
| ALLOWED_HOSTS | Host yang diizinkan |
| DATABASE_URL | URL database produksi |
| EMAIL_HOST | SMTP host |
| EMAIL_PORT | SMTP port |
| EMAIL_HOST_USER | Email username |
| EMAIL_HOST_PASSWORD | Email password |

---

## 12. Deployment

- **WSGI Server:** Gunicorn
- **Static Files:** WhiteNoise
- **Environment Variables:** python-dotenv
- **Database:** MySQL

---

## 13. Seed Data

- File: `apps/fixtures/setup_data.json`
- Berisi data awal untuk setup aplikasi

---

## 14. Known Limitations

1. Single-file architecture (semua model/form/view dalam satu file)
2. Raw SQL digunakan untuk beberapa query kompleks
3. Tidak ada REST API (hanya server-rendered)
4. Admin Django tidak terkonfigurasi (admin.py kosong)
5. Tidak ada automated tests (tests.py kosong)

---

*Document generated from codebase analysis on July 15, 2026*
