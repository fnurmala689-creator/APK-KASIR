import streamlit as st
import pandas as pd
import copy
from datetime import datetime
import urllib.parse
from streamlit_qrcode_scanner import qrcode_scanner

st.set_page_config(page_title="TOKO JABON KIDUL SEPUR", page_icon="🤞", layout="wide")

# Kurangi ruang kosong di pinggir dan atas supaya muat lebih banyak di layar tablet
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
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("😊 TOKO JABON KIDUL SEPUR")
st.markdown("Don't Forget to Pray")

# --- LINK SPREADSHEET PERMANEN ---
PERMANENT_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIw6LgDSUn_lDlosWSAGQra0bR597E_Av6OYoo9uRpVr1P9ROMMgSaS_OSjp1Jj3Sp5GBRV01lIh0k/pub?output=csv"

# Data cadangan kalau Google Sheets gagal diunduh
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
        df = pd.read_csv(PERMANENT_CSV_URL, dtype=str)  # semua dibaca sebagai teks
        ok = True
    except Exception:
        df = FALLBACK.astype(str)
        ok = False
    df.columns = df.columns.str.strip()
    # kolom harga diubah jadi angka
    for c in df.columns:
        if c.lower().startswith("harga"):
            df[c] = (
                df[c].fillna("0").astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.replace(r"[^\d]", "", regex=True)
                .replace("", "0")
                .astype(int)
            )
    return df, ok


def norm_kode(x):
    """Samakan format barcode: hapus spasi, '.0', dan angka 0 di depan."""
    s = str(x).strip().replace("\u00a0", "")
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0")


def rp(angka):
    return f"{angka:,.0f}".replace(",", ".")


df_produk, data_dari_sheet = muat_produk()
df_produk = df_produk.copy()

if not data_dari_sheet:
    st.error("⚠️ Gagal mengambil data dari Google Sheets. Sekarang memakai data contoh.")

kolom_nama_opsi = ["Nama Barang", "nama barang", "Nama", "nama", "Produk", "produk"]
kolom_nama_barang = next((c for c in kolom_nama_opsi if c in df_produk.columns), df_produk.columns[0])

kolom_barcode_opsi = ["Barcode", "barcode", "SKU", "sku", "Kode", "kode"]
kolom_barcode = next((c for c in kolom_barcode_opsi if c in df_produk.columns), None)

if kolom_barcode:
    df_produk["_kode"] = df_produk[kolom_barcode].map(norm_kode)

# --- SESSION STATE ---
defaults = {
    "keranjang": [],
    "scan_trigger": "",
    "scan_counter": 0,
    "scan_counter_db": 0,  # counter scanner di tab Daftar Harga
    "last_scan": "",
    "editor_counter": 0,  # untuk reset tabel keranjang setelah diedit
    "riwayat": [],        # riwayat keranjang untuk fitur batalkan
    "konfirmasi_kosong": False,
    "pilihan": [],      # hasil pencarian yang punya lebih dari 1 produk
    "pesan": None,      # (tipe, teks)
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def simpan_riwayat():
    """Simpan kondisi keranjang sekarang, supaya bisa dibatalkan."""
    st.session_state.riwayat.append(copy.deepcopy(st.session_state.keranjang))
    st.session_state.riwayat = st.session_state.riwayat[-20:]  # simpan maksimal 20 langkah


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
    st.session_state.pesan = ("success", f"✅ Berhasil masuk keranjang: **{nama}** (Rp {rp(harga)})")


def submit_teks():
    """Dipanggil saat Enter ditekan di kolom pencarian."""
    st.session_state.scan_trigger = st.session_state.input_text_kasir.strip()
    st.session_state.input_text_kasir = ""


def terapkan_edit_qty():
    """Dipanggil saat Qty di tabel keranjang diubah. Qty 0 = hapus barang."""
    key = f"editor_keranjang_{st.session_state.editor_counter}"
    edits = st.session_state.get(key, {}).get("edited_rows", {})
    simpan_riwayat()
    baru = []
    for i, item in enumerate(st.session_state.keranjang):
        qty = edits.get(i, {}).get("Qty", item["Qty"])
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = item["Qty"]  # kalau kolom dikosongkan, pakai nilai lama
        if qty > 0:
            item["Qty"] = qty
            item["Subtotal"] = qty * item["Harga Satuan"]
            baru.append(item)
    st.session_state.keranjang = baru
    st.session_state.editor_counter += 1


def batalkan_terakhir():
    """Kembalikan keranjang ke kondisi sebelum input terakhir."""
    if st.session_state.riwayat:
        st.session_state.keranjang = st.session_state.riwayat.pop()
        st.session_state.editor_counter += 1
        st.session_state.pilihan = []
        st.session_state.pesan = ("info", "↩️ Input terakhir dibatalkan.")


def hapus_barang(key_pilihan):
    """Hapus satu barang tertentu dari keranjang."""
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
    st.session_state.pesan = ("info", "🗑️ Keranjang dikosongkan. Klik 'Batalkan Input Terakhir' untuk mengembalikan.")
    st.session_state.last_scan = ""
    st.session_state.konfirmasi_kosong = False
    st.session_state.diskon_input = 0
    st.session_state.ongkir_input = 0
    st.session_state.arisan_input = 0
    st.session_state.editor_counter += 1


def hapus_pencarian_db():
    st.session_state.search_db = ""


tab1, tab2 = st.tabs(["🛒 Kasir", "📋 Database Harga"])

# ================= TAB 2 =================
with tab2:
    st.subheader("Daftar Barang & Harga")

    # Scanner harus dirender SEBELUM kolom pencarian, supaya hasil scan
    # bisa langsung diisikan ke kolom pencarian.
    buka_kamera_db = st.checkbox("📷 Buka Scanner", value=False, key="toggle_kamera_db")
    if buka_kamera_db:
        st.caption("Gunakan salah satu kamera saja. Matikan scanner di tab Kasir kalau sedang aktif.")
        hasil_scan_db = qrcode_scanner(key=f"scanner_db_{st.session_state.scan_counter_db}")
        if hasil_scan_db:
            st.session_state.search_db = str(hasil_scan_db).strip()
            st.session_state.scan_counter_db += 1
            st.rerun()

    search_database = st.text_input(
        "🔍 Cari produk :",
        placeholder="Ketik nama barang atau barcode...",
        key="search_db",
    )
    df_tampil = df_produk.drop(columns="_kode", errors="ignore")
    if search_database:
        kata = search_database.strip()
        mask = df_tampil.astype(str).apply(
            lambda x: x.str.contains(kata, case=False, na=False, regex=False)
        ).any(axis=1)
        # cocokkan juga barcode dengan format yang sudah disamakan (abaikan 0 di depan)
        if "_kode" in df_produk.columns:
            mask = mask | (df_produk["_kode"] == norm_kode(kata))
        df_tampil = df_tampil[mask]
        st.caption(f"Menampilkan {len(df_tampil)} produk untuk pencarian: `{kata}`")
        st.button("✖️ Hapus pencarian", on_click=hapus_pencarian_db)
    # Tampilkan kolom harga dengan titik ribuan (15000 -> 15.000)
    df_tampil = df_tampil.copy()
    for c in df_tampil.columns:
        if c.lower().startswith("harga"):
            df_tampil[c] = df_tampil[c].map(rp)
    st.dataframe(df_tampil, use_container_width=True)

# ================= TAB 1 =================
with tab1:
    jenis_pelanggan = st.selectbox(
        "🏷️ Pilih Jenis Pelanggan :",
        ["Umum", "Bakul", "Umum Antar", "Usaha"],
        key="pilih_level_harga",
    )

    kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
    if kolom_harga_pilihan not in df_produk.columns:
        kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]

    kamera_aktif = st.session_state.get("toggle_kamera_box", False)
    expander_terbuka = len(st.session_state.keranjang) == 0 or kamera_aktif

    with st.expander("🔍 Klik untuk Input", expanded=expander_terbuka):
        st.text_input(
            "Ketik nama barang / barcode lalu Enter:",
            placeholder="Contoh: Beras atau 899111",
            key="input_text_kasir",
            on_change=submit_teks,
        )

        buka_kamera = st.checkbox("📷 Buka Scanner", value=False, key="toggle_kamera_box")

        if buka_kamera:
            # key berubah tiap scan sukses -> scanner di-reset,
            # jadi barcode yang sama bisa discan berulang kali
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
            st.session_state.pesan = ("warning", f"⚠️ Produk '{keyword_aktif}' tidak ditemukan.")
        else:
            daftar = []
            for _, row in df_match.iterrows():
                harga = int(row[kolom_harga_pilihan])
                daftar.append((str(row[kolom_nama_barang]), harga))

            if len(daftar) == 1:
                pilih_produk(*daftar[0])
            else:
                st.session_state.pilihan = daftar
                st.session_state.pesan = ("info", f"Pilih yang mana nih '{keyword_aktif}':")

    # --- TAMPILKAN PESAN & PILIHAN ---
    if st.session_state.pesan:
        tipe, teks = st.session_state.pesan
        getattr(st, tipe)(teks)

    for i, (nm, hg) in enumerate(st.session_state.pilihan):
        st.button(
            f"➕ Tambah: {nm} - Rp {rp(hg)}",
            key=f"pilih_{i}",
            on_click=pilih_produk,
            args=(nm, hg),
        )

    if st.session_state.riwayat:
        st.button(
            "↩️ Batalkan Input Terakhir",
            on_click=batalkan_terakhir,
            help="Mengembalikan keranjang ke kondisi sebelum input terakhir (tambah barang, ubah Qty, hapus, atau kosongkan).",
        )

    st.divider()

    # ================= KERANJANG & NOTA =================
    if len(st.session_state.keranjang) > 0:
        st.subheader("🛒 Keranjang Belanja")
        df_keranjang = pd.DataFrame(st.session_state.keranjang)
        df_keranjang.index = range(1, len(df_keranjang) + 1)  # nomor urut mulai dari 1
        df_keranjang.index.name = "No"
        # Salinan khusus tampilan: harga dengan titik ribuan (data asli tetap angka)
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
                    "Qty", min_value=0, step=1, format="%d",
                    help="Klik lalu ketik jumlah. Isi 0 untuk menghapus barang.",
                ),
                "Harga Satuan": st.column_config.TextColumn("Harga Satuan"),
                "Subtotal": st.column_config.TextColumn("Subtotal"),
            },
            use_container_width=True,
        )

        subtotal_barang = int(df_keranjang["Subtotal"].sum())

        col_dk1, col_dk2, col_dk3 = st.columns(3)
        with col_dk1:
            diskon_input = st.number_input(
                "Diskon (Rp)", min_value=0, value=0, step=500, key="diskon_input",
                help="Kosongkan / isi 0 kalau tidak ada diskon. Tidak akan dicetak di nota jika 0.",
            )
        with col_dk2:
            ongkir = int(st.number_input(
                "Ongkir (Rp)", min_value=0, value=0, step=500, key="ongkir_input",
                help="Kosongkan / isi 0 kalau tidak ada ongkir. Tidak akan dicetak di nota jika 0.",
            ))
        with col_dk3:
            arisan = int(st.number_input(
                "Arisan (Rp)", min_value=0, value=0, step=1000, key="arisan_input",
                help="Isi nominal arisan secara manual. Kosongkan / isi 0 kalau tidak ada. Tidak akan dicetak di nota jika 0.",
            ))

        diskon = min(int(diskon_input), subtotal_barang)
        if int(diskon_input) > subtotal_barang:
            st.warning("⚠️ Diskon melebihi total belanja, jadi dihitung maksimal sebesar total belanja.")

        total_belanja_semua = subtotal_barang - diskon + ongkir + arisan
        st.metric(label="TOTAL", value=f"Rp {rp(total_belanja_semua)}")

        col_aksi1, col_aksi2 = st.columns(2)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum", key="nama_pelanggan_input")
        with col_aksi2:
            uang_tunai = st.number_input(
                "Bayar (Rp)", min_value=0, value=total_belanja_semua, step=5000, key=f"uang_tunai_{total_belanja_semua}"
            )

        # --- BATALKAN / HAPUS BARANG ---
        key_hapus = f"pilih_hapus_{st.session_state.editor_counter}"
        col_h1, col_h2 = st.columns([3, 2])
        with col_h1:
            st.selectbox(
                "❌ Pilih barang yang dibatalkan:",
                options=list(range(len(st.session_state.keranjang))),
                format_func=lambda i: f"{i + 1}. {st.session_state.keranjang[i]['Nama Barang']} (x{st.session_state.keranjang[i]['Qty']})",
                key=key_hapus,
            )
        with col_h2:
            st.write("")
            st.button(
                "❌ Hapus Barang",
                on_click=hapus_barang,
                args=(key_hapus,),
                use_container_width=True,
            )

        if not st.session_state.konfirmasi_kosong:
            st.button("🗑️ Kosongkan Semua Keranjang", type="secondary", on_click=minta_konfirmasi_kosong)
        else:
            st.warning("Yakin ingin mengosongkan SEMUA barang di keranjang?")
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                st.button("Ya, Kosongkan", type="primary", on_click=kosongkan_keranjang, use_container_width=True)
            with col_k2:
                st.button("Batal", on_click=batal_kosongkan, use_container_width=True)

        uang_kembalian = uang_tunai - total_belanja_semua

        st.divider()

        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        printer_width = 32

        def baris_kiri_kanan(label, val):
            space = printer_width - (len(label) + len(val))
            return label + (" " * max(1, space)) + val

        total_str = rp(total_belanja_semua)
        tunai_str = rp(uang_tunai)
        kembalian_str = rp(uang_kembalian)

        # Rincian (Subtotal/Diskon/Ongkir) hanya muncul kalau ada diskon atau ongkir
        rincian = []
        if diskon > 0 or ongkir > 0 or arisan > 0:
            rincian.append(("Subtotal", rp(subtotal_barang)))
            if diskon > 0:
                rincian.append(("Diskon", "-" + rp(diskon)))
            if ongkir > 0:
                rincian.append(("Ongkir", rp(ongkir)))
            if arisan > 0:
                rincian.append(("Arisan", rp(arisan)))


        # --- ESC/POS ---
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
        add_line(f"Kepada : {nama_pembeli} ({jenis_pelanggan})")
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
        raw_bytes.extend(CUT_PAPER)

        nama_file_bin = f"nota_{datetime.now().strftime('%d%m%y_%H%M%S')}.bin"

        # --- WHATSAPP ---
        pesan_wa = (
            "*NOTA BELANJA - TOKO JABON KIDUL SEPUR*\n"
            "----------------------------------\n"
            f"Tanggal : {waktu_sekarang}\n"
            f"Kepada : {nama_pembeli} ({jenis_pelanggan})\n"
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

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button(
                label="🖨️ Cetak Nota",
                data=bytes(raw_bytes),
                file_name=nama_file_bin,
                mime="application/octet-stream",
                use_container_width=True,
            )
        with col_btn2:
            st.markdown(f"""
<div style="text-align: center;">
    <a href="{whatsapp_url}" target="_blank" style="background-color: #25d366; color: white; padding: 10px 20px; text-decoration: none; font-size: 15px; border-radius: 4px; font-weight: bold; display: block; margin-top: 2px;">
        💬 Kirim via WhatsApp
    </a>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Keranjang masih kosong. Silakan ketik nama barang atau centang kamera untuk scan barcode.")
