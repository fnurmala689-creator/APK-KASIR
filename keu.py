name=keu (7).py
```[cite: 1]
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

st.set_page_config(page_title="TOKO JABON KIDUL SEPUR", page_icon="💼", layout="wide")

# --- CSS: TAMPILAN CLASSIC, PROFESIONAL, & BERSIH ---
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
        font-size: 16px !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Styling tombol menu utama ala dashboard profesional */
    div[data-testid="column"] .menu-btn > button {
        width: 100% !important;
        border-radius: 8px !important;
        padding: 24px 16px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        border: 1px solid #dcdde1 !important;
        background-color: #f5f6fa !important;
        color: #2f3640 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    }
    
    div[data-testid="column"] .menu-btn > button:hover {
        background-color: #e4e4e9 !important;
        border-color: #b2bec3 !important;
    }

    input {
        font-size: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PERMANENT_CSV_URL = "[https://docs.google.com/spreadsheets/d/e/2PACX-1vRIw6LgDSUn_lDlosWSAGQra0bR597E_Av6OYoo9uRpVr1P9ROMMgSaS_OSjp1Jj3Sp5GBRV01lIh0k/pub?output=csv](https://docs.google.com/spreadsheets/d/e/2PACX-1vRIw6LgDSUn_lDlosWSAGQra0bR597E_Av6OYoo9uRpVr1P9ROMMgSaS_OSjp1Jj3Sp5GBRV01lIh0k/pub?output=csv)"

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
