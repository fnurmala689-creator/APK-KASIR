import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import streamlit.components.v1 as components

st.set_page_config(page_title="Aplikasi Kasir Toko Sembako", page_icon="🏪")

# --- 1. JUDUL ---
st.title("🏪 Kasir Toko Sembako")

# --- 2. SUBJUDUL ---
st.markdown("Aplikasi Kasir Cepat dengan Scanner Kamera & Pencarian Manual")

# --- LINK SPREADSHEET PERMANEN ---
PERMANENT_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIw6LgDSUn_lDlosWSAGQra0bR597E_Av6OYoo9uRpVr1P9ROMMgSaS_OSjp1Jj3Sp5GBRV01lIh0k/pub?output=csv"

try:
    df_produk = pd.read_csv(PERMANENT_CSV_URL)
except Exception as e:
    df_produk = pd.DataFrame({
        "Barcode": ["899111", "899222"],
        "Nama Barang": ["Beras Premium 1 Kg", "Minyak Goreng 1 Liter"],
        "Harga Umum": [15000, 17500],
        "Harga Reseller": [13500, 16000],
        "Harga Pengusaha": [12500, 15000]
    })

df_produk.columns = df_produk.columns.str.strip()

# Deteksi kolom nama barang
kolom_nama_opsi = ["Nama Barang", "nama barang", "Nama", "nama", "Produk", "produk"]
kolom_nama_barang = next((col for col in kolom_nama_opsi if col in df_produk.columns), df_produk.columns[0])

# Deteksi kolom barcode
kolom_barcode_opsi = ["Barcode", "barcode", "SKU", "sku", "Kode", "kode"]
kolom_barcode = next((col for col in kolom_barcode_opsi if col in df_produk.columns), None)

if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

if "scan_trigger" not in st.session_state:
    st.session_state.scan_trigger = ""

# Tangkap parameter URL jika ada kiriman dari scanner
query_params = st.query_params
if "scan" in query_params:
    st.session_state.scan_trigger = query_params["scan"].strip()
    st.query_params.clear()
    st.rerun()

tab1, tab2 = st.tabs(["🛒 Kasir & Keranjang", "📋 Daftar Harga (Database)"])

with tab2:
    st.subheader("Daftar Barang & Harga Bertingkat (Google Sheets)")
    search_database = st.text_input("🔍 Cari produk di database:", placeholder="Ketik nama barang atau barcode...", key="search_db")
    
    df_database_tampil = df_produk.copy()
    if search_database:
        mask = df_database_tampil.astype(str).apply(lambda x: x.str.contains(search_database, case=False, na=False)).any(axis=1)
        df_database_tampil = df_database_tampil[mask]
    
    st.dataframe(df_database_tampil, use_container_width=True)

with tab1:
    # --- 3. PILIH JENIS PELANGGAN ---
    jenis_pelanggan = st.selectbox(
        "🏷️ Pilih Level Harga / Jenis Pelanggan:", 
        ["Umum", "Bakul", "Umum Antar", "Usaha"],
        key="pilih_level_harga"
    )
    
    kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
    if kolom_harga_pilihan not in df_produk.columns:
        kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]
    
    # --- 4. INPUT PENCARIAN & KAMERA DALAM EXPANDER ---
    status_buka_expander = len(st.session_state.keranjang) == 0
    
    with st.expander("🔍 Klik untuk Cari Barang / Buka Scanner Kamera", expanded=status_buka_expander):
        input_keyword = st.text_input(
            "Ketik nama barang / barcode lalu Enter:",
            placeholder="Contoh: Beras atau 899111",
            key="input_text_kasir"
        )

        col_cam_btn1, col_cam_btn2 = st.columns([1, 4])
        with col_cam_btn1:
            buka_kamera = st.checkbox("📷 Buka Kamera Scanner", value=False, key="toggle_kamera_box")

        if buka_kamera:
            scanner_html = """
            <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #ced4da; text-align: center; margin-bottom: 10px;">
                <div id="reader" style="width: 100%; max-width: 350px; margin: 0 auto;"></div>
                <p style="font-size: 12px; color: #666; margin-top: 5px;">Arahkan kamera ke barcode produk</p>
            </div>
            <script src="https://unpkg.com/html5-qrcode"></script>
            <script>
                let scannerRunning = false;
                function onScanSuccess(decodedText, decodedResult) {
                    if (!scannerRunning) {
                        scannerRunning = true;
                        window.location.href = window.location.pathname + "?scan=" + encodeURIComponent(decodedText);
                    }
                }
                try {
                    let html5QrCode = new Html5Qrcode("reader");
                    html5QrCode.start(
                        { facingMode: "environment" },
                        { fps: 20, qrbox: { width: 250, height: 100 } },
                        onScanSuccess,
                        (errorMessage) => {}
                    ).catch(err => { console.log(err); });
                } catch(e) {}
            </script>
            """
            components.html(scanner_html, height=220)

    # --- 5. PEMROSESAN OTOMATIS KERANJANG ---
    keyword_aktif = ""
    if st.session_state.scan_trigger:
        keyword_aktif = st.session_state.scan_trigger
        st.session_state.scan_trigger = "" 
    elif 'input_text_kasir' in st.session_state and st.session_state.input_text_kasir:
        keyword_aktif = st.session_state.input_text_kasir.strip()
        # Bersihkan input text agar tidak melooping terus menerus
        st.session_state.input_text_kasir = ""

    if keyword_aktif:
        df_match = pd.DataFrame()

        if kolom_barcode and kolom_barcode in df_produk.columns:
            df_match = df_produk[df_produk[kolom_barcode].astype(str).str.strip() == keyword_aktif]

        if len(df_match) == 0:
            df_match = df_produk[df_produk[kolom_nama_barang].astype(str).str.contains(keyword_aktif, case=False, na=False)]

        if len(df_match) > 0:
            if len(df_match) == 1:
                data_terpilih = df_match.iloc[0]
                nama_barang_ditemukan = data_terpilih[kolom_nama_barang]
                harga_otomatis = int(data_terpilih[kolom_harga_pilihan])

                sudah_ada = False
                for item in st.session_state.keranjang:
                    if item["Nama Barang"] == nama_barang_ditemukan and item["Harga Satuan"] == harga_otomatis:
                        item["Qty"] += 1
                        item["Subtotal"] = item["Qty"] * item["Harga Satuan"]
                        sudah_ada = True
                        break
                
                if not sudah_ada:
                    st.session_state.keranjang.append({
                        "Nama Barang": nama_barang_ditemukan,
                        "Qty": 1,
                        "Harga Satuan": harga_otomatis,
                        "Subtotal": harga_otomatis
                    })

                st.success(f"✅ Berhasil masuk keranjang: **{nama_barang_ditemukan}** (Rp {harga_otomatis:,.0f})".replace(',', '.'))
            else:
                st.info(f"Ditemukan beberapa produk untuk '{keyword_aktif}':")
                for idx, row in df_match.iterrows():
                    nm = row[kolom_nama_barang]
                    hg = int(row[kolom_harga_pilihan])
                    if st.button(f"➕ Tambah: {nm} - Rp {hg:,.0f}".replace('.',''), key=f"pilih_{idx}"):
                        sudah_ada = False
                        for item in st.session_state.keranjang:
                            if item["Nama Barang"] == nm and item["Harga Satuan"] == hg:
                                item["Qty"] += 1
                                item["Subtotal"] = item["Qty"] * item["Harga Satuan"]
                                sudah_ada = True
                                break
                        if not sudah_ada:
                            st.session_state.keranjang.append({
                                "Nama Barang": nm,
                                "Qty": 1,
                                "Harga Satuan": hg,
                                "Subtotal": hg
                            })
                        st.rerun()
        else:
            st.warning(f"⚠️ Produk '{keyword_aktif}' tidak ditemukan.")

    st.divider()

    # --- TAMPILAN KERANJANG & NOTA ---
    if len(st.session_state.keranjang) > 0:
        st.subheader("🛒 Keranjang Belanja")
        df_keranjang = pd.DataFrame(st.session_state.keranjang)
        st.dataframe(df_keranjang, use_container_width=True)

        total_belanja_semua = df_keranjang["Subtotal"].sum()
        st.metric(label="TOTAL YANG HARUS DIBAYAR", value=f"Rp {total_belanja_semua:,.0f}")

        col_aksi1, col_aksi2 = st.columns(2)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum", key="nama_pelanggan_input")
        with col_aksi2:
            uang_tunai = st.number_input("Uang Tunai (Rp)", min_value=0, value=int(total_belanja_semua), step=5000, key="uang_tunai_input")

        if st.button("🗑️ Kosongkan Keranjang", type="secondary"):
            st.session_state.keranjang = []
            st.rerun()

        uang_kembalian = uang_tunai - total_belanja_semua

        st.divider()
        st.subheader("👀 Pratinjau (Preview) Nota")

        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        printer_width = 32

        lines_preview = []
        lines_preview.append("TOKO JABON KIDUL SEPUR")
        lines_preview.append("Jabon - Jombang")
        lines_preview.append("Telp. 0857 3395 8305")
        lines_preview.append("-" * printer_width)
        lines_preview.append(f"Tanggal : {waktu_sekarang}")
        lines_preview.append(f"Kepada : {nama_pembeli} ({jenis_pelanggan})")
        lines_preview.append("-" * printer_width)

        for item in st.session_state.keranjang:
            lines_preview.append(item['Nama Barang'])
            harga_str = f"{item['Harga Satuan']:,.0f}".replace(',', '.')
            sub_str = f"{item['Subtotal']:,.0f}".replace(',', '.')
            detail_kiri = f"{harga_str} x {item['Qty']} item"
            space_len = printer_width - (len(detail_kiri) + len(sub_str))
            lines_preview.append(detail_kiri + (" " * max(1, space_len)) + sub_str)
            lines_preview.append("")

        lines_preview.append("-" * printer_width)
        
        def add_row_preview(label, val):
            space = printer_width - (len(label) + len(val))
            return label + (" " * max(1, space)) + val

        sub_total_str = f"{total_belanja_semua:,.0f}".replace(',', '.')
        tot_str = f"{total_belanja_semua:,.0f}".replace(',', '.')
        tunai_str = f"{uang_tunai:,.0f}".replace(',', '.')
        kembalian_str = f"{uang_kembalian:,.0f}".replace(',', '.')

        lines_preview.append(add_row_preview("Subtotal", sub_total_str))
        lines_preview.append("-" * printer_width)
        lines_preview.append(add_row_preview("Total", tot_str))
        lines_preview.append(add_row_preview("Tunai", tunai_str))
        lines_preview.append(add_row_preview("Kembalian", kembalian_str))
        lines_preview.append("-" * printer_width)
        lines_preview.append("Terima Kasih & Semoga Berkah")

        teks_preview_html = "\n".join(lines_preview)

        st.markdown(f"""
            <div style="background-color: #f8f9fa; border: 1px dashed #6c757d; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; font-size: 13px; color: #000; max-width: 400px; margin: 0 auto; text-align: center;">
{teks_preview_html}
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        # --- PEMBUATAN BYTE ESC/POS & WHATSAPP ---
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
            if bold:
                raw_bytes.extend(BOLD_ON)
            else:
                raw_bytes.extend(BOLD_OFF)
            raw_bytes.extend((text + "\n").encode('utf-8'))

        add_line("TOKO JABON KIDUL SEPUR", ALIGN_CENTER, bold=True)
        add_line("Jabon - Jombang", ALIGN_CENTER)
        add_line("Telp. 0857 3395 8305", ALIGN_CENTER)
        add_line("-" * printer_width, ALIGN_CENTER)
        add_line(f"Tanggal : {waktu_sekarang}", ALIGN_LEFT)
        add_line(f"Kepada : {nama_pembeli} ({jenis_pelanggan})", ALIGN_LEFT)
        add_line("-" * printer_width, ALIGN_CENTER)

        for item in st.session_state.keranjang:
            add_line(item['Nama Barang'], ALIGN_LEFT, bold=True)
            harga_str = f"{item['Harga Satuan']:,.0f}".replace(',', '.')
            sub_str = f"{item['Subtotal']:,.0f}".replace(',', '.')
            detail_kiri = f"{harga_str} x {item['Qty']} item"
            space_len = printer_width - (len(detail_kiri) + len(sub_str))
            baris_item = detail_kiri + (" " * max(1, space_len)) + sub_str
            add_line(baris_item, ALIGN_LEFT)
            add_line("")

        add_line("-" * printer_width, ALIGN_CENTER)

        def add_row_bytes(label, val, is_bold=False):
            space = printer_width - (len(label) + len(val))
            row_text = label + (" " * max(1, space)) + val
            add_line(row_text, ALIGN_LEFT, bold=is_bold)

        add_row_bytes("Subtotal", sub_total_str)
        add_line("-" * printer_width, ALIGN_CENTER)
        add_row_bytes("Total", tot_str, is_bold=True)
        add_row_bytes("Tunai", tunai_str)
        add_row_bytes("Kembalian", kembalian_str)
        add_line("-" * printer_width, ALIGN_CENTER)
        
        raw_bytes.extend(ALIGN_CENTER)
        raw_bytes.extend(BOLD_ON)
        raw_bytes.extend(b"Terima Kasih & Semoga Berkah")
        raw_bytes.extend(BOLD_OFF)
        raw_bytes.extend(CUT_PAPER)

        timestamp_file = datetime.now().strftime("%d%m%y_%H%M%S")
        nama_file_bin = f"nota_{timestamp_file}.bin"

        pesan_wa = f"*NOTA BELANJA - TOKO JABON KIDUL SEPUR*\n" \
                   f"----------------------------------\n" \
                   f"Tanggal : {waktu_sekarang}\n" \
                   f"Kepada : {nama_pembeli} ({jenis_pelanggan})\n" \
                   f"----------------------------------\n"
        for item in st.session_state.keranjang:
            pesan_wa += f"• {item['Nama Barang']}\n  {item['Harga Satuan']:,.0f} x {item['Qty']} = *Rp {item['Subtotal']:,.0f}*\n\n".replace(',', '.')
        pessan_wa_final = pesan_wa + f"----------------------------------\n" \
                    f"Total    : *Rp {total_belanja_semua:,.0f}*\n" \
                    f"Tunai    : Rp {uang_tunai:,.0f}\n" \
                    f"Kembalian: Rp {uang_kembalian:,.0f}\n" \
                    f"----------------------------------\n" \
                    f"Terima Kasih & Semoga Berkah".replace(',', '.')
        
        encoded_wa = urllib.parse.quote(pessan_wa_final)
        whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_wa}"

        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            st.download_button(
                label="🖨️ Cetak Nota ESC/POS",
                data=bytes(raw_bytes),
                file_name=nama_file_bin,
                mime="application/octet-stream",
                use_container_width=True
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
