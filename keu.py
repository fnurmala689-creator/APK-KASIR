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

# --- CSS: BUBBLE HANYA UNTUK MENU UTAMA, TOMBOL LAIN NORMAL ---
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
    
    @keyframes floatBubble {
        0% { transform: translateY(0px) scale(1); }
        50% { transform: translateY(-6px) scale(1.02); }
        100% { transform: translateY(0px) scale(1); }
    }

    div[data-testid="column"] .menu-btn > button {
        width: 100% !important;
        border-radius: 40px !important;
        padding: 35px 20px !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        border: 4px solid #ffffff !important;
        animation: floatBubble 4s ease-in-out infinite;
        transition: all 0.3s ease !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        color: #2d3436 !important;
    }

    div[data-testid="column"]:nth-of-type(1) .menu-btn > button {
        background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 99%, #fad0c4 100%) !important;
    }
    div[data-testid="column"]:nth-of-type(2) .menu-btn > button {
        background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%) !important;
    }
    div[data-testid="column"]:nth-of-type(3) .menu-btn > button {
        background: linear-gradient(135deg, #fbc531 0%, #e1b12c 100%) !important;
    }

    input {
        font-size: 18px !important;
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
  <button id="btn" style="width:100%; padding:14px; font-size:18px; font-weight:bold;
          border-radius:12px; border:2px solid #28a745; background:#28a745; color:#ffffff; cursor:pointer;">
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

// Variabel global untuk menyimpan perangkat yang aktif di sesi browser saat ini
let cachedDevice = null;

async function sambungkan() {
  let server = null;

  // 1. Coba gunakan perangkat di memori sesi aktif jika ada
  if (cachedDevice && cachedDevice.gatt.connected) {
    return { device: cachedDevice, ch: await cariKarakteristik(cachedDevice.gatt) };
  }

  // 2. Coba ambil dari riwayat perangkat yang diizinkan browser
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

  // 3. Jika belum pernah atau memori bersih, tampilkan kotak pilih perangkat (hanya sekali)
  setStatus("Pilih printer Bluetooth Anda...");
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
      setStatus("❌ Jalur cetak printer tidak dikenali.");
      return;
    }
    
    device = hasil.device;
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
  } catch (e) {
    cachedDevice = resetDeviceCache();
    setStatus("❌ Gagal. Pastikan printer menyala & klik cetak ulang.");
  } finally {
    btn.disabled = false;
  }
}

function resetDeviceCache() {
  return null;
}

if (btn) btn.addEventListener("click", cetak);
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

defaults = {
    "menu_aktif": None,
    "keranjang": [],
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
        st.session_state.pesan = ("info", f"Ditemukan beberapa barang untuk '{val}', silakan pilih dari daftar.")
    
    st.session_state.editor_counter += 1


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


def hapus_item_satuan(index_item):
    simpan_riwayat()
    if 0 <= index_item < len(st.session_state.keranjang):
        st.session_state.keranjang.pop(index_item)
        st.session_state.pesan = ("info", "❌ Baris dihapus dari keranjang.")
        st.session_state.editor_counter += 1


def batalkan_terakhir():
    if st.session_state.riwayat:
        st.session_state.keranjang = st.session_state.riwayat.pop()
        st.session_state.editor_counter += 1
        st.session_state.pesan = ("info", "↩️ Perubahan terakhir dibatalkan.")


def minta_konfirmasi_kosong():
    st.session_state.konfirmasi_kosong = True


def batal_kosongkan():
    st.session_state.konfirmasi_kosong = False


def kosongkan_keranjang():
    simpan_riwayat()
    st.session_state.keranjang = []
    st.session_state.pesan = ("info", "🗑️ Keranjang dikosongkan.")
    st.session_state.konfirmasi_kosong = False
    st.session_state.editor_counter += 1


def simpan_pending(nama_pelanggan):
    item_valid = [it for it in st.session_state.keranjang if it["Harga Satuan"] > 0]
    if not item_valid:
        st.session_state.pesan = ("warning", "⚠️ Keranjang masih kosong, tidak ada yang bisa dipending.")
        return
    
    waktu_pending = datetime.now().strftime("%H:%M:%S")
    label_pending = f"{nama_pelanggan} ({waktu_pending}) - {len(item_valid)} Item"
    
    st.session_state.daftar_pending.append({
        "nama": label_pending,
        "keranjang": copy.deepcopy(item_valid),
        "waktu": waktu_pending
    })
    st.session_state.keranjang = []
    st.session_state.pesan = ("success", f"⏸️ Nota untuk '{nama_pelanggan}' berhasil dipending!")
    st.session_state.editor_counter += 1


def muat_pending(index_pending):
    if 0 <= index_pending < len(st.session_state.daftar_pending):
        pending_item = st.session_state.daftar_pending.pop(index_pending)
        st.session_state.keranjang = pending_item["keranjang"]
        st.session_state.pesan = ("success", f"▶️ Memuat kembali nota pending: {pending_item['nama']}")
        st.session_state.editor_counter += 1


def hapus_pending(index_pending):
    if 0 <= index_pending < len(st.session_state.daftar_pending):
        st.session_state.daftar_pending.pop(index_pending)
        st.session_state.pesan = ("info", "❌ Nota pending dihapus.")
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


st.title("😊 TOKO JABON KIDUL SEPUR")
st.markdown("### 🙏 Don't Forget to Pray")

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
    st.markdown("### Pilih Menu Gelembung:")
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("🛒\n\nKASIR UTAMA", key="menu_kasir_utama"):
                st.session_state.menu_aktif = "Kasir"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("📋\n\nCARI HARGA", key="menu_cari_harga"):
                st.session_state.menu_aktif = "Database"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        with st.container():
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button("➕\n\nTAMBAH BARANG", key="menu_tambah_barang"):
                st.session_state.menu_aktif = "Tambah"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

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

    elif st.session_state.menu_aktif == "Kasir":
        st.markdown("### 🏷️ 1. Pilih Jenis Pembeli")
        jenis_pelanggan = st.selectbox(
            "Pilih kategori pembeli di bawah:",
            ["Umum", "Bakul", "Umum Antar", "Usaha"],
            key="pilih_level_harga",
            label_visibility="collapsed"
        )

        # --- BAGIAN PENDING NOTA / DAFTAR TUNGGU ---
        if st.session_state.daftar_pending:
            with st.expander(f"⏸️ Daftar Nota Pending ({len(st.session_state.daftar_pending)} Nota Tertunda)", expanded=False):
                for p_idx, p_data in enumerate(st.session_state.daftar_pending):
                    col_pn1, col_pn2, col_pn3 = st.columns([3, 1, 1])
                    with col_pn1:
                        st.markdown(f"**{p_data['nama']}**")
                    with col_pn2:
                        if st.button("▶️ Lanjutkan", key=f"load_pending_{p_idx}", use_container_width=True):
                            muat_pending(p_idx)
                            st.rerun()
                    with col_pn3:
                        if st.button("🗑️ Hapus", key=f"del_pending_{p_idx}", use_container_width=True):
                            hapus_pending(p_idx)
                            st.rerun()
            st.markdown("---")

        st.markdown("---")

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

        st.markdown("### 🛒 Daftar Belanjaan")
        st.info("💡 Ketik nama barang/barcode, tembak scanner fisik, atau klik ikon kamera 📷 untuk scan.")

        if st.session_state.scan_counter_kasir_aktif is not None:
            idx_aktif = st.session_state.scan_counter_kasir_aktif
            st.markdown(f"---")
            st.warning(f"📷 **Kamera Aktif untuk Baris #{idx_aktif + 1}**")
            hasil_scan_item = qrcode_scanner(key=f"scanner_kasir_{idx_aktif}_{st.session_state.editor_counter}")
            if hasil_scan_item:
                val_hasil = str(hasil_scan_item).strip()
                st.session_state.scan_counter_kasir_aktif = None
                proses_input_barcode(idx_aktif, val_hasil, kolom_harga_pilihan)
                st.rerun()
            if st.button("✖️ Tutup Kamera", key="tutup_kamera_kasir"):
                st.session_state.scan_counter_kasir_aktif = None
                st.rerun()
            st.markdown(f"---")

        options_html = ""
        for _, row in df_produk.iterrows():
            b_val = str(row[kolom_barcode]).strip() if kolom_barcode else ""
            n_val = str(row[kolom_nama_barang]).strip()
            if b_val:
                options_html += f'<option value="{b_val}">{n_val}</option>'
            if n_val:
                options_html += f'<option value="{n_val}"></option>'

        h_col0, h_col1, h_col2, h_col3, h_col4 = st.columns([1.8, 3, 2, 2, 1])
        with h_col0:
            st.markdown("**Barcode / Kode**")
        with h_col1:
            st.markdown("**Nama Barang**")
        with h_col2:
            st.markdown("**Jumlah (Qty)**")
        with h_col3:
            st.markdown("**Subtotal**")
        with h_col4:
            st.markdown("**Aksi**")
        st.markdown("---")

        for idx, item in enumerate(st.session_state.keranjang):
            row_c0, row_c0_cam, row_c1, row_c2, row_c3, row_c4 = st.columns([1.3, 0.5, 3, 2, 2, 1])
            with row_c0:
                val_bc = item.get("Barcode", "")
                
                components.html(f"""
                <div style="margin: 0px; padding: 0px; font-family: sans-serif;">
                  <input type="text" id="bc_{idx}" value="{val_bc}" placeholder="Ketik/Scan..." 
                         list="list_produk_{idx}" 
                         style="width: 100%; padding: 8px 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;"
                         onkeydown="if(event.key === 'Enter') {{ 
                             const val = encodeURIComponent(this.value);
                             window.parent.location.href = window.parent.location.pathname + '?scan_idx={idx}&scan_val=' + val;
                         }}"
                         onchange="const val = encodeURIComponent(this.value); window.parent.location.href = window.parent.location.pathname + '?scan_idx={idx}&scan_val=' + val;" />
                  <datalist id="list_produk_{idx}">
                    {options_html}
                  </datalist>
                </div>
                """, height=45)

            with row_c0_cam:
                st.markdown("<div style='margin-top: 2px;'>", unsafe_allow_html=True)
                if st.button("📷", key=f"btn_cam_{idx}", help="Scan Kamera"):
                    st.session_state.scan_counter_kasir_aktif = idx
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            with row_c1:
                st.markdown(f"**{idx + 1}. {item['Nama Barang']}**<br><span style='color:gray; font-size:14px;'>@ Rp {rp(item['Harga Satuan'])}</span>", unsafe_allow_html=True)
            with row_c2:
                sub_q1, sub_q2, sub_q3 = st.columns([1, 1, 1])
                with sub_q1:
                    if st.button("➖", key=f"min_{idx}", use_container_width=True):
                        ubah_qty_langsung(idx, -1)
                        st.rerun()
                with sub_q2:
                    st.markdown(f"<div style='text-align: center; font-weight: bold; padding-top: 5px;'>{item['Qty']}</div>", unsafe_allow_html=True)
                with sub_q3:
                    if st.button("➕", key=f"plus_{idx}", use_container_width=True):
                        ubah_qty_langsung(idx, 1)
                        st.rerun()
            with row_c3:
                st.markdown(f"**Rp {rp(item['Subtotal'])}**")
            with row_c4:
                if st.button("🗑️", key=f"del_{idx}", use_container_width=True):
                    hapus_item_satuan(idx)
                    st.rerun()

            if "_dropdown_pilihan" in item:
                st.markdown(f"🔽 **Pilih barang untuk baris {idx+1}:**")
                for p_idx, (p_bcode, p_nm, p_hg) in enumerate(item["_dropdown_pilihan"]):
                    if st.button(f"👉 [{p_bcode}] {p_nm} - Rp {rp(p_hg)}", key=f"drop_{idx}_{p_idx}", use_container_width=True):
                        pilih_dari_dropdown(idx, p_bcode, p_nm, p_hg)
                        st.rerun()

            st.markdown("---")

        col_tambah_baris, col_batal_aksi = st.columns(2)
        with col_tambah_baris:
            st.button("➕ Tambah Baris Belanja Baru", on_click=tambah_baris_kosong, use_container_width=True)
        with col_batal_aksi:
            if st.session_state.riwayat:
                st.button("↩️ Batalkan Perubahan Terakhir", on_click=batalkan_terakhir, use_container_width=True)

        if len(st.session_state.keranjang) > 0:
            df_keranjang = pd.DataFrame(st.session_state.keranjang)
            subtotal_barang = int(df_keranjang["Subtotal"].sum()) if not df_keranjang.empty else 0

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
                    "Uang Diterima dari Pembeli (Rp)", min_value=0, value=max(total_belanja_semua, 0), step=5000, key=f"uang_tunai_{total_belanja_semua}"
                )

            uang_kembalian = uang_tunai - total_belanja_semua
            if uang_kembalian >= 0:
                st.success(f"### Kembalian: Rp {rp(uang_kembalian)}")
            else:
                st.error(f"### Uang Kurang: Rp {rp(abs(uang_kembalian))}")

            st.markdown("---")
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
            st.markdown("### 🖨️ Cetak Struk / Kirim Nota")

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

            item_valid = [it for it in st.session_state.keranjang if it["Harga Satuan"] > 0]
            for item in item_valid:
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
            if rincian:
                for lbl, val in rincian:
                    pesan_wa += f"{lbl}: Rp {val}\n"
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
    <a href="{whatsapp_url}" target="_blank" style="background-color: #25d366; color: white; padding: 14px 20px; text-type: none; text-decoration: none; font-size: 18px; border-radius: 12px; font-weight: bold; display: block; margin-top: 2px;">
        💬 Kirim via WhatsApp
    </a>
</div>
""", unsafe_allow_html=True)
