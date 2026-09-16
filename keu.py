import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Aplikasi Kasir Toko Sembako", page_icon="🏪")

st.title("🏪 Kasir Toko Sembako")
st.markdown("Aplikasi Kasir Praktis & Cetak Otomatis via RawBT")

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

        col_aksi1, col_aksi2 = st.columns(2)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum")
        with col_aksi2:
            st.write("")
            st.write("")
            if st.button("🗑️ Kosongkan Keranjang"):
                st.session_state.keranjang = []
                st.rerun()

        if st.button("✨ Proses Nota Pembelian"):
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Susun teks struk khusus printer thermal 58mm (lebar ~32 karakter)
            teks_struk = "================================\n"
            teks_struk += "       TOKO SEMBAKO BERKAH     \n"
            teks_struk += "     Jl. Raya Sembako Jombang   \n"
            teks_struk += "================================\n"
            teks_struk += f"Tgl : {waktu_sekarang}\n"
            teks_struk += f"Pelanggan : {nama_pembeli}\n"
            teks_struk += "--------------------------------\n"
            
            for item in st.session_state.keranjang:
                teks_struk += f"{item['Nama Barang']}\n"
                teks_struk += f"  {item['Qty']} x {item['Harga Satuan']:,.0f} = {item['Subtotal']:,.0f}\n"
                
            teks_struk += "--------------------------------\n"
            teks_struk += f"TOTAL: Rp {total_belanja_semua:,.0f}\n"
            teks_struk += "================================\n"
            teks_struk += "   TERIMA KASIH TELAH BELANJA   \n"
            teks_struk += "================================\n\n\n"

            st.success("Nota berhasil dibuat! Silakan klik tombol cetak di bawah.")

            # Encode teks agar aman dikirim ke URL RawBT
            encoded_text = urllib.parse.quote(teks_struk)
            rawbt_url = f"rawbt:data:text/plain;charset=utf-8,{encoded_text}"

            # Tombol Cetak langsung memicu aplikasi RawBT
            st.markdown(f"""
                <div style="text-align: center; margin-top: 15px;">
                    <a href="{rawbt_url}" target="_blank" style="background-color: #ff4b4b; color: white; padding: 12px 24px; text-decoration: none; font-size: 16px; border-radius: 6px; font-weight: bold; display: inline-block;">
                        🖨️ Cetak Langsung via RawBT
                    </a>
                </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("Keranjang masih kosong. Silakan cari dan tambah barang di atas.")