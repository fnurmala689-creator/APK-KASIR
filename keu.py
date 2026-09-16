import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import base64

st.set_page_config(page_title="Aplikasi Kasir Toko Sembako", page_icon="🏪")

st.title("🏪 Kasir Toko Sembako")
st.markdown("Aplikasi Kasir Praktis & Cetak Gambar via RawBT (Thermal 58mm)")

# Inisialisasi Database Produk
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

tab1, tab2 = st.tabs(["🛒 Kasir & Keranjang", "📋 Kelola Daftar Harga"])

with tab2:
    st.subheader("Edit Daftar Barang dan Harga Jual")
    st.session_state.df_produk = st.data_editor(
        st.session_state.df_produk,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_produk"
    )

with tab1:
    st.subheader("1. Cari & Tambah Barang")
    
    keyword_cari = st.text_input("🔍 Cari nama barang:", placeholder="Contoh: minyak, beras, gula...")
    
    df_produk_aktif = st.session_state.df_produk.copy()
    
    if keyword_cari:
        df_produk_aktif = df_produk_aktif[
            df_produk_aktif["Nama Barang"].str.contains(keyword_cari, case=False, na=False)
        ]
    
    if len(df_produk_aktif) > 0:
        col_input1, col_input2, col_input3 = st.columns([2, 1, 1])
        
        with col_input1:
            pilihan_barang = st.selectbox("Pilih Barang:", df_produk_aktif["Nama Barang"])
            data_terpilih = df_produk_aktif[df_produk_aktif["Nama Barang"] == pilihan_barang].iloc[0]
            harga_otomatis = int(data_terpilih["Harga Jual"])
        
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
            st.toast(f"Berhasil menambahkan {pilihan_barang}!", icon="✅")
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

            # --- PENGATURAN KANVAS & FONT PAS PERSIS CONTOH (58MM) ---
            canvas_width = 192  # Lebar standar mutlak printer thermal 58mm
            margin_left = 5  
            margin_right = 5
            
            estimated_height = 1000 + (len(st.session_state.keranjang) * 120)
            img = Image.new("RGB", (canvas_width, estimated_height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            try:
                # Menyesuaikan ukuran agar presisi dengan cetakan thermal kasir
                font = ImageFont.truetype("arial.ttf", 60)         # Teks biasa / detail tanggal & telp
                font_bold = ImageFont.truetype("arial.ttf", 62)    # Nama barang & angka rincian
                font_title = ImageFont.truetype("arial.ttf", 64)   # Judul toko
            except:
                font = ImageFont.load_default()
                font_bold = ImageFont.load_default()
                font_title = ImageFont.load_default()

            def draw_center(y, text, f):
                bbox = draw.textbbox((0, 0), text, font=f)
                w = bbox[2] - bbox[0]
                x = (canvas_width - w) / 2
                draw.text((x, y), text, fill=(0, 0, 0), font=f)

            y_offset = 5 

            # Header Toko (Rata Tengah)
            draw_center(y_offset, "TOKO JABON KIDUL SEPUR", font_title)
            y_offset += 15
            draw_center(y_offset, "Jabon - Jombang", font)
            y_offset += 15
            draw_center(y_offset, "Tel. 0857 3395 8305", font)
            y_offset += 15
            draw_center(y_offset, "----------------------------------------------------------------", font)
            y_offset += 18

            # Info Transaksi (Rata Kiri)
            draw.text((margin_left, y_offset), f"Tgl : {waktu_sekarang}", fill=(0, 0, 0), font=font)
            y_offset += 15
            draw.text((margin_left, y_offset), f"Pelanggan: {nama_pembeli}", fill=(0, 0, 0), font=font)
            y_offset += 15
            draw_center(y_offset, "----------------------------------------------------------------", font)
            y_offset += 18

            # Daftar Barang (Format persis contoh: Nama barang di atas, Harga x Qty di kiri & Subtotal di kanan)
            for item in st.session_state.keranjang:
                draw.text((margin_left, y_offset), f"{item['Nama Barang']}", fill=(0, 0, 0), font=font_bold)
                y_offset += 15
                
                detail_kiri = f"{item['Harga Satuan']:,.0f} x {item['Qty']} item".replace(',', '.')
                detail_kanan = f"{item['Subtotal']:,.0f}".replace(',', '.')
                
                draw.text((margin_left, y_offset), detail_kiri, fill=(0, 0, 0), font=font)
                
                bbox_kanan = draw.textbbox((0, 0), detail_kanan, font=font)
                w_kanan = bbox_kanan[2] - bbox_kanan[0]
                x_kanan = canvas_width - margin_right - w_kanan
                draw.text((x_kanan, y_offset), detail_kanan, fill=(0, 0, 0), font=font)
                y_offset += 18

            draw_center(y_offset, "----------------------------------------------------------------", font)
            y_offset += 18

            # Ringkasan Total, Tunai, Kembalian (Format Sejajar Kiri-Kanan)
            items_ringkasan = [
                ("Subtotal", f"{total_belanja_semua:,.0f}".replace(',', '.')),
                ("Total", f"{total_belanja_semua:,.0f}".replace(',', '.')),
                ("Tunai", f"{uang_tunai:,.0f}".replace(',', '.')),
                ("Kembalian", f"{uang_kembalian:,.0f}".replace(',', '.'))
            ]

            for label_txt, nilai_txt in items_ringkasan:
                if label_txt == "Subtotal":
                    draw.text((margin_left, y_offset), label_txt, fill=(0, 0, 0), font=font)
                    bbox_val = draw.textbbox((0, 0), nilai_txt, font=font)
                    w_val = bbox_val[2] - bbox_val[0]
                    x_val = canvas_width - margin_right - w_val
                    draw.text((x_val, y_offset), nilai_txt, fill=(0, 0, 0), font=font)
                    y_offset += 15
                    draw_center(y_offset, "----------------------------------------------------------------", font)
                    y_offset += 18
                else:
                    is_bold = label_txt == "Total"
                    f_used = font_bold if is_bold else font
                    
                    draw.text((margin_left, y_offset), label_txt, fill=(0, 0, 0), font=f_used)
                    bbox_val = draw.textbbox((0, 0), nilai_txt, font=f_used)
                    w_val = bbox_val[2] - bbox_val[0]
                    x_val = canvas_width - margin_right - w_val
                    draw.text((x_val, y_offset), nilai_txt, fill=(0, 0, 0), font=f_used)
                    y_offset += 15

            draw_center(y_offset, "----------------------------------------------------------------", font)
            y_offset += 18

            # Footer
            draw_center(y_offset, "Terima Kasih", font_bold)
            y_offset += 15

            img_final = img.crop((0, 0, canvas_width, y_offset + 10))

            buf = io.BytesIO()
            img_final.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            base64_img = base64.b64encode(byte_im).decode('utf-8')
            rawbt_url = f"rawbt:data:image/png;base64,{base64_img}"

            st.success("Struk berhasil dicetak!")

            st.markdown(f"""
                <div style="text-align: center; margin-top: 15px;">
                    <a href="{rawbt_url}" target="_blank" style="background-color: #ff4b4b; color: white; padding: 12px 24px; text-decoration: none; font-size: 16px; border-radius: 6px; font-weight: bold; display: inline-block;">
                        🖨️ Cetak Struk (Kirim ke RawBT)
                    </a>
                </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label="📥 Download Gambar Nota (.png)",
                data=byte_im,
                file_name=f"nota_{nama_pembeli}.png",
                mime="image/png"
            )
    else:
        st.info("Keranjang masih kosong. Silakan cari dan tambah barang di atas.")
