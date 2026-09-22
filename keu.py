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
        setStatus("Menghubungkan ke printer...");
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
@@ -200,17 +193,14 @@ def rp(angka):
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
@@ -225,17 +215,12 @@ def rp(angka):
   }
   setStatus("✅ Berhasil dicetak!");
 } catch (e) {
    cachedDevice = resetDeviceCache();
    cachedDevice = null;
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
@@ -258,6 +243,7 @@ def rp(angka):
defaults = {
"menu_aktif": None,
"keranjang": [],
    "daftar_pending": [],  # Menyimpan daftar nota pending
"scan_counter_db": 0,
"scan_counter_tambah": 0,
"scan_counter_kasir_aktif": None,
@@ -393,6 +379,40 @@ def kosongkan_keranjang():
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

@@ -582,6 +602,23 @@ def simpan_barang(kol_barcode, kol_nama, kol_harga_list):
if kolom_harga_pilihan not in df_produk.columns:
kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]

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

if not st.session_state.keranjang:
@@ -729,6 +766,12 @@ def simpan_barang(kol_barcode, kol_nama, kol_harga_list):
"Uang Diterima dari Pembeli (Rp)", min_value=0, value=max(total_belanja_semua, 0), step=5000, key=f"uang_tunai_{total_belanja_semua}"
)

            # Tombol Pending Nota
            st.markdown("")
            if st.button("⏸️ Pending Nota Ini (Simpan Sementara)", type="primary", use_container_width=True):
                simpan_pending(nama_pembeli)
                st.rerun()

uang_kembalian = uang_tunai - total_belanja_semua
if uang_kembalian >= 0:
st.success(f"### Kembalian: Rp {rp(uang_kembalian)}")
