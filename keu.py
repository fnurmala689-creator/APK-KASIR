import streamlit as st
import pandas as pd
import base64
import copy
import json
import requests
from datetime import datetime
import urllib.parse
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner

st.set_page_config(page_title="TOKO JABON KIDUL SEPUR", page_icon="🛒", layout="wide")

# --- CSS: TAMPILAN RESPONSIF HP & PROFESIONAL ---
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    html, body, [class*="css"] {
        font-size: 15px !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Styling tombol menu utama */
    div[data-testid="column"] .menu-btn > button {
        width: 100% !important;
        border-radius: 8px !important;
        padding: 20px 12px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        border: 1px solid #dcdde1 !important;
        background-color: #f5f6fa !important;
        color: #2f3640 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    }

    /* Penyesuaian khusus tampilan HP agar elemen tidak terlalu mepet */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h3 {
            font-size: 1.2rem !important;
        }
    }

    input {
        font-size: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PERMANENT_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIw6LgDSUn_lDlosWSAGQra0bR597E_Av6OYoo9uRpVr1P9ROMMgSaS_OSjp1Jj3Sp5GBRV01lIh0k/pub?output=csv"

FALLBACK = pd.DataFrame({
    "Barcode": ["899111", "899222"],
    "Nama Barang": ["Beras Premium 1 Kg", "Minyak Goreng 1 Liter"],
    "Harga Umum": [15000, 17500],
    "Harga Reseller": [13500, 16000],
    "Harga Pengusaha": [12500, 15000],
})


@st.cache_data(ttl=300)
def muat_produk():
    try:
        df = pd.read_csv(PERMANENT_CSV_URL, dtype=str)
        ok = True
    except Exception:
        df = FALLBACK.astype(str)
        ok = False
    df.columns = df.columns.str.strip()
    for c in df.columns:
        if c.lower().startswith("harga"):
            df[c] = (
                df[c].fillna("0").astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.replace(r"[^\d]", "", regex=True)
                .replace("", "0")
                .astype(int)
            )
        else:
            df[c] = df[c].fillna("")
    return df, ok


def norm_kode(x):
    s = str(x).strip().replace("\u00a0", "")
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0")


def rp(angka):
    return f"{angka:,.0f}".replace(",", ".")


HTML_CETAK_BLE = """
<div style="font-family: sans-serif; margin: 0; padding: 0;">
  <button id="btn" style="width:100%; padding:12px; font-size:16px; font-weight:600;
          border-radius:6px; border:1px solid #2f3640; background:#2f3640; color:#ffffff; cursor:pointer;">
    🖨️ Cetak Struk Bluetooth
  </button>
  <div id="status" style="font-size:13px; color:#555; margin-top:6px; min-height:20px; font-weight:500;"></div>
</div>
<script>
const DATA_B64 = "__DATA__";
const CHUNK = 20;
const DELAY = 25;
const SERVICES = [
  "000018f0-0000-1000-8000-00805f9b34fb",
  "e7810a71-73ae-499d-8c15-faa9aef0c3f2",
  "49535343-fe7d-4ae5-8fa9-9fafd205e455",
  "0000ff00-0000-1000-8000-00805f9b34fb",
  "0000ffe0-0000-1000-8000-00805f9b34fb",
  "0000fff0-0000-1000-8000-00805f9b34fb",
  "0000fee7-0000-1000-8000-00805f9b34fb",
  "0000ae30-0000-1000-8000-00805f9b34fb",
  "0000ff80-0000-1000-8000-00805f9b34fb"
];
const btn = document.getElementById("btn");
const statusEl = document.getElementById("status");
function setStatus(t) { statusEl.textContent = t; }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function bytesDariB64(b64) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}

async function cariKarakteristik(server) {
  for (const svc of SERVICES) {
    try {
      const service = await server.getPrimaryService(svc);
      const chars = await service.getCharacteristics();
      for (const c of chars) {
        if (c.properties.write || c.properties.writeWithoutResponse) return c;
      }
    } catch (e) {}
  }
  return null;
}

let cachedDevice = null;

async function sambungkan() {
  let server = null;
  if (cachedDevice && cachedDevice.gatt.connected) {
    return { device: cachedDevice, ch: await cariKarakteristik(cachedDevice.gatt) };
  }
  if (navigator.bluetooth.getDevices) {
    try {
      const daftar = await navigator.bluetooth.getDevices();
      if (daftar && daftar.length > 0) {
        cachedDevice = daftar[0];
        setStatus("Menghubungkan ke printer tersimpan...");
        server = await cachedDevice.gatt.connect();
        const ch = await cariKarakteristik(server);
        if (ch) return { device: cachedDevice, ch: ch };
      }
    } catch (e) {}
  }
  setStatus("Pilih printer Bluetooth...");
  cachedDevice = await navigator.bluetooth.requestDevice({
    acceptAllDevices: true,
    optionalServices: SERVICES
  });
  server = await cachedDevice.gatt.connect();
  const ch = await cariKarakteristik(server);
  return { device: cachedDevice, ch: ch };
}

async function cetak() {
  btn.disabled = true;
  let device = null;
  try {
    if (!navigator.bluetooth) {
      setStatus("❌ Browser tidak mendukung Bluetooth.");
      return;
    }
    setStatus("Menghubungkan...");
    const hasil = await sambungkan();
    if (!hasil || !hasil.ch) {
      setStatus("❌ Jalur cetak tidak dikenali.");
      return;
    }
    device = hasil.device;
    const ch = hasil.ch;
    setStatus("Mencetak...");
    const data = bytesDariB64(DATA_B64);
    for (let i = 0; i < data.length; i += CHUNK) {
      const potong = data.slice(i, i + CHUNK);
      if (ch.properties.write) {
        if (ch.writeValueWithResponse) await ch.writeValueWithResponse(potong);
        else await ch.writeValue(potong);
      } else {
        await ch.writeValueWithoutResponse(potong);
      }
      await sleep(DELAY);
    }
    setStatus("✅ Berhasil dicetak!");
  } catch (e) {
    cachedDevice = null;
    setStatus("❌ Gagal. Pastikan printer menyala.");
  } finally {
    btn.disabled = false;
  }
}
if (btn) btn.addEventListener("click", cetak);
</script>
"""

df_produk, data_dari_sheet = muat_produk()
df_produk = df_produk.copy()

if not data_dari_sheet:
    st.error("⚠️ Gagal mengambil data dari internet.")

kolom_nama_opsi = ["Nama Barang", "nama barang", "Nama", "nama", "Produk", "produk"]
kolom_nama_barang = next((c for c in kolom_nama_opsi if c in df_produk.columns), df_produk.columns[0])

kolom_barcode_opsi = ["Barcode", "barcode", "SKU", "sku", "Kode", "kode"]
kolom_barcode = next((c for c in kolom_barcode_opsi if c in df_produk.columns), None)

if kolom_barcode:
    df_produk["_kode"] = df_produk[kolom_barcode].map(norm_kode)

defaults = {
    "menu_aktif": None,
    "keranjang": [],
    "lain_lain": [],
    "scan_counter_db": 0,
    "scan_counter_tambah": 0,
    "scan_counter_kasir_aktif": None,
    "tambah_barcode": "",
    "tambah_nama": "",
    "tambah_riwayat": [],
    "pesan_tambah": None,
    "editor_counter": 0,
    "riwayat": [],
    "konfirmasi_kosong": False,
    "pesan": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def simpan_riwayat():
    st.session_state.riwayat.append(copy.deepcopy(st.session_state.keranjang))
    st.session_state.riwayat = st.session_state.riwayat[-20:]


def proses_input_barcode(idx_baris, input_val, kolom_harga_pilihan):
    val = str(input_val).strip()
    if not val:
        return

    simpan_riwayat()
    df_match = pd.DataFrame()
    if kolom_barcode:
        df_match = df_produk[df_produk["_kode"] == norm_kode(val)]
    if len(df_match) == 0:
        df_match = df_produk[
            df_produk[kolom_nama_barang].astype(str).str.contains(val, case=False, na=False, regex=False)
        ]

    if len(df_match) == 0:
        st.session_state.pesan = ("warning", f"⚠️ Barang '{val}' tidak ditemukan.")
    elif len(df_match) == 1:
        row = df_match.iloc[0]
        bcode = str(row[kolom_barcode]).strip() if kolom_barcode else "-"
        nm = str(row[kolom_nama_barang]).strip() or "(Tanpa Nama)"
        hg = int(row[kolom_harga_pilihan])
        
        st.session_state.keranjang[idx_baris] = {
            "Barcode": bcode,
            "Nama Barang": nm,
            "Qty": 1,
            "Harga Satuan": hg,
            "Subtotal": hg,
        }
        st.session_state.pesan = ("success", f"✅ Memuat: **{nm}** (Rp {rp(hg)})")
    else:
        opsi_list = []
        for _, row in df_match.iterrows():
            bcode = str(row[kolom_barcode]).strip() if kolom_barcode else "-"
            nm = str(row[kolom_nama_barang]).strip() or "(Tanpa Nama)"
            hg = int(row[kolom_harga_pilihan])
            opsi_list.append((bcode, nm, hg))
        st.session_state.keranjang[idx_baris]["_dropdown_pilihan"] = opsi_list
        st.session_state.pesan = ("info", f"Ditemukan beberapa barang untuk '{val}', silakan pilih.")
    
    st.session_state.editor_counter += 1


def barcode_diketik(idx_baris, kolom_harga_pilihan, key_widget):
    val = st.session_state.get(key_widget, "")
    proses_input_barcode(idx_baris, val, kolom_harga_pilihan)


def pilih_dari_dropdown(idx_baris, bcode, nm, hg):
    simpan_riwayat()
    st.session_state.keranjang[idx_baris] = {
        "Barcode": bcode,
        "Nama Barang": nm,
        "Qty": 1,
        "Harga Satuan": hg,
        "Subtotal": hg,
    }
    if "_dropdown_pilihan" in st.session_state.keranjang[idx_baris]:
        del st.session_state.keranjang[idx_baris]["_dropdown_pilihan"]
    st.session_state.pesan = ("success", f"✅ Dipilih: **{nm}** (Rp {rp(hg)})")
    st.session_state.editor_counter += 1


def tambah_baris_kosong():
    simpan_riwayat()
    st.session_state.keranjang.append({
        "Barcode": "",
        "Nama Barang": "Ketik barcode atau nama barang...",
        "Qty": 1,
        "Harga Satuan": 0,
        "Subtotal": 0,
    })
    st.session_state.editor_counter += 1


def tambah_baris_lain():
    st.session_state.lain_lain.append({"tipe": "Diskon", "nominal": 0})


def hapus_baris_lain(idx):
    if 0 <= idx < len(st.session_state.lain_lain):
        st.session_state.lain_lain.pop(idx)


def ubah_qty_langsung(index_item, delta):
    simpan_riwayat()
    if 0 <= index_item < len(st.session_state.keranjang):
        item = st.session_state.keranjang[index_item]
        item["Qty"] += delta
        if item["Qty"] <= 0:
            st.session_state.keranjang.pop(index_item)
        else:
            item["Subtotal"] = item["Qty"] * item["Harga Satuan"]
        st.session_state.editor_counter += 1


def update_qty_ketik(index_item, key_qty_widget):
    simpan_riwayat()
    if 0 <= index_item < len(st.session_state.keranjang):
        val_baru = int(st.session_state.get(key_qty_widget, 1) or 1)
        item = st.session_state.keranjang[index_item]
        if val_baru <= 0:
            st.session_state.keranjang.pop(index_item)
        else:
            item["Qty"] = val_baru
            item["Subtotal"] = item["Qty"] * item["Harga Satuan"]
        st.session_state.editor_counter += 1


def hapus_item_satuan(index_item):
    simpan_riwayat()
    if 0 <= index_item < len(st.session_state.keranjang):
        st.session_state.keranjang.pop(index_item)
        st.session_state.pesan = ("info", "❌ Baris dihapus.")
        st.session_state.editor_counter += 1


def batalkan_terakhir():
    if st.session_state.riwayat:
        st.session_state.keranjang = st.session_state.riwayat.pop()
        st.session_state.editor_counter += 1
        st.session_state.pesan = ("info", "↩️ Perubahan dibatalkan.")


def minta_konfirmasi_kosong():
    st.session_state.konfirmasi_kosong = True


def batal_kosongkan():
    st.session_state.konfirmasi_kosong = False


def kosongkan_keranjang():
    simpan_riwayat()
    st.session_state.keranjang = []
    st.session_state.lain_lain = []
    st.session_state.pesan = ("info", "🗑️ Keranjang dikosongkan.")
    st.session_state.konfirmasi_kosong = False
    st.session_state.editor_counter += 1


def hapus_pencarian_db():
    st.session_state.search_db = ""


def ambil_secret(nama):
    try:
        return str(st.secrets[nama]).strip()
    except Exception:
        return ""


def simpan_barang(kol_barcode, kol_nama, kol_harga_list):
    barcode = st.session_state.tambah_barcode.strip()
    nama = st.session_state.tambah_nama.strip()
    url = ambil_secret("SHEET_WEBHOOK_URL")
    token = ambil_secret("SHEET_TOKEN")

    if not barcode:
        st.session_state.pesan_tambah = ("warning", "⚠️ Barcode belum diisi.")
        return
    if not url or not token:
        st.session_state.pesan_tambah = ("error", "⚠️ Konfigurasi sistem pusat belum lengkap.")
        return

    values = {kol_barcode: barcode, kol_nama: nama}
    for c in kol_harga_list:
        v = int(st.session_state.get(f"tambah_{c}", 0) or 0)
        values[c] = v if v > 0 else ""

    payload = {"token": token, "kolom_barcode": kol_barcode, "values": values}
    try:
        r = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "text/plain"}, timeout=25)
    except Exception as e:
        st.session_state.pesan_tambah = ("error", f"⚠️ Gagal menyambung: {e}")
        return

    try:
        hasil = r.json()
    except Exception:
        st.session_state.pesan_tambah = ("error", "⚠️ Kesalahan format data dari server.")
        return

    if hasil.get("ok"):
        st.session_state.tambah_riwayat.append((datetime.now().strftime("%H:%M:%S"), barcode, nama or "(Tanpa Nama)"))
        st.session_state.pesan_tambah = ("success", "✅ Barang baru berhasil disimpan.")
        st.session_state.tambah_barcode = ""
        st.session_state.tambah_nama = ""
        for c in kol_harga_list:
            st.session_state[f"tambah_{c}"] = 0
    else:
        st.session_state.pesan_tambah = ("error", f"⚠️ Ditolak: {hasil.get('error', 'kesalahan')}")


# --- HEADER UTAMA ---
st.title("TOKO JABON KIDUL SEPUR")
st.caption("Sistem Kasir & Manajemen Toko")

query_params = st.query_params
if "scan_val" in query_params and "scan_idx" in query_params:
    try:
        s_idx = int(query_params["scan_idx"])
        s_val = str(query_params["scan_val"])
        st.query_params.clear()
        kol_harga_temp = f"Harga {st.session_state.get('pilih_level_harga', 'Umum')}"
        if kol_harga_temp not in df_produk.columns:
            kol_harga_temp = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]
        proses_input_barcode(s_idx, s_val, kol_harga_temp)
        st.rerun()
    except Exception:
        st.query_params.clear()

if st.session_state.menu_aktif is None:
    st.markdown("---")
    st.markdown("### Pilih Menu Utama:")
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("KASIR", key="menu_kasir_utama", use_container_width=True):
                st.session_state.menu_aktif = "Kasir"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("CEK HARGA", key="menu_cari_harga", use_container_width=True):
                st.session_state.menu_aktif = "Database"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("TAMBAH", key="menu_tambah_barang", use_container_width=True):
                st.session_state.menu_aktif = "Tambah"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("---")
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("🛒 Kasir", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Kasir" else "secondary"):
            st.session_state.menu_aktif = "Kasir"
            st.rerun()
    with nav2:
        if st.button("🔍 Harga", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Database" else "secondary"):
            st.session_state.menu_aktif = "Database"
            st.rerun()
    with nav3:
        if st.button("➕ Tambah", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Tambah" else "secondary"):
            st.session_state.menu_aktif = "Tambah"
            st.rerun()
    st.markdown("---")

    if st.session_state.menu_aktif == "Database":
        st.subheader("Daftar Barang")
        
        buka_kamera_db = st.checkbox("📷 Aktifkan Pemindai Kamera", value=False, key="toggle_kamera_db")
        if buka_kamera_db:
            hasil_scan_db = qrcode_scanner(key=f"scanner_db_{st.session_state.scan_counter_db}")
            if hasil_scan_db:
                st.session_state.search_db = str(hasil_scan_db).strip()
                st.session_state.scan_counter_db += 1
                st.rerun()

        search_database = st.text_input("Cari Nama Barang / Barcode:", placeholder="Ketik kata kunci...", key="search_db")
        df_tampil = df_produk.drop(columns="_kode", errors="ignore")
        if search_database:
            kata = search_database.strip()
            mask = df_tampil.astype(str).apply(lambda x: x.str.contains(kata, case=False, na=False, regex=False)).any(axis=1)
            if "_kode" in df_produk.columns:
                mask = mask | (df_produk["_kode"] == norm_kode(kata))
            df_tampil = df_tampil[mask]
            st.button("Reset Pencarian", on_click=hapus_pencarian_db)

        df_tampil = df_tampil.copy()
        for c in df_tampil.columns:
            if c.lower().startswith("harga"):
                df_tampil[c] = df_tampil[c].map(rp)
        st.dataframe(df_tampil, use_container_width=True)

    elif st.session_state.menu_aktif == "Tambah":
        st.subheader("➕ Tambah Barang Baru")
        kolom_harga_list = [c for c in df_produk.columns if c.lower().startswith("harga")]

        if not kolom_barcode:
            st.error("Kolom Barcode tidak ditemukan pada lembar data.")
        else:
            buka_kamera_tambah = st.checkbox("Aktifkan Kamera untuk Scan Barcode", value=False, key="toggle_kamera_tambah")
            if buka_kamera_tambah:
                hasil_scan_tambah = qrcode_scanner(key=f"scanner_tambah_{st.session_state.scan_counter_tambah}")
                if hasil_scan_tambah:
                    st.session_state.tambah_barcode = str(hasil_scan_tambah).strip()
                    st.session_state.scan_counter_tambah += 1
                    st.rerun()

            st.text_input("Barcode / SKU", key="tambah_barcode", placeholder="Scan atau ketik kode...")
            st.text_input("Nama Produk", key="tambah_nama", placeholder="Ketik nama produk...")

            if kolom_harga_list:
                st.markdown("#### Pengaturan Harga")
                for c in kolom_harga_list:
                    st.number_input(c, min_value=0, value=0, step=500, key=f"tambah_{c}")

            st.markdown("")
            st.button("Simpan Data Barang", type="primary", on_click=simpan_barang, args=(kolom_barcode, kolom_nama_barang, kolom_harga_list), use_container_width=True)

            if st.session_state.pesan_tambah:
                tipe_t, teks_t = st.session_state.pesan_tambah
                getattr(st, tipe_t)(teks_t)

    elif st.session_state.menu_aktif == "Kasir":
        st.markdown("### Kategori Harga Pelanggan")
        jenis_pelanggan = st.selectbox(
            "Pilih kategori:",
            ["Umum", "Bakul", "Umum Antar", "Usaha"],
            key="pilih_level_harga",
            label_visibility="collapsed"
        )

        kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
        if kolom_harga_pilihan not in df_produk.columns:
            kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]

        st.markdown("---")

        if not st.session_state.keranjang:
            st.session_state.keranjang.append({
                "Barcode": "",
                "Nama Barang": "Ketik barcode atau nama barang...",
                "Qty": 1,
                "Harga Satuan": 0,
                "Subtotal": 0,
            })

        if st.session_state.pesan:
            tipe, teks = st.session_state.pesan
            getattr(st, tipe)(teks)

        st.markdown("### Daftar Transaksi")

        if st.session_state.scan_counter_kasir_aktif is not None:
            idx_aktif = st.session_state.scan_counter_kasir_aktif
            st.markdown("---")
            st.info(f"📷 Pemindai aktif untuk Baris #{idx_aktif + 1}")
            hasil_scan_item = qrcode_scanner(key=f"scanner_kasir_{idx_aktif}_{st.session_state.editor_counter}")
            if hasil_scan_item:
                val_hasil = str(hasil_scan_item).strip()
                st.session_state.scan_counter_kasir_aktif = None
                proses_input_barcode(idx_aktif, val_hasil, kolom_harga_pilihan)
                st.rerun()
            if st.button("Tutup Kamera", key="tutup_kamera_kasir", use_container_width=True):
                st.session_state.scan_counter_kasir_aktif = None
                st.rerun()
            st.markdown("---")

        # Tampilan Item Keranjang Runtut per Baris dengan Qty terpadu (Minus - Ketik - Plus)
        for idx, item in enumerate(st.session_state.keranjang):
            with st.container(border=True):
                st.markdown(f"**#{idx + 1} - {item['Nama Barang']}**")
                
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    key_bc = f"barcode_input_{idx}_{st.session_state.editor_counter}"
                    st.text_input(
                        "Barcode",
                        value=item.get("Barcode", ""),
                        key=key_bc,
                        placeholder="Scan/ketik barcode...",
                        label_visibility="collapsed",
                        on_change=barcode_diketik,
                        args=(idx, kolom_harga_pilihan, key_bc),
                    )
                with rc2:
                    if st.button("📷 Scan", key=f"btn_cam_{idx}", use_container_width=True):
                        st.session_state.scan_counter_kasir_aktif = idx
                        st.rerun()

                        st.rerun()
                with q_c_del:
                    if st.button("🗑️ Hapus", key=f"del_{idx}", use_container_width=True):
                        hapus_item_satuan(idx)
                        st.rerun()

                st.markdown(f"<div style='font-size:13px; color:gray; margin-top:4px;'>@ Rp {rp(item['Harga Satuan'])} &nbsp;|&nbsp; Subtotal: <b style='color:#2f3640;'>Rp {rp(item['Subtotal'])}</b></div>", unsafe_allow_html=True)

            if "_dropdown_pilihan" in item:
                st.markdown(f"Pilih opsi barang untuk baris {idx+1}:")
                for p_idx, (p_bcode, p_nm, p_hg) in enumerate(item["_dropdown_pilihan"]):
                    if st.button(f"[{p_bcode}] {p_nm} - Rp {rp(p_hg)}", key=f"drop_{idx}_{p_idx}", use_container_width=True):
                        pilih_dari_dropdown(idx, p_bcode, p_nm, p_hg)
                        st.rerun()

        col_tambah_baris, col_batal_aksi = st.columns(2)
        with col_tambah_baris:
            st.button("＋ Tambah Baris", on_click=tambah_baris_kosong, use_container_width=True)
        with col_batal_aksi:
            if st.session_state.riwayat:
                st.button("↩️ Batalkan", on_click=batalkan_terakhir, use_container_width=True)

        if len(st.session_state.keranjang) > 0:
            df_keranjang = pd.DataFrame(st.session_state.keranjang)
            subtotal_barang = int(df_keranjang["Subtotal"].sum()) if not df_keranjang.empty else 0

            st.markdown("### Lain-Lain (Diskon / Ongkir / Arisan)")
            st.button("＋ Tambah Catatan Lain-Lain", on_click=tambah_baris_lain, use_container_width=True)

            total_diskon = 0
            total_penambah = 0
            rincian_lain = []

            for i, ll in enumerate(st.session_state.lain_lain):
                with st.container(border=True):
                    c_ll1, c_ll2, c_ll3 = st.columns([2, 2, 1])
                    with c_ll1:
                        ll["tipe"] = st.selectbox("Jenis", ["Diskon", "Ongkir", "Arisan"], key=f"tipe_ll_{i}", index=["Diskon", "Ongkir", "Arisan"].index(ll["tipe"]))
                    with c_ll2:
                        ll["nominal"] = int(st.number_input("Nominal (Rp)", min_value=0, value=ll["nominal"], step=500, key=f"Nominal_ll_{i}"))
                    with c_ll3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("❌ Hapus", key=f"del_ll_{i}", use_container_width=True):
                            hapus_baris_lain(i)
                            st.rerun()

                if ll["tipe"] == "Diskon":
                    total_diskon += ll["nominal"]
                    rincian_lain.append(("Diskon", -ll["nominal"]))
                else:
                    total_penambah += ll["nominal"]
                    rincian_lain.append((ll["tipe"], ll["nominal"]))

            total_diskon = min(total_diskon, subtotal_barang)
            total_belanja_semua = subtotal_barang - total_diskon + total_penambah

            st.markdown("---")
            st.markdown(f"### TOTAL BAYAR: **Rp {rp(total_belanja_semua)}**")

            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum", key="nama_pelanggan_input")
            uang_tunai = st.number_input(
                "Uang Tunai (Rp)", min_value=0, value=max(total_belanja_semua, 0), step=5000, key=f"uang_tunai_{total_belanja_semua}"
            )

            uang_kembalian = uang_tunai - total_belanja_semua
            if uang_kembalian >= 0:
                st.success(f"Kembalian: Rp {rp(uang_kembalian)}")
            else:
                st.error(f"Uang Kurang: Rp {rp(abs(uang_kembalian))}")

            st.markdown("---")
            if not st.session_state.konfirmasi_kosong:
                st.button("Kosongkan Keranjang", type="secondary", on_click=minta_konfirmasi_kosong, use_container_width=True)
            else:
                st.warning("Yakin ingin mengosongkan seluruh keranjang?")
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.button("Ya, Kosongkan", type="primary", on_click=kosongkan_keranjang, use_container_width=True)
                with col_k2:
                    st.button("Batal", on_click=batal_kosongkan, use_container_width=True)

            st.markdown("---")
            st.markdown("### Cetak Nota")

            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            printer_width = 32

            def baris_kiri_kanan(label, val):
                space = printer_width - (len(label) + len(val))
                return label + (" " * max(1, space)) + val

            total_str = rp(total_belanja_semua)
            tunai_str = rp(uang_tunai)
            kembalian_str = rp(uang_kembalian)

            INIT = b'\x1b\x40'
            ALIGN_CENTER = b'\x1b\x61\x01'
            ALIGN_LEFT = b'\x1b\x61\x00'
            BOLD_ON = b'\x1b\x45\x01'
            BOLD_OFF = b'\x1b\x45\x00'
            CUT_PAPER = b'\x1d\x56\x00'

            raw_bytes = bytearray()
            raw_bytes.extend(INIT)

            def add_line(text="", align=ALIGN_LEFT, bold=False):
                raw_bytes.extend(align)
                raw_bytes.extend(BOLD_ON if bold else BOLD_OFF)
                raw_bytes.extend((text + "\n").encode("utf-8"))

            add_line("TOKO JABON KIDUL SEPUR", ALIGN_CENTER, bold=True)
            add_line("Jabon - Jombang", ALIGN_CENTER)
            add_line("Telp. 0857 3395 8305", ALIGN_CENTER)
            add_line("-" * printer_width, ALIGN_CENTER)
            add_line(f"Tanggal : {waktu_sekarang}")
            add_line(f"Kepada : {nama_pembeli}")
            add_line("-" * printer_width, ALIGN_CENTER)

            item_valid = [it for it in st.session_state.keranjang if it["Harga Satuan"] > 0]
            for item in item_valid:
                add_line(item["Nama Barang"], bold=True)
                add_line(baris_kiri_kanan(f"{rp(item['Harga Satuan'])} x {item['Qty']}", rp(item["Subtotal"])))
                add_line("")

            add_line("-" * printer_width, ALIGN_CENTER)
            if rincian_lain:
                add_line(baris_kiri_kanan("Subtotal", rp(subtotal_barang)))
                for lbl, val in rincian_lain:
                    val_str = ("-" if val < 0 else "") + rp(abs(val))
                    add_line(baris_kiri_kanan(lbl, val_str))
                add_line("-" * printer_width, ALIGN_CENTER)
                
            add_line(baris_kiri_kanan("Total", total_str), bold=True)
            add_line(baris_kiri_kanan("Tunai", tunai_str))
            add_line(baris_kiri_kanan("Kembalian", kembalian_str))
            add_line("-" * printer_width, ALIGN_CENTER)

            raw_bytes.extend(ALIGN_CENTER)
            raw_bytes.extend(BOLD_ON)
            raw_bytes.extend(b"Terima Kasih & Semoga Berkah\n")
            raw_bytes.extend(BOLD_OFF)
            raw_bytes.extend(b"\n\n\n")
            raw_bytes.extend(CUT_PAPER)

            pesan_wa = (
                "*NOTA BELANJA - TOKO JABON KIDUL SEPUR*\n"
                "----------------------------------\n"
                f"Tanggal : {waktu_sekarang}\n"
                f"Kepada : {nama_pembeli}\n"
                "----------------------------------\n"
            )
            for item in item_valid:
                pesan_wa += (
                    f"• {item['Nama Barang']}\n"
                    f"  {rp(item['Harga Satuan'])} x {item['Qty']} = *Rp {rp(item['Subtotal'])}*\n\n"
                )
            pesan_wa += "----------------------------------\n"
            if rincian_lain:
                pesan_wa += f"Subtotal : Rp {rp(subtotal_barang)}\n"
                for lbl, val in rincian_lain:
                    val_str = ("-" if val < 0 else "") + rp(abs(val))
                    pesan_wa += f"{lbl} : Rp {val_str}\n"
                pesan_wa += "----------------------------------\n"
            pesan_wa += (
                f"Total    : *Rp {total_str}*\n"
                f"Tunai    : Rp {tunai_str}\n"
                f"Kembalian: Rp {kembalian_str}\n"
                "----------------------------------\n"
                "Terima Kasih & Semoga Berkah"
            )
            whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(pesan_wa)}"

            col_ble, col_wa = st.columns(2)
            with col_ble:
                data_b64 = base64.b64encode(bytes(raw_bytes)).decode()
                components.html(HTML_CETAK_BLE.replace("__DATA__", data_b64), height=110)
            with col_wa:
                st.markdown(f"""
<div style="text-align: center;">
    <a href="{whatsapp_url}" target="_blank" style="background-color: #25d366; color: white; padding: 12px 20px; text-decoration: none; font-size: 16px; border-radius: 6px; font-weight: 600; display: block; margin-top: 2px;">
        💬 Kirim via WhatsApp
    </a>
</div>
""", unsafe_allow_html=True)
