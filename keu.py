import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

st.set_page_config(page_title="Aplikasi Keuangan & Kasir Toko Sembako", page_icon="🏪")

st.title("🏪 Kalkulator HPP & Kasir Multi-Item Toko Sembako")
st.markdown("Dilengkapi fitur pencarian, keranjang belanja, dan cetak nota PNG!")

# Inisialisasi Database Produk di session_state
if "df_produk" not in st.session_state:
    st.session_state.df_produk = pd.DataFrame({
        "Nama Barang": [
            "Beras Premium 1 Kg", 
            "Minyak Goreng 1 Liter", 
            "Gula Pasir 1 Kg", 
            "Telur Ayam 1 Kg", 
            "Kopi Bubuk 250g",
            "Tepung Terigu 1 Kg"
        ],
        "Harga Modal (HPP)": [13000, 15000, 14000, 24000, 12000, 10000],
        "Harga Jual": [15000, 17500, 16000, 27000, 15000, 12000]
    })

# Inisialisasi keranjang belanja
if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

tab1, tab2 = st.tabs(["🛒 Kasir & Keranjang Belanja", "📋 Kelola Daftar Harga & Stok"])

with tab2:
    st.subheader("Edit Daftar Barang, Modal, dan Harga Jual")
    st.markdown("💡 *Tips:* Kamu bisa **tambah baris baru** (klik `+`), **hapus baris**, atau **ketik langsung** di dalam tabel di bawah ini:")
    
    st.session_state.df_produk = st.data_editor(
        st.session_state.df_produk,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_produk"
    )

with tab1:
    st.subheader("1. Cari & Tambah Barang ke Keranjang")
    
    keyword_cari = st.text_input("🔍 Ketik nama barang yang dicari:", placeholder="Contoh: minyak, beras, gula...")
    
    df_produk_aktif = st.session_state.df_produk.copy()
    
    if keyword_cari:
        df_produk_aktif = df_produk_aktif[
            df_produk_aktif["Nama Barang"].str.contains(keyword_cari, case=False, na=False)
        ]
    
    if len(df_produk_aktif) > 0:
        col_input1, col_input2, col_input3 = st.columns([2, 1, 1])
        
        with col_input1:
            pilihan_barang = st.selectbox("Pilih Nama Barang Hasil Pencarian:", df_produk_aktif["Nama Barang"])
            data_terpilih = df_produk_aktif[df_produk_aktif["Nama Barang"] == pilihan_barang].iloc[0]
            harga_otomatis = int(data_terpilih["Harga Jual"])
        
        with col_input2:
            qty_pilih = st.number_input("Jumlah (Qty)", min_value=1, value=1)
            
        with col_input3:
            st.write("") 
            st.write("")
            tambah_btn = st.button("➕ Tambah ke Keranjang")

        if tambah_btn:
            subtotal = qty_pilih * harga_otomatis
            st.session_state.keranjang.append({
                "Nama Barang": pilihan_barang,
                "Qty": qty_pilih,
                "Harga Satuan": harga_otomatis,
                "Subtotal": subtotal
            })
            st.toast(f"Berhasil menambahkan {pilihan_barang} ke keranjang!", icon="✅")
    else:
        st.warning(f"Barang dengan kata kunci **'{keyword_cari}'** tidak ditemukan di daftar.")

    st.divider()
    st.subheader("2. Daftar Belanjaan (Keranjang)")

    if len(st.session_state.keranjang) > 0:
        df_keranjang = pd.DataFrame(st.session_state.keranjang)
        st.dataframe(df_keranjang, use_container_width=True)

        total_belanja_semua = df_keranjang["Subtotal"].sum()
        st.metric(label="TOTAL YANG HARUS DIBAYAR", value=f"Rp {total_belanja_semua:,.0f}")

        col_aksi1, col_aksi2 = st.columns(2)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum")
        with col_aksi2:
            st.write("")
            st.write("")
            reset_btn = st.button("🗑️ Kosongkan Keranjang")
            if reset_btn:
                st.session_state.keranjang = []
                st.rerun()

        if st.button("✨ Proses Nota Pembelian"):
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            st.success("Nota berhasil dibuat! Silakan download gambar nota di bawah ini untuk dicetak lewat aplikasi printer thermal HP.")

            # --- MEMBUAT GAMBAR PNG (RATA TENGAH / CENTERED) UTK DI-PRINT DI HP ---
            img_width, img_height = 450, 650 + (len(st.session_state.keranjang) * 50)
            img = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()

            def draw_center(y, text, f):
                bbox = draw.textbbox((0, 0), text, font=f)
                w = bbox[2] - bbox[0]
                x = (img_width - w) / 2
                draw.text((x, y), text, fill=(0, 0, 0), font=f)

            y_offset = 25
            lines_to_draw = [
                "========================================",
                "TOKO SEMBAKO BERKAH",
                "Jl. Raya Sembako No. 45, Jombang",
                "========================================",
                f"Tanggal  : {waktu_sekarang}",
                f"Pembeli  : {nama_pembeli}",
                "----------------------------------------"
            ]

            for line in lines_to_draw:
                draw_center(y_offset, line, font)
                y_offset += 25

            for item in st.session_state.keranjang:
                t1 = f"{item['Nama Barang']}"
                t2 = f"{item['Qty']} x Rp {item['Harga Satuan']:,.0f} = Rp {item['Subtotal']:,.0f}"
                draw_center(y_offset, t1, font)
                y_offset += 22
                draw_center(y_offset, t2, font)
                y_offset += 25
                draw_center(y_offset, "----------------------------------------", font)
                y_offset += 25

            footer_lines = [
                f"TOTAL    : Rp {total_belanja_semua:,.0f}",
                "========================================",
                "TERIMA KASIH TELAH BERBELANJA!",
                "========================================"
            ]

            for line in footer_lines:
                draw_center(y_offset, line, font)
                y_offset += 25

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()

            st.download_button(
                label="🖼️ Download Nota (Format Gambar .png)",
                data=byte_im,
                file_name=f"nota_{nama_pembeli}.png",
                mime="image/png"
            )
    else:
        st.info("Keranjang masih kosong. Silakan pilih barang di atas lalu klik 'Tambah ke Keranjang'.")