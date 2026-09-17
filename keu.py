import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Aplikasi Kasir Toko Sembako", page_icon="🏪")

st.title("🏪 Kasir Toko Sembako (Multi-Level Pricing)")
st.markdown("Aplikasi Kasir dengan Harga Berdasarkan Jenis Pelanggan & Cetak Teks RawBT")

# --- LINK SPREADSHEET PERMANEN ---
PERMANENT_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIw6LgDSUn_lDlosWSAGQra0bR597E_Av6OYoo9uRpVr1P9ROMMgSaS_OSjp1Jj3Sp5GBRV01lIh0k/pub?output=csv"

# Inisialisasi Database Produk & Otomatis Tarik dari Link Permanen saat pertama kali buka / refresh
if "df_produk" not in st.session_state:
    try:
        st.session_state.df_produk = pd.read_csv(PERMANENT_CSV_URL)
    except:
        # Fallback cadangan jika koneksi gagal
        st.session_state.df_produk = pd.DataFrame({
            "Nama Barang": ["Beras Premium 1 Kg", "Minyak Goreng 1 Liter"],
            "Harga Umum": [15000, 17500],
            "Harga Reseller": [13500, 16000],
            "Harga Pengusaha": [12500, 15000]
        })

# Tombol untuk memperbarui/sinkronkan data jika sewaktu-waktu harga di spreadsheet berubah
if st.sidebar.button("🔄 Sinkronkan Ulang Data dari Spreadsheet"):
    try:
        df_cloud = pd.read_csv(PERMANENT_CSV_URL)
        df_cloud.columns = df_cloud.columns.str.strip()
        st.session_state.df_produk = df_cloud
        st.sidebar.success("Berhasil memperbarui data dari Google Sheets!")
    except Exception as e:
        st.sidebar.error(f"Gagal memuat data: {e}")

# Pastikan nama kolom standar aman
df_aktif_check = st.session_state.df_produk.copy()
df_aktif_check.columns = df_aktif_check.columns.str.strip()

# Deteksi nama kolom produk secara fleksibel
kolom_nama_opsi = ["Nama Barang", "nama barang", "Nama", "nama", "Produk", "produk"]
kolom_nama_barang = next((col for col in kolom_nama_opsi if col in df_aktif_check.columns), df_aktif_check.columns[0])

# Inisialisasi keranjang belanja
if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

tab1, tab2 = st.tabs(["🛒 Kasir & Keranjang", "📋 Kelola Daftar Harga"])

with tab2:
    st.subheader("Daftar Barang & Harga Bertingkat (Database)")
    st.dataframe(st.session_state.df_produk, use_container_width=True)
    st.info("💡 Data di atas terhubung otomatis dari Google Spreadsheet Anda. Jika mengubah harga di spreadsheet, klik tombol 'Sinkronkan Ulang Data' di menu samping kiri.")

with tab1:
    st.subheader("1. Pilih Jenis Pelanggan & Tambah Barang")
    
    # Pilihan Jenis Pelanggan untuk menentukan level harga
    jenis_pelanggan = st.selectbox(
        "🏷️ Pilih Level Harga / Jenis Pelanggan:", 
        ["Umum", "Reseller", "Pengusaha"]
    )
    
    # Deteksi kolom harga fleksibel di spreadsheet
    kolom_harga_pilihan = f"Harga {jenis_pelanggan}"
    if kolom_harga_pilihan not in df_aktif_check.columns:
        kolom_harga_pilihan = "Harga Umum" if "Harga Umum" in df_aktif_check.columns else df_aktif_check.columns[1]
    
    keyword_cari = st.text_input("🔍 Cari nama barang:", placeholder="Contoh: minyak, beras, gula...")
    
    df_produk_aktif = df_aktif_check.copy()
    
    if keyword_cari:
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
            st.toast(f"Berhasil menambahkan {pilihan_barang} ({jenis_pelanggan})!", icon="✅")
    else:
        st.warning("Barang tidak ditemukan.")

    st.divider()
    st.subheader("2. Keranjang Belanja")

    if len(st.session_state.keranjang) > 0:
        df_keranjang = pd.DataFrame(st.session_state.keranjang)
        st.dataframe(df_keranjang, use_container_width=True)

        total_belanja_semua = df_keranjang["Subtotal"].sum()
        st.metric(label="TOTAL YANG HARUS DIBAYAR", value=f"Rp {total_belanja_semua:,.0f}")

        col_aksi1, col_aksi2, col_aksi3 = st.columns(3)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum")
        with col_aksi2:
            uang_tunai = st.number_input("Uang Tunai (Rp)", min_value=0, value=int(total_belanja_semua), step=5000)
        with col_aksi3:
            st.write("")
            st.write("")
            if st.button("🗑️ Kosongkan Keranjang"):
                st.session_state.keranjang = []
                st.rerun()

        uang_kembalian = uang_tunai - total_belanja_semua

        if st.button("✨ Proses Nota Pembelian"):
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            printer_width = 32  # Lebar standar karakter printer thermal 58mm

            # --- PENYUSUNAN FORMAT TEKS STRUK ---
            lines = []
            
            # Header Toko (Center)
            lines.append("TOKO JABON KIDUL SEPUR".center(printer_width))
            lines.append("Jabon - Jombang".center(printer_width))
            lines.append("Tel. 0857 3395 8305".center(printer_width))
            lines.append("-" * printer_width)
            
            # Info Transaksi
            lines.append(f"Tgl : {waktu_sekarang}")
            lines.append(f"Plg : {nama_pembeli} ({jenis_pelanggan})")
            lines.append("-" * printer_width)
            
            # Daftar Barang
            for item in st.session_state.keranjang:
                lines.append(item['Nama Barang'])
                harga_str = f"{item['Harga Satuan']:,.0f}".replace(',', '.')
                sub_str = f"{item['Subtotal']:,.0f}".replace(',', '.')
                detail_kiri = f"{harga_str} x {item['Qty']} item"
                space_len = printer_width - (len(detail_kiri) + len(sub_str))
                lines.append(detail_kiri + (" " * max(1, space_len)) + sub_str)
                
            lines.append("-" * printer_width)
            
            # Ringkasan Pembayaran
            sub_total_str = f"{total_belanja_semua:,.0f}".replace(',', '.')
            tot_str = f"{total_belanja_semua:,.0f}".replace(',', '.')
            tunai_str = f"{uang_tunai:,.0f}".replace(',', '.')
            kembalian_str = f"{uang_kembalian:,.0f}".replace(',', '.')
            
            def add_row(label, val):
                space = printer_width - (len(label) + len(val))
                return label + (" " * max(1, space)) + val

            lines.append(add_row("Subtotal", sub_total_str))
            lines.append("-" * printer_width)
            lines.append(add_row("Total", tot_str))
            lines.append(add_row("Tunai", tunai_str))
            lines.append(add_row("Kembalian", kembalian_str))
            lines.append("-" * printer_width)
            
            # Footer (Center)
            lines.append("Terima Kasih".center(printer_width))
            lines.append("\n\n")

            teks_nota = "\n".join(lines)

            # --- BUAT LINK RAWBT TEXT ---
            encoded_text = urllib.parse.quote(teks_nota)
            rawbt_url = f"rawbt:data:text/plain;charset=utf-8,{encoded_text}"

            st.success("Nota teks berhasil dibuat!")

            # Tombol Cetak Teks via RawBT
            st.markdown(f"""
                <div style="text-align: center; margin-top: 15px;">
                    <a href="{rawbt_url}" target="_blank" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; font-size: 16px; border-radius: 6px; font-weight: bold; display: inline-block;">
                        🖨️ Cetak Nota Teks (Anti Blur & Tajam)
                    </a>
                </div>
            """, unsafe_allow_html=True)

    else:
        st.info("Keranjang masih kosong. Silakan cari dan tambah barang di atas.")
