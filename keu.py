import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import streamlit.components.v1 as components

st.set_page_config(page_title="Aplikasi Kasir Toko Sembako", page_icon="🏪")

st.title("🏪 Kasir Toko Sembako (ESC/POS & Barcode Scanner)")
st.markdown("Aplikasi Kasir Cepat dengan Tombol Scanner Kamera Belakang & Pencocokan Barcode Otomatis")

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

# Deteksi kolom barcode (jika ada)
kolom_barcode_opsi = ["Barcode", "barcode", "SKU", "sku", "Kode", "kode"]
kolom_barcode = next((col for col in kolom_barcode_opsi if col in df_produk.columns), None)

if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

# Inisialisasi state untuk menampung hasil scan barcode
if "scanned_barcode" not in st.session_state:
    st.session_state.scanned_barcode = ""

# Tangkap hasil scan dari URL parameter jika ada
query_params = st.query_params
if "scan" in query_params:
    val_scan = query_params["scan"]
    if val_scan != st.session_state.scanned_barcode:
        st.session_state.scanned_barcode = val_scan
        st.query_params.clear()
        st.rerun()

tab1, tab2 = st.tabs(["🛒 Kasir & Keranjang", "📋 Daftar Harga (Database)"])

with tab2:
    st.subheader("Daftar Barang & Harga Bertingkat (Google Sheets)")
    st.info("💡 Pastikan ada kolom 'Barcode' di Google Spreadsheet Anda untuk pencocokan pemindai.")
    
    search_database = st.text_input("🔍 Cari produk di database:", placeholder="Ketik nama barang atau barcode...", key="search_db")
    
    df_database_tampil = df_produk.copy()
    if search_database:
        mask = df_database_tampil.astype(str).apply(lambda x: x.str.contains(search_database, case=False, na=False)).any(axis=1)
        df_database_tampil = df_database_tampil[mask]
    
    st.dataframe(df_database_tampil, use_container_width=True)

with tab1:
    st.subheader("1. Pilih Jenis Pelanggan & Tambah Barang")
    
    jenis_pelanggan = st.selectbox(
        "🏷️ Pilih Level Harga / Jenis Pelanggan:", 
        ["Umum", "Bakul", "Umum Antar", "Usaha"]
    )
    
    kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
    if kolom_harga_pilihan not in df_produk.columns:
        kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]
    
    # --- TOMBOL SCANNER KAMERA BELAKANG YANG RINGKAS & STABIL ---
    st.markdown("📷 **Scanner Barcode (Kamera Belakang)**")
    
    scanner_html = f"""
    <div>
        <button id="open-btn" onclick="startScanner()" style="background-color: #2baf2b; color: white; border: none; padding: 8px 14px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 13px;">📷 Buka Kamera Scanner</button>
        <button id="close-btn" onclick="stopScanner()" style="background-color: #ff4b4b; color: white; border: none; padding: 8px 14px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 13px; display: none;">🛑 Tutup Kamera</button>
        
        <div id="reader" style="width: 100%; max-width: 320px; margin-top: 10px;"></div>
    </div>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
        let html5QrCode;
        function startScanner() {{
            document.getElementById('open-btn').style.display = 'none';
            document.getElementById('close-btn').style.display = 'block';
            
            html5QrCode = new Html5Qrcode("reader");
            html5QrCode.start(
                {{ facingMode: "environment" }},
                {{ fps: 15, qrbox: {{ width: 220, height: 110 }} }},
                (decodedText, decodedResult) => {{
                    stopScanner();
                    window.location.href = window.location.pathname + "?scan=" + encodeURIComponent(decodedText);
                }},
                (errorMessage) => {{}}
            ).catch((err) => {{
                alert("Gagal membuka kamera belakang: " + err);
                stopScanner();
            }});
        }}
        
        function stopScanner() {{
            if (html5QrCode) {{
                html5QrCode.stop().then(() => {{
                    document.getElementById('open-btn').style.display = 'block';
                    document.getElementById('close-btn').style.display = 'none';
                }}).catch(err => {{
                    document.getElementById('open-btn').style.display = 'block';
                    document.getElementById('close-btn').style.display = 'none';
                }});
            }} else {{
                document.getElementById('open-btn').style.display = 'block';
                document.getElementById('close-btn').style.display = 'none';
            }}
        }}
    </script>
    """
    components.html(scanner_html, height=260)

    # Kotak input pencarian (Nilai otomatis terisi jika ada hasil scan dari kamera)
    keyword_cari = st.text_input(
        "🔍 Cari nama barang atau Scan Barcode:", 
        value=st.session_state.scanned_barcode, 
        placeholder="Ketik nama barang / hasil scan barcode..."
    )
    
    # Sinkronisasi manual jika user mengetik ulang
    if keyword_cari != st.session_state.scanned_barcode and not query_params:
        st.session_state.scanned_barcode = keyword_cari

    df_produk_aktif = df_produk.copy()
    
    if keyword_cari:
        if kolom_barcode and kolom_barcode in df_produk_aktif.columns:
            match_barcode = df_produk_aktif[df_produk_aktif[kolom_barcode].astype(str).str.contains(keyword_cari, case=False, na=False)]
            if len(match_barcode) > 0:
                df_produk_aktif = match_barcode
            else:
                df_produk_aktif = df_produk_aktif[
                    df_produk_aktif[kolom_nama_barang].astype(str).str.contains(keyword_cari, case=False, na=False)
                ]
        else:
            df_produk_aktif = df_produk_aktif[
                df_produk_aktif[kolom_nama_barang].astype(str).str.contains(keyword_cari, case=False, na=False)
            ]
    
    if len(df_produk_aktif) > 0:
        col_input1, col_input2, col_input3 = st.columns([2, 1, 1])
        
        with col_input1:
            pilihan_barang = st.selectbox("Pilih Barang:", df_produk_aktif[kolom_nama_barang])
            data_terpilih = df_produk_aktif[df_produk_aktif[kolom_nama_barang] == pilihan_barang].iloc[0]
            
            harga_otomatis = int(data_terpilih[kolom_harga_pilihan])
            st.caption(f"Harga Satuan ({jenis_pelanggan}): Rp {harga_otomatis:,.0f}".replace(',', '.'))
        
        with col_input2:
            qty_pilih = st.number_input("Jumlah (Qty)", min_value=1, value=1)
            
        with col_input3:
            st.write("") 
            st.write("")
            tambah_btn = st.button("➕ Tambah")

        if tambah_btn:
            subtotal = qty_pilih * harga_otomatis
            st.session_state.keranjang.append({
                "Nama Barang": pilihan_barang,
                "Qty": qty_pilih,
                "Harga Satuan": harga_otomatis,
                "Subtotal": subtotal
            })
            st.session_state.scanned_barcode = ""
            st.toast(f"Berhasil menambahkan {pilihan_barang} ({jenis_pelanggan})!", icon="✅")
    else:
        st.warning("Barang atau Barcode tidak ditemukan di database.")
        if st.button("🔄 Reset Pencarian"):
            st.session_state.scanned_barcode = ""
            st.rerun()

    st.divider()
    st.subheader("2. Keranjang Belanja")

    if len(st.session_state.keranjang) > 0:
        df_keranjang = pd.DataFrame(st.session_state.keranjang)
        st.dataframe(df_keranjang, use_container_width=True)

        total_belanja_semua = df_keranjang["Subtotal"].sum()
        st.metric(label="TOTAL YANG HARUS DIBAYAR", value=f"Rp {total_belanja_semua:,.0f}")

        col_aksi1, col_aksi2 = st.columns(2)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum", key="nama_pelanggan_input")
        with col_aksi2:
            uang_tunai = st.number_input("Uang Tunai (Rp)", min_value=0, value=int(total_belanja_semua), step=5000)

        if st.button("🗑️ Kosongkan Keranjang", type="secondary"):
            st.session_state.keranjang = []
            st.rerun()

        uang_kembalian = uang_tunai - total_belanja_semua

        st.divider()
        st.subheader("👀 Pratinjau (Preview) Nota")

        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        printer_width = 32  # Lebar standar karakter printer thermal 58mm

        # --- PENYUSUNAN STRUK TEKS UNTUK PREVIEW ---
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
            lines_preview.append("") # Spasi antar barang

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

        # --- PEMBUATAN BYTE ESC/POS UNTUK RAWBT ---
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

        # --- BUAT NAMA FILE UNIK BERDASARKAN WAKTU ---
        timestamp_file = datetime.now().strftime("%d%m%y_%H%M%S")
        nama_file_bin = f"nota_{timestamp_file}.bin"

        # --- BUAT LINK WHATSAPP ---
        pesan_wa = f"*NOTA BELANJA - TOKO JABON KIDUL SEPUR*\n" \
                   f"----------------------------------\n" \
                   f"Tanggal : {waktu_sekarang}\n" \
                   f"Kepada : {nama_pembeli} ({jenis_pelanggan})\n" \
                   f"----------------------------------\n"
        for item in st.session_state.keranjang:
            pesan_wa += f"• {item['Nama Barang']}\n  {item['Harga Satuan']:,.0f} x {item['Qty']} = *Rp {item['Subtotal']:,.0f}*\n\n".replace(',', '.')
        pesan_wa += f"----------------------------------\n" \
                    f"Total    : *Rp {total_belanja_semua:,.0f}*\n" \
                    f"Tunai    : Rp {uang_tunai:,.0f}\n" \
                    f"Kembalian: Rp {uang_kembalian:,.0f}\n" \
                    f"----------------------------------\n" \
                    f"Terima Kasih & Semoga Berkah".replace(',', '.')
        
        encoded_wa = urllib.parse.quote(pesan_wa)
        whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_wa}"

        # Tombol Aksi Akhir
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
        st.info("Keranjang masih kosong. Silakan cari dan tambah barang di atas.")
