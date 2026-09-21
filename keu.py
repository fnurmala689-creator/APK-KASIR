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

st.set_page_config(page_title="TOKO JABON KIDUL SEPUR", page_icon="🤞", layout="wide")

# --- CSS: BUBBLE STREAMLIT YANG RAPI & BERANIMASI ---
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }
    html, body, [class*="css"] {
        font-size: 18px !important;
    }
    
    /* Animasi Melayang Lembut */
    @keyframes floatBubble {
        0% { transform: translateY(0px) scale(1); }
        50% { transform: translateY(-6px) scale(1.02); }
        100% { transform: translateY(0px) scale(1); }
    }

    /* Kustomisasi Tombol Streamlit Menjadi Bubble Lucu */
    .stButton > button {
        width: 100% !important;
        border-radius: 40px !important;
        padding: 35px 20px !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        border: 4px solid #ffffff !important;
        animation: floatBubble 4s ease-in-out infinite;
        transition: all 0.3s ease !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        color: white !important;
    }

    /* Warna Bubble 1: Pink Peach (Kasir) */
    div[data-testid="column"]:nth-of-type(1) .stButton > button {
        background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 99%, #fad0c4 100%) !important;
    }
    div[data-testid="column"]:nth-of-type(1) .stButton > button:hover {
        transform: scale(1.06) !important;
        box-shadow: 0 15px 30px rgba(255, 154, 158, 0.6) !important;
    }

    /* Warna Bubble 2: Biru Langit (Cari Harga) */
    div[data-testid="column"]:nth-of-type(2) .stButton > button {
        background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%) !important;
    }
    div[data-testid="column"]:nth-of-type(2) .stButton > button:hover {
        transform: scale(1.06) !important;
        box-shadow: 0 15px 30px rgba(161, 196, 253, 0.6) !important;
    }

    /* Warna Bubble 3: Kuning Ceria (Tambah Barang) */
    div[data-testid="column"]:nth-of-type(3) .stButton > button {
        background: linear-gradient(135deg, #fbc531 0%, #e1b12c 100%) !important;
    }
    div[data-testid="column"]:nth-of-type(3) .stButton > button:hover {
        transform: scale(1.06) !important;
        box-shadow: 0 15px 30px rgba(251, 197, 49, 0.6) !important;
    }

    input {
        font-size: 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- LINK SPREADSHEET PERMANEN ---
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


# ============ CETAK BLUETOOTH (BLE) ============
HTML_CETAK_BLE = """
<div style="font-family: sans-serif;">
  <button id="btn" style="width:100%; padding:12px; font-size:18px; font-weight:bold;
          border-radius:10px; border:2px solid #28a745; background:#28a745; color:#ffffff; cursor:pointer;">
    🖨️ Cetak Struk via Bluetooth
  </button>
  <div id="status" style="font-size:14px; color:#333; margin-top:6px; min-height:20px; font-weight:bold;"></div>
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

async function sambungkan() {
  let device = null, server = null;
  if (navigator.bluetooth.getDevices) {
    try {
      let idTersimpan = null;
      try { idTersimpan = localStorage.getItem("kasir_printer_id"); } catch (e) {}
      if (idTersimpan) {
        const daftar = await navigator.bluetooth.getDevices();
        device = daftar.find((d) => d.id === idTersimpan) || null;
        if (device) server = await device.gatt.connect();
      }
    } catch (e) { device = null; server = null; }
  }

  if (!server) {
    device = await navigator.bluetooth.requestDevice({
      acceptAllDevices: true,
      optionalServices: SERVICES
    });
    server = await device.gatt.connect();
    try { localStorage.setItem("kasir_printer_id", device.id); } catch (e) {}
  }

  const ch = await cariKarakteristik(server);
  return { device, server, ch };
}

async function cetak() {
  btn.disabled = true;
  let device = null;
  try {
    if (!navigator.bluetooth) {
      setStatus("❌ Browser tidak mendukung Bluetooth.");
      return;
    }
    setStatus("Menghubungkan ke printer...");
    const hasil = await sambungkan();
    device = hasil.device;
    if (!hasil.ch) {
      setStatus("❌ Jalur cetak printer tidak dikenali.");
      try { device.gatt.disconnect(); } catch (e) {}
      return;
    }
    const ch = hasil.ch;
    setStatus("Sedang mencetak...");
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
    setTimeout(() => { try { device.gatt.disconnect(); } catch (e) {} }, 1500);
  } catch (e) {
    setStatus("❌ Gagal mencetak. Pastikan printer menyala.");
    try { if (device) device.gatt.disconnect(); } catch (x) {}
  } finally {
    btn.disabled = false;
  }
}
btn.addEventListener("click", cetak);
</script>
"""

df_produk, data_dari_sheet = muat_produk()
df_produk = df_produk.copy()

if not data_dari_sheet:
    st.error("⚠️ Gagal mengambil data dari internet. Memakai data cadangan sementara.")

kolom_nama_opsi = ["Nama Barang", "nama barang", "Nama", "nama", "Produk", "produk"]
kolom_nama_barang = next((c for c in kolom_nama_opsi if c in df_produk.columns), df_produk.columns[0])

kolom_barcode_opsi = ["Barcode", "barcode", "SKU", "sku", "Kode", "kode"]
kolom_barcode = next((c for c in kolom_barcode_opsi if c in df_produk.columns), None)

if kolom_barcode:
    df_produk["_kode"] = df_produk[kolom_barcode].map(norm_kode)

# --- SESSION STATE ---
defaults = {
    "menu_aktif": None,
    "keranjang": [],
    "scan_trigger": "",
    "scan_counter": 0,
    "scan_counter_db": 0,
    "scan_counter_tambah": 0,
    "tambah_barcode": "",
    "tambah_nama": "",
    "tambah_riwayat": [],
    "pesan_tambah": None,
    "last_scan": "",
    "editor_counter": 0,
    "riwayat": [],
    "konfirmasi_kosong": False,
    "pilihan": [],
    "pesan": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def simpan_riwayat():
    st.session_state.riwayat.append(copy.deepcopy(st.session_state.keranjang))
    st.session_state.riwayat = st.session_state.riwayat[-20:]


def tambah_ke_keranjang(nama, harga):
    simpan_riwayat()
    for item in st.session_state.keranjang:
        if item["Nama Barang"] == nama and item["Harga Satuan"] == harga:
            item["Qty"] += 1
            item["Subtotal"] = item["Qty"] * item["Harga Satuan"]
            return
    st.session_state.keranjang.append({
        "Nama Barang": nama,
        "Qty": 1,
        "Harga Satuan": harga,
        "Subtotal": harga,
    })


def pilih_produk(nama, harga):
    tambah_ke_keranjang(nama, harga)
    st.session_state.pilihan = []
    st.session_state.pesan = ("success", f"✅ Masuk Keranjang: **{nama}** (Rp {rp(harga)})")


def submit_teks():
    st.session_state.scan_trigger = st.session_state.input_text_kasir.strip()
    st.session_state.input_text_kasir = ""


def terapkan_edit_qty():
    key = f"editor_keranjang_{st.session_state.editor_counter}"
    edits = st.session_state.get(key, {}).get("edited_rows", {})
    simpan_riwayat()
    baru = []
    for i, item in enumerate(st.session_state.keranjang):
        qty = edits.get(i, {}).get("Qty", item["Qty"])
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = item["Qty"]
        if qty > 0:
            item["Qty"] = qty
            item["Subtotal"] = qty * item["Harga Satuan"]
            baru.append(item)
    st.session_state.keranjang = baru
    st.session_state.editor_counter += 1


def batalkan_terakhir():
    if st.session_state.riwayat:
        st.session_state.keranjang = st.session_state.riwayat.pop()
        st.session_state.editor_counter += 1
        st.session_state.pilihan = []
        st.session_state.pesan = ("info", "↩️ Perubahan terakhir dibatalkan.")


def hapus_barang(key_pilihan):
    i = st.session_state.get(key_pilihan)
    if i is not None and 0 <= i < len(st.session_state.keranjang):
        simpan_riwayat()
        nama = st.session_state.keranjang[i]["Nama Barang"]
        del st.session_state.keranjang[i]
        st.session_state.editor_counter += 1
        st.session_state.pilihan = []
        st.session_state.pesan = ("info", f"❌ {nama} dihapus dari keranjang.")


def minta_konfirmasi_kosong():
    st.session_state.konfirmasi_kosong = True


def batal_kosongkan():
    st.session_state.konfirmasi_kosong = False


def kosongkan_keranjang():
    simpan_riwayat()
    st.session_state.keranjang = []
    st.session_state.pilihan = []
    st.session_state.pesan = ("info", "🗑️ Keranjang dikosongkan.")
    st.session_state.last_scan = ""
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
        st.session_state.pesan_tambah = ("error", "⚠️ Sambungan ke sistem pusat belum diatur.")
        return

    values = {kol_barcode: barcode, kol_nama: nama}
    for c in kol_harga_list:
        v = int(st.session_state.get(f"tambah_{c}", 0) or 0)
        values[c] = v if v > 0 else ""

    payload = {"token": token, "kolom_barcode": kol_barcode, "values": values}
    try:
        r = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "text/plain"}, timeout=25)
    except Exception as e:
        st.session_state.pesan_tambah = ("error", f"⚠️ Gagal menyambung ke internet: {e}")
        return

    try:
        hasil = r.json()
    except Exception:
        st.session_state.pesan_tambah = ("error", "⚠️ Ada kesalahan data dari pusat.")
        return

    if hasil.get("ok"):
        st.session_state.tambah_riwayat.append((datetime.now().strftime("%H:%M:%S"), barcode, nama or "(Tanpa Nama)"))
        st.session_state.pesan_tambah = ("success", "✅ Berhasil menyimpan barang baru!")
        st.session_state.tambah_barcode = ""
        st.session_state.tambah_nama = ""
        for c in kol_harga_list:
            st.session_state[f"tambah_{c}"] = 0
    else:
        st.session_state.pesan_tambah = ("error", f"⚠️ Ditolak: {hasil.get('error', 'kesalahan')}")


# ================= TAMPILAN UTAMA =================
st.title("😊 TOKO JABON KIDUL SEPUR")
st.markdown("### 🙏 Don't Forget to Pray")

# JIKA BELUM ADA MENU -> TAMPILKAN 3 BUBBLE TOMBOL UTAMA
if st.session_state.menu_aktif is None:
    st.markdown("---")
    st.markdown("### Pilih Menu Gelembung:")
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("🛒\n\nKASIR UTAMA"):
            st.session_state.menu_aktif = "Kasir"
            st.rerun()

    with c2:
        if st.button("📋\n\nCARI HARGA"):
            st.session_state.menu_aktif = "Database"
            st.rerun()

    with c3:
        if st.button("➕\n\nTAMBAH BARANG"):
            st.session_state.menu_aktif = "Tambah"
            st.rerun()

# JIKA SUDAH DIPILIH -> MASUK RUANGAN & IKON KECIL DI ATAS
else:
    st.markdown("---")
    nav1, nav2, nav3, nav_kosong = st.columns([1, 1, 1, 4])
    with nav1:
        if st.button("🛒 Kasir", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Kasir" else "secondary"):
            st.session_state.menu_aktif = "Kasir"
            st.rerun()
    with nav2:
        if st.button("📋 Harga", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Database" else "secondary"):
            st.session_state.menu_aktif = "Database"
            st.rerun()
    with nav3:
        if st.button("➕ Tambah", use_container_width=True, type="primary" if st.session_state.menu_aktif == "Tambah" else "secondary"):
            st.session_state.menu_aktif = "Tambah"
            st.rerun()
    st.markdown("---")

    # ---------------- RUANGAN 2: CARI HARGA (DATABASE) ----------------
    if st.session_state.menu_aktif == "Database":
        st.subheader("📋 Daftar Barang dan Cek Harga")
        st.info("💡 Gunakan halaman ini untuk mencari tahu harga barang dengan cepat.")

        buka_kamera_db = st.checkbox("📷 Nyalakan Kamera untuk Scan Barcode", value=False, key="toggle_kamera_db")
        if buka_kamera_db:
            hasil_scan_db = qrcode_scanner(key=f"scanner_db_{st.session_state.scan_counter_db}")
            if hasil_scan_db:
                st.session_state.search_db = str(hasil_scan_db).strip()
                st.session_state.scan_counter_db += 1
                st.rerun()

        search_database = st.text_input("🔍 Ketik Nama Barang atau Barcode:", placeholder="Contoh: Gula atau Beras", key="search_db")
        df_tampil = df_produk.drop(columns="_kode", errors="ignore")
        if search_database:
            kata = search_database.strip()
            mask = df_tampil.astype(str).apply(lambda x: x.str.contains(kata, case=False, na=False, regex=False)).any(axis=1)
            if "_kode" in df_produk.columns:
                mask = mask | (df_produk["_kode"] == norm_kode(kata))
            df_tampil = df_tampil[mask]
            st.button("✖️ Bersihkan Pencarian", on_click=hapus_pencarian_db)

        df_tampil = df_tampil.copy()
        for c in df_tampil.columns:
            if c.lower().startswith("harga"):
                df_tampil[c] = df_tampil[c].map(rp)
        st.dataframe(df_tampil, use_container_width=True)


    # ---------------- RUANGAN 3: TAMBAH BARANG ----------------
    elif st.session_state.menu_aktif == "Tambah":
        st.subheader("➕ Tambah Barang Baru")
        kolom_harga_list = [c for c in df_produk.columns if c.lower().startswith("harga")]

        if not kolom_barcode:
            st.error("Kolom Barcode tidak ditemukan.")
        else:
            buka_kamera_tambah = st.checkbox("📷 Nyalakan Kamera untuk Scan Barcode Baru", value=False, key="toggle_kamera_tambah")
            if buka_kamera_tambah:
                hasil_scan_tambah = qrcode_scanner(key=f"scanner_tambah_{st.session_state.scan_counter_tambah}")
                if hasil_scan_tambah:
                    st.session_state.tambah_barcode = str(hasil_scan_tambah).strip()
                    st.session_state.scan_counter_tambah += 1
                    st.rerun()

            st.text_input("Barcode Barang", key="tambah_barcode", placeholder="Scan atau ketik nomor barcode...")
            st.text_input("Nama Barang", key="tambah_nama", placeholder="Ketik nama barang...")

            if kolom_harga_list:
                st.markdown("### Atur Harga")
                kolom_ui = st.columns(len(kolom_harga_list))
                for kol, c in zip(kolom_ui, kolom_harga_list):
                    with kol:
                        st.number_input(c, min_value=0, value=0, step=500, key=f"tambah_{c}")

            st.markdown("")
            st.button("💾 Simpan Barang Ini", type="primary", on_click=simpan_barang, args=(kolom_barcode, kolom_nama_barang, kolom_harga_list), use_container_width=True)

            if st.session_state.pesan_tambah:
                tipe_t, teks_t = st.session_state.pesan_tambah
                getattr(st, tipe_t)(teks_t)


    # ---------------- RUANGAN 1: KASIR UTAMA ----------------
    elif st.session_state.menu_aktif == "Kasir":
        st.markdown("### 🏷️ 1. Pilih Jenis Pembeli")
        jenis_pelanggan = st.selectbox(
            "Pilih kategori pembeli di bawah:",
            ["Umum", "Bakul", "Umum Antar", "Usaha"],
            key="pilih_level_harga",
            label_visibility="collapsed"
        )

        kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
        if kolom_harga_pilihan not in df_produk.columns:
            kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]

        st.markdown("---")
        st.markdown("### 🔍 2. Masukkan Barang (Ketik atau Scan)")
        
        kamera_aktif = st.session_state.get("toggle_kamera_box", False)
        expander_terbuka = len(st.session_state.keranjang) == 0 or kamera_aktif

        with st.expander("👉 KLIK DI SINI UNTUK KETIK / SCAN BARANG", expanded=expander_terbuka):
            st.text_input(
                "Ketik nama barang atau barcode, lalu tekan ENTER:",
                placeholder="Contoh: Beras atau Minyak",
                key="input_text_kasir",
                on_change=submit_teks,
            )

            buka_kamera = st.checkbox("📷 Buka Kamera Scanner Barcode", value=False, key="toggle_kamera_box")

            if buka_kamera:
                hasil_scan = qrcode_scanner(key=f"scanner_{st.session_state.scan_counter}")
                if hasil_scan:
                    st.session_state.scan_trigger = str(hasil_scan).strip()
                    st.session_state.last_scan = str(hasil_scan).strip()
                    st.session_state.scan_counter += 1
                    st.rerun()

        # --- PEMROSESAN KEYWORD ---
        keyword_aktif = st.session_state.scan_trigger
        if keyword_aktif:
            st.session_state.scan_trigger = ""
            st.session_state.pilihan = []
            st.session_state.pesan = None

            df_match = pd.DataFrame()
            if kolom_barcode:
                df_match = df_produk[df_produk["_kode"] == norm_kode(keyword_aktif)]
            if len(df_match) == 0:
                df_match = df_produk[
                    df_produk[kolom_nama_barang].astype(str).str.contains(
                        keyword_aktif, case=False, na=False, regex=False
                    )
                ]

            if len(df_match) == 0:
                st.session_state.pesan = ("warning", f"⚠️ Maaf, barang '{keyword_aktif}' tidak ditemukan.")
            else:
                daftar = []
                for _, row in df_match.iterrows():
                    harga = int(row[kolom_harga_pilihan])
                    daftar.append((str(row[kolom_nama_barang]).strip() or "(Tanpa Nama)", harga))

                if len(daftar) == 1:
                    pilih_produk(*daftar[0])
                else:
                    st.session_state.pilihan = daftar
                    st.session_state.pesan = ("info", f"Ditemukan beberapa barang untuk '{keyword_aktif}', silakan pilih salah satu:")

        if st.session_state.pesan:
            tipe, teks = st.session_state.pesan
            getattr(st, tipe)(teks)

        for i, (nm, hg) in enumerate(st.session_state.pilihan):
            st.button(
                f"👉 Pilih: {nm} - Rp {rp(hg)}",
                key=f"pilih_{i}",
                on_click=pilih_produk,
                args=(nm, hg),
                use_container_width=True
            )

        if st.session_state.riwayat:
            st.markdown("")
            st.button(
                "↩️ BATALKAN PERUBAHAN TERAKHIR",
                on_click=batalkan_terakhir,
                use_container_width=True
            )

        st.markdown("---")

        # ================= KERANJANG & NOTA =================
        if len(st.session_state.keranjang) > 0:
            st.subheader("🛒 3. Daftar Belanjaan (Keranjang)")
            st.info("💡 Anda bisa mengubah jumlah (Qty) langsung di tabel bawah ini. Ketik angka 0 jika ingin menghapus barang.")
            
            df_keranjang = pd.DataFrame(st.session_state.keranjang)
            df_keranjang.index = range(1, len(df_keranjang) + 1)
            df_keranjang.index.name = "No"
            
            df_tampil_keranjang = df_keranjang.copy()
            df_tampil_keranjang["Harga Satuan"] = df_tampil_keranjang["Harga Satuan"].map(rp)
            df_tampil_keranjang["Subtotal"] = df_tampil_keranjang["Subtotal"].map(rp)
            
            st.data_editor(
                df_tampil_keranjang,
                key=f"editor_keranjang_{st.session_state.editor_counter}",
                on_change=terapkan_edit_qty,
                disabled=["Nama Barang", "Harga Satuan", "Subtotal"],
                column_config={
                    "Qty": st.column_config.NumberColumn(
                        "Jumlah", min_value=0, step=1, format="%d",
                        help="Ubah jumlah barang",
                    ),
                    "Harga Satuan": st.column_config.TextColumn("Harga Satuan"),
                    "Subtotal": st.column_config.TextColumn("Subtotal"),
                },
                use_container_width=True,
            )

            subtotal_barang = int(df_keranjang["Subtotal"].sum())

            st.markdown("### 💰 Rincian Biaya Tambahan")
            col_dk1, col_dk2, col_dk3 = st.columns(3)
            with col_dk1:
                diskon_input = st.number_input("Diskon (Rp)", min_value=0, value=0, step=500, key="diskon_input")
            with col_dk2:
                ongkir = int(st.number_input("Ongkir (Rp)", min_value=0, value=0, step=500, key="ongkir_input"))
            with col_dk3:
                arisan = int(st.number_input("Arisan (Rp)", min_value=0, value=0, step=1000, key="arisan_input"))

            diskon = min(int(diskon_input), subtotal_barang)
            total_belanja_semua = subtotal_barang - diskon + ongkir + arisan

            st.markdown("")
            st.markdown(f"## 💵 **TOTAL BAYAR: Rp {rp(total_belanja_semua)}**")

            col_aksi1, col_aksi2 = st.columns(2)
            with col_aksi1:
                nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum", key="nama_pelanggan_input")
            with col_aksi2:
                uang_tunai = st.number_input(
                    "Uang Diterima dari Pembeli (Rp)", min_value=0, value=total_belanja_semua, step=5000, key=f"uang_tunai_{total_belanja_semua}"
                )

            uang_kembalian = uang_tunai - total_belanja_semua
            if uang_kembalian >= 0:
                st.success(f"### Kembalian: Rp {rp(uang_kembalian)}")
            else:
                st.error(f"### Uang Kurang: Rp {rp(abs(uang_kembalian))}")

            st.markdown("---")
            st.markdown("### 🗑️ Hapus Barang / Kosongkan Keranjang")
            key_hapus = f"pilih_hapus_{st.session_state.editor_counter}"
            col_h1, col_h2 = st.columns([3, 2])
            with col_h1:
                st.selectbox(
                    "Pilih barang yang ingin dibuang:",
                    options=list(range(len(st.session_state.keranjang))),
                    format_func=lambda i: f"{i + 1}. {st.session_state.keranjang[i]['Nama Barang']} (x{st.session_state.keranjang[i]['Qty']})",
                    key=key_hapus,
                    label_visibility="collapsed"
                )
            with col_h2:
                st.button("❌ Hapus Barang Ini", on_click=hapus_barang, args=(key_hapus,), use_container_width=True)

            if not st.session_state.konfirmasi_kosong:
                st.button("🗑️ Kosongkan Seluruh Keranjang", type="secondary", on_click=minta_konfirmasi_kosong, use_container_width=True)
            else:
                st.warning("⚠️ Yakin ingin menghapus SEMUA belanjaan di keranjang?")
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.button("Ya, Kosongkan", type="primary", on_click=kosongkan_keranjang, use_container_width=True)
                with col_k2:
                    st.button("Batal", on_click=batal_kosongkan, use_container_width=True)

            st.markdown("---")
            st.markdown("### 🖨️ 4. Cetak Struk / Kirim Nota")

            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            printer_width = 32

            def baris_kiri_kanan(label, val):
                space = printer_width - (len(label) + len(val))
                return label + (" " * max(1, space)) + val

            total_str = rp(total_belanja_semua)
            tunai_str = rp(uang_tunai)
            kembalian_str = rp(uang_kembalian)

            rincian = []
            if diskon > 0 or ongkir > 0 or arisan > 0:
                rincian.append(("Subtotal", rp(subtotal_barang)))
                if diskon > 0:
                    rincian.append(("Diskon", "-" + rp(diskon)))
                if ongkir > 0:
                    rincian.append(("Ongkir", rp(ongkir)))
                if arisan > 0:
                    rincian.append(("Arisan", rp(arisan)))

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

            for item in st.session_state.keranjang:
                add_line(item["Nama Barang"], bold=True)
                add_line(baris_kiri_kanan(f"{rp(item['Harga Satuan'])} x {item['Qty']} item", rp(item["Subtotal"])))
                add_line("")

            add_line("-" * printer_width, ALIGN_CENTER)
            if rincian:
                for lbl, val in rincian:
                    add_line(baris_kiri_kanan(lbl, val))
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

            nama_file_bin = f"nota_{datetime.now().strftime('%d%m%y_%H%M%S')}.bin"

            pesan_wa = (
                "*NOTA BELANJA - TOKO JABON KIDUL SEPUR*\n"
                "----------------------------------\n"
                f"Tanggal : {waktu_sekarang}\n"
                f"Kepada : {nama_pembeli}\n"
                "----------------------------------\n"
            )
            for item in st.session_state.keranjang:
                pesan_wa += (
                    f"• {item['Nama Barang']}\n"
                    f"  {rp(item['Harga Satuan'])} x {item['Qty']} = *Rp {rp(item['Subtotal'])}*\n\n"
                )
            pesan_wa += "----------------------------------\n"
            if rincian:
                for lbl, val in rincian:
                    pesan_wa += f"{lbl:<9}: Rp {val}\n".replace("Rp -", "-Rp ")
                pesan_wa += "----------------------------------\n"
            pesan_wa += (
                f"Total    : *Rp {total_str}*\n"
                f"Tunai    : Rp {tunai_str}\n"
                f"Kembalian: Rp {kembalian_str}\n"
                "----------------------------------\n"
                "Terima Kasih & Semoga Berkah"
            )
            whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(pesan_wa)}"

            col_ble, col_btn1, col_btn2 = st.columns(3)
            with col_ble:
                data_b64 = base64.b64encode(bytes(raw_bytes)).decode()
                components.html(HTML_CETAK_BLE.replace("__DATA__", data_b64), height=110)
            with col_btn1:
                st.download_button(
                    label="📄 Cetak via RawBT",
                    data=bytes(raw_bytes),
                    file_name=nama_file_bin,
                    mime="application/octet-stream",
                    use_container_width=True,
                )
            with col_btn2:
                st.markdown(f"""
<div style="text-align: center;">
    <a href="{whatsapp_url}" target="_blank" style="background-color: #25d366; color: white; padding: 12px 20px; text-decoration: none; font-size: 18px; border-radius: 10px; font-weight: bold; display: block; margin-top: 2px;">
        💬 Kirim via WhatsApp
    </a>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("🛒 Keranjang belanja masih kosong. Silakan ketik nama barang di atas atau nyalakan kamera untuk mulai scan.")
